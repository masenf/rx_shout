import reflex as rx
import reflex_enterprise as rxe
from reflex.utils.exec import is_prod_mode

from rx_shout.auth.authz import require_valid_user

# Providers are referenced by import-path string: provider modules can't be
# imported here (they call get_config() at import, which loads this file). The
# mock provider is only offered in dev mode.
auth_providers = ["rx_shout.auth.google.GoogleAuthState"]
if not is_prod_mode():
    auth_providers.append("rx_shout.auth.mock.MockAuthState")

config = rxe.Config(
    app_name="rx_shout",
    db_url="sqlite:///reflex.db",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rxe.auth.AuthPlugin(auth=require_valid_user, auth_providers=auth_providers),
    ],
)
