from io import BytesIO

import pytest
from botocore.exceptions import ClientError


class FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self):
        return self._data


class FakeS3Client:
    def __init__(self):
        self.presigned_calls = []
        self.upload_calls = []
        self.get_object_calls = []
        self.get_object_response = {"Body": FakeBody(b"file-content")}
        self.get_object_error = None

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        self.presigned_calls.append(
            {
                "operation": operation,
                "Params": Params,
                "ExpiresIn": ExpiresIn,
            }
        )
        return "https://signed-url.example.com/file"

    def upload_fileobj(self, file, bucket, key, ExtraArgs):
        current_pos = file.tell()
        content = file.read()
        self.upload_calls.append(
            {
                "bucket": bucket,
                "key": key,
                "extra_args": ExtraArgs,
                "content": content,
                "position_at_read": current_pos,
            }
        )

    def get_object(self, Bucket, Key):
        self.get_object_calls.append({"Bucket": Bucket, "Key": Key})
        if self.get_object_error:
            raise self.get_object_error
        return self.get_object_response


class FakeS3WithMeta:
    def __init__(self, client):
        self.meta = type("Meta", (), {"client": client})()


def test_get_path_returns_presigned_url_using_bucket_and_key(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    result = storage.get_path("photo.png")

    assert result == "https://signed-url.example.com/file"
    assert fake_s3.presigned_calls == [
        {
            "operation": "get_object",
            "Params": {
                "Bucket": "test-bucket",
                "Key": "uploads/photo.png",
            },
            "ExpiresIn": 3600,
        }
    ]


def test_write_uploads_file_with_guessed_content_type_and_acl(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    file_obj = BytesIO(b"hello-world")
    file_obj.seek(5)

    result = storage.write(file_obj, "photo.png")

    assert result == "uploads/photo.png"
    assert len(fake_s3.upload_calls) == 1

    call = fake_s3.upload_calls[0]
    assert call["bucket"] == "test-bucket"
    assert call["key"] == "uploads/photo.png"
    assert call["content"] == b"hello-world"
    assert call["position_at_read"] == 0
    assert call["extra_args"]["ContentType"] == "image/png"
    assert call["extra_args"]["CacheControl"] == "max-age=3600"
    assert call["extra_args"]["ACL"] == "public-read"


def test_write_uses_default_content_type_when_mimetype_is_unknown(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    result = storage.write(BytesIO(b"data"), "file.unknownext")

    assert result == "uploads/file.unknownext"
    assert len(fake_s3.upload_calls) == 1
    call = fake_s3.upload_calls[0]
    assert call["extra_args"]["ContentType"] == "application/octet-stream"


def test_write_does_not_include_acl_when_default_acl_is_missing(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    storage.AWS_DEFAULT_ACL = None

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    storage.write(BytesIO(b"data"), "photo.png")

    call = fake_s3.upload_calls[0]
    assert "ACL" not in call["extra_args"]
    assert call["extra_args"]["ContentType"] == "image/png"
    assert call["extra_args"]["CacheControl"] == "max-age=3600"


def test_open_reads_file_using_meta_client_and_returns_buffer_at_start(storage, monkeypatch):
    fake_client = FakeS3Client()
    fake_s3 = FakeS3WithMeta(fake_client)

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    result = storage.open("photo.png")

    assert isinstance(result, BytesIO)
    assert result.tell() == 0
    assert result.read() == b"file-content"
    assert fake_client.get_object_calls == [
        {
            "Bucket": "test-bucket",
            "Key": "uploads/photo.png",
        }
    ]


def test_open_reads_file_directly_from_s3_when_meta_is_missing(storage, monkeypatch):
    fake_s3 = FakeS3Client()

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    result = storage.open("document.pdf")

    assert isinstance(result, BytesIO)
    assert result.read() == b"file-content"
    assert fake_s3.get_object_calls == [
        {
            "Bucket": "test-bucket",
            "Key": "uploads/document.pdf",
        }
    ]


def test_open_raises_file_not_found_for_404_error(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    fake_s3.get_object_error = ClientError(
        error_response={"Error": {"Code": "404", "Message": "Not Found"}},
        operation_name="GetObject",
    )

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    with pytest.raises(FileNotFoundError, match="File 'uploads/missing.png' not found in S3"):
        storage.open("missing.png")


def test_open_raises_file_not_found_for_no_such_key(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    fake_s3.get_object_error = ClientError(
        error_response={"Error": {"Code": "NoSuchKey", "Message": "Missing key"}},
        operation_name="GetObject",
    )

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: f"uploads/{name}")

    with pytest.raises(FileNotFoundError, match="File 'uploads/missing.png' not found in S3"):
        storage.open("missing.png")


def test_open_reraises_unexpected_client_error(storage, monkeypatch):
    fake_s3 = FakeS3Client()
    fake_s3.get_object_error = ClientError(
        error_response={"Error": {"Code": "403", "Message": "Forbidden"}},
        operation_name="GetObject",
    )

    monkeypatch.setattr(storage, "_s3", fake_s3)
    monkeypatch.setattr(storage, "get_name", lambda name: "uploads/forbidden.png")

    with pytest.raises(ClientError) as exc_info:
        storage.open("forbidden.png")

    assert exc_info.value.response["Error"]["Code"] == "403"
