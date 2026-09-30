# Architecture Brief — CMNSD + FMLY 3.0

## Context
Two related projects, greenfield (no existing database, no migration
constraints):

- **CMNSD** — a shared/reusable Django app providing base models, base
  methods, a dynamic API layer, and a JS library, consumed by multiple
  applications.
- **FMLY 3.0** — a ground-up rebuild of fmly.cmns.nl, a family archive
  (~200 people, ~300 content items), consuming CMNSD. Current pain: the
  site is organized around individual records, making it easy to get lost.
  The rebuild shifts the center of gravity toward curated stories, with
  individual records as the supporting layer underneath.

This brief is the implementation reference for both. Where a design point
is still open, it's marked explicitly — don't invent an answer, flag it.

---

## Part 1 — CMNSD

### 1.1 Base functionality as composable mixins, not one BaseModel
The old `BaseModel` bundled token, status, timestamps, ownership, and
search helpers into a single abstract class every model inherited
wholesale. Replace it with independent abstract mixins, composed per
model:

```python
class TimestampMixin(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class TokenMixin(models.Model):
    generate_public_id = generate_public_id  # class attribute so migrations
                                               # serialize the default correctly
    token = models.CharField(
        max_length=20, unique=True, editable=False, blank=True,
        default=generate_public_id,
        help_text=_("Short unique ID for public URL / API use"),
    )
    class Meta:
        abstract = True

    def _generate_unique_public_id(self):
        for _ in range(10):
            pid = generate_public_id()
            if not self.__class__.objects.filter(token=pid).exists():
                return pid
        return generate_public_id(15)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self._generate_unique_public_id()
        super().save(*args, **kwargs)


class StatusMixin(models.Model):
    class Status(models.TextChoices):
        CONCEPT = 'c', _('Concept')
        PUBLISHED = 'p', _('Published')
        REVOKED = 'r', _('Revoked')
        DELETED = 'x', _('Deleted')

    status = models.CharField(
        max_length=1, choices=Status.choices,
        default=getattr(settings, 'CMNSD_DEFAULT_MODEL_STATUS', Status.PUBLISHED),
    )
    class Meta:
        abstract = True

    @classmethod
    def filter_status(cls, queryset, request=None):
        if not request and hasattr(cls, 'request'):
            request = cls.request
        if request and request.user.is_authenticated:
            if request.user.is_staff:
                return queryset.filter(models.Q(status='p') | models.Q(status='c') | models.Q(status='r'))
            return queryset.filter(models.Q(status='p') | models.Q(status='c', user=request.user))
        return queryset.filter(status='p')


class OwnershipMixin(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="%(class)s_created_by",
    )
    class Meta:
        abstract = True


class VisibilityMixin(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = 'p', _('Private')
        FAMILY = 'f', _('Family')
        # ... remaining values per current system
    visibility = models.CharField(max_length=1, choices=Visibility.choices, default='p')
    class Meta:
        abstract = True

    def is_visible_to(self, user):
        if self.visibility == 'f':
            if self.user_id == user.pk:
                return True
            manager = self._resolve_family_manager()
            if manager is None:
                return False
            return user in manager.all()
        # ... other visibility branches

    def _resolve_family_manager(self):
        lookup = type(self)._family_lookup_path(type(self))
        if not lookup:
            return None
        obj = self
        for part in lookup.split('__'):
            obj = getattr(obj, part, None)
            if obj is None:
                return None
        return obj

    @classmethod
    def _family_lookup_path(cls, model):
        lookup = getattr(settings, 'CMNSD_VISIBILITY_FAMILY_LOOKUP_STORAGE', None)
        if lookup and cls._lookup_path_exists(model, lookup):
            return lookup
        return None

    @classmethod
    def filter_visibility(cls, queryset, request=None):
        if request and request.user.is_authenticated:
            user = request.user
            q = (
                models.Q(visibility='p') |
                models.Q(visibility='c') |
                models.Q(visibility='f', user=user) |
                models.Q(visibility='q', user=user)
            )
            family_lookup = cls._family_lookup_path(queryset.model)
            if family_lookup:
                q |= models.Q(visibility='f', **{family_lookup: user})
            return queryset.filter(q)
        return queryset.filter(visibility='p')


class SearchableMixin(models.Model):
    """No field footprint — safe to include on any model."""
    class Meta:
        abstract = True

    def __str__(self):
        return getattr(self, 'name', f"{self.__class__.__name__} ({self.pk})")

    @classmethod
    def get_optimized_queryset(cls):
        return cls.objects.all()

    @classmethod
    def get_model_fields(cls):
        return [f.name for f in cls._meta.get_fields()]

    @classmethod
    def get_searchable_fields(cls):
        fields = [f.name for f in cls._meta.get_fields()]
        functions = [name for name, func in getmembers(cls, predicate=isfunction)
                     if getattr(func, "is_searchable", False)]
        return fields + functions
```

