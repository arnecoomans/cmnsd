import os
from django.conf import settings
from django.core.checks import register, Warning


@register()
def check_cmnsd_config(app_configs, **kwargs):
    """
    Central cmnsd system check:
    - Ensure cmnsd templatetags are added to builtins.
    - Ensure required settings are present.
    - Ensure i18n is available as a builtin.
    """
    warnings = []

    # --- 1. Check cmnsd templatetags ---
    app_dir = os.path.dirname(__file__)
    templatetags_dir = os.path.join(app_dir, "templatetags")

    builtin_tags = (
        settings.TEMPLATES[0]
        .get("OPTIONS", {})
        .get("builtins", [])
    )

    if os.path.isdir(templatetags_dir):
        for filename in os.listdir(templatetags_dir):
            if filename.endswith(".py") and filename not in ("__init__.py",):
                module_name = f"cmnsd.templatetags.{filename[:-3]}"
                if module_name not in builtin_tags:
                    warnings.append(
                        Warning(
                            f"Templatetag '{module_name}' is not in TEMPLATES[0]['OPTIONS']['builtins'].",
                            hint=f"Add '{module_name}' to builtins in settings.py if you want it always available.",
                            id="cmnsd.W001",
                        )
                    )

    # --- 2. Check required settings ---
    required_settings = [
        "DEFAULT_MODEL_STATUS",
        "DEFAULT_MODEL_VISIBILITY",
        "SITE_NAME",
        "META_DESCRIPTION",
        "LANGUAGE_CODE",
        "SEARCH_QUERY_CHARACTER",
        "SEARCH_EXCLUDE_CHARACTER",
        "SEARCH_MIN_LENGTH",
        "AJAX_DEFAULT_DATA_SOURCES",
        "AJAX_RENDER_REMOVE_NEWLINES",
        "AJAX_PROTECTED_FIELDS",
        "AJAX_RESTRICTED_FIELDS",
        "AJAX_BLOCKED_MODELS",
        "AJAX_ALLOW_FK_CREATION_MODELS",
        "AJAX_ALLOW_RELATED_CREATION_MODELS",
        "AJAX_MAX_DEPTH_RECURSION",
    ]
    for setting in required_settings:
        if not hasattr(settings, setting):
            warnings.append(
                Warning(
                    f"Missing setting: {setting}",
                    hint=f"Define {setting} in settings.py to configure cmnsd properly.",
                    id="cmnsd.W002",
                )
            )

    # --- 3. Check i18n availability ---
    if "django.templatetags.i18n" not in builtin_tags:
        warnings.append(
            Warning(
                "The 'i18n' template tag library is not in builtins.",
                hint="Add 'django.templatetags.i18n' to "
                     "TEMPLATES[0]['OPTIONS']['builtins'] in settings.py "
                     "so {% trans %} and {% blocktrans %} work everywhere without {% load i18n %}.",
                id="cmnsd.W003",
            )
        )

    return warnings
