"""All state management for the app is defined in this module."""

from __future__ import annotations
import dataclasses
import functools
from typing import Any

import reflex as rx
import reflex_google_auth
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from . import s3
from .db import Session
from .models import Author, Entry, EntryFlags, Topic, UserInfo


# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


@dataclasses.dataclass(kw_only=True, slots=True)
class LoadingState:
    """Control loading spinners for different controls."""

    posts: bool = False
    posting: bool = False
    liking: int | None = None
    flagging: int | None = None
    deleting: int | None = None


class UserInfoState(reflex_google_auth.GoogleAuthState):
    auth_error: str = ""

    @rx.var(cache=True)
    async def user_info(self) -> UserInfo:
        if not self.tokeninfo:
            user = UserInfo(ext_id="", email="")
            user.id = -1
            return user
        async with Session() as session:
            user = await session.scalar(
                select(UserInfo)
                .where(UserInfo.ext_id == self.tokeninfo["sub"])
                .options(selectinload(UserInfo.author))
            )
            if not user:
                user = UserInfo(
                    ext_id=self.tokeninfo["sub"],
                    email=self.tokeninfo["email"],
                )
                session.add(user)
                await session.flush()
                session.add(
                    Author(
                        user_id=user.id,
                        name=self.tokeninfo["name"],
                        picture=self.tokeninfo["picture"],
                    )
                )
                await session.commit()
                # Populate the new author relationship.
                await session.refresh(user, ["author"])
            return user

    @rx.event
    async def set_enabled(self, user_id: int, enable: bool = False):
        """Ban or unban a user."""
        if not await self.is_admin:
            return
        async with Session() as session:
            user = await session.get(UserInfo, user_id)
            if user:
                user.enabled = enable
                await session.commit()
        return State.load_entries

    @rx.var(cache=True)
    async def is_admin(self) -> bool:
        if self.token_is_valid:
            user_info = await self.user_info
            return user_info.id == 1 and user_info.enabled
        return False

    async def _is_valid_user(self):
        user_info = await self.user_info
        if self.token_is_valid and user_info.id > 0:
            if user_info.enabled:
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
    async def reload_after_login(self):
        self.reset()
        await self._is_valid_user()
        return State.load_entries()

    @rx.event
    def logout_and_reset(self):
        self.logout()
        return State.reload_after_login()

    @rx.event
    async def handle_submit(self, form_data: dict[str, Any]):
        """Handle form submission."""
        form_data.pop(UPLOAD_ID, None)
        if not await self._is_valid_user():
            return
        if not form_data.get("text") and not self.image_relative_path:
            self.form_error = "You have to at least write something or upload an image."
            return
        self.loading.posting = True
        yield
        try:
            async with Session() as session:
                entry = Entry(
                    author_id=(await self.user_info).id,
                    text=form_data.get("text") or "",
                    topic_id=self.topic.id if self.topic else None,
                )
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
                session.add(entry)
                await session.commit()
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

    async def _load_topic(self, session: AsyncSession) -> Topic | None:
        """Load the topic (if any)."""
        if not self.topic_name:
            self.topic = None
            return
        topic = (
            await session.scalars(select(Topic).where(Topic.name == self.topic_name))
        ).one_or_none()
        if topic is None:
            topic = Topic(
                name=self.topic_name,
                description=self.router.url.query_parameters.get("description", ""),
            )
            session.add(topic)
            await session.commit()
        return topic

    @rx.event
    async def load_entries(self):
        """Load entries from the database."""
        self.loading.posts = True
        yield
        try:
            if await self.is_admin:
                load_options = [
                    selectinload(Entry.author).selectinload(Author.user_info),
                ]
            else:
                load_options = [
                    selectinload(Entry.author),
                ]
            async with Session() as session:
                self.topic = await self._load_topic(session)
                self.entries = list(
                    await session.scalars(
                        select(Entry)
                        .where(
                            Entry.hidden == False,  # noqa: E712
                            Entry.topic_id == (self.topic.id if self.topic else None),
                        )
                        .options(*load_options)
                        .order_by(Entry.ts.desc())
                    )
                )
                await self._load_entry_flag_counts(session)
                await self._load_user_entry_flags(session)
        finally:
            self.loading.posts = False
            self.loading.liking = None
            self.loading.flagging = None
            self.loading.deleting = None

    async def _load_entry_flag_counts(self, session: AsyncSession):
        is_admin = await self.is_admin
        self.entry_flag_counts = {
            row[0]: {
                "flag": row[1] if is_admin else 0,
                "like": row[2],
            }
            for row in (
                await session.execute(
                    text(
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

    async def _load_user_entry_flags(self, session: AsyncSession):
        user_info = await self.user_info
        if user_info.id:
            self.user_entry_flags = {}
            for row in (
                await session.execute(
                    text(
                        "SELECT entry_id, type "
                        "FROM entryflags "
                        "WHERE user_id = :user_id"
                    ),
                    {"user_id": user_info.id},
                )
            ).all():
                self.user_entry_flags.setdefault(row[0], {})[row[1]] = True

    @rx.event
    async def delete_entry(self, entry_id: int):
        """Delete an entry from the database."""
        if not await self.is_admin:
            return
        self.loading.deleting = entry_id
        yield
        async with Session() as session:
            entry = await session.get(Entry, entry_id)
            if entry:
                entry.hidden = True
                await session.commit()
        yield State.load_entries

    async def _flag_entry(self, entry_id: int, type_: str):
        if not await self._is_valid_user():
            return
        user_info = await self.user_info
        async with Session() as session:
            session.add(EntryFlags(user_id=user_info.id, entry_id=entry_id, type=type_))
            await session.commit()

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
        if not await self._is_valid_user():
            return
        self.loading.liking = entry_id
        yield
        user_info = await self.user_info
        async with Session() as session:
            await session.execute(
                delete(EntryFlags).where(
                    EntryFlags.user_id == user_info.id,
                    EntryFlags.entry_id == entry_id,
                    EntryFlags.type == "like",
                )
            )
            await session.commit()
        yield State.load_entries

    @rx.event
    async def unflag_entry(self, entry_id: int):
        """Unflag an entry."""
        if not await self._is_valid_user():
            return
        self.loading.flagging = entry_id
        yield
        query = delete(EntryFlags).where(
            EntryFlags.entry_id == entry_id,
            EntryFlags.type == "flag",
        )
        if not await self.is_admin:
            # Only allow users to unflag their own flags.
            query = query.where(EntryFlags.user_id == (await self.user_info).id)
        async with Session() as session:
            await session.execute(query)
            await session.commit()
        yield State.load_entries

    @rx.event
    async def edit_topic_description(self, description: str):
        """Edit the topic description."""
        if not await self.is_admin or self.topic is None:
            return
        async with Session() as session:
            topic = await session.get(Topic, self.topic.id)
            if topic:
                topic.description = description
                await session.commit()
        yield State.load_entries
