import os

import reflex_enterprise as rxe
from reflex.utils.exec import is_prod_mode


def mock_auth_enabled() -> bool:
    """Whether the dev mock auth provider should be active (dev mode only)."""
    return not is_prod_mode() or bool(os.environ.get("PYTEST_CURRENT_TEST"))


async def require_valid_user(ctx: rxe.auth.AuthContext) -> bool:
    """Require the user to be a valid user to run the handler/var."""
    from ..state import UserState

    user_state = await ctx.auth_user_state.get_state(UserState)
    return user_state._is_valid_user()


async def require_admin(ctx: rxe.auth.AuthContext) -> bool:
    """Require the user to be an admin to run the handler/var."""
    from ..state import UserState

    user_state = await ctx.auth_user_state.get_state(UserState)
    return user_state.is_admin
