# cmnsd JavaScript Framework — v2.0.0

Lightweight modular JavaScript framework for Django-based applications.  
Provides unified handling for AJAX requests, dynamic DOM updates, autosuggest fields, and contextual message rendering.

---

## 🧩 Overview

cmnsd enables declarative AJAX and UI interaction directly through HTML `data-*` attributes.  
It is built around the following components:

| Module | Purpose |
|--------|----------|
| `core.js` | Framework initialization, global config, debugging |
| `http.js` | Wrapper around `fetch()` for JSON GET/POST/PATCH/DELETE |
| `dom.js` | Safe DOM insertion, update, and event delegation |
| `loader.js` | Batch content loading via one JSON payload |
| `actions.js` | Delegated AJAX handling and clipboard actions |
| `messages.js` | Bootstrap-compatible message display |
| `autosuggest.js` | Dynamic and local autosuggest support |

---

## ⚙️ Initialization

```js
import cmnsd from "/static/js/cmnsd/index.js";
import { initAutosuggest } from "/static/js/cmnsd/autosuggest.js";

cmnsd.init({
  baseURL: '',
  debug: true,
  messages: { container: '#messages', dismissible: true, clearBefore: false, max: 5 },
  actions: { autoBind: true }
});

// Optional autosuggest initialization
initAutosuggest();
```

---

## 🧠 Core Concepts

### 1. AJAX Actions

Elements with `data-action` trigger asynchronous requests or special operations.

#### Example: Standard AJAX update

```html
<button
  data-action
  data-url="/json/location/1/update/"
  data-method="PATCH"
  data-params='{"status":"active"}'
  data-map='{"details":"#details"}'>
  Update
</button>
```

#### Example: Form with AJAX submit

```html
<form
  data-action
  data-method="POST"
  data-body="form"
  data-map='{"comments":"#comments"}'>
  <input name="comment" type="text" placeholder="Write comment...">
  <button type="submit" class="btn btn-primary">Send</button>
</form>
```

#### Example: Copy to clipboard

```html
<button data-action="copy" data-text="Hello world" data-message="Copied!">
  Copy text
</button>

<pre id="snippet">console.log("Example");</pre>
<button data-action="copy" data-clipboard-target="#snippet">
  Copy code
</button>
```

---

### 2. Autosuggest

The autosuggest system binds to any input with `data-autosuggest`.  
It supports both remote (AJAX) and local (embedded JSON) suggestion sources.

#### Example: Remote

```html
<input
  type="text"
  data-autosuggest
  data-url="/json/tags/"
  data-param="q"
  data-field-input="name"
  data-field-hidden="slug"
  data-container="tag"
  placeholder="Type to search...">
```

#### Example: Local list

```html
<input
  type="text"
  data-autosuggest
  data-local-source='[{"slug":"alice","name":"Alice"},{"slug":"bob","name":"Bob"}]'
  data-field-input="name"
  data-field-hidden="slug"
  placeholder="Search user...">
```

#### Example: Follow URL on click

```html
<input
  type="text"
  data-autosuggest
  data-url="/json/locations/"
  data-onclick-follow="url">
```

#### Example: Multi-field display

```html
<input
  type="text"
  data-autosuggest
  data-url="/json/links/"
  data-display-fields="name,url"
  data-display-secondary-size="0.8">
```

#### Example: Autosuggest with search restrictions

```html
<input
  type="text"
  data-autosuggest
  data-url="/json/locations/"
  data-min="2"
  data-allow-create="0">
```

#### Example: Info box
```html
<button
  data-action="info"
  data-title="About Location"
  data-url="/ajax/location/1/info/"
  data-placement="right"
>
  Show Info
</button>
````
or
```html
<button
  data-action="info"
  data-title="Details"
  data-info="<p>This feature displays an <b>HTML-enabled</b> info box without needing an AJAX request.</p>"
>
  ℹ️ Info
</button>
```
---

### 3. Messages

Server messages are normalized and displayed in a configurable container.

#### Example response
```json
{
  "messages": [
    {"level": "success", "message": "Item saved."},
    {"level": "warning", "message": "Some fields were skipped."}
  ]
}
```

#### Bootstrap message container

```html
<div id="messages" class="position-fixed top-0 w-100 p-3"></div>
```

---

## 🧱 Data Attribute Reference

| Attribute | Default | Applies to | Description |
|------------|----------|-------------|-------------|
| **`data-action`** | – | button, form, link | Enables AJAX or special action handling |
| **`data-action=info`** | – | button, form, link | when clicked, an info box appears |
| **`data-url`** | – | all | Target URL for AJAX request |
| **`data-method`** | `POST` | all | HTTP method (`GET`, `POST`, `PATCH`, `DELETE`) |
| **`data-params`** | – | all | JSON or querystring params |
| **`data-map`** | – | all | Maps payload keys to DOM selectors |
| **`data-body`** | – | form | Defines body type: `"form"` or JSON string |
| **`data-disable`** | – | all | Temporarily disables element during request |
| **`data-confirm`** | – | all | Optional confirm dialog before request |
| **`data-refresh-url`** | – | all | Secondary request triggered after completion |
| **`data-refresh-map`** | – | all | Map for refresh content |
| **`data-refresh-mode`** | `update` | all | How refreshed data is applied (`insert` or `update`) |
| **`data-autosuggest`** | – | input | Enables autosuggest on this field |
| **`data-url`** | – | input | Source URL for suggestions |
| **`data-param`** | `q` | input | Query parameter name |
| **`data-extra-params`** | – | input | JSON-encoded extra parameters |
| **`data-local-source`** | – | input | JSON array for local suggestions |
| **`data-field-input`** | `name` | input | Name for submitted visible field |
| **`data-field-hidden`** | `slug` | input | Name for submitted hidden value |
| **`data-container`** | – | input | Optional payload subkey |
| **`data-min`** | `2` | input | Min characters before fetch |
| **`data-force-unique`** | - | input | In the results, force unique results for this field |
| **`data-debounce`** | `300` | input | Delay before fetch in ms |
| **`data-allow-create`** | `1` | input | Whether custom text can be submitted |
| **`data-onclick-follow`** | – | input | Follow `url` on suggestion click |
| **`data-display-fields`** | `name` | input | Comma-separated list of fields to show |
| **`data-display-secondary-size`** | `0.8` | input | Font scale for secondary display fields |
| **`data-message`** | `"Copied to clipboard."` | copy action | Custom message for clipboard |
| **`data-text`** | – | copy action | Direct text to copy |
| **`data-clipboard-target`** | – | copy action | Selector of element whose text/value to copy |
| **`data-title`** | – | info overlay | Direct text to copy |
| **`data-url`** | – | info overlay | Source of data to show on overlay |
| **`data-info`** | – | info overlay | Local source of data to show on overlay |
| **`data-placement`** | right left top botoom | info overlay | Direct text to copy |
---

## 🧩 Events

| Event | Triggered when | Detail payload |
|--------|----------------|----------------|
| `cmnsd:content:applied` | New content inserted or replaced | `{ container: HTMLElement }` |
| `cmnsd:autosuggest:selected` | Suggestion selected | `{ host, item }` |
| `cmnsd:autosuggest:shown` | Suggestions rendered | `{ host }` |
| `cmnsd:autosuggest:hidden` | Suggestions cleared | `{ host }` |
| `cmnsd:autosuggest:positioned` | Dropdown repositioned | `{ host }` |

---

## 🧾 License & Credits

Developed as part of the **cmnsd** project by Arne Coomans.  
All code and documentation generated collaboratively with OpenAI ChatGPT.

---
