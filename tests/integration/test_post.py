from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


def test_like_unlike_post(reflex_app: ReflexApp, page: Page, post_by_alice: str):
    page.goto(f"{reflex_app.url}")
    post_card = page.get_by_text(post_by_alice).locator("..").locator("..").locator("..")
    like_button = post_card.get_by_role("button", name="Like")
    like_button.click()
    # Expect the like button to change to unlike
    unlike_button = post_card.get_by_role("button", name="Unlike")
    expect(unlike_button).to_be_visible()
    # Expect the like count to be 1
    expect(unlike_button.get_by_text("1")).to_be_visible()
    unlike_button.click()
    # Expect the like button to change back to like
    expect(like_button).to_be_visible()
    delete_button = post_card.get_by_role("button", name="Delete")
    delete_button.click()


def test_flag_post(reflex_app: ReflexApp, page: Page, post_by_alice: str):
    page.goto(f"{reflex_app.url}")
    post_card = page.get_by_text(post_by_alice).locator("..").locator("..").locator("..")
    flag_button = post_card.get_by_role("button", name="Flag")
    flag_button.click()
    # Click the flag button in the popover
    page.get_by_role("button", name="Flag Post", exact=True).click()
    # Expect the flag button to change to unflag
    unflag_button = post_card.get_by_role("button", name="Unflag Post", exact=True)
    expect(unflag_button).to_be_visible()
    # Expect the flag count to be 1
    expect(unflag_button.get_by_text("1")).to_be_visible()
    unflag_button.click()
    # Expect the flag button to change back to flag
    expect(flag_button).to_be_visible()
