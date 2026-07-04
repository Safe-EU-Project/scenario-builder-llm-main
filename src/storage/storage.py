"""
MinIO client for reading extracted documents from Umami service.
"""

import json
from collections.abc import Iterator
from typing import Any, Dict, Optional

import structlog
from minio import Minio
from minio.error import S3Error

from ..config.settings import settings

log = structlog.get_logger()


class MinIOClient:
    """MinIO client for reading extracted documents"""

    def __init__(self):
        """Initialize MinIO client with settings"""
        self.client = Minio(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket_name = settings.minio_bucket

        log.info(
            "minio_client_initialized", endpoint=settings.minio_endpoint, bucket=self.bucket_name
        )

    def get_extracted_text(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve extracted text data from MinIO

        Args:
            file_id: Unique file identifier

        Returns:
            Document data dictionary or None if not found
        """
        try:
            object_name = f"extracted/{file_id}.json"

            response = self.client.get_object(self.bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()

            document_data = json.loads(data.decode("utf-8"))

            log.debug(
                "extracted_text_retrieved",
                file_id=file_id,
                text_length=document_data.get("text_length", 0),
            )

            return document_data

        except S3Error as e:
            if e.code == "NoSuchKey":
                log.debug("extracted_text_not_found", file_id=file_id)
                return None
            log.error("minio_get_error", file_id=file_id, error=str(e))
            return None
        except Exception as e:
            log.error("minio_get_unexpected_error", file_id=file_id, error=str(e))
            return None

    def list_extracted_documents(
        self, project_filter: Optional[str] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        List all extracted documents in MinIO

        Args:
            project_filter: Filter by project name

        Yields:
            Document metadata dictionaries
        """
        try:
            objects = self.client.list_objects(
                self.bucket_name, prefix="extracted/", recursive=True
            )

            for obj in objects:
                try:
                    # Get object metadata
                    stat = self.client.stat_object(self.bucket_name, obj.object_name)

                    # Filter by project if specified
                    if project_filter:
                        project_name = stat.metadata.get("project_name", "")
                        if project_name != project_filter:
                            continue

                    # Extract file_id from object name
                    file_id = obj.object_name.replace("extracted/", "").replace(".json", "")

                    yield {
                        "file_id": file_id,
                        "object_name": obj.object_name,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                        "project_name": stat.metadata.get("project_name", "unknown"),
                        "document_name": stat.metadata.get("document_name", "unknown"),
                        "file_type": stat.metadata.get("file_type", "unknown"),
                        "extracted_at": stat.metadata.get("extracted_at"),
                    }

                except Exception as e:
                    log.warning("minio_list_item_error", object_name=obj.object_name, error=str(e))
                    continue

        except S3Error as e:
            log.error("minio_list_error", error=str(e))

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get MinIO storage statistics"""
        try:
            objects = list(
                self.client.list_objects(self.bucket_name, prefix="extracted/", recursive=True)
            )

            total_objects = len(objects)
            total_size = sum(obj.size for obj in objects)

            return {
                "total_documents": total_objects,
                "total_size_bytes": total_size,
                "bucket_name": self.bucket_name,
                "endpoint": self.client._base_url._url.netloc,
            }

        except S3Error as e:
            log.error("minio_stats_error", error=str(e))
            return {"error": str(e)}
