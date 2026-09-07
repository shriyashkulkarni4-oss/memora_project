"""S3-compatible object storage service."""

import logging
import os
import uuid
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """Store uploaded files in MinIO or another S3-compatible service."""

    def __init__(
        self,
        settings: Settings | None = None,
        s3_client: Any | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        scheme = "https" if self.settings.minio_secure else "http"
        self.s3_client = s3_client or boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{self.settings.minio_endpoint}",
            aws_access_key_id=self.settings.minio_access_key,
            aws_secret_access_key=self.settings.minio_secret_key,
            region_name="us-east-1",
        )
        self.bucket = self.settings.minio_bucket
        self._bucket_ready = False

    def _ensure_bucket_exists(self) -> None:
        """Create the configured bucket on first storage operation."""
        if self._bucket_ready:
            return

        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code not in {"404", "NoSuchBucket", "NotFound"}:
                raise
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                logger.info("Created storage bucket: %s", self.bucket)
            except ClientError:
                logger.exception("Failed to create storage bucket: %s", self.bucket)
                raise

        self._bucket_ready = True

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "screenshots",
        user_id: str | None = None,
    ) -> dict:
        """
        Upload a file to MinIO
        Returns: dict with file_url, file_key, file_size
        """
        content = await file.read()
        return self.upload_bytes(
            content,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename,
            folder=folder,
            user_id=user_id,
        )

    def upload_bytes(
        self,
        content: bytes,
        *,
        content_type: str,
        original_filename: str | None = None,
        folder: str = "screenshots",
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Upload validated bytes under a generated, user-scoped object key."""
        extension_by_type = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/gif": ".gif",
            "image/webp": ".webp",
        }
        file_ext = extension_by_type.get(content_type)
        if file_ext is None:
            file_ext = os.path.splitext(original_filename or "")[1].lower() or ".bin"
        file_key = f"{folder}/{user_id or 'unknown'}/{uuid.uuid4()}{file_ext}"

        try:
            self._ensure_bucket_exists()
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=content,
                ContentType=content_type,
                Metadata={
                    "original-filename": original_filename or "unknown",
                    "user-id": user_id or "unknown",
                },
            )
            return {
                "file_key": file_key,
                "file_size": len(content),
                "content_type": content_type,
            }
        except ClientError as exc:
            logger.exception("Failed to upload file")
            raise RuntimeError("Failed to upload file") from exc

    def get_file_url(self, file_key: str, expires_in: int = 3600 * 24 * 7) -> str:
        """
        Generate a presigned URL for file access
        Default expiry: 7 days
        """
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": file_key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError:
            logger.exception("Failed to generate presigned URL")
            return ""

    def delete_file(self, file_key: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_key)
            return True
        except ClientError:
            logger.exception("Failed to delete file")
            return False

    def get_file_info(self, file_key: str) -> dict | None:
        """Get file metadata"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=file_key)
            return {
                "size": response["ContentLength"],
                "content_type": response["ContentType"],
                "last_modified": response["LastModified"],
                "metadata": response.get("Metadata", {}),
            }
        except ClientError:
            return None

    def get_file_bytes(self, file_key: str) -> bytes:
        """Read a private object for server-side processing."""
        response = self.s3_client.get_object(Bucket=self.bucket, Key=file_key)
        return response["Body"].read()


@lru_cache
def get_storage_service() -> StorageService:
    """Construct storage only when an endpoint first requests it."""
    return StorageService()
