"""Topic feeds: isolation from the main feed and description management."""

import uuid
from urllib.parse import quote

from helpers import create_post
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


def _topic_name() -> str:
    return f"topic-{uuid.uuid4().hex[:8]}"


def test_topic_feed_is_isolated_from_main_feed(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """Posts made in a topic do not appear on the main feed, and vice versa."""
    page.goto(f"{reflex_app.url}")
    main_post = create_post(page, prefix="main_feed_post")

    topic = _topic_name()
    page.goto(f"{reflex_app.url}/?topic={topic}")
    # A topic without a description shows its name as the heading.
    expect(page.get_by_role("heading", name=topic)).to_be_visible()
    topic_post = create_post(page, prefix="topic_post")
    # The main feed post is not in the topic feed.
    expect(page.get_by_text(main_post)).to_have_count(0)

    page.goto(f"{reflex_app.url}/")
    expect(page.get_by_text(main_post)).to_be_visible()
    # The topic post is not on the main feed.
    expect(page.get_by_text(topic_post)).to_have_count(0)

    # Returning to the topic still shows its post.
    page.goto(f"{reflex_app.url}/?topic={topic}")
    expect(page.get_by_text(topic_post)).to_be_visible()


def test_topic_description_from_query_param(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """A new topic picks up its description from the `description` query param."""
    topic = _topic_name()
    description = f"All about {topic}"
    page.goto(f"{reflex_app.url}/?topic={topic}&description={quote(description)}")
    expect(page.get_by_role("heading", name=description)).to_be_visible()


def test_admin_can_edit_topic_description(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """The admin can open the topic heading editor and save a new description."""
    topic = _topic_name()
    page.goto(f"{reflex_app.url}/?topic={topic}")
    page.get_by_role("heading", name=topic).click()
    editor = page.get_by_placeholder("Edit topic description...")
    expect(editor).to_be_visible()
    new_description = f"Updated description {uuid.uuid4().hex[:8]}"
    editor.fill(new_description)
    page.get_by_role("button", name="Save Description").click()
    expect(page.get_by_role("heading", name=new_description)).to_be_visible()
    # The new description survives a reload.
    page.goto(f"{reflex_app.url}/?topic={topic}")
    expect(page.get_by_role("heading", name=new_description)).to_be_visible()


def test_admin_can_cancel_topic_description_edit(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """Cancelling the editor leaves the description unchanged."""
    topic = _topic_name()
    page.goto(f"{reflex_app.url}/?topic={topic}")
    page.get_by_role("heading", name=topic).click()
    editor = page.get_by_placeholder("Edit topic description...")
    expect(editor).to_be_visible()
    editor.fill("should be discarded")
    page.get_by_role("button", name="Cancel Edit").click()
    expect(editor).to_have_count(0)
    expect(page.get_by_role("heading", name=topic)).to_be_visible()


def test_non_admin_cannot_edit_topic_description(
    reflex_app: ReflexApp, page: Page, bob_logged_in: None
):
    """Clicking the topic heading as a non-admin does not open the editor."""
    topic = _topic_name()
    page.goto(f"{reflex_app.url}/?topic={topic}")
    heading = page.get_by_role("heading", name=topic)
    expect(heading).to_be_visible()
    heading.click()
    page.wait_for_timeout(1000)
    expect(page.get_by_placeholder("Edit topic description...")).to_have_count(0)


def test_edit_description_on_main_feed_is_noop(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """The main feed has no topic, so saving a description changes nothing."""
    page.goto(f"{reflex_app.url}/")
    heading = page.get_by_role("heading", name="Shout Your Thoughts Into the Void")
    heading.click()
    editor = page.get_by_placeholder("Edit topic description...")
    expect(editor).to_be_visible()
    editor.fill("description without a topic")
    page.get_by_role("button", name="Save Description").click()
    # The editor closes and the default heading is unchanged.
    expect(editor).to_have_count(0)
    expect(heading).to_be_visible()
    page.goto(f"{reflex_app.url}/")
    expect(
        page.get_by_role("heading", name="Shout Your Thoughts Into the Void")
    ).to_be_visible()


def test_saving_empty_description_is_noop(
    reflex_app: ReflexApp, page: Page, alice_logged_in: None
):
    """Saving the editor with an empty value closes it without changes."""
    topic = _topic_name()
    page.goto(f"{reflex_app.url}/?topic={topic}")
    page.get_by_role("heading", name=topic).click()
    editor = page.get_by_placeholder("Edit topic description...")
    expect(editor).to_be_visible()
    editor.fill("")
    page.get_by_role("button", name="Save Description").click()
    expect(editor).to_have_count(0)
    expect(page.get_by_role("heading", name=topic)).to_be_visible()