Rules for composing mixins on a concrete model:
- Only inherit the mixins a model actually needs — a model without
  meaningful "draft vs published" semantics simply doesn't inherit
  `StatusMixin`, rather than inheriting it and being told to ignore it.
- A model that needs status-like behavior but with different choices
  (e.g. `ResearchQuestion` using open/answered instead of
  concept/published/revoked/deleted) does **not** inherit `StatusMixin` —
  it defines its own `status` field directly. Mixin composition *is* the
  capability declaration; there's no separate override flag needed for
  this case.
- Any mixin overriding `save()` must call `super().save(*args, **kwargs)`
  so multiple `save()`-overriding mixins chain correctly through the MRO.
- `Meta.abstract = True` does not propagate — every mixin declares its
  own; a concrete model combining `Meta` options from a mixin must
  subclass that `Meta` explicitly or declare its own from scratch.

### 1.2 Dynamic API: capability detection + registry decorators
Goal: the API layer accesses models dynamically — no hardcoded per-model
API code. Two mechanisms work together:

**Capability detection is duck-typed, not field-name-matched.** A model
has the "visibility capability" if it exposes `is_visible_to` /
`filter_visibility`, regardless of whether that came from `VisibilityMixin`
or a hand-rolled implementation:

```python
def detect_capabilities(model_cls):
    caps = {}
    if hasattr(model_cls, 'is_visible_to') and hasattr(model_cls, 'filter_visibility'):
        caps['visibility'] = 'field-agnostic'
    if hasattr(model_cls, 'get_status_display_choices'):
        caps['status'] = 'field-agnostic'
    return caps
```

**Explicit registration via decorators** marks a model as API-accessible
and controls whether CMNSD's default capability logic should be applied:

```python
API_REGISTRY = {}

def api_model(name=None, *, status=True, visibility=True):
    """
    True  (default) = auto-detect via duck-typing, apply CMNSD default logic if found
    False            = capability may be present but API should not apply CMNSD's
                        default interpretation of it (e.g. overridden choices)
    'field_name'     = capability lives under a non-standard field/attribute name
    """
    def decorator(model_cls):
        entry = API_REGISTRY.setdefault(model_cls, {
            "name": name or model_cls._meta.model_name,
            "capabilities": {}, "fields": {}, "actions": {},
        })
        detected = detect_capabilities(model_cls)
        for cap, requested in (('status', status), ('visibility', visibility)):
            if requested is False:
                continue
            if isinstance(requested, str):
                entry["capabilities"][cap] = {"field": requested, "apply_default_logic": False}
            elif cap in detected:
                entry["capabilities"][cap] = {"field": cap, "apply_default_logic": True}

        for attr_name, attr in vars(model_cls).items():
            if hasattr(attr, "_api_field"):
                entry["fields"][attr_name] = attr._api_field
            if hasattr(attr, "_api_action"):
                entry["actions"][attr_name] = attr._api_action
        return model_cls
    return decorator


def api_field(*, readonly=True, label=None):
    def decorator(func):
        func._api_field = {"readonly": readonly, "label": label}
        return func
    return decorator


def api_action(*, requires_auth=True):
    def decorator(method):
        method._api_action = {"requires_auth": requires_auth}
        return method
    return decorator
```

**Import timing:** `API_REGISTRY` must only be read after all app models
are loaded. Build/validate it in `AppConfig.ready()`, or lazily on first
API access — never at API-app import time, or the registry will be
partially populated depending on app load order.

**No implicit exposure:** `@api_model` should not auto-expose all model
fields by default. Every exposed field needs an explicit `@api_field`.
Given `VisibilityMixin` exists specifically to restrict access, a
"default to open" API would eventually leak something meant to stay
family-only.

### 1.3 API security: no bare-ID lookups
Every API object lookup requires the pk **plus** a slug or token — never
pk alone (prevents ID-enumeration / IDOR). Reads may use slug or token;
writes (PUT/PATCH/DELETE) specifically require the token, since a slug is
already public/discoverable in URLs and isn't sufficient authorization
for a mutation.

```python
class SecureLookupMixin:
    def get_lookup_kwargs(self):
        pk = self.kwargs.get('pk')
        if not pk:
            raise Http404("An ID is required.")

        model = self.get_queryset().model
        token = self.kwargs.get('token') or self.request.query_params.get('token')
        slug = self.kwargs.get('slug')
        write_action = self.request.method in ('PUT', 'PATCH', 'DELETE')

        if write_action:
            if not (token and hasattr(model, 'token')):
                raise PermissionDenied("A token is required to modify this record.")
            return {'pk': pk, 'token': token}

        if slug and hasattr(model, 'slug'):
            return {'pk': pk, 'slug': slug}
        if token and hasattr(model, 'token'):
            return {'pk': pk, 'token': token}
        raise Http404("An ID plus a slug or token is required.")

    def get_object(self):
        obj = get_object_or_404(self.filter_queryset(self.get_queryset()), **self.get_lookup_kwargs())
        self.check_object_permissions(self.request, obj)
        return obj
```

