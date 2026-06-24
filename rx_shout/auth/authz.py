import reflex_enterprise as rxe


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
