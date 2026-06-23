"""This is an shoutbox-like app for posting text and images."""

import importlib.metadata
import sys
import reflex as rx
import reflex_enterprise as rxe

from .components.entry import entry_view
from .components.google_auth import (
    auth_error_callout,
    google_auth_button,
)
from .components.form import submission_form
from .state import PostFormState, TopicState, UserState


def index() -> rx.Component:
    return rx.fragment(
        rx.hstack(
            rx.icon("sun", size=16),
            rx.color_mode.switch(size="1"),
            rx.icon("moon", size=16),
            margin="8px",
            float="right",
        ),
        rx.center(
            rx.vstack(
                rx.card(
                    rx.cond(
                        UserState.user_info.enabled,
                        submission_form(),
                        rx.flex(
                            auth_error_callout(),
                            rx.spacer(),
                            google_auth_button(),
                            justify="end",
                            width="100%",
                            on_click=PostFormState.set_form_error(""),
                        ),
                    ),
                    width="100%",
                ),
                rx.vstack(
                    rx.foreach(
                        TopicState.entries,
                        entry_view,
                    ),
                    gap="2em",
                    margin_y="2em",
                    width="100%",
                ),
                rx.hstack(
                    rx.text(f"Python v{sys.version}"),
                    rx.logo(),
                    rx.text(f"v{importlib.metadata.version('reflex')}"),
                ),
                width=["100vw", "75vw", "75vw", "50vw", "50vw"],
            ),
            width="100%",
        ),
    )


app = rxe.App()
app.add_page(
    index,
    title=rx.cond(
        TopicState.topic_name,
        rx.cond(
            TopicState.topic_description & TopicState.topic_name
            != TopicState.topic_description,
            f"rx_shout | {TopicState.topic_name} - {TopicState.topic_description}",
            f"rx_shout | {TopicState.topic_name}",
        ),
        "rx_shout",
    ),
    description="A shoutbox-like app for posting text and images.",
    on_load=TopicState.load_entries,
    auth=False,
)
rx.Model.migrate()
