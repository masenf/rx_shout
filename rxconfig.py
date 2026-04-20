import reflex as rx

config = rx.Config(
    app_name="rx_shout",
    db_url="sqlite:///reflex.db",
    plugins=[rx.plugins.SitemapPlugin()],
)
