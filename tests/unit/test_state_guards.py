"""Unit tests for state guard helpers not reachable through the UI flows.

These exercise small guard branches directly; the interesting user-visible
behavior is covered by the integration tests.
"""

from collections.abc import Callable
from unittest import mock

from rx_shout.components.image_upload import UploadState
from rx_shout.state import PostFormState, UserFlagState, UserState


def test_handle_upload_invalid_user(run_coro: Callable):
    """An upload from a session without a valid user is dropped outright.

    This guard backs up the AuthPlugin middleware, which already denies
    unauthenticated /_upload requests before the handler runs (see
    test_upload.test_upload_without_valid_user_is_noop), so it can only be
    exercised by calling the handler directly.
    """
    state = UploadState(_reflex_internal_init=True)
    user_state = mock.Mock(spec=UserState)
    user_state._is_valid_user.return_value = False

    async def _drain() -> list:
        return [event async for event in state.handle_upload([mock.Mock()])]

    with mock.patch.object(
        UploadState, "get_state", mock.AsyncMock(return_value=user_state)
    ):
        # The handler bails before emitting any event (not even the toast).
        assert run_coro(_drain()) == []


def test_delete_uploaded_image_without_upload(run_coro: Callable):
    """Deleting when no image was uploaded is a no-op."""
    state = PostFormState(_reflex_internal_init=True)
    state.image_relative_path = ""
    run_coro(state.delete_uploaded_image())
    assert state.image_relative_path == ""


def test_load_user_flags_invalid_user(run_coro: Callable):
    """An invalid user gets empty flags without touching the database."""
    state = UserFlagState(_reflex_internal_init=True)
    state.user_entry_flags = {1: {"like": True}}
    user_state = mock.Mock(spec=UserState)
    user_state._is_valid_user.return_value = False
    run_coro(state._load_user_flags(None, user_state))
    assert state.user_entry_flags == {}
