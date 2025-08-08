import os
import uuid
from pathlib import Path
from typing import Tuple

try:
    import boto3  # type: ignore
except Exception:  # pragma: no cover
    boto3 = None


def _get_cdn_url(path_or_url: str) -> str:
    cdn_base = os.getenv("CDN_BASE_URL", "").rstrip("/")
    if cdn_base:
        # If input is a path like /static/uploads/xyz.jpg, return CDN + path
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return f"{cdn_base}{path_or_url}"
    return path_or_url


class LocalStorage:
    def __init__(self) -> None:
        self.upload_dir = Path(__file__).resolve().parent / "static" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, data: bytes, content_type: str, filename: str) -> str:
        # create unique name
        ext = f".{filename.rsplit('.', 1)[1]}" if "." in filename else ""
        unique_name = f"{uuid.uuid4().hex}{ext}"
        dest = self.upload_dir / unique_name
        with dest.open("wb") as f:
            f.write(data)
        return _get_cdn_url(f"/static/uploads/{unique_name}")


class S3Storage:
    def __init__(self) -> None:
        if boto3 is None:
            raise RuntimeError("boto3 is required for S3 storage")
        self.bucket = os.environ["S3_BUCKET"]
        self.region = os.getenv("S3_REGION", "us-east-1")
        self.endpoint_url = os.getenv("S3_ENDPOINT_URL")
        self.prefix = os.getenv("S3_PREFIX", "uploads/")
        session = boto3.session.Session()
        self.client = session.client(
            "s3",
            region_name=self.region,
            endpoint_url=self.endpoint_url,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    def save_file(self, data: bytes, content_type: str, filename: str) -> str:
        ext = f".{filename.rsplit('.', 1)[1]}" if "." in filename else ""
        key = f"{self.prefix}{uuid.uuid4().hex}{ext}"
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type, ACL="public-read")
        base_url = os.getenv("S3_PUBLIC_BASE_URL")
        if base_url:
            url = f"{base_url.rstrip('/')}/{key}"
        else:
            url = f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{key}"
        return _get_cdn_url(url)


def get_storage():
    backend = os.getenv("STORAGE_BACKEND", "local").lower()
    if backend == "s3":
        return S3Storage()
    return LocalStorage()