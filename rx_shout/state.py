"""All state management for the app is defined in this module."""

from pathlib import Path
import uuid

import reflex as rx

from .models import Entry

# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


class State(rx.State):
    """The base state for the App."""
    entries: list[Entry]
    form_error: str = ""
    image_relative_path: str

    def handle_submit(self, form_data: dict[str, str]):
        """Handle form submission."""
        form_data.pop(UPLOAD_ID, None)
        if not form_data.get("author"):
            self.form_error = "You have to at least give us a name."
            return
        if not form_data.get("text") and not self.image_relative_path:
            self.form_error = "You have to at least write something or upload an image."
            return
        with rx.session() as session:
            entry = Entry(**form_data)
            if self.image_relative_path:
                entry.image = self.image_relative_path
                if not entry.text:
                    entry.text = ""
            session.add(entry)
            session.commit()
            session.refresh(entry)
        self.image_relative_path = ""
        self.form_error = ""
        return [rx.set_value("text", ""), rx.redirect("/")]

    def load_entries(self):
        """Load entries from the database."""
        with rx.session() as session:
            self.entries = session.exec(Entry.select.order_by(Entry.ts.desc())).all()

    def on_load(self):
        self.load_entries()


class UploadState(State):
    """State for handling file uploads."""
    upload_progress: int
    is_uploading: bool = False

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Write the file bytes to disk and update the filename in base state."""
        yield rx.clear_selected_files(UPLOAD_ID)
        for file in files:
            upload_data = await file.read()
            filename = f"{uuid.uuid4()}_{file.filename.lstrip('/')}"
            outfile = Path(rx.get_upload_dir()) / filename
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(upload_data)
            self.image_relative_path = filename
            break  # only allow one upload

    def on_upload_progress(self, prog: dict):
        """Handle interim progress updates while waiting for upload."""
        if prog["progress"] < 1:
            self.is_uploading = True
        else:
            self.is_uploading = False
        self.upload_progress = round(prog["progress"] * 100)

    def cancel_upload(self, upload_id: str):
        """Cancel the upload before it is complete."""
        self.is_uploading = False
        return rx.cancel_upload(upload_id)

    def delete_uploaded_image(self):
        """If the user wants to delete the image before making a post."""
        if self.image_relative_path:
            (Path(rx.get_upload_dir()) / self.image_relative_path).unlink()
            self.image_relative_path = ""
