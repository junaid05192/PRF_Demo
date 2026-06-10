import os
import uuid

import boto3

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")
R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "flocksense-frames")
R2_PUBLIC_BASE_URL = os.environ.get("R2_PUBLIC_BASE_URL")  # public bucket URL or custom domain

_client = None


def _get_client():
    global _client
    if _client is None:
        if not (R2_ACCOUNT_ID and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY):
            raise RuntimeError("R2 credentials not configured")
        _client = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    return _client


def upload_frame(node_id: str, content: bytes, content_type: str = "image/jpeg") -> str:
    """Upload a camera frame to R2 and return its public URL."""
    key = f"frames/{node_id}/{uuid.uuid4().hex}.jpg"
    client = _get_client()
    client.put_object(
        Bucket=R2_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentType=content_type,
    )
    if R2_PUBLIC_BASE_URL:
        return f"{R2_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    return f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{R2_BUCKET_NAME}/{key}"
