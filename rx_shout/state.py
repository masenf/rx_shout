"""All state management for the app is defined in this module."""

from pathlib import Path
import uuid

import reflex as rx
import sqlalchemy
from sqlmodel import delete, Session

from .google_auth_state import GoogleAuthState
from .models import Entry, EntryFlags, UserInfo

# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


class UserInfoState(GoogleAuthState):
    auth_error: str = ""

    @rx.cached_var
    def user_info(self) -> UserInfo:
        if not self.tokeninfo:
            return UserInfo(id=-1)
        with rx.session() as session:
            user = session.exec(
                UserInfo.select().where(UserInfo.ext_id == self.tokeninfo["sub"])
            ).first()
            if not user:
                user = UserInfo(
                    ext_id=self.tokeninfo["sub"],
                    name=self.tokeninfo["name"],
                    email=self.tokeninfo["email"],
                    picture=self.tokeninfo["picture"],
                )
                print(f"Created new user: {user}")
                session.add(user)
                session.commit()
                session.refresh(user)
            else:
                print(f"Got existing user: {user}")
            return user

    async def set_enabled(self, user_id: int, enable: bool = False):
        """Ban or unban a user."""
        if not self.is_admin:
            return
        with rx.session() as session:
            user = session.exec(UserInfo.select().where(UserInfo.id == user_id)).first()
            if user:
                user.enabled = enable
            session.add(user)
            session.commit()
        self.load_entries()

    @rx.cached_var
    def is_admin(self) -> bool:
        if self.token_is_valid:
            return self.user_info.id == 1 and self.user_info.enabled

    def _is_valid_user(self):
        if self.token_is_valid and self.user_info.id > 0:
            if self.user_info.enabled:
                self.auth_error = ""
                return True
            self.auth_error = "Your account has been disabled."
        else:
            self.auth_error = "Sign in with Google to post."
        return False


class State(UserInfoState):
    """The base state for the App."""

    entries: list[Entry]
    entry_flag_counts: dict[int, dict[str, int]]
    user_entry_flags: dict[int, dict[str, bool]]
    form_error: str = ""
    image_relative_path: str

    def reload_after_login(self, data):
        print("reload after login")
        self.reset()
        self.load_entries()
        self._is_valid_user()

    def logout_and_reset(self):
        self.logout()
        self.reload_after_login(None)

    async def handle_submit(self, form_data: dict[str, str]):
        """Handle form submission."""
        form_data.pop(UPLOAD_ID, None)
        if not self._is_valid_user():
            return
        if not form_data.get("text") and not self.image_relative_path:
            self.form_error = "You have to at least write something or upload an image."
            return
        with rx.session() as session:
            entry = Entry(**form_data)
            entry.author_id = self.user_info.id
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
            self.entries = session.exec(
                Entry.select()
                .where(Entry.hidden is False)
                .options(
                    sqlalchemy.orm.selectinload(Entry.user_info),
                )
                .order_by(Entry.ts.desc())
            ).all()
            self._load_entry_flag_counts(session)
            self._load_user_entry_flags(session)

    def _load_entry_flag_counts(self, session: Session):
        self.entry_flag_counts = {
            row[0]: {
                "flag": row[1] if self.is_admin else 0,
                "like": row[2],
            }
            for row in session.execute(
                sqlalchemy.text(
                    "SELECT "
                    "entry_id, "
                    "COUNT(CASE type WHEN 'flag' THEN 1 ELSE NULL END) as flags, "
                    "COUNT(CASE type WHEN 'like' THEN 1 ELSE NULL END) as likes "
                    "FROM entryflags "
                    "GROUP BY entry_id"
                ),
            ).all()
        }

    def _load_user_entry_flags(self, session: Session):
        if self.user_info.id:
            self.user_entry_flags = {}
            for row in session.execute(
                sqlalchemy.text(
                    "SELECT entry_id, type "
                    "FROM entryflags "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": self.user_info.id},
            ).all():
                self.user_entry_flags.setdefault(row[0], {})[row[1]] = True

    def on_load(self):
        self.load_entries()

    def delete_entry(self, entry_id: int):
        """Delete an entry from the database."""
        if not self.is_admin:
            return
        with rx.session() as session:
            entry = session.exec(Entry.select().where(Entry.id == entry_id)).first()
            if entry:
                entry.hidden = True
            session.add(entry)
            session.commit()
        self.load_entries()

    def _flag_entry(self, entry_id: int, type_: str):
        if not self._is_valid_user():
            return
        with rx.session() as session:
            session.add(
                EntryFlags(user_id=self.user_info.id, entry_id=entry_id, type=type_)
            )
            session.commit()
        self.load_entries()

    def like_entry(self, entry_id: int):
        """Like an entry."""
        self._flag_entry(entry_id, "like")

    def flag_entry(self, entry_id: int):
        """Flag an entry."""
        self._flag_entry(entry_id, "flag")

    def unlike_entry(self, entry_id: int):
        """Unlike an entry."""
        if not self._is_valid_user():
            return
        with rx.session() as session:
            session.exec(
                delete(EntryFlags).where(
                    EntryFlags.user_id == self.user_info.id,
                    EntryFlags.entry_id == entry_id,
                    EntryFlags.type == "like",
                )
            )
            session.commit()
        self.load_entries()


class UploadState(State):
    """State for handling file uploads."""

    upload_progress: int
    is_uploading: bool = False

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
