"""Admin vs non-admin moderation surfaces: delete, ban/unban."""

from helpers import ALICE, BOB, login_as, logout, post_card
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


def test_non_admin_has_no_moderation_controls(
    reflex_app: ReflexApp, page: Page, post_by_bob: str
):
    """A non-admin does not see delete or ban buttons, even on their own post."""
    card = post_card(page, post_by_bob)
    # The like button proves the entry actions rendered...
    expect(card.get_by_role("button", name="Like")).to_be_visible()
    # ...but none of the admin-only controls did.
    expect(card.get_by_role("button", name="Delete")).to_have_count(0)
    expect(card.get_by_role("button", name="Ban User")).to_have_count(0)
    expect(card.get_by_role("button", name="Unban User")).to_have_count(0)


def test_admin_sees_moderation_controls(
    reflex_app: ReflexApp, page: Page, post_by_bob: str
):
    """The admin sees delete and ban buttons on another user's post."""
    logout(reflex_app, page)
    login_as(reflex_app, page, ALICE)
    card = post_card(page, post_by_bob)
    expect(card.get_by_role("button", name="Delete")).to_be_visible()
    expect(card.get_by_role("button", name="Ban User")).to_be_visible()


def test_admin_can_delete_other_users_post(
    reflex_app: ReflexApp, page: Page, post_by_bob: str
):
    """The admin can delete another user's post and it stays gone."""
    logout(reflex_app, page)
    login_as(reflex_app, page, ALICE)
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Delete").click()
    expect(page.get_by_text(post_by_bob)).not_to_be_visible()
    # The post is gone for its author too.
    logout(reflex_app, page)
    login_as(reflex_app, page, BOB)
    expect(page.get_by_placeholder("Enter text here...")).to_be_visible()
    expect(page.get_by_text(post_by_bob)).to_have_count(0)


def test_admin_can_ban_and_unban_user(
    reflex_app: ReflexApp, page: Page, post_by_bob: str
):
    """A banned user can still log in, but cannot post or like."""
    logout(reflex_app, page)
    login_as(reflex_app, page, ALICE)
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Ban User").click()
    expect(card.get_by_role("button", name="Unban User")).to_be_visible()

    # Bob can still log in...
    logout(reflex_app, page)
    login_as(reflex_app, page, BOB)
    # ...but the submission form is replaced with the sign-in prompt.
    expect(page.get_by_role("button", name="Sign in")).to_be_visible()
    expect(page.get_by_placeholder("Enter text here...")).to_have_count(0)
    # And liking a post is rejected by the backend.
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Like").click()
    page.wait_for_timeout(1000)
    expect(card.get_by_role("button", name="Unlike")).to_have_count(0)

    # The admin unbans bob and he can post again.
    logout(reflex_app, page)
    login_as(reflex_app, page, ALICE)
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Unban User").click()
    expect(card.get_by_role("button", name="Ban User")).to_be_visible()
    logout(reflex_app, page)
    login_as(reflex_app, page, BOB)
    expect(page.get_by_placeholder("Enter text here...")).to_be_visible()
