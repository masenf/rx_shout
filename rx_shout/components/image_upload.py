"""Frontend components for handling image upload."""

import uuid
from pathlib import Path

import reflex as rx

from ..state import State, UPLOAD_ID


MAX_FILE_SIZE = 5 * 1024**2  # 5 MB


class UploadProgressState(rx.State):
    upload_progress: int
    is_uploading: bool = False
    is_cancelled: bool = False

    @rx.event
    def on_upload_progress(self, prog: dict):
        """Handle interim progress updates while waiting for upload."""
        if not self.is_cancelled and prog["progress"] < 1:
            self.is_uploading = True
        else:
            self.is_uploading = False
        self.upload_progress = round(prog["progress"] * 100)

    @rx.event
    def cancel_upload(self, upload_id: str):
        """Cancel the upload before it is complete."""
        self.is_cancelled = True
        self.is_uploading = False
        return rx.cancel_upload(upload_id)


class UploadState(State):
    """State for handling file uploads."""

    @rx.event
    async def handle_upload(self, files: list[rx.UploadFile] = []):
        """Write the file bytes to disk and update the filename in base state."""
        if not self._is_valid_user():
            return
        if not files:
            yield rx.toast("File size too large or invalid format")
            return
        yield rx.clear_selected_files(UPLOAD_ID)
        try:
            for file in files:
                upload_data = await file.read()
                filename = f"{uuid.uuid4()}_{file.name}"
                outfile = rx.get_upload_dir() / filename
                outfile.parent.mkdir(parents=True, exist_ok=True)
                outfile.write_bytes(upload_data)
                self.image_relative_path = filename
                break  # only allow one upload
        finally:
            progress_state = await self.get_state(UploadProgressState)
            progress_state.is_uploading = False

    @rx.event
    def delete_uploaded_image(self):
        """If the user wants to delete the image before making a post."""
        if self.image_relative_path:
            try:
                (Path(rx.get_upload_dir()) / self.image_relative_path).unlink()
            except FileNotFoundError:
                pass
            self.image_relative_path = ""


def upload_form() -> rx.Component:
    """The dropzone and button for selecting an image to upload."""
    return rx.upload.root(
        rx.vstack(
            rx.button(
                "Select or Drop Image",
                rx.icon("image", size=20),
                type="button",
            ),
            align="center",
            border=f"1px dashed {rx.color("gray", 8, alpha=True)}",
            padding="1em",
            width="100%",
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
        on_drop=[
            UploadProgressState.set_is_cancelled(False),
            UploadState.handle_upload(
                rx.upload_files(
                    upload_id=UPLOAD_ID,
                    on_upload_progress=UploadProgressState.on_upload_progress,
                ),
            ),
        ],
        width="100%",
        drag_active_style=rx.Style(
            {
                "&::after": {
                    "content": "''",
                    "position": "absolute",
                    "top": "0",
                    "left": "0",
                    "right": "0",
                    "bottom": "0",
                    "background": "rgba(0, 0, 0, 0.5)",  # Black with 50% opacity
                },
            }
        ),
    )


def uploaded_image_view() -> rx.Component:
    """Rendered when an image has been uploaded and allows the user to delete it."""
    return rx.box(
        rx.icon(
            "circle_x",
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
        # ensure circle_x is positioned relative to the box
        position="relative",
    )


def image_upload_component() -> rx.Component:
    """A component for selecting an image, uploading it, and displaying a preview."""
    return rx.cond(
        UploadState.image_relative_path,
        uploaded_image_view(),  # Upload complete
        rx.cond(
            UploadProgressState.is_uploading,
            rx.progress(value=UploadProgressState.upload_progress, flex_grow="1"),
            upload_form(),
        ),
    )
