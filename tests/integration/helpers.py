"""Shared helpers for driving the rx_shout app in integration tests.

These are plain functions (not fixtures) so tests that switch between users
mid-test can call them directly.
"""

import contextlib
import re
import uuid

from playwright.sync_api import Locator, Page, expect
from reflex_enterprise.testing import ReflexApp

# Seed users offered by the dev-mode mock OIDC provider (see rx_shout/auth/mock.py).
# The first user to ever sign in becomes UserInfo.id == 1, which the app treats
# as the admin -- the `admin_user_exists` fixture guarantees that is Alice.
ALICE = "alice@example.com"
BOB = "bob@example.com"
CAROL = "carol@example.com"


def login_as(reflex_app: ReflexApp, page: Page, email: str):
    """Log in via the mock OIDC provider as the given seed user."""
    page.goto(f"{reflex_app.url}/login?redirect_to=%2F")
    page.get_by_text("Login with Mock", exact=True).click()
    # Pick the user on the mock provider's authorization form.
    page.get_by_text(email, exact=True).click()
    # Expect the url to change to / after login
    expect(page).to_have_url(f"{reflex_app.url}/")


def logout(reflex_app: ReflexApp, page: Page):
    """End the current session (tolerates already being logged out)."""
    page.goto(f"{reflex_app.url}/logout?redirect_to=%2F")
    # An anonymous visitor is redirected home without the provider's
    # end-session confirmation page.
    with contextlib.suppress(Exception):
        page.get_by_text("End session", exact=True).click(timeout=5000)
    # Back on the app, with or without a query string.
    expect(page).to_have_url(re.compile(re.escape(reflex_app.url) + r"/?(\?.*)?$"))


def create_post(page: Page, prefix: str = "post") -> str:
    """Submit a new text post from the currently loaded feed and return its content."""
    post_content = f"{prefix} {uuid.uuid4()}"
    page.get_by_placeholder("Enter text here...").fill(post_content)
    page.get_by_role("button", name="Post", exact=True).click()
    # Expect the post to be visible on the page
    expect(page.get_by_text(post_content)).to_be_visible()
    return post_content


def post_card(page: Page, post_content: str) -> Locator:
    """Locate the card containing a post's action buttons from its text content."""
    return page.get_by_text(post_content).locator("..").locator("..").locator("..")
