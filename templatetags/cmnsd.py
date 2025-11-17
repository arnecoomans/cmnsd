from django import template

register = template.Library()

@register.inclusion_tag('templatetags/cropper.html')
def portrait_crop(image, x=None, y=None, w=None, h=None, src=None, crop_source=None):
    """
    Renders a responsive cropped portrait using CSS transform trickery.

    image: image object (must have .url and get_image_dimensions)
    x,y,w,h: optional explicit crop values, otherwise read from image model
    """
    crop_source = image if not crop_source else crop_source

    if not image:
        return {"enabled": False}

    oy, ox = image.get_image_dimensions()
    print(f"Original dimensions: width(y): {ox} height(x): {oy}")
    # Get crop values
    cx = getattr(crop_source, "portrait_x", x or 0) or 0
    cy = getattr(crop_source, "portrait_y", y or 0) or 0
    cw = getattr(crop_source, "portrait_w", w or ox) or ox
    ch = getattr(crop_source, "portrait_h", h or oy) or oy
    print(f"Crop values: x={cx}, y={cy}, w={cw}, h={ch}")
    # Avoid division by zero
    if cw <= 0: cw = ox
    if ch <= 0: ch = oy

    # Wrapper height: (crop height / crop width) * 100%
    height_pct = (ch / cw) * 100 if cw else 100

    return {
        "enabled": True,
        "src": src if src is not None else (image.source if hasattr(image, "source") else ''),
        "url": image.source if hasattr(image, "source") else '',
        "ox": ox,
        "oy": oy,
        "cx": cx,
        "cy": cy,
        "cw": cw,
        "ch": ch,
        "height_pct": height_pct,
    }