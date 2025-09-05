"""All state management for the app is defined in this module."""

from __future__ import annotations
import functools
from typing import Any

import reflex as rx
import reflex_google_auth
import sqlalchemy
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession

from . import s3
from .models import Author, Entry, EntryFlags, Topic, UserInfo


# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


class LoadingState(rx.Base):
    """Control loading spinners for different controls."""

    posts: bool = False
    posting: bool = False
    liking: int | None = None
    flagging: int | None = None
    deleting: int | None = None


class UserInfoState(reflex_google_auth.GoogleAuthState):
    auth_error: str = ""

    @rx.var(cache=True)
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

    @rx.event
    async def set_enabled(self, user_id: int, enable: bool = False):
        """Ban or unban a user."""
        if not self.is_admin:
            return
        async with rx.asession() as asession:
            user = (
                await asession.exec(UserInfo.select().where(UserInfo.id == user_id))
            ).first()
            if user:
                user.enabled = enable
            asession.add(user)
            await asession.commit()
        return State.load_entries

    @rx.var(cache=True)
    def is_admin(self) -> bool:
        if self.token_is_valid:
            return self.user_info.id == 1 and self.user_info.enabled
        return False

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
    loading: LoadingState = LoadingState()

    @rx.event
    def set_form_error(self, error: str):
        self.form_error = error

    @rx.event
    def reload_after_login(self):
        self.reset()
        self._is_valid_user()
        return State.load_entries()

    @rx.event
    def logout_and_reset(self):
        self.logout()
        return self.reload_after_login()

    @rx.event
    async def handle_submit(self, form_data: dict[str, Any]):
        """Handle form submission."""
        form_data.pop(UPLOAD_ID, None)
        if not self._is_valid_user():
            return
        if not form_data.get("text") and not self.image_relative_path:
            self.form_error = "You have to at least write something or upload an image."
            return
        self.loading.posting = True
        yield
        try:
            async with rx.asession() as asession:
                entry = Entry(**form_data)
                entry.author_id = self.user_info.id
                entry.topic_id = self.topic.id if self.topic else None
                if self.image_relative_path:
                    if s3.endpoint_url:
                        entry.image = await rx._x.run_in_thread(
                            functools.partial(
                                s3.upload_image,
                                self.image_relative_path,
                                delete_original=True,
                            )
                        )
                    else:
                        entry.image = self.image_relative_path
                    if not entry.text:
                        entry.text = ""
                asession.add(entry)
                await asession.commit()
                await asession.refresh(entry)
            self.image_relative_path = ""
            self.form_error = ""
            yield [rx.set_value("text", ""), rx.redirect(self.router.url)]
        finally:
            self.loading.posting = False

    @rx.var
    def topic_name(self) -> str:
        return self.router.url.query_parameters.get("topic", "")

    @rx.var
    def topic_description(self) -> str:
        return self.topic.description if self.topic else ""

    async def _load_topic(self, asession: AsyncSession) -> Topic | None:
        """Load the topic (if any)."""
        if not self.topic_name:
            self.topic = None
            return
        topic = (
            await asession.exec(Topic.select().where(Topic.name == self.topic_name))
        ).one_or_none()
        if topic is None:
            topic = Topic(
                name=self.topic_name,
                description=self.router.url.query_parameters.get("description", ""),
            )
            asession.add(topic)
            await asession.commit()
            await asession.refresh(topic)
        return topic

    @rx.event
    async def load_entries(self):
        """Load entries from the database."""
        self.loading.posts = True
        yield
        try:
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
            async with rx.asession() as asession:
                self.topic = await self._load_topic(asession)
                self.entries = (
                    await asession.exec(
                        Entry.select()
                        .where(
                            Entry.hidden == False,  # noqa: E712
                            Entry.topic_id == (self.topic.id if self.topic else None),
                        )
                        .options(*load_options)
                        .order_by(Entry.ts.desc())
                    )
                ).all()
                await self._load_entry_flag_counts(asession)
                await self._load_user_entry_flags(asession)
        finally:
            self.loading.posts = False
            self.loading.liking = None
            self.loading.flagging = None
            self.loading.deleting = None

    async def _load_entry_flag_counts(self, asession: AsyncSession):
        self.entry_flag_counts = {
            row[0]: {
                "flag": row[1] if self.is_admin else 0,
                "like": row[2],
            }
            for row in (
                await asession.execute(
                    sqlalchemy.text(
                        "SELECT "
                        "entry_id, "
                        "COUNT(CASE type WHEN 'flag' THEN 1 ELSE NULL END) as flags, "
                        "COUNT(CASE type WHEN 'like' THEN 1 ELSE NULL END) as likes "
                        "FROM entryflags "
                        "GROUP BY entry_id"
                    ),
                )
            ).all()
        }

    async def _load_user_entry_flags(self, asession: AsyncSession):
        if self.user_info.id:
            self.user_entry_flags = {}
            for row in (
                await asession.execute(
                    sqlalchemy.text(
                        "SELECT entry_id, type "
                        "FROM entryflags "
                        "WHERE user_id = :user_id"
                    ),
                    {"user_id": self.user_info.id},
                )
            ).all():
                self.user_entry_flags.setdefault(row[0], {})[row[1]] = True

    @rx.event
    async def delete_entry(self, entry_id: int):
        """Delete an entry from the database."""
        if not self.is_admin:
            return
        self.loading.deleting = entry_id
        yield
        async with rx.asession() as asession:
            entry = (
                await asession.exec(Entry.select().where(Entry.id == entry_id))
            ).first()
            if entry:
                entry.hidden = True
            asession.add(entry)
            await asession.commit()
        yield State.load_entries

    async def _flag_entry(self, entry_id: int, type_: str):
        if not self._is_valid_user():
            return
        async with rx.asession() as asession:
            asession.add(
                EntryFlags(user_id=self.user_info.id, entry_id=entry_id, type=type_)
            )
            await asession.commit()

    @rx.event
    async def like_entry(self, entry_id: int):
        """Like an entry."""
        self.loading.liking = entry_id
        yield
        await self._flag_entry(entry_id, "like")
        yield State.load_entries

    @rx.event
    async def flag_entry(self, entry_id: int):
        """Flag an entry."""
        self.loading.flagging = entry_id
        yield
        await self._flag_entry(entry_id, "flag")
        yield State.load_entries

    @rx.event
    async def unlike_entry(self, entry_id: int):
        """Unlike an entry."""
        if not self._is_valid_user():
            return
        self.loading.liking = entry_id
        yield
        async with rx.asession() as asession:
            await asession.exec(
                delete(EntryFlags).where(
                    EntryFlags.user_id == self.user_info.id,
                    EntryFlags.entry_id == entry_id,
                    EntryFlags.type == "like",
                )
            )
            await asession.commit()
        yield State.load_entries

    @rx.event
    async def unflag_entry(self, entry_id: int):
        """Unflag an entry."""
        if not self._is_valid_user():
            return
        self.loading.flagging = entry_id
        yield
        query = delete(EntryFlags).where(
            EntryFlags.entry_id == entry_id,
            EntryFlags.type == "flag",
        )
        if not self.is_admin:
            # Only allow users to unflag their own flags.
            query = query.where(EntryFlags.user_id == self.user_info.id)
        async with rx.asession() as asession:
            await asession.exec(query)
            await asession.commit()
        yield State.load_entries

    @rx.event
    async def edit_topic_description(self, description: str):
        """Edit the topic description."""
        if not self.is_admin or self.topic is None:
            return
        async with rx.asession() as asession:
            self.topic.description = description
            asession.add(self.topic)
            await asession.commit()
        yield State.load_entries
