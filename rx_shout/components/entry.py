"""Frontend components for displaying entries."""
import reflex as rx

from ..models import Entry


def entry_metadata(e: Entry) -> rx.Component:
    """Rendered above the entry text and next to the icon."""
    return rx.hstack(
        rx.text.strong(e.author),
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
        width="100%"
    )


def entry_view(e: Entry) -> rx.Component:
    """The entire entry, including the image if present."""
    return rx.card(
        rx.vstack(
            entry_content(e),
            rx.cond(
                e.image,
                rx.image(src=rx.get_upload_url(e.image), width="100%"),
            ),
        ),
        width="100%",
    )
