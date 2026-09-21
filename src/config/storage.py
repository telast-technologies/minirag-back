import mimetypes
from io import BytesIO
from typing import BinaryIO

from botocore.exceptions import ClientError
from fastapi_storages import S3Storage as BaseS3Storage

from src.config.loggers import Logger
from src.config.settings import settings

logger = Logger(__name__)


class BucketS3Storage(BaseS3Storage):
    """
    Custom S3 storage implementation.

    Extends FastAPI Storages S3Storage with custom configuration
    and file opening capabilities.

    Attributes:
        AWS_S3_BUCKET_NAME (str): Name of the S3 bucket.
        AWS_S3_ENDPOINT_URL (str): S3 endpoint URL.
    """

    AWS_ACCESS_KEY_ID: str = settings.AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY: str = settings.AWS_SECRET_ACCESS_KEY
    AWS_S3_BUCKET_NAME: str = settings.AWS_S3_BUCKET_NAME
    AWS_S3_ENDPOINT_URL: str = settings.AWS_S3_ENDPOINT_URL
    AWS_S3_SIGNATURE_VERSION: str = "s3v4"

    def get_path(self, name: str) -> str:
        key = self.get_name(name)
        params = {"Bucket": self.AWS_S3_BUCKET_NAME, "Key": key}
        return self._s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=3600,
        )

    def write(self, file: BinaryIO, name: str) -> str:
        file.seek(0, 0)
        key = self.get_name(name)
        content_type, _ = mimetypes.guess_type(key)

        params = {
            "ContentType": content_type or self.default_content_type,
            **self.AWS_S3_OBJECT_PARAMETERS,
        }

        if self.AWS_DEFAULT_ACL:
            params["ACL"] = self.AWS_DEFAULT_ACL

        self._s3.upload_fileobj(
            file,
            self.AWS_S3_BUCKET_NAME,
            key,
            ExtraArgs=params,
        )
        return key

    def open(self, name: str) -> BinaryIO:
        key = self.get_name(name)

        try:
            s3_client = self._s3.meta.client if hasattr(self._s3, "meta") else self._s3
            response = s3_client.get_object(
                Bucket=self.AWS_S3_BUCKET_NAME,
                Key=key,
            )

            buffer = BytesIO(response["Body"].read())
            buffer.seek(0)
            return buffer

        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey"):
                raise FileNotFoundError(f"File '{key}' not found in S3")
            raise


S3Storage = BucketS3Storage()