Enforce this as a startup check, not a runtime surprise — any model
registered via `@api_model` without `token` or `slug` should fail
`manage.py check`:

```python
@register()
def check_api_lookup_fields(app_configs, **kwargs):
    errors = []
    for model_cls in API_REGISTRY:
        if not (hasattr(model_cls, 'token') or hasattr(model_cls, 'slug')):
            errors.append(Error(
                f"{model_cls.__name__} is registered via @api_model but has neither "
                "'token' nor 'slug' — API lookups require ID plus one of these.",
                id="cmnsd.api.E001",
            ))
    return errors
```

Apply the same "fail at check-time, not request-time" pattern to any
other CMNSD-wide required setting (mail backend config, etc.) via
`checks.py`.

**Open decision:** does every model that's API-registered get
`TokenMixin`, or only ones with a genuine public-facing identity (e.g.
`Content`, `Storyline` — not pure through-models like `Mention`)? Resolve
per-model during implementation using the check above as the forcing
function.

---

## Part 2 — FMLY 3.0

### 2.1 App layout
One app per cohesive domain, not per model:

- **`content`** — `Content`, `Kind`, per-kind detail models
  (`PhotoContent`, `BookContent`, `AttachmentContent`, `NoteContent`, ...),
  `Mention` (lives here since most mentions target Content, avoiding a
  circular dependency with `stories`)
- **`people`** — `Person`, `Relationship`
- **`places`** — `Location`
- **`timeline`** (or `events`) — `Event`
- **`stories`** — `Storyline`, `ResearchQuestion`
- **`core`** — cross-cutting pieces not specific to one domain (`Tag`, etc.)

Project-level package should not be named `fmly` if an app is also named
`fmly` — keep the product name free of Python import collisions.

