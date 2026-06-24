"""Frontend components for displaying entries."""

import reflex as rx

from ..models import Author, Entry
from ..state import EntryActionState, LoadingState, TopicState, UserFlagState, UserState


def ban_button(author: Author) -> rx.Component:
    """The button to ban a user."""
    return rx.cond(
        UserState.is_admin,
        rx.cond(
            author.user_info.enabled,
            rx.tooltip(
                rx.icon_button(
                    rx.icon("user"),
                    on_click=UserState.set_enabled(author.user_id, False),
                    color_scheme="green",
                    size="1",
                ),
                content="Ban User",
            ),
            rx.tooltip(
                rx.icon_button(
                    rx.icon("user_x"),
                    on_click=UserState.set_enabled(author.user_id, True),
                    color_scheme="red",
                    size="1",
                ),
                content="Unban User",
            ),
        ),
    )


def entry_metadata(e: Entry) -> rx.Component:
    """Rendered above the entry text and next to the icon."""
    return rx.hstack(
        rx.avatar(
            src=e.author.picture,
            size="1",
            alt=e.author.name,
            margin_right="0.5em",
        ),
        rx.text.strong(e.author.name),
        ban_button(e.author),
        rx.spacer(),
        rx.text(e.ts, font_size="0.75em"),
        width="100%",
    )


def entry_content(e: Entry) -> rx.Component:
    """The icon, metadata, and textual content of an entry."""
    return rx.hstack(
        rx.cond(
            e.image,
            rx.icon("image", size=32),
            rx.icon("message-square-quote", size=32),
        ),
        rx.vstack(
            entry_metadata(e),
            rx.text(e.text),
            width="100%",
            padding_left="0.75em",
        ),
        align="center",
        width="100%",
    )


def like_badge(e: Entry) -> rx.Component:
    """The badge for the like count."""
    like_counts = TopicState.entry_like_counts[e.id.to(str)]
    user_flags = UserFlagState.user_entry_flags[e.id.to(str)]
    children = [
        rx.icon("heart"),
        rx.cond(
            like_counts & like_counts["like"],
            rx.text(like_counts["like"]),
        ),
    ]
    return rx.cond(
        user_flags & user_flags["like"],
        rx.tooltip(
            rx.button(
                *children,
                color_scheme="red",
                on_click=EntryActionState.unlike_entry(e.id),
                loading=LoadingState.liking == e.id,
            ),
            content="Unlike",
        ),
        rx.tooltip(
            rx.button(
                *children,
                color_scheme="gray",
                on_click=EntryActionState.like_entry(e.id),
                loading=LoadingState.liking == e.id,
            ),
            content="Like",
        ),
    )


def flag_badge(e: Entry) -> rx.Component:
    """The badge for the flag count."""
    entry_flags = UserFlagState.entry_flag_counts[e.id.to(str)]
    user_flags = UserFlagState.user_entry_flags[e.id.to(str)]
    flag_count = rx.cond(
        UserState.is_admin & entry_flags & entry_flags["flag"],
        rx.text(entry_flags["flag"]),
    )
    return rx.cond(
        user_flags & user_flags["flag"] | entry_flags & entry_flags["flag"],
        rx.tooltip(
            rx.button(
                rx.icon("flag", color="red"),
                flag_count,
                color_scheme="orange",
                on_click=EntryActionState.unflag_entry(e.id),
                loading=LoadingState.flagging == e.id,
            ),
            content="Unflag Post",
        ),
        rx.popover.root(
            rx.tooltip(
                rx.popover.trigger(
                    rx.button(
                        rx.icon("flag"),
                        flag_count,
                        color_scheme="gray",
                        loading=LoadingState.flagging == e.id,
                    ),
                ),
                content="Flag for Moderation",
            ),
            rx.popover.content(
                rx.popover.close(
                    rx.button(
                        rx.icon("flag"),
                        "Flag Post",
                        rx.icon("triangle_alert"),
                        on_click=EntryActionState.flag_entry(e.id),
                        width="100%",
                        color_scheme="orange",
                        loading=LoadingState.flagging == e.id,
                    ),
                ),
                align="center",
                side="top",
            ),
        ),
    )


def trash_badge(e: Entry) -> rx.Component:
    """The badge for the delete button."""
    return rx.cond(
        UserState.is_admin,
        rx.tooltip(
            rx.icon_button(
                rx.icon("trash"),
                on_click=EntryActionState.delete_entry(e.id),
                color_scheme="red",
                loading=LoadingState.deleting == e.id,
            ),
            content="Delete Post",
        ),
    )


def entry_footer(e: Entry) -> rx.Component:
    return rx.hstack(
        like_badge(e),
        rx.spacer(),
        flag_badge(e),
        trash_badge(e),
        width="100%",
    )


def entry_view(e: Entry) -> rx.Component:
    """The entire entry, including the image if present."""
    return rx.card(
        rx.vstack(
            entry_content(e),
            rx.cond(
                e.image,
                rx.cond(
                    e.image.startswith("http"),
                    rx.image(src=e.image, width="100%"),
                    rx.image(src=rx.get_upload_url(e.image), width="100%"),
                ),
            ),
            entry_footer(e),
        ),
        width="100%",
    )
