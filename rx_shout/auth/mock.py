"""Dev-only mock OIDC provider for logging in as different users easily.

This wires up an in-process mock OpenID Connect provider
(`oidc-provider-mock <https://pypi.org/project/oidc-provider-mock/>`_) so a
developer can sign in as arbitrary users without a real IdP. It is **only ever
active in dev mode** (see :func:`mock_auth_enabled`) and ``oidc-provider-mock``
is a dev-only dependency, so all imports of it are kept local to the functions
that need them — a production install that omits the package still imports this
module cleanly.

Wiring:
    * ``rxconfig.py`` adds ``MockAuthState`` to the ``AuthPlugin`` providers in
      dev, which makes a "Login with Mock" button appear on ``/login``.
    * ``rx_shout.py`` calls :func:`register_mock_auth` to start the mock
      provider server alongside the app in dev.
"""

from __future__ import annotations

import contextlib
from collections.abc import AsyncIterator

import reflex as rx
import reflex_enterprise as rxe
from reflex.utils.exec import is_prod_mode

# Fixed port so the issuer URI is stable across restarts (the default the
# library uses too). The browser and the backend both reach it on localhost.
MOCK_OIDC_PORT = 9400
MOCK_OIDC_ISSUER = f"http://localhost:{MOCK_OIDC_PORT}"


def mock_auth_enabled() -> bool:
    """Whether the dev mock auth provider should be active (dev mode only)."""
    return not is_prod_mode()


class MockAuthState(rxe.auth.OIDCAuthState, rx.State):
    """OIDC provider backed by the local ``oidc-provider-mock`` server (dev only).

    The mock accepts any client id/secret without registration, so the issuer
    and client id are hardcoded here instead of read from env vars.
    """

    __provider__ = "mock"

    async def _issuer_uri(self) -> str:
        return MOCK_OIDC_ISSUER

    async def _client_id(self) -> str:
        return "rx-shout-dev"


def _seed_users() -> list:
    """Predefined users offered by the mock provider's login form.

    Sign in with one of these subjects (or type any other email to create a
    user on the fly). The first user to ever sign in becomes ``UserInfo.id == 1``,
    which the app treats as the admin (see ``UserState.is_admin``) — so sign in
    as Alice first to get an admin account.
    """
    from oidc_provider_mock import User

    def _user(sub: str, name: str) -> "User":
        return User(
            sub=sub,
            claims={
                "email": sub,
                "email_verified": True,
                "name": name,
                "picture": f"https://api.dicebear.com/9.x/thumbs/svg?seed={name}",
            },
        )

    return [
        _user("alice@example.com", "Alice Admin"),
        _user("bob@example.com", "Bob Builder"),
        _user("carol@example.com", "Carol Coder"),
    ]


@contextlib.asynccontextmanager
async def _mock_oidc_lifespan() -> AsyncIterator[None]:
    """Run the mock OIDC provider on a background thread for the app's lifetime."""
    from oidc_provider_mock import run_server_in_thread

    with run_server_in_thread(port=MOCK_OIDC_PORT, user_claims=_seed_users()) as server:
        print(  # noqa: T201 - surfaced in the dev server log
            f"Mock OIDC provider running at http://localhost:{server.server_port}"
        )
        yield


def register_mock_auth(app: rxe.App) -> None:
    """In dev mode, start the mock OIDC provider alongside the app.

    No-op in production. Safe to call unconditionally.
    """
    if not mock_auth_enabled():
        return
    app.register_lifespan_task(_mock_oidc_lifespan)
