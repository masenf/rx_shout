"""Unit tests for the dev-only mock OIDC provider wiring."""

import contextlib
import socket
from collections.abc import Callable
from unittest import mock

import pytest

import rx_shout.auth.authz
from rx_shout.auth import mock as mock_auth


def test_issuer_uri_requires_running_provider(
    monkeypatch: pytest.MonkeyPatch, run_coro: Callable
):
    """_issuer_uri raises when the mock provider was never started."""
    monkeypatch.setattr(mock_auth, "_mock_oidc_issuer", None)
    state = mock_auth.MockAuthState()
    with pytest.raises(RuntimeError, match="not running"):
        run_coro(state._issuer_uri())


def test_issuer_uri_of_running_provider(
    monkeypatch: pytest.MonkeyPatch, run_coro: Callable
):
    """_issuer_uri returns the issuer recorded by the lifespan task."""
    monkeypatch.setattr(mock_auth, "_mock_oidc_issuer", "http://localhost:1234")
    state = mock_auth.MockAuthState()
    assert run_coro(state._issuer_uri()) == "http://localhost:1234"
    assert run_coro(state._client_id()) == "rx-shout-dev"


def test_register_mock_auth_noop_in_prod(monkeypatch: pytest.MonkeyPatch):
    """In prod mode the mock provider is never registered."""
    monkeypatch.setattr(rx_shout.auth.authz, "is_prod_mode", lambda: True)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert not mock_auth.mock_auth_enabled()
    app = mock.Mock()
    mock_auth.register_mock_auth(app)
    app.register_lifespan_task.assert_not_called()


def test_register_mock_auth_registers_in_dev(monkeypatch: pytest.MonkeyPatch):
    """In dev mode the mock provider lifespan task is registered."""
    monkeypatch.setattr(rx_shout.auth.authz, "is_prod_mode", lambda: False)
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    assert mock_auth.mock_auth_enabled()
    app = mock.Mock()
    mock_auth.register_mock_auth(app)
    app.register_lifespan_task.assert_called_once_with(mock_auth._mock_oidc_lifespan)


def test_mock_oidc_lifespan_port_fallback(run_coro: Callable):
    """When the preferred port is taken, the provider binds a random port."""

    async def _exercise():
        # Occupy the preferred port (unless something else already holds it,
        # e.g. the app under test's own provider during integration runs).
        sock = socket.socket()
        with contextlib.suppress(OSError):
            sock.bind(("127.0.0.1", mock_auth.MOCK_OIDC_PORT))
            sock.listen(1)
        try:
            async with mock_auth._mock_oidc_lifespan():
                issuer = mock_auth._mock_oidc_issuer
                assert issuer is not None
                assert not issuer.endswith(f":{mock_auth.MOCK_OIDC_PORT}")
        finally:
            sock.close()
        # The lifespan clears the issuer on the way out.
        assert mock_auth._mock_oidc_issuer is None

    run_coro(_exercise())
