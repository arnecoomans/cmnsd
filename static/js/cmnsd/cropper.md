# cmnsd.js — Cropper Module

A lightweight, configurable cropping module for the cmnsd.js framework.

## Features

- Pure JavaScript (no external libraries)
- Auto-bind via `data-cropper`
- Fully responsive
- Works with AJAX-loaded content
- Converts displayed crop to natural image coordinates
- Sends crop values as JSON payload via `data-action`
- Supports multiple independent croppers on the same page
- Optional preview modes

## Usage

### 1. Markup

```html
<div data-cropper
     data-cropper-target="#crop-image"
     data-cropper-save="#crop-save-btn"
     data-cropper-fields="x=portrait_x,y=portrait_y,w=portrait_w,h=portrait_h">
  <img id="crop-image" src="/path/to/image.jpg" class="img-fluid">
  <div class="crop-rect"></div>
</div>

<button id="crop-save-btn"
        data-action
        data-method="PATCH"
        data-url="/ajax/person/123/portrait_x,portrait_y,portrait_w,portrait_h/">
  Save Crop
</button>
```

### 2. Auto-bind

```js
import { initCropper } from "/static/js/cmnsd/cropper.js";

document.addEventListener("DOMContentLoaded", () => initCropper());
document.addEventListener("cmnsd:content:applied", e => initCropper(e.detail?.container));
```

### 3. Options

| Attribute | Description | Default |
|----------|-------------|---------|
| `data-cropper` | Enables cropper | required |
| `data-cropper-target` | Image to crop | required |
| `data-cropper-save` | Button receiving payload | required |
| `data-cropper-fields` | Mapping natural → payload fields | `"x=x,y=y,w=w,h=h"` |
| `data-cropper-aspect` | Define aspect ratio of cropped image | optional |

### 4. JSON Output Format

```json
{
  "portrait_x": 12,
  "portrait_y": 44,
  "portrait_w": 510,
  "portrait_h": 620
}
```

### 5. AJAX submission via cmnsd.js

```html
<button data-action data-method="PATCH">...</button>
```

### 6. Browser Support

- Chrome ✔  
- Firefox ✔  
- Safari / iOS ✔ (with CSS fallback)  
- No canvas required  

### 7. Styling

```css
[data-cropper] {
  position: relative;
  display: inline-block;
  width: 100%;
}

.crop-rect {
  position: absolute;
  border: 2px dashed red;
  background: rgba(255,0,0,0.15);
  display: none;
  pointer-events: none;
}
```

### 8. Fallback Mode (auto-enabled on iOS)

Fallback cropping is enabled automatically when precise CSS transforms are not supported.

---

## Changelog

### v1.0
- Initial release  
- Auto-bind  
- AJAX-ready  
- iOS-compatible  
- Multiple cropper instances supported  

---

## License
MIT — free to use in cmnsd-based and non-cmnsd projects.
