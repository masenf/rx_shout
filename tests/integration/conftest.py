"""Shared fixtures for the rx_shout integration tests."""

import pytest
from helpers import ALICE, BOB, create_post, login_as, logout
from playwright.sync_api import Page
from reflex_enterprise.testing import AppManager, ReflexApp


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
    }
