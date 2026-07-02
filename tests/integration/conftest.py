"""Shared fixtures for the rx_shout integration tests."""

import json
from pathlib import Path

import boto3
import pytest
from helpers import ALICE, BOB, PNG_BYTES, create_post, login_as, logout
from playwright.sync_api import Page
from reflex_enterprise.testing import AppManager, ReflexApp

S3_BUCKET_NAME = "rx-shout-test"


@pytest.fixture
def png_file(tmp_path: Path) -> Path:
    """Write a small PNG to disk for upload tests."""
    png_path = tmp_path / "pixel.png"
    png_path.write_bytes(PNG_BYTES)
    return png_path


@pytest.fixture(scope="session")
def _admin_seeded() -> list[bool]:
    """Session-wide flag recording whether the admin user has been created."""
    return []


@pytest.fixture
def admin_user_exists(reflex_app: ReflexApp, page: Page, _admin_seeded: list[bool]):
    """Guarantee alice is the first user ever created (UserInfo.id == 1 == admin).

    Any fixture that logs in a non-admin user must depend on this so that the
    non-admin user does not accidentally claim the admin user id.
    """
    if not _admin_seeded:
        login_as(reflex_app, page, ALICE)
        logout(reflex_app, page)
        _admin_seeded.append(True)


@pytest.fixture
def alice_logged_in(reflex_app: ReflexApp, page: Page):
    """Log in as alice (the admin) for the duration of the test."""
    login_as(reflex_app, page, ALICE)
    yield
    logout(reflex_app, page)


@pytest.fixture
def bob_logged_in(reflex_app: ReflexApp, page: Page, admin_user_exists: None):
    """Log in as bob (a non-admin) for the duration of the test."""
    login_as(reflex_app, page, BOB)
    yield
    logout(reflex_app, page)


@pytest.fixture
def post_by_alice(reflex_app: ReflexApp, page: Page, alice_logged_in: None):
    """Create a post on the main feed as alice and return its content."""
    page.goto(f"{reflex_app.url}")
    return create_post(page, prefix="test_create_post")


@pytest.fixture
def post_by_bob(reflex_app: ReflexApp, page: Page, bob_logged_in: None):
    """Create a post on the main feed as bob and return its content."""
    page.goto(f"{reflex_app.url}")
    return create_post(page, prefix="post_by_bob")


@pytest.fixture(scope="session")
def tmp_database(tmp_path_factory: pytest.TempPathFactory):
    """Create a temporary database file for testing."""
    return tmp_path_factory.mktemp("data") / "test.db"


@pytest.fixture(scope="session", autouse=True)
def use_tmp_database(reflex_app_manager: AppManager, tmp_database: str):
    """Monkeypatch the database URL to use the temporary database."""
    reflex_app_manager.settings.extra_env = {
        **reflex_app_manager.settings.extra_env,
        "REFLEX_DB_URL": f"sqlite:///{tmp_database}",
        "REFLEX_ASYNC_DB_URL": f"sqlite+aiosqlite:///{tmp_database}",
        # reflex-enterprise exits at startup unless the developer has a fresh
        # `reflex login` token; CI mode skips that check so test runs do not
        # depend on the developer's login state.
        "CI": "true",
    }


@pytest.fixture(scope="session")
def moto_server_url():
    """Run a moto S3 server (in server mode) for the whole test session."""
    from moto.server import ThreadedMotoServer

    server = ThreadedMotoServer(port=0, verbose=False)
    server.start()
    _, port = server.get_host_and_port()
    yield f"http://127.0.0.1:{port}"
    server.stop()


@pytest.fixture(scope="session", autouse=True)
def s3_bucket_url(reflex_app_manager: AppManager, moto_server_url: str) -> str:
    """Create a public-read bucket in moto and point the app's S3 env vars at it.

    The bucket policy allows anonymous GET so the browser can load uploaded
    images directly from the moto endpoint, end to end.
    """
    client = boto3.client(
        "s3",
        endpoint_url=moto_server_url,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="us-east-1",
    )
    client.create_bucket(Bucket=S3_BUCKET_NAME)
    client.put_bucket_policy(
        Bucket=S3_BUCKET_NAME,
        Policy=json.dumps(
            {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*",
                    }
                ],
            }
        ),
    )
    bucket_url = f"{moto_server_url}/{S3_BUCKET_NAME}/"
    reflex_app_manager.settings.extra_env = {
        **reflex_app_manager.settings.extra_env,
        "S3_ENDPOINT_URL": moto_server_url,
        "S3_ACCESS_KEY_ID": "testing",
        "S3_SECRET_ACCESS_KEY": "testing",
        "AWS_DEFAULT_REGION": "us-east-1",
        "S3_BUCKET_NAME": S3_BUCKET_NAME,
        # Must end with "/" so urljoin() appends the object key.
        "S3_BUCKET_ACCESS_URL": bucket_url,
    }
    return bucket_url
