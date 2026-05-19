"""Image processing utilities."""
from io import BytesIO
from random import randrange, randint

import numpy as np
from PIL import Image

from exception.image_build_error import ImageBuildError
from utility.constants import SONG_JACKET_THUMBNAIL_SIZE, CARD_CROP_SIZE, VERTICAL_CARDS
from utility.r2 import get_object_with_retry, get_mask_from_r2
from utility.utility_functions import logger


def prepare_answer_song_jacket(s3, bucket_name, jacket_key):
    """Prepare resized jacket image for answer display."""
    try:
        obj = get_object_with_retry(s3, bucket_name, jacket_key)
        buffer = BytesIO(obj['Body'].read())
        buffer.seek(0)
        img = Image.open(buffer)
        img.load()

        img = img.resize(SONG_JACKET_THUMBNAIL_SIZE)

        buffer.seek(0)
        buffer.truncate()

        img.save(buffer, format="PNG")
        buffer.seek(0)
    except Exception as e:
        raise ImageBuildError(e)

    return buffer


def prepare_cropped_jacket_question_and_answer(s3, bucket_name, jacket_key, crop_size):
    """Prepare both cropped jacket (question) and resized jacket (answer).

    Returns:
        tuple: (question_bytes, answer_buffer)
            - question_bytes: BytesIO with cropped jacket image
            - answer_buffer: BytesIO with resized full jacket
    """
    try:
        obj = get_object_with_retry(s3, bucket_name, jacket_key)
        buffer = BytesIO(obj['Body'].read())
        buffer.seek(0)
        img = Image.open(buffer)
        img.load()
    except Exception as e:
        raise ImageBuildError(e)

    # Prepare cropped image (question)
    region = generate_img_crop(img, crop_size)
    question_buffer = BytesIO()
    region.save(question_buffer, 'PNG', quality=95, optimize=True)
    question_buffer.seek(0)
    question_bytes = question_buffer.getvalue()

    # Prepare answer buffer (resized full jacket)
    answer_buffer = BytesIO()
    img_resized = img.resize(SONG_JACKET_THUMBNAIL_SIZE)
    img_resized.save(answer_buffer, "PNG", quality=95, optimize=True)
    answer_buffer.seek(0)

    return question_bytes, answer_buffer


def _fetch_and_prepare_card_image(s3, bucket_name, card_key):
    """Fetch card image and handle vertical rotation.

    Returns:
        tuple: (working_img, original_img) - both as PIL Image objects
    """
    try:
        obj = get_object_with_retry(s3, bucket_name, card_key)
        buffer = BytesIO(obj['Body'].read())
        buffer.seek(0)
        img = Image.open(buffer)
        img.load()
        original_img = img.copy()
    except Exception as e:
        raise ImageBuildError(f"Failed to fetch card image: {e}")

    # Handle vertical card rotation
    if "vertical" in card_key and "after_training" in card_key:
        img = img.rotate(270, expand=True)
        original_img = img.copy()

    return img, original_img


def _crop_card_image(img, card_id, use_mask, s3=None, bucket_name=None):
    """Generate cropped card image for question.

    Selects crop strategy (mask-based for 2-star, random for others).
    """
    if use_mask and s3 and bucket_name:
        try:
            mask_key = f"masks/card_{card_id}_normal.npz"
            alpha = get_mask_from_r2(s3, bucket_name, mask_key)
            return generate_foreground_crop_from_mask(img, alpha, CARD_CROP_SIZE)
        except Exception as e:
            logger.warning(f"Failed to use mask for card {card_id}, falling back to random crop: {e}")

    return generate_img_crop(img, CARD_CROP_SIZE)


def _save_image_to_buffer(img, buffer):
    """Save PIL Image to BytesIO buffer."""
    img.save(buffer, 'PNG', quality=95, optimize=True)
    buffer.seek(0)


def prepare_card_question_and_answer(
    s3, bucket_name, card_key, card_id, use_mask=False
):
    """Prepare both cropped card (question) and resized card (answer).

    Returns:
        tuple: (question_bytes, answer_buffer)
            - question_bytes: Cropped card image bytes
            - answer_buffer: BytesIO with quarter-sized card for answer
    """
    # Fetch and prepare base image
    img, original_img = _fetch_and_prepare_card_image(s3, bucket_name, card_key)

    # Generate and save cropped question
    question_region = _crop_card_image(img, card_id, use_mask, s3, bucket_name)
    question_buffer = BytesIO()
    _save_image_to_buffer(question_region, question_buffer)
    question_bytes = question_buffer.getvalue()

    # Generate and save resized answer
    answer_buffer = BytesIO()
    w, h = original_img.size
    resized = original_img.resize((w // 4, h // 4))
    _save_image_to_buffer(resized, answer_buffer)

    return question_bytes, answer_buffer


def prepare_card_answer_only(s3, bucket_name, card_key):
    """Prepare only the answer buffer (resized card).

    Returns:
        BytesIO: Quarter-sized card image
    """
    img, _ = _fetch_and_prepare_card_image(s3, bucket_name, card_key)

    answer_buffer = BytesIO()
    w, h = img.size
    resized = img.resize((w // 4, h // 4))
    _save_image_to_buffer(resized, answer_buffer)

    return answer_buffer


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


def fetch_card_image_raw(s3, bucket_name, card_key) -> BytesIO:
    """Fetch a card image without any processing.

    Used for displaying random cards.

    Returns:
        BytesIO: Raw card image buffer
    """
    try:
        obj = get_object_with_retry(s3, bucket_name, card_key)
        buffer = BytesIO(obj['Body'].read())
        buffer.seek(0)
        return buffer
    except Exception as e:
        raise ImageBuildError(f"Failed to fetch card image: {e}")
