"""Unit tests for the S3 helper's configuration guard rails."""

from pathlib import Path

import pytest

from rx_shout import s3


def test_get_client_without_endpoint(monkeypatch: pytest.MonkeyPatch):
    """Without S3_ENDPOINT_URL, no client is created."""
    monkeypatch.setattr(s3, "endpoint_url", None)
    monkeypatch.setattr(s3, "_client", None)
    assert s3.get_client() is None


def test_get_client_with_endpoint(monkeypatch: pytest.MonkeyPatch):
    """With S3_ENDPOINT_URL, a client is created against that endpoint."""
    monkeypatch.setattr(s3, "endpoint_url", "http://127.0.0.1:9")
    monkeypatch.setattr(s3, "access_key_id", "testing")
    monkeypatch.setattr(s3, "secret_access_key", "testing")
    monkeypatch.setattr(s3, "_client", None)
    client = s3.get_client()
    assert client is not None
    assert client.meta.endpoint_url == "http://127.0.0.1:9"


def test_upload_image_requires_bucket_access_url(monkeypatch: pytest.MonkeyPatch):
    """upload_image refuses to run without S3_BUCKET_ACCESS_URL."""
    monkeypatch.setattr(s3, "bucket_access_url", None)
    with pytest.raises(RuntimeError, match="S3_BUCKET_ACCESS_URL"):
        s3.upload_image("whatever.png")


def test_upload_image_requires_endpoint(monkeypatch: pytest.MonkeyPatch):
    """upload_image refuses to run when no client can be created."""
    monkeypatch.setattr(s3, "bucket_access_url", "http://bucket.example/")
    monkeypatch.setattr(s3, "endpoint_url", None)
    monkeypatch.setattr(s3, "_client", None)
    with pytest.raises(RuntimeError, match="S3_ENDPOINT_URL"):
        s3.upload_image("whatever.png")


def test_upload_image_happy_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """upload_image pushes the file to the bucket and returns its public URL."""
    from moto.server import ThreadedMotoServer

    server = ThreadedMotoServer(port=0, verbose=False)
    server.start()
    try:
        _, port = server.get_host_and_port()
        url = f"http://127.0.0.1:{port}"
        monkeypatch.setattr(s3, "endpoint_url", url)
        monkeypatch.setattr(s3, "access_key_id", "testing")
        monkeypatch.setattr(s3, "secret_access_key", "testing")
        monkeypatch.setattr(s3, "bucket_name", "unit-bucket")
        monkeypatch.setattr(s3, "bucket_access_url", f"{url}/unit-bucket/")
        monkeypatch.setattr(s3, "_client", None)
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
        monkeypatch.setenv("REFLEX_UPLOADED_FILES_DIR", str(tmp_path))
        client = s3.get_client()
        assert client is not None
        client.create_bucket(Bucket="unit-bucket")
        (tmp_path / "img.png").write_bytes(b"png-bytes")
        result = s3.upload_image("img.png", delete_original=False)
        assert result == f"{url}/unit-bucket/img.png"
        # delete_original=False keeps the local file.
        assert (tmp_path / "img.png").exists()
        obj = client.get_object(Bucket="unit-bucket", Key="img.png")
        assert obj["Body"].read() == b"png-bytes"
    finally:
        server.stop()
