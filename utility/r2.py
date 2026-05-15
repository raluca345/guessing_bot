"""R2/S3 storage utilities."""
import logging
import os
import time
from io import BytesIO

import numpy as np
import boto3
from botocore.client import Config
import aiohttp
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# R2 configuration
ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID')
SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY')
BUCKET_NAME = os.getenv('BUCKET_NAME')
ENDPOINT_URL = os.getenv('ENDPOINT_URL')


def connect_to_r2_storage():
    """Connect to R2 storage (S3-compatible API)."""
    s3 = boto3.client('s3',
                      endpoint_url=ENDPOINT_URL,
                      aws_access_key_id=ACCESS_KEY_ID,
                      aws_secret_access_key=SECRET_ACCESS_KEY,
                      config=Config(signature_version='s3v4'))
    return s3


def get_object_with_retry(s3, bucket, key, retries=3, delay=2):
    """Fetch an object from S3/R2 with retries and logging.

    Returns the object dict on success or raises the final exception.
    """
    attempt = 1
    while attempt <= retries:
        try:
            logger.info("Fetching R2 object (attempt %d/%d): %s/%s", attempt, retries, bucket, key)
            obj = s3.get_object(Bucket=bucket, Key=key)
            # log content length when available
            headers = obj.get('ResponseMetadata', {}).get('HTTPHeaders', {})
            content_length = headers.get('content-length') or obj.get('ContentLength')
            logger.info("Fetched object %s (size=%s)", key, content_length)
            return obj
        except Exception as e:
            logger.warning("Failed fetching %s (attempt %d/%d): %s", key, attempt, retries, e)
            if attempt == retries:
                logger.exception("Exceeded retries fetching %s from bucket %s", key, bucket)
                raise
            time.sleep(delay * attempt)
            attempt += 1


def get_mask_from_r2(s3, bucket, mask_key):
    """Fetch and load a mask file from R2.
    
    Expects a compressed .npz file with an 'alpha' key.
    """
    obj = s3.get_object(Bucket=bucket, Key=mask_key)
    loaded = np.load(BytesIO(obj["Body"].read()))
    if isinstance(loaded, np.lib.npyio.NpzFile):
        try:
            if "alpha" in loaded.files:
                return loaded["alpha"]
            raise ValueError(f"Compressed mask archive at '{mask_key}' is missing 'alpha'.")
        finally:
            loaded.close()

    raise ValueError(f"Unsupported mask format for '{mask_key}'. Expected compressed .npz data.")
