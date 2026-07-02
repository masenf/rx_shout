import pytest
from playwright.sync_api import Page, expect
from reflex_enterprise.testing import ReflexApp


@pytest.mark.usefixtures("alice_logged_in")
def test_login(reflex_app: ReflexApp, page: Page):
    # Expect the url to change to / after login
    expect(page).to_have_url(f"{reflex_app.url}/")
    inputs = page.get_by_role("textbox")
    expect(inputs).to_have_count(3)
    # Expect to see Alice Admin and email on the page
    expect(inputs.nth(0)).to_have_value("Alice Admin")
    expect(inputs.nth(1)).to_have_value("alice@example.com")
    expect(inputs.nth(2)).to_have_attribute("placeholder", "Enter text here...")
