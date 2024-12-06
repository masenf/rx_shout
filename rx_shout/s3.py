import os
from urllib.parse import urljoin

import boto3
import reflex as rx


endpoint_url = os.environ.get("S3_ENDPOINT_URL")
access_key_id = os.environ.get("S3_ACCESS_KEY_ID")
secret_access_key = os.environ.get("S3_SECRET_ACCESS_KEY")
bucket_name = os.environ.get("S3_BUCKET_NAME")
bucket_access_url = os.environ.get("S3_BUCKET_ACCESS_URL")


if endpoint_url:
    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
else:
    client = None


def upload_image(filename: str, delete_original: bool = False) -> str:
    if bucket_access_url is None:
        raise RuntimeError("Set S3_BUCKET_ACCESS_URL environment variable")
    if client is None:
        raise RuntimeError("Set S3_ENDPOINT_URL environment variable")
    image_file = rx.get_upload_dir() / filename
    with image_file.open("rb") as fh:
        client.upload_fileobj(
            fh,
            bucket_name,
            filename,
        )
    if delete_original:
        image_file.unlink()
    return urljoin(bucket_access_url, filename)
