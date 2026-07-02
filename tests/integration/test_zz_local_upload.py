"""Image posting without S3 configured (images stay in local upload storage).

This module restarts the app under test *without* the S3 env vars, so it should
run after the other integration modules — the ``zz`` in the filename keeps it
last in alphabetical collection order.
"""

import uuid
from pathlib import Path

import pytest
from helpers import post_card, preview_filename, upload_image
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import AppManager, ReflexApp


@pytest.fixture(scope="module", autouse=True)
def no_s3_app(reflex_app_manager: AppManager):
    """Strip the S3 env vars and restart the app under test without them."""
    previous_extra_env = dict(reflex_app_manager.settings.extra_env)
    reflex_app_manager.settings.extra_env = {
        key: value
        for key, value in reflex_app_manager.settings.extra_env.items()
        if not key.startswith("S3_")
    }
    reflex_app_manager.stop_all()
    yield
    # Restore settings so that other tests (if any) run with S3 configured.
    reflex_app_manager.settings.extra_env = previous_extra_env
    reflex_app_manager.stop_all()


def test_post_with_image_stored_locally(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, png_file: Path
):
    """Without S3 configured, the posted image is served from the upload dir."""
    page.goto(f"{reflex_app.url}")
    upload_image(page, png_file)
    filename = preview_filename(page)
    post_content = f"local image post {uuid.uuid4()}"
    page.get_by_placeholder("Enter text here...").fill(post_content)
    page.get_by_role("button", name="Post", exact=True).click()
    expect(page.get_by_text(post_content)).to_be_visible()
    card = post_card(page, post_content)
    # The feed image is served from the backend's upload route, not S3.
    feed_image = card.locator(f"img[src$='_upload/{filename}']")
    expect(feed_image).to_be_visible()
    # Clean up (alice is admin).
    card.get_by_role("button", name="Delete").click()
    expect(page.get_by_text(post_content)).not_to_be_visible()
