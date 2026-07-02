"""Image upload: preview, removal, progress/cancel, and posting to S3 (moto)."""

import json
import secrets
import uuid
from pathlib import Path

import httpx
import pytest
from helpers import PNG_BYTES, UPLOAD_DIR, post_card, preview_filename, upload_image
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp

# The dropzone rejects files over 5 MB (see image_upload.MAX_FILE_SIZE).
BIG_PNG_SIZE = 4 * 1024**2  # accepted; big enough for interim progress events
TOO_BIG_PNG_SIZE = 6 * 1024**2  # rejected by the dropzone


@pytest.fixture
def big_png_file(tmp_path: Path) -> Path:
    """A ~4 MB .png file, accepted by the dropzone but slow to upload."""
    png_path = tmp_path / "big.png"
    png_path.write_bytes(PNG_BYTES + secrets.token_bytes(BIG_PNG_SIZE))
    return png_path


@pytest.fixture
def too_big_png_file(tmp_path: Path) -> Path:
    """A ~6 MB .png file, rejected by the dropzone's max_size."""
    png_path = tmp_path / "too_big.png"
    png_path.write_bytes(PNG_BYTES + secrets.token_bytes(TOO_BIG_PNG_SIZE))
    return png_path


def _throttle_upload(page: Page, bytes_per_second: int):
    """Throttle upload bandwidth via CDP so progress events are observable."""
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    cdp.send(
        "Network.emulateNetworkConditions",
        {
            "offline": False,
            "latency": 0,
            "downloadThroughput": -1,
            "uploadThroughput": bytes_per_second,
        },
    )


def test_upload_image_preview_and_remove(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, png_file: Path
):
    """An uploaded image shows a preview which can be removed before posting."""
    page.goto(f"{reflex_app.url}")
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible()
    upload_image(page, png_file)
    # The dropzone is replaced by the preview.
    expect(page.get_by_role("button", name="Select or Drop Image")).to_have_count(0)
    # Remove the image via the X icon overlaying the preview.
    preview = page.locator("img[src*='_upload']").first
    preview.locator("..").locator("svg").click()
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible()
    expect(page.locator("img[src*='_upload']")).to_have_count(0)


def test_remove_preview_with_missing_file(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, png_file: Path
):
    """Removing the preview tolerates the upload file already being gone on disk."""
    page.goto(f"{reflex_app.url}")
    upload_image(page, png_file)
    uploaded = UPLOAD_DIR / preview_filename(page)
    assert uploaded.exists()
    uploaded.unlink()
    preview = page.locator("img[src*='_upload']").first
    preview.locator("..").locator("svg").click()
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible()
    expect(page.locator("img[src*='_upload']")).to_have_count(0)


def test_post_with_image(
    reflex_app: ReflexApp,
    page: Page,
    alice_logged_in: None,
    png_file: Path,
    s3_bucket_url: str,
):
    """A posted image is uploaded to S3 and served from the bucket URL."""
    page.goto(f"{reflex_app.url}")
    upload_image(page, png_file)
    filename = preview_filename(page)
    local_file = UPLOAD_DIR / filename
    assert local_file.exists()
    post_content = f"image post {uuid.uuid4()}"
    page.get_by_placeholder("Enter text here...").fill(post_content)
    page.get_by_role("button", name="Post", exact=True).click()
    expect(page.get_by_text(post_content)).to_be_visible()
    card = post_card(page, post_content)
    # The feed image is served from the moto S3 endpoint, not the upload dir.
    feed_image = card.locator(f"img[src='{s3_bucket_url}{filename}']")
    expect(feed_image).to_be_visible()
    # The browser can fetch the object end-to-end and it round-trips intact.
    response = page.request.get(f"{s3_bucket_url}{filename}")
    assert response.status == 200
    assert response.body() == PNG_BYTES
    # The local upload was deleted after landing in S3 (delete_original=True).
    assert not local_file.exists()
    # Clean up so other tests' image locators are unambiguous (alice is admin).
    card.get_by_role("button", name="Delete").click()
    expect(page.get_by_text(post_content)).not_to_be_visible()


def test_post_image_without_text(
    reflex_app: ReflexApp,
    page: Page,
    alice_logged_in: None,
    png_file: Path,
    s3_bucket_url: str,
):
    """An image-only post is allowed and stores empty text."""
    page.goto(f"{reflex_app.url}")
    upload_image(page, png_file)
    filename = preview_filename(page)
    page.get_by_role("button", name="Post", exact=True).click()
    feed_image = page.locator(f"img[src='{s3_bucket_url}{filename}']")
    expect(feed_image).to_be_visible()
    # Clean up (alice is admin); the entry vstack contains the delete button.
    feed_image.locator("..").get_by_role("button", name="Delete").click()
    expect(feed_image).not_to_be_visible()


def test_empty_post_shows_error(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """Posting with no text and no image shows a validation error."""
    page.goto(f"{reflex_app.url}")
    page.get_by_role("button", name="Post", exact=True).click()
    expect(
        page.get_by_text("You have to at least write something or upload an image.")
    ).to_be_visible()


def test_upload_progress_and_cancel(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, big_png_file: Path
):
    """A slow upload shows the progress bar and can be cancelled midway."""
    page.goto(f"{reflex_app.url}")
    _throttle_upload(page, 512 * 1024)  # ~8s for the 4 MB file
    page.locator("input[type='file']").set_input_files(big_png_file)
    # Interim progress replaces the dropzone with a progress bar...
    expect(page.get_by_role("progressbar")).to_be_visible()
    # ...and swaps the Post button for a Cancel button.
    page.get_by_role("button", name="Cancel", exact=True).click()
    # After cancelling, the dropzone returns and no preview is shown.
    expect(page.get_by_role("button", name="Select or Drop Image")).to_be_visible(
        timeout=15_000
    )
    expect(page.locator("img[src*='_upload']")).to_have_count(0)


def test_upload_without_valid_user_is_noop(reflex_app: ReflexApp):
    """A raw POST to /_upload with an unknown client token changes nothing.

    The dropzone is only rendered for logged-in users, so the server-side
    guard in UploadState.handle_upload can only be exercised by hitting the
    upload endpoint directly with a client token that maps to no session.
    The handler must return early: no state deltas and no file on disk.
    """
    from rx_shout.components.image_upload import UploadState

    handler_name = f"{UploadState.get_full_name()}.handle_upload"
    files_before = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
    response = httpx.post(
        f"{reflex_app.backend_url or reflex_app.url}/_upload",
        headers={
            "reflex-client-token": str(uuid.uuid4()),
            "reflex-event-handler": handler_name,
        },
        files={"files": ("evil.png", PNG_BYTES, "image/png")},
    )
    assert response.status_code == 200
    print("RESPONSE TEXT:", repr(response.text))
    print("APP LOGS TAIL:", reflex_app.logs()[-3000:])
    updates = [json.loads(line) for line in response.text.splitlines() if line.strip()]
    assert not any(update.get("delta") for update in updates)
    files_after = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
    assert files_after == files_before


def test_oversized_upload_rejected(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None, too_big_png_file: Path
):
    """A file over the 5 MB limit is rejected with a toast and no preview."""
    page.goto(f"{reflex_app.url}")
    page.locator("input[type='file']").set_input_files(too_big_png_file)
    expect(page.get_by_text("File size too large or invalid format")).to_be_visible()
    expect(page.locator("img[src*='_upload']")).to_have_count(0)
