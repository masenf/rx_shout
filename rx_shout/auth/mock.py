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
from datetime import timedelta

import reflex as rx
import reflex_enterprise as rxe

from .authz import mock_auth_enabled

# Preferred port, so the issuer URI is stable across restarts. If it is
# already taken (e.g. another dev instance running concurrently), the server
# falls back to a system-assigned port.
MOCK_OIDC_PORT = 9400

# Issuer URI of the running mock provider, filled in by the lifespan task once
# the port is known. The browser and the backend both reach it on localhost.
_mock_oidc_issuer: str | None = None


class MockAuthState(rxe.auth.OIDCAuthState, rx.State):
    """OIDC provider backed by the local ``oidc-provider-mock`` server (dev only).

    The mock accepts any client id/secret without registration, so the issuer
    and client id are hardcoded here instead of read from env vars.
    """

    __provider__ = "mock"

    async def _issuer_uri(self) -> str:
        if _mock_oidc_issuer is None:
            raise RuntimeError(
                "Mock OIDC provider is not running; "
                "was register_mock_auth() called on the app?"
            )
        return _mock_oidc_issuer

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

    def _start(port: int):
        return run_server_in_thread(
            port=port,
            user_claims=_seed_users(),
            access_token_max_age=timedelta(minutes=2),
        )

    global _mock_oidc_issuer
    with contextlib.ExitStack() as stack:
        try:
            server = stack.enter_context(_start(MOCK_OIDC_PORT))
        except OSError, SystemExit:
            # Port taken (e.g. another dev instance) — let the OS pick one.
            # werkzeug turns the bind EADDRINUSE into sys.exit(1), hence
            # SystemExit rather than OSError.
            server = stack.enter_context(_start(0))
        _mock_oidc_issuer = f"http://localhost:{server.server_port}"
        print(  # noqa: T201 - surfaced in the dev server log
            f"Mock OIDC provider running at {_mock_oidc_issuer}"
        )
        try:
            yield
        finally:
            _mock_oidc_issuer = None


def register_mock_auth(app: rxe.App) -> None:
    """In dev mode, start the mock OIDC provider alongside the app.

    No-op in production. Safe to call unconditionally.
    """
    if not mock_auth_enabled():
        return
    app.register_lifespan_task(_mock_oidc_lifespan)
