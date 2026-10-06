# cmnsd.css

cmnsd's own stylesheets, in `static/cmnsd.css/`: only what cmnsd's own markup can't do without. Everything else - layout, edit blocks, sections, pickers - is the project's CSS: cmnsd ships markup and class names, the project decides the look.

## The files

| File | For |
|---|---|
| `messages.css` | The message area (`cmnsd/messages.html`, cmnsd.js `messages.js`) |
| `cmnsd.branding.css` | The Inter and Geist fonts, and the "powered by cmnsd" mark |
| `branding/*.png` | The cmnsd logos: `cmnsd.png`, and one each for `cmnsd_js`, `cmnsd_model`, `cmnsd_ui`, `cmnsd_ajax` |

```django
<link rel="stylesheet" href="{% static 'cmnsd.css/messages.css' %}">
<link rel="stylesheet" href="{% static 'cmnsd.css/cmnsd.branding.css' %}">
```

## Messages

A stack of small notices, fixed top right below the header, each with a coloured edge by level: `.cmnsd-message--success`, `--info`, `--warning`, `--error`, `--debug`. Successes fade by themselves (`.is-leaving`); errors stay until closed.

The colours come from the project's design tokens when it defines them, with neutral fallbacks, so the file works unchanged in any project:

| Token | Used for |
|---|---|
| `--color-surface`, `--color-ink`, `--color-ink-3`, `--color-border` | The notice and its close button |
| `--color-complete-text`, `--color-accent`, `--color-draft-text`, `--color-draft-soft` | Success, info, warning and error |
| `--radius-md`, `--shadow-modal`, `--text-sm` | Shape and size |

The stack sits at `top: 76px`, below a header of that height. A project with another header overrides `.cmnsd-messages { top: ... }`.

## Branding

`@font-face` rules for **Inter** (variable) and **Geist** / **Geist Mono**, loaded from `static/fonts/` - include the file to use them as `font-family: 'Inter'` or `'Geist'`.

And the cmnsd mark, for a footer:

```html
Powered by <span class="cmnsd"><span class="cmnsd-square"></span> cmnsd</span>
and <span class="cmnsd js"><span class="cmnsd-square"></span> cmnsd.js</span>
```

`{ ◆ } cmnsd` in green; `js`, `api`, `css` and `ui` colour the diamond blue, orange, purple and grey.

## Adding to it

A rule belongs here only when cmnsd's own markup is unusable without it in every project, like the message area. Use the project's tokens with a fallback (`var(--color-accent, #3a6ea5)`), never fixed colours alone. Prefix classes with `cmnsd-`.
