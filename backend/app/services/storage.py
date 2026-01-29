"""
MinIO Storage Service
Handles file uploads to S3-compatible storage
"""

import os
import uuid
from datetime import timedelta
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
import logging

logger = logging.getLogger(__name__)

# Configuration from environment
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "memora-uploads")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"


class StorageService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            endpoint_url=f"{'https' if MINIO_SECURE else 'http'}://{MINIO_ENDPOINT}",
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name='us-east-1'
        )
        self.bucket = MINIO_BUCKET
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
            except ClientError as e:
                logger.error(f"Failed to create bucket: {e}")

    async def upload_file(
        self,
        file: UploadFile,
        folder: str = "screenshots",
        user_id: str = None
    ) -> dict:
        """
        Upload a file to MinIO
        Returns: dict with file_url, file_key, file_size
        """
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else '.png'
        unique_id = str(uuid.uuid4())
        file_key = f"{folder}/{user_id or 'unknown'}/{unique_id}{file_ext}"

        # Read file content
        content = await file.read()
        file_size = len(content)

        # Upload to MinIO
        try:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=content,
                ContentType=file.content_type or 'application/octet-stream',
                Metadata={
                    'original-filename': file.filename or 'unknown',
                    'user-id': user_id or 'unknown'
                }
            )

            # Generate URL
            file_url = self.get_file_url(file_key)

            return {
                'file_url': file_url,
                'file_key': file_key,
                'file_size': file_size,
                'content_type': file.content_type
            }

        except ClientError as e:
            logger.error(f"Failed to upload file: {e}")
            raise Exception(f"Failed to upload file: {str(e)}")

    def get_file_url(self, file_key: str, expires_in: int = 3600 * 24 * 7) -> str:
        """
        Generate a presigned URL for file access
        Default expiry: 7 days
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': file_key},
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return ""

    def delete_file(self, file_key: str) -> bool:
        """Delete a file from MinIO"""
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=file_key)
            return True
        except ClientError as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    def get_file_info(self, file_key: str) -> Optional[dict]:
        """Get file metadata"""
        try:
            response = self.s3_client.head_object(Bucket=self.bucket, Key=file_key)
            return {
                'size': response['ContentLength'],
                'content_type': response['ContentType'],
                'last_modified': response['LastModified'],
                'metadata': response.get('Metadata', {})
            }
        except ClientError:
            return None


# Singleton instance
storage_service = StorageService()


def get_storage_service() -> StorageService:
    return storage_service