### 2.2 Content model
Single storage point for every uploaded file; type-specific behavior
lives in separate detail models, not subclasses (avoids multi-table
inheritance's join overhead and rigid single-type-per-row constraint).

```python
class Content(TimestampMixin, TokenMixin, StatusMixin, OwnershipMixin,
              VisibilityMixin, SearchableMixin, models.Model):
    class Kind(models.TextChoices):
        PHOTO = "photo", _("Photo")
        SCAN = "scan", _("Scan")
        DOCUMENT = "document", _("Document")
        BOOK = "book", _("Book")
        ATTACHMENT = "attachment", _("Attachment")
        PODCAST = "podcast", _("Podcast")
        FILM = "film", _("Film")
        NOTE = "note", _("Note")

    class UploadStatus(models.TextChoices):
        DRAFT = "draft", _("Draft")
        COMPLETE = "complete", _("Complete")

    file = models.FileField(upload_to="content/%Y/")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    upload_status = models.CharField(max_length=10, choices=UploadStatus.choices, default=UploadStatus.DRAFT)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    date_created_content = models.DateField(null=True, blank=True)  # date the *content* is from, distinct from TimestampMixin's date_created

    def get_detail(self):
        return CONTENT_KIND_REGISTRY.get(self.kind)
```

Per-kind detail models attach via
`OneToOneField(Content, related_name="<kind>_detail")`. Register them
explicitly so a missing detail model is caught at check-time:

```python
CONTENT_KIND_REGISTRY = {}

def register_content_kind(kind):
    def decorator(model_cls):
        CONTENT_KIND_REGISTRY[kind] = model_cls
        return model_cls
    return decorator

@register_content_kind(Content.Kind.PHOTO)
class PhotoContent(models.Model):
    content = models.OneToOneField(Content, on_delete=models.CASCADE, related_name="photo_detail")
    # sorl-thumbnail applied to Content.file directly, crop/portrait settings
    # defined once here and inherited by every kind rather than per-type
```

**Draft flow:** a Content row can be created from just a dropped file
(`upload_status=draft`, `kind` guessed from mimetype), completed later —
supports "drop image into draft, fill in from there."

**Thumbnails:** sorl-thumbnail wired on `Content.file` from the start;
crop/portrait settings defined once, inherited by every kind.

### 2.3 Person + relationships
- `Relationship`: explicit `Person A is parent/partner of Person B`.
- `children` = reverse of `parent`.
- `siblings` = derived from shared parents, not stored (cheap at ~200
  people, avoids a second source of truth).
- New quick-add/edit flow: fill in more Person data immediately on
  creation rather than a bare stub.

### 2.4 Event + Location
```python
class Location(TimestampMixin, TokenMixin, models.Model):
    name = models.CharField(max_length=255)
    # open decision: flat label vs. hierarchy (city -> region -> country)
    # vs. coordinates for a future map view — decide once browse/search
    # UI is scoped


class Event(TimestampMixin, TokenMixin, models.Model):
    class Kind(models.TextChoices):
        BIRTH = "birth", _("Birth")
        DEATH = "death", _("Death")
        MARRIAGE = "marriage", _("Marriage")
        OTHER = "other", _("Other")

    kind = models.CharField(max_length=20, choices=Kind.choices)
    date = models.DateField(null=True, blank=True)
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL)
    persons = models.ManyToManyField(Person, related_name="events")
```

Event's existing optional link to Content ("proof") is generalized into
`Mention` (below) rather than kept as a bespoke field.

### 2.5 Mention (generalized link table)
Replaces one-off relations (Content↔Person, Content↔Event "proof",
Storyline references) with one queryable table, so "what does X
reference" / "what references X" is a single uniform query regardless of
type:

```python
class Mention(models.Model):
    class Role(models.TextChoices):
        SUBJECT = "subject", _("Subject")
        AUTHOR = "author", _("Author")
        MENTIONED = "mentioned", _("Mentioned")
        PROOF = "proof", _("Proof")

    source_content_type = models.ForeignKey(ContentType, related_name="+", on_delete=models.CASCADE)
    source_id = models.PositiveIntegerField()
    source = GenericForeignKey("source_content_type", "source_id")

    target_content_type = models.ForeignKey(ContentType, related_name="+", on_delete=models.CASCADE)
    target_id = models.PositiveIntegerField()
    target = GenericForeignKey("target_content_type", "target_id")

    role = models.CharField(max_length=20, choices=Role.choices, blank=True)
```
`source` is typically a `Storyline` or a `Content` item; `target` is a
`Person`, `Event`, `Content`, or `ResearchQuestion`.

### 2.6 Storyline
Narrative-first: a markdown body with inline references, not a bag of
M2M fields — matches the "shift focus toward stories" goal directly.

```python
class Storyline(TimestampMixin, TokenMixin, VisibilityMixin, models.Model):
    title = models.CharField(max_length=255)
    body = models.TextField()  # markdown with [[kind:id]] reference tokens
```

- References are inserted via a search-and-pick UI control that drops in
  a fixed-format token, e.g. `[[person:42]]` — not free-typed `@mention`
  autocomplete. This keeps parsing deterministic: a small markdown
  extension renders tokens as links; a regex pass on save populates the
  `Mention` table.
- Free-typed `@name` autocomplete is a possible later upgrade once the
  picker-based version is in use and the friction is actually felt —
  **do not build it first.**

### 2.7 ResearchQuestion
Own model, not just inline text, so it's trackable on the dashboard:

```python
class ResearchQuestion(TimestampMixin, models.Model):
    text = models.TextField()
    status = models.CharField(max_length=20, choices=[('open', _('Open')), ('answered', _('Answered'))])
    tags = models.ManyToManyField("core.Tag", blank=True)
```
Note: deliberately does **not** inherit `StatusMixin` — different choice
set. A `ResearchQuestion` is itself a valid `Mention` target.

---

## Build order
1. **Content** — base model, `Kind`, per-kind detail models, draft
   status, sorl-thumbnail wiring, `CONTENT_KIND_REGISTRY`.
2. **Person + Relationship** — confirm derived siblings, build the
   quick-add/edit flow.
3. **Event + Location** — introduce `Location`; connect Event to Content
   via `Mention` (role=`proof`).
4. **CMNSD mixins finalized** (Visibility, Status, Token, etc.) and
   applied across Person/Content/Storyline.
5. **Mention + Storyline** — link table, reference picker UI, markdown
   rendering.
6. **ResearchQuestion** — tracking, tagging, dashboard surface.
7. **CMNSD API layer** — `@api_model`/`@api_field`/`@api_action`
   registry, capability detection, secure lookup enforcement, checks.
8. **Search + Dashboard** — indexing across Person/Content/Event/
   Storyline, recently-viewed / current-interest views.
9. **Text recognition (OCR)** — applied to Content once storage is
   stable.

## Open decisions (not yet settled — do not assume an answer)
- Location: flat label vs. hierarchy vs. coordinates.
- Storyline references: picker-inserted tokens (current plan) vs.
  free-typed `@mention` — revisit only after the picker version ships.
- Which models get `TokenMixin`: every `@api_model`-registered model, or
  only ones with genuine public-facing identity?
- Whether `TimestampMixin` should be applied via explicit inheritance
  per model, or granted automatically to anything decorated with
  `@api_model`.
