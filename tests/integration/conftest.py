import re
import uuid

import pytest
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import AppManager, ReflexApp


def _login_as(reflex_app: ReflexApp, page: Page, email: str):
    page.goto(f"{reflex_app.url}/login?redirect_to=%2F")
    page.get_by_text("Login with Mock", exact=True).click()
    # Login with Mock provider
    page.get_by_text(email, exact=True).click()
    # Expect the url to change to / after login
    expect(page).to_have_url(f"{reflex_app.url}/")


def _logout(reflex_app: ReflexApp, page: Page):
    page.goto(f"{reflex_app.url}/logout?redirect_to=%2F")
    page.get_by_text("End session", exact=True).click()
    # Expect the url to change to / after logout
    expect(page).to_have_url(re.compile(re.escape(reflex_app.url + "/?") + ".*"))


@pytest.fixture
def alice_logged_in(reflex_app: ReflexApp, page: Page):
    _login_as(reflex_app, page, "alice@example.com")
    yield
    _logout(reflex_app, page)


@pytest.fixture
def post_by_alice(reflex_app: ReflexApp, page: Page, alice_logged_in: None):
    page.goto(f"{reflex_app.url}")
    post_content = f"test_create_post {uuid.uuid4()}"
    page.get_by_placeholder("Enter text here...").fill(post_content)
    page.get_by_role("button", name="Post", exact=True).click()
    # Expect the post to be visible on the page
    expect(page.get_by_text(post_content)).to_be_visible()
    return post_content


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
