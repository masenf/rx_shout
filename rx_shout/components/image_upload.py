"""Frontend components for handling image upload."""

import uuid
from pathlib import Path

import reflex as rx

from ..state import State, UPLOAD_ID


MAX_FILE_SIZE = 5 * 1024**2  # 5 MB


class UploadProgressState(rx.State):
    upload_progress: int
    is_uploading: bool = False

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


class UploadState(State):
    """State for handling file uploads."""

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Write the file bytes to disk and update the filename in base state."""
        if not self._is_valid_user():
            return
        yield rx.clear_selected_files(UPLOAD_ID)
        for file in files:
            upload_data = await file.read()
            filename = f"{uuid.uuid4()}_{file.filename.lstrip('/')}"
            outfile = Path(rx.get_upload_dir()) / filename
            outfile.parent.mkdir(parents=True, exist_ok=True)
            outfile.write_bytes(upload_data)
            self.image_relative_path = filename
            break  # only allow one upload

    def delete_uploaded_image(self):
        """If the user wants to delete the image before making a post."""
        if self.image_relative_path:
            (Path(rx.get_upload_dir()) / self.image_relative_path).unlink()
            self.image_relative_path = ""


def is_uploading_view() -> rx.Component:
    """Rendered while upload is in progress."""
    return rx.hstack(
        rx.progress(value=UploadProgressState.upload_progress),
        rx.button(
            "Cancel",
            on_click=UploadProgressState.cancel_upload(UPLOAD_ID),
            type="button",
        ),
    )


def upload_form() -> rx.Component:
    """The dropzone and button for selecting an image to upload."""
    return rx.upload(
        rx.vstack(
            rx.button(
                "Select or Drop Image",
                rx.icon("image", size=20),
                type="button",
            ),
            align="center",
        ),
        id=UPLOAD_ID,
        multiple=False,
        accept={
            "image/png": [".png"],
            "image/jpeg": [".jpg", ".jpeg"],
            "image/gif": [".gif"],
            "image/webp": [".webp"],
        },
        max_size=MAX_FILE_SIZE,
        border="1px dotted var(--gray-10)",
        padding="10px",
        width="100%",
        on_drop=UploadState.handle_upload(
            rx.upload_files(
                upload_id=UPLOAD_ID,
                on_upload_progress=UploadProgressState.on_upload_progress,
            ),
        ),
    )


def uploaded_image_view() -> rx.Component:
    """Rendered when an image has been uploaded and allows the user to delete it."""
    return rx.box(
        rx.icon(
            "x-circle",
            size=25,
            on_click=UploadState.delete_uploaded_image,
            color="var(--gray-10)",
            cursor="pointer",
            position="absolute",
            right="1em",
            top="1em",
            # Clip background as a circle
            background_clip="content-box",
            border_radius="50%",
            background_color="var(--gray-2)",
            box_shadow="rgba(0, 0, 0, 0.3) 1px 3px 5px",
        ),
        rx.image(
            src=rx.get_upload_url(UploadState.image_relative_path),
            height="15em",
        ),
        # ensure x-circle is positioned relative to the box
        position="relative",
    )


def image_upload_component() -> rx.Component:
    """A component for selecting an image, uploading it, and displaying a preview."""
    return rx.cond(
        rx.selected_files(UPLOAD_ID),
        rx.cond(
            UploadProgressState.is_uploading,
            is_uploading_view(),
        ),
        rx.cond(
            UploadState.image_relative_path,
            uploaded_image_view(),  # Upload complete
            upload_form(),
        ),
    )
