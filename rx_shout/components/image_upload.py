"""Frontend components for handling image upload."""

import reflex as rx

from ..state import UploadState, UPLOAD_ID


MAX_FILE_SIZE = 5 * 1024**2  # 5 MB


def is_uploading_view() -> rx.Component:
    """Rendered while upload is in progress."""
    return rx.hstack(
        rx.progress(value=UploadState.upload_progress),
        rx.button("Cancel", on_click=UploadState.cancel_upload(UPLOAD_ID), type="button"),
    )


def pre_uploading_view(auto_upload_delay_ms: int = 500) -> rx.Component:
    """Rendered when files are selected, but the upload has not started.
    
    Contains a timer to automatically start the upload after some delay.
    """
    upload_handler_spec = UploadState.handle_upload(
        rx.upload_files(
            upload_id=UPLOAD_ID,
            on_upload_progress=UploadState.on_upload_progress,
        ),
    )

    return rx.hstack(
        rx.foreach(
            rx.selected_files(UPLOAD_ID),
            rx.text,
        ),
        rx.spacer(),
        rx.button(
            "Upload",
            type="button",
            on_click=upload_handler_spec,
        ),
        # Auto-upload after half second.
        rx.moment(
            interval=rx.cond(
                rx.selected_files(UPLOAD_ID) & ~UploadState.is_uploading,
                auto_upload_delay_ms,
                0,
            ),
            on_change=lambda _: upload_handler_spec,
            display="none",
        ),
        width="100%",
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
        rx.cond(  # Files are selected.
            UploadState.is_uploading,
            is_uploading_view(),
            pre_uploading_view(),
        ),
        rx.cond(
            UploadState.image_relative_path,
            uploaded_image_view(),  # Upload complete
            upload_form(),
        )
    )
