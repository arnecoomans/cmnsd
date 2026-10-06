# Images and uploads

Looking at images closely, browsing a sequence of them, and uploading files. The view changes; the files never do.

## Image viewer (viewer.js)

```html
<div data-cmnsd-viewer data-viewer-original="{{ item.file_url }}">
  <img data-viewer-image src="{{ item.screen_url }}" alt="">
  <button type="button" data-viewer-zoom-in>+</button>
  <button type="button" data-viewer-zoom-out>-</button>
  <button type="button" data-viewer-fit>Fit</button>
  <button type="button" data-viewer-rotate>Rotate</button>
</div>
```

The image fits first. Then: scroll moves it, pinch or Ctrl/Cmd + scroll zooms around the pointer, dragging pans, the buttons do what they say. **Alt** + arrows, plus, minus, 0 and R work from anywhere on the page - also while typing in a text field beside the image, as on a transcription page.

`data-viewer-original` is a sharper version, loaded only once the zoom passes the shown image's own pixels: the page shows fast, detail comes when asked for.

**Crop mode** - `data-viewer-crop` on the container makes it a frame, and what's inside the frame is the crop. Inputs `[data-crop="x"]`, `y`, `w`, `h` in the surrounding form hold it as fractions of the image (0-1); they set the first view and every move writes them back. With an input `[data-crop="rotate"]` the image can be turned (0, 90, 180, 270). Radios `[data-crop-source="<image url>"]` switch between images - choosing a portrait from several photos.

## Gallery (gallery.js)

Step through a sequence of images in place - an item and its pages:

```django
<div data-cmnsd-gallery>
  <a href="{{ first.file }}" data-gallery-link><img src="{{ first.src }}" data-gallery-image alt=""></a>
  <div hidden>
    <button type="button" data-gallery-previous>‹</button>
    <span data-gallery-counter>1 / {{ items|length }}</span> · <a href="" data-gallery-caption></a>
    <button type="button" data-gallery-next>›</button>
  </div>
  {{ items|json_script:"gallery-items" }}   {# [{title, src, file, page}, ...] #}
</div>
<a href="{{ part.url }}" data-gallery-show="3">...</a>
```

‹ and › and the arrow keys step through, wrapping round; the image, its link, the counter and the caption follow. `data-gallery-show="<n>"` elsewhere on the page shows item n instead of navigating. `[data-gallery-open]` links to the shown item's own page. Without JavaScript: no buttons, and the thumbnails are plain links.

## Lightbox (lightbox.js)

A link to an image file marked `data-cmnsd-lightbox` opens it full-screen in a viewer instead of navigating to the bare file:

| Attribute | |
|---|---|
| `href` | The original file - what a click with a modifier key, or without JavaScript, still opens |
| `data-lightbox-src` | What shows first, a screen-sized version |
| `data-lightbox-zoom` | A sharper version, loaded when zooming in |
| `data-lightbox-title`, `data-lightbox-page` | The caption and its link |
| `data-lightbox-items` | A selector of a JSON script with a sequence - then ‹ › step through it, starting at the link's own file |
| `data-lightbox-text-*` | The labels: `close`, `original`, `previous`, `next`, `zoom-in`, `zoom-out`, `fit`, `rotate` |

Escape or the close button close it. A click beside the image doesn't: the whole area drags the image.

## Uploads (upload.js)

A container `[data-cmnsd-upload="<url>"]` is a drop area, with a file input `[data-upload-input]` (multiple) and a list `[data-upload-list]`:

- Files - dropped or chosen - are posted one at a time, sorted by name with numbers as numbers, each as its own request (field `file`) with a progress bar. A large scan doesn't hold up the rest; one failure stops nothing else.
- Each row shows the answer: `created` `{name, url, thumb}` - a link to the new item - or `duplicate` `{name, url}`, or the error.
- `[data-upload-done]` is shown when the queue is done. `data-upload-count="<selector>"` counts up with every added file; `data-upload-thumbs="<selector>"` adds each new file's thumbnail to a strip, at most `data-upload-thumbs-max`.

The project writes the view at `<url>`, answering in the [API response shape](../api.md) - cmnsd decides nothing about where files go.
