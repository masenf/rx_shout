"""This is an shoutbox-like app for posting text and images."""
import reflex as rx

from .components.entry import entry_view
from .components.form import submission_form
from .state import State


@rx.page(
    title="rx_shout",
    description="A shoutbox-like app for anonymously posting text and images.",
    on_load=State.on_load,
)
def index() -> rx.Component:
    return rx.fragment(
        rx.color_mode.button(rx.color_mode.icon(), float="right"),
        rx.center(
            rx.vstack(
                rx.card(
                    submission_form(),
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        State.entries,
                        entry_view,
                    ),
                    gap="2em",
                    margin_y="2em",
                    width="100%",
                ),
                width=["100vw", "75vw", "75vw", "50vw", "50vw"],
            ),
            width="100%",
        ),
    )


app = rx.App()