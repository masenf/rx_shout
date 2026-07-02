"""Image upload: preview, removal, and posting with an image."""

import base64
import uuid
from pathlib import Path

import pytest
from helpers import post_card
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp

# A valid 1x1 PNG.
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png_file(tmp_path: Path) -> Path:
    """Write a small PNG to disk for upload tests."""
    png_path = tmp_path / "pixel.png"
    png_path.write_bytes(PNG_BYTES)
    return png_path


def _upload_image(page: Page, png_file: Path):
    """Select the image in the upload dropzone and wait for the preview."""
    page.locator("input[type='file']").set_input_files(png_file)
    expect(page.locator("img[src*='_upload']").first).to_be_visible()


def test_upload_image_preview_and_remove(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, png_file: Path
):
    """An uploaded image shows a preview which can be removed before posting."""
    page.goto(f"{reflex_app.url}")
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible()
    _upload_image(page, png_file)
    # The dropzone is replaced by the preview.
    expect(page.get_by_role("button", name="Select or Drop Image")).to_have_count(0)
    # Remove the image via the X icon overlaying the preview.
    preview = page.locator("img[src*='_upload']").first
    preview.locator("..").locator("svg").click()
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible()
    expect(page.locator("img[src*='_upload']")).to_have_count(0)


def test_post_with_image(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, png_file: Path
):
    """A post with an uploaded image displays the image in the feed."""
    page.goto(f"{reflex_app.url}")
    _upload_image(page, png_file)
    post_content = f"image post {uuid.uuid4()}"
    page.get_by_placeholder("Enter text here...").fill(post_content)
    page.get_by_role("button", name="Post", exact=True).click()
    expect(page.get_by_text(post_content)).to_be_visible()
    card = post_card(page, post_content)
    expect(card.locator("img[src*='_upload']")).to_be_visible()
    # Clean up so other tests' image locators are unambiguous (alice is admin).
    card.get_by_role("button", name="Delete").click()
    expect(page.get_by_text(post_content)).not_to_be_visible()
