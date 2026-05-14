"""Image processing utilities."""
from random import randrange, randint

import numpy as np
from PIL import Image


def generate_img_crop(img: Image.Image, crop_size):
    """Generate a random crop from an image."""
    width = img.width
    height = img.height
    x1 = randint(0, width - crop_size - 1)
    y1 = randint(0, height - crop_size - 1)
    box = (x1, y1, x1 + crop_size, y1 + crop_size)
    return img.crop(box)


def generate_foreground_crop_from_mask(orig_img, alpha, crop_size, min_fg_ratio=0.12):
    """Generate a crop biased towards foreground content using a mask.
    
    Uses an alpha mask to prefer crops containing foreground pixels.
    Falls back to random crops if mask detection fails.
    """
    width = orig_img.width
    height = orig_img.height

    # same guard idea as normal crop
    if crop_size >= width or crop_size >= height:
        return orig_img.copy()

    ys, xs = np.where(alpha > 0)

    # if mask failed → behave exactly like normal crop
    if len(xs) == 0:
        return generate_img_crop(orig_img, crop_size)

    last_box = None
    for _ in range(4):  # try a few foreground-biased crops
        # pick a random foreground pixel as anchor
        i = randrange(len(xs))
        cx, cy = xs[i], ys[i]

        # convert center → top-left (like normal crop uses x1,y1)
        x1 = cx - crop_size // 2
        y1 = cy - crop_size // 2

        # clamp like bounds-safe random crop
        x1 = max(0, min(x1, width - crop_size))
        y1 = max(0, min(y1, height - crop_size))

        box = (x1, y1, x1 + crop_size, y1 + crop_size)
        last_box = box

        # foreground coverage check
        patch = alpha[y1:y1 + crop_size, x1:x1 + crop_size]
        if (patch > 0).mean() >= min_fg_ratio:
            return orig_img.crop(box)

    # fallback → return the last generated crop
    if last_box is not None:
        return orig_img.crop(last_box)
    return generate_img_crop(orig_img, crop_size)
