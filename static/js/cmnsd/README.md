
# cmnsd JavaScript Framework

The **cmnsd** framework provides dynamic JSON-based content loading, form actions, and autosuggest functionality for Django-based applications.  

---

## 🚀 Autosuggest Component

The `autosuggest.js` script adds smart suggestions to any input field using declarative `data-*` attributes.

### ✅ Features
- Dynamic AJAX fetching (`api.get`)
- Multi-field display in suggestions (`data-display-fields`)
- Configurable click-follow behavior (`data-onclick-follow`)
- Intelligent field submission logic (hidden vs visible fields)
- Keyboard navigation (↑ ↓ Enter Esc)
- Automatic re-initialization on `cmnsd:content:applied`
- Configurable debounce, minimum characters, and custom parameters
- Optional `data-field-prefix` for related/nested fields

---

## ⚙️ Data Attributes Reference

| Attribute | Default | Description |
|------------|----------|-------------|
| `data-autosuggest` | *(required)* | Enables autosuggest on the input. |
| `data-url` | *(required)* | JSON endpoint for fetching suggestions. |
| `data-param` | `q` | Query parameter name for search term. |
| `data-min` | `2` | Minimum characters before search triggers. |
| `data-debounce` | `300` | Debounce delay (ms) between keystrokes and API calls. |
| `data-container` | *(none)* | If the payload has nested data, specify the container key. |
| `data-field-input` | `name` | Field name for visible input value. |
| `data-field-hidden` | `slug` | Field name for hidden field (ID or slug). |
| `data-field-prefix` | *(none)* | Prefix added to both field names for related/nested fields (e.g., `link__`). |
| `data-display-fields` | `name` | Comma-separated fields shown in the suggestion list (first = main, rest = secondary). |
| `data-display-secondary-size` | `0.8` | Font-size multiplier for secondary fields. |
| `data-onclick-follow` | *(none)* | When set to `url`, follows the suggestion’s URL instead of inserting value. |
| `data-allow-create` | `1` | When `0`, only allows selecting valid suggestions (disables free text). |
| `data-extra-params` | *(none)* | JSON string of additional query parameters to include in requests. |
| `data-search-mode` | `false` | If true, retains `name='q'` for standard search forms. |

---

## 💡 Example Usages

### 🔹 Default
```html
<input
  data-autosuggest
  data-url="/json/tags/"
  data-field-input="name"
  data-field-hidden="id">
```

### 🔹 Display multiple fields
```html
<input
  data-autosuggest
  data-url="/json/links/"
  data-field-input="name"
  data-field-hidden="id"
  data-display-fields="name,url"
  data-display-secondary-size="0.8">
```

### 🔹 Follow URL on click
```html
<input
  data-autosuggest
  data-url="/json/locations/"
  data-field-input="name"
  data-field-hidden="id"
  data-onclick-follow="url">
```

### 🔹 Nested prefix
```html
<input
  data-autosuggest
  data-url="/json/links/"
  data-field-input="name"
  data-field-hidden="id"
  data-field-prefix="link__">
```

---

## 💅 Optional CSS
```css
.cmnsd-autosuggest .autosuggest-main {
  font-weight: 500;
  line-height: 1.2;
}

.cmnsd-autosuggest .autosuggest-secondary {
  color: #666;
  line-height: 1.1;
  font-size: 0.8em;
}

.cmnsd-autosuggest .list-group-item.active {
  background-color: var(--bs-primary);
  color: white;
}
```
