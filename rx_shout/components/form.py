"""The form for submitting new entries."""

from typing import Any
import reflex as rx

from ..state import LoadingState, PostFormState, TopicState, UserState, UPLOAD_ID
from .image_upload import image_upload_component, UploadProgressState


def form_error_callout() -> rx.Component:
    """Rendered when there is a form validation error."""
    return rx.cond(
        PostFormState.form_error,
        rx.callout.root(
            rx.callout.icon(rx.icon("triangle_alert", size=20)),
            rx.callout.text(PostFormState.form_error),
            size="1",
            color_scheme="red",
            variant="soft",
            width="100%",
        ),
    )


class EditTopicViewState(UserState):
    editor_open: bool = False

    @rx.event
    def set_editor_open(self, value: bool):
        if self.is_admin:
            self.editor_open = value

    @rx.event
    def handle_submit(self, form_dict: dict[str, Any]):
        self.editor_open = False
        if form_dict.get("topic_description"):
            return TopicState.edit_topic_description(form_dict["topic_description"])


def edit_topic_view() -> rx.Component:
    return rx.form.root(
        rx.hstack(
            rx.input(
                rx.input.slot(rx.icon("pencil", size=20)),
                placeholder="Edit topic description...",
                default_value=TopicState.topic.description,
                id="topic_description",
                width="100%",
            ),
            rx.icon_button(rx.icon("save")),
            rx.icon_button(
                rx.icon("x"),
                type="button",
                on_click=EditTopicViewState.set_editor_open(False),
                color_scheme="red",
            ),
        ),
        on_submit=EditTopicViewState.handle_submit,
        width="100%",
    )


def topic_description() -> rx.Component:
    return rx.heading(
        rx.cond(
            TopicState.topic,
            rx.cond(
                TopicState.topic.description,
                TopicState.topic.description,
                TopicState.topic.name,
            ),
            "Shout Your Thoughts Into the Void",
        ),
        size="4",
        on_click=EditTopicViewState.set_editor_open(True),
        cursor=rx.cond(
            UserState.is_admin,
            "pointer",
            "default",
        ),
    )


def topic_view() -> rx.Component:
    return rx.hstack(
        rx.icon("megaphone", size=25),
        rx.cond(
            EditTopicViewState.editor_open,
            edit_topic_view(),
            topic_description(),
        ),
        align="center",
        width="100%",
    )


def submission_form() -> rx.Component:
    """The form for submitting new entries."""
    return rx.vstack(
        topic_view(),
        form_error_callout(),
        rx.form(
            rx.vstack(
                rx.hstack(
                    rx.input(
                        rx.input.slot(rx.icon("user", size=20)),
                        value=UserState.user_info.author.name,
                        read_only=True,
                        width="100%",
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("at_sign", size=20)),
                        value=UserState.user_info.email,
                        read_only=True,
                        width="100%",
                    ),
                    rx.icon_button(
                        rx.icon("log-out", size=20),
                        on_click=rx.redirect("/logout"),
                        color_scheme="gray",
                        type="button",
                    ),
                    width="100%",
                ),
                rx.input(
                    rx.input.slot(rx.icon("text", size=20)),
                    placeholder="Enter text here...",
                    id="text",
                    width="100%",
                ),
                image_upload_component(),
                rx.hstack(
                    rx.button(
                        "Reload",
                        rx.icon("refresh-cw", size=20),
                        loading=LoadingState.posts,
                        on_click=TopicState.load_entries,
                        type="button",
                        color_scheme="gray",
                    ),
                    rx.spacer(),
                    rx.cond(
                        UploadProgressState.is_uploading,
                        rx.button(
                            "Cancel",
                            on_click=UploadProgressState.cancel_upload(UPLOAD_ID),
                            type="button",
                        ),
                        rx.button(
                            "Post",
                            rx.icon("send", size=20),
                            loading=LoadingState.posting,
                            disabled=UploadProgressState.is_uploading,
                        ),
                    ),
                    width="100%",
                ),
                gap="1em",
            ),
            on_submit=PostFormState.handle_submit,
            width="100%",
        ),
    )
