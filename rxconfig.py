import reflex as rx
import reflex_enterprise as rxe


config = rxe.Config(
    app_name="rx_shout",
    db_url="sqlite:///reflex.db",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rxe.auth.AuthPlugin(auth_providers=["rx_shout.auth.GoogleAuthState"])
    ],
)
