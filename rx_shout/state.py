"""All state management for the app is defined in this module."""

from __future__ import annotations

import reflex as rx
import reflex_google_auth
import sqlalchemy
from sqlmodel import delete, Session

from .models import Author, Entry, EntryFlags, Topic, UserInfo


# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


class UserInfoState(reflex_google_auth.GoogleAuthState):
    auth_error: str = ""

    @rx.cached_var
    def user_info(self) -> UserInfo:
        if not self.tokeninfo:
            return UserInfo(id=-1)
        with rx.session() as session:
            user = session.exec(
                UserInfo.select()
                .where(UserInfo.ext_id == self.tokeninfo["sub"])
                .options(sqlalchemy.orm.selectinload(UserInfo.author))
            ).first()
            if not user:
                user = UserInfo(
                    ext_id=self.tokeninfo["sub"],
                    email=self.tokeninfo["email"],
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                author = Author(
                    user_id=user.id,
                    name=self.tokeninfo["name"],
                    picture=self.tokeninfo["picture"],
                )
                session.add(author)
                session.commit()
                session.refresh(user)
                # Populate the new author relationship.
                user.author
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
        return State.load_entries

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
    topic: Topic | None
    entry_flag_counts: dict[int, dict[str, int]]
    user_entry_flags: dict[int, dict[str, bool]]
    form_error: str = ""
    image_relative_path: str

    def reload_after_login(self, data):
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
            entry.topic_id = self.topic.id if self.topic else None
            if self.image_relative_path:
                entry.image = self.image_relative_path
                if not entry.text:
                    entry.text = ""
            session.add(entry)
            session.commit()
            session.refresh(entry)
        self.image_relative_path = ""
        self.form_error = ""
        return [rx.set_value("text", ""), rx.redirect(self.router.page.raw_path)]

    def _load_topic(self, session) -> Topic | None:
        """Load the topic (if any)."""
        topic_name = self.router.page.params.get("topic")
        if not topic_name:
            self.topic = None
            return
        topic = session.exec(
            Topic.select().where(Topic.name == topic_name)
        ).one_or_none()
        if topic is None:
            topic = Topic(
                name=topic_name,
                description=self.router.page.params.get("description", ""),
            )
            session.add(topic)
            session.commit()
            session.refresh(topic)
        return topic

    def load_entries(self):
        """Load entries from the database."""
        if self.is_admin:
            load_options = [
                sqlalchemy.orm.selectinload(Entry.author).options(
                    sqlalchemy.orm.selectinload(Author.user_info)
                ),
            ]
        else:
            load_options = [
                sqlalchemy.orm.selectinload(Entry.author),
            ]
        with rx.session() as session:
            self.topic = self._load_topic(session)
            self.entries = session.exec(
                Entry.select()
                .where(
                    Entry.hidden == False,
                    Entry.topic_id == (self.topic.id if self.topic else None),
                )
                .options(*load_options)
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

    def unflag_entry(self, entry_id: int):
        """Unflag an entry."""
        if not self._is_valid_user():
            return
        query = delete(EntryFlags).where(
            EntryFlags.entry_id == entry_id,
            EntryFlags.type == "flag",
        )
        if not self.is_admin:
            # Only allow users to unflag their own flags.
            query = query.where(EntryFlags.user_id == self.user_info.id)
        with rx.session() as session:
            session.exec(query)
            session.commit()
        self.load_entries()

    def edit_topic_description(self, description: str):
        """Edit the topic description."""
        if not self.is_admin or self.topic is None:
            return
        with rx.session() as session:
            self.topic.description = description
            session.add(self.topic)
            session.commit()
        self.load_entries()
