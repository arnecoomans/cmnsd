# cmnsd JavaScript Framework

This is a lightweight JavaScript framework built to handle AJAX-based content loading,
message rendering, action delegation, and autosuggest inputs in Django projects.

## Features

- **Core**: Central init and configuration handling.
- **HTTP**: Fetch wrapper with automatic CSRF handling.
- **DOM**: Helpers for injecting, updating, and inserting content. Dispatches `cmnsd:content:applied` events.
- **Actions**: Delegated event handling for `[data-action]` elements and forms.
- **Loader**: Generic JSON loader for mapping payload fragments into containers.
- **Messages**: Bootstrap-styled message rendering with auto-dismiss and stacking.
- **Autosuggest**: Adds autosuggest/searchable dropdown functionality for inputs with `[data-autosuggest]`.

## Autosuggest usage

### Free text + suggestions
```html
<input
  type="text"
  class="form-control"
  placeholder="Enter or select a tag..."
  data-autosuggest
  data-url="/json/tags/"
  data-container="tags"
  data-field-input="name"
  data-field-hidden="slug"
/>
```

- Free text allowed.
- Hidden field `slug` is submitted if suggestion chosen; otherwise the typed value.

### Searchable dropdown (no free text allowed)
```html
<input
  type="text"
  class="form-control"
  placeholder="Select a size..."
  data-autosuggest
  data-url="/json/sizes/"
  data-container="sizes"
  data-field-input="name"
  data-field-hidden="id"
  data-min="0"
  data-allow-create="0"
/>
```

- Starts with all options (`data-min="0"` fetches empty query).
- Only valid suggestions allowed (`data-allow-create="0"`).
- Submit button is disabled until a valid option is chosen.

### Free text allowed, but not empty
- Default behavior (`data-allow-create` missing or not `"0"`) allows free text entry.
- Submit button is disabled if input is empty.

## Messages
- Messages are shown in a floating container (configurable in `init`).
- Stacked up to a configurable max (default 5).
- Automatically dismissed after type-dependent timeout.

## Example Init

```js
cmnsd.init({
  baseURL: '',
  debug: true,
  messages: { container: '#messages', dismissible: true, clearBefore: false, max: 5 },
  actions: { autoBind: true },
  onError: (err) => console.error('cmnsd global error handler', err)
});

// Initialize autosuggest
import { initAutosuggest } from "/static/js/cmnsd/autosuggest.js";
initAutosuggest();
```

## Notes
- Requires Bootstrap 5 for styling of messages and autosuggest dropdowns.
- Designed for Django with CSRF support out of the box.
- All framework code was created using ChatGPT collaboration.
