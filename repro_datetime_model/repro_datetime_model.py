import datetime

import reflex as rx
from sqlmodel import Field, DateTime, Column, func


class Entry(rx.Model, table=True):
    ts: datetime.datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    text: str = Field(nullable=False)

    def dict(self, *args, **kwargs) -> dict:
        d = super().dict(*args, **kwargs)
        d["ts"] = self.ts.replace(microsecond=0).isoformat()
        return d


class State(rx.State):
    """The app state."""
    entries: list[Entry]

    def handle_submit(self, form_data: dict[str, str]):
        """Handle form submission."""
        with rx.session() as session:
            entry = Entry(**form_data)
            session.add(entry)
            session.commit()
            session.refresh(entry)
        return [rx.set_value(field, "") for field in form_data] + [rx.redirect("/")]

    def load_entries(self):
        """Load entries from the database."""
        with rx.session() as session:
            self.entries = session.exec(Entry.select.order_by(Entry.ts.desc())).all()

    def on_load(self):
        self.load_entries()


def submission_form() -> rx.Component:
    return rx.form(
        rx.vstack(
            rx.heading(rx.hstack("Shout Your Thoughts Into the Void", rx.icon("megaphone"), align="center"), size="2"),
            rx.input.root(
                rx.input(placeholder="Enter text here...", id="text"),
                width="100%",
            ),
            rx.hstack(
                rx.button("Reload", rx.icon("refresh-cw", size=20), on_click=State.load_entries, type="button", color_scheme="gray"),
                rx.spacer(),
                rx.button("Post", rx.icon("send", size=20)),
                width="100%"
            ),
            gap="1em",
        ),
        on_submit=State.handle_submit,
    )

def entry(e: Entry) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(e.ts, font_size="0.75em"),
            rx.text(e.text),
        ),
        width="100%",
    )
    

@rx.page(on_load=State.on_load)
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
                        entry,
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