"""Like visibility across accounts and for anonymous visitors."""

from helpers import BOB, login_as, logout, post_card
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


def test_likes_visible_across_accounts(
    reflex_app: ReflexApp, page: Page, post_by_alice: str
):
    """Bob sees alice's like count, and his own like adds to it but not hers."""
    # Alice likes her own post.
    card = post_card(page, post_by_alice)
    card.get_by_role("button", name="Like").click()
    unlike_button = card.get_by_role("button", name="Unlike")
    expect(unlike_button).to_be_visible()
    expect(unlike_button.get_by_text("1")).to_be_visible()

    # Bob sees the count, but the button is in the un-liked state for him.
    logout(reflex_app, page)
    login_as(reflex_app, page, BOB)
    card = post_card(page, post_by_alice)
    like_button = card.get_by_role("button", name="Like")
    expect(like_button).to_be_visible()
    expect(like_button.get_by_text("1")).to_be_visible()

    # Bob's like is added to alice's.
    like_button.click()
    unlike_button = card.get_by_role("button", name="Unlike")
    expect(unlike_button).to_be_visible()
    expect(unlike_button.get_by_text("2")).to_be_visible()

    # Un-liking only removes bob's like, not alice's.
    unlike_button.click()
    expect(like_button).to_be_visible()
    expect(like_button.get_by_text("1")).to_be_visible()


def test_anonymous_sees_posts_but_cannot_interact(
    reflex_app: ReflexApp, page: Page, post_by_alice: str
):
    """Logged-out visitors see the feed and like counts, but cannot post or like."""
    # Alice likes her own post so there is a count to observe.
    card = post_card(page, post_by_alice)
    card.get_by_role("button", name="Like").click()
    expect(card.get_by_role("button", name="Unlike")).to_be_visible()
    logout(reflex_app, page)

    page.goto(f"{reflex_app.url}")
    # No submission form, just the sign-in prompt.
    expect(page.get_by_role("button", name="Sign in")).to_be_visible()
    expect(page.get_by_placeholder("Enter text here...")).to_have_count(0)
    # The post and its like count are still visible.
    card = post_card(page, post_by_alice)
    like_button = card.get_by_role("button", name="Like")
    expect(like_button).to_be_visible()
    expect(like_button.get_by_text("1")).to_be_visible()
    # Clicking like is rejected by the backend.
    like_button.click()
    page.wait_for_timeout(1000)
    expect(card.get_by_role("button", name="Unlike")).to_have_count(0)
