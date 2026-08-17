"""
S3 helper, local to the recipes function. RecipePhotosBucket (template.yaml)
blocks all public access, so photos are uploaded via the Lambda and read
back through short-lived presigned GET URLs generated per response.

recipes.photo_url (schema.sql) stores the S3 object *key*, not a public
URL — there's no such thing as a stable public URL against this bucket.
The column name is a little misleading as a result; flagging it but not
renaming it, since that'd be a schema change outside this ticket's scope.

boto3 ships with the Lambda Python runtime already — not added to
requirements.txt.
"""
import os
import uuid
import boto3
from botocore.config import Config

_s3 = boto3.client("s3", config=Config(signature_version="s3v4"))

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

READ_URL_TTL_SECONDS = 3600


def _bucket() -> str:
    return os.environ["PHOTOS_BUCKET"]


def new_photo_key(recipe_id, content_type: str) -> str:
    ext = _ALLOWED_CONTENT_TYPES.get(content_type)
    if not ext:
        raise ValueError(
            f"Unsupported contentType '{content_type}'. "
            f"Allowed: {', '.join(_ALLOWED_CONTENT_TYPES)}"
        )
    return f"recipes/{recipe_id}/{uuid.uuid4().hex}.{ext}"


def upload_bytes(photo_key: str, content: bytes, content_type: str) -> None:
    _s3.put_object(Bucket=_bucket(), Key=photo_key, Body=content, ContentType=content_type)


def presign_read(photo_key: str) -> str:
    return _s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": _bucket(), "Key": photo_key},
        ExpiresIn=READ_URL_TTL_SECONDS,
    )