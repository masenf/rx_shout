import datetime

import reflex as rx
from sqlmodel import Field, DateTime, Column, func


class Entry(rx.Model, table=True):
    ts: datetime.datetime = Field(
        datetime.datetime.now(datetime.timezone.utc),
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        nullable=False,
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
        # shove it into the list of entries
        self.entries.insert(0, entry)
        return [rx.set_value(field, "") for field in form_data]

    def load_entries(self):
        """Load entries from the database."""
        with rx.session() as session:
            self.entries = session.exec(Entry.select.order_by(Entry.ts.desc())).all()


def index() -> rx.Component:
    return rx.fragment(
        rx.color_mode_button(rx.color_mode_icon(), float="right"),
        rx.vstack(
            rx.form(
                rx.input(placeholder="Enter text here...", id="text"),
                rx.button("Submit", type_="submit"),
                on_submit=State.handle_submit,
            ),
            rx.button("Reload 🔁", on_click=State.load_entries),
            rx.list(
                rx.foreach(
                    State.entries,
                    lambda e: rx.vstack(
                        rx.text(e.ts, font_size="0.75em"),
                        rx.text(e.text),
                        align_items="start",
                        margin_bottom="2em",
                    )
                )
            ),
        ),
    )


# Add state and page to the app.
app = rx.App()
app.add_page(index)
app.compile()
