"""Flag visibility: flags are private to the flagger, counts are admin-only."""

from helpers import ALICE, CAROL, login_as, logout, post_card
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


def test_flag_visibility_by_role(reflex_app: ReflexApp, page: Page, post_by_bob: str):
    """Only the flagger sees their own flag, and only the admin sees flag counts."""
    # Bob flags his own post.
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Flag", exact=True).click()
    page.get_by_role("button", name="Flag Post", exact=True).click()
    unflag_button = card.get_by_role("button", name="Unflag Post", exact=True)
    expect(unflag_button).to_be_visible()
    # Non-admins never see a flag count, not even on their own flag.
    expect(unflag_button.get_by_text("1")).to_have_count(0)

    # Carol (non-admin) sees no trace of bob's flag.
    logout(reflex_app, page)
    login_as(reflex_app, page, CAROL)
    card = post_card(page, post_by_bob)
    flag_button = card.get_by_role("button", name="Flag", exact=True)
    expect(flag_button).to_be_visible()
    expect(flag_button.get_by_text("1")).to_have_count(0)

    # Alice (admin) sees the flagged state and the count.
    logout(reflex_app, page)
    login_as(reflex_app, page, ALICE)
    card = post_card(page, post_by_bob)
    unflag_button = card.get_by_role("button", name="Unflag Post", exact=True)
    expect(unflag_button).to_be_visible()
    expect(unflag_button.get_by_text("1")).to_be_visible()

    # The admin's unflag clears every user's flag on the entry.
    unflag_button.click()
    expect(card.get_by_role("button", name="Flag", exact=True)).to_be_visible()


def test_non_admin_can_unflag_own_flag(
    reflex_app: ReflexApp, page: Page, post_by_bob: str
):
    """A non-admin can remove their own flag (and only their own)."""
    card = post_card(page, post_by_bob)
    card.get_by_role("button", name="Flag", exact=True).click()
    page.get_by_role("button", name="Flag Post", exact=True).click()
    unflag_button = card.get_by_role("button", name="Unflag Post", exact=True)
    expect(unflag_button).to_be_visible()
    # Bob unflags his own flag; the button returns to the un-flagged state.
    unflag_button.click()
    expect(card.get_by_role("button", name="Flag", exact=True)).to_be_visible()
