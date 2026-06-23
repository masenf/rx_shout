"""All state management for the app is defined in this module."""

from __future__ import annotations
import functools
from pathlib import Path
from typing import Any

import reflex as rx
import reflex_enterprise as rxe
import sqlalchemy
from sqlmodel import delete, select
from sqlmodel.ext.asyncio.session import AsyncSession

from . import s3
from .models import Author, Entry, EntryFlags, Topic, UserInfo


# The ID the will be used by the upload component.
UPLOAD_ID = "upload_image"


class LoadingState(rx.State):
    """Control loading spinners for different controls."""

    posts: rx.Field[bool] = rxe.field(False, auth=False)
    posting: rx.Field[bool] = rx.field(False)
    liking: rx.Field[int | None] = rx.field(None)
    flagging: rx.Field[int | None] = rx.field(None)
    deleting: rx.Field[int | None] = rx.field(None)


async def _require_admin(auth_user_state: rxe.auth.AuthUserState) -> bool:
    """Require the user to be an admin to run the handler/var."""
    user_state = await auth_user_state.get_state(UserState)
    return user_state.is_admin


async def require_admin(handler: rx.EventHandler, payload: dict[str, Any], auth_user_state: rxe.auth.AuthUserState) -> bool:
    """Require the user to be an admin to run the handler."""
    return await _require_admin(auth_user_state)


async def require_admin_var(field_or_var: Any, auth_user_state: rxe.auth.AuthUserState) -> bool:
    """Require the user to be an admin to access the field/var."""
    return await _require_admin(auth_user_state)


class UserState(rxe.auth.AuthUserState):
    auth_error: str = ""

    @rxe.var(auth=False)
    def user_info(self) -> UserInfo:
        print(f"UserState.user_info called with sub={self.sub}, email={self.email}")
        if not self.sub:
            return UserInfo(id=-1, ext_id="", email="", enabled=False)
        with rx.session() as session:
            user = session.exec(
                select(UserInfo)
                .where(UserInfo.ext_id == self.sub)
                .options(sqlalchemy.orm.selectinload(UserInfo.author))
            ).first()
            if not user:
                user = UserInfo(
                    ext_id=self.sub,
                    email=self.email,
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                author = Author(
                    user_id=user.id,
                    name=self.name,
                    picture=self.picture,
                )
                session.add(author)
                session.commit()
                session.refresh(user)
                # Populate the new author relationship.
                user.author
            return user

    @rxe.event(auth=require_admin)
    async def set_enabled(self, user_id: int, enable: bool = False):
        """Ban or unban a user."""
        async with rx.asession() as asession:
            user = (
                await asession.exec(select(UserInfo).where(UserInfo.id == user_id))
            ).first()
            if user:
                user.enabled = enable
            asession.add(user)
            await asession.commit()
        return TopicState.load_entries

    @rx.var(initial_value=False)
    def is_admin(self) -> bool:
        if self._is_valid_user() and self.user_info.id == 1:
            return True
        return False
    
    def _check_valid_user(self):
        if self._is_valid_user():
            self.auth_error = ""
            return True
        elif not self.user_info.enabled:
            self.auth_error = "Your account has been disabled."
        else:
            self.auth_error = "Sign in to post."
        return False

    def _is_valid_user(self):
        return self.sub and self.user_info.id > 0 and self.user_info.enabled


class TopicState(rx.State):
    entries: rx.Field[list[Entry]] = rxe.field(auth=False)
    topic: rx.Field[Topic | None] = rxe.field(auth=False)
    entry_like_counts: rx.Field[dict[int, dict[str, int]]] = rxe.field(auth=False)

    @rxe.var(auth=False)
    def topic_name(self) -> str:
        return self.router.url.query_parameters.get("topic", "")

    @rxe.var(auth=False)
    def topic_description(self) -> str:
        return self.topic.description if self.topic else ""

    async def _load_topic(self, asession: AsyncSession) -> Topic | None:
        """Load the topic (if any)."""
        if not self.topic_name:
            self.topic = None
            return
        topic = (
            await asession.exec(select(Topic).where(Topic.name == self.topic_name))
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

    @rxe.event(auth=False)
    async def load_entries(self):
        """Load entries from the database."""
        loading_state = await self.get_state(LoadingState)
        loading_state.posts = True
        yield
        user_state = await self.get_state(UserState)
        try:
            if user_state.is_admin:
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
                        select(Entry)
                        .where(
                            Entry.hidden == False,  # noqa: E712
                            Entry.topic_id == (self.topic.id if self.topic else None),
                        )
                        .options(*load_options)
                        .order_by(Entry.ts.desc())
                    )
                ).all()
                self.entry_like_counts = await self._load_entry_like_counts(asession)
                user_flag_state = await self.get_state(UserFlagState)
                if user_state._is_valid_user():
                    await user_flag_state._load_user_flags(asession, user_state)
                else:
                    user_flag_state.reset()
        finally:
            loading_state.posts = False
            loading_state.liking = None
            loading_state.flagging = None
            loading_state.deleting = None

    async def _load_entry_like_counts(self, asession: AsyncSession) -> dict[int, dict[str, int]]:
        return {
            row[0]: {
                "like": row[1],
            }
            for row in (
                await asession.execute(
                    sqlalchemy.text(
                        "SELECT "
                        "entry_id, "
                        "COUNT(CASE type WHEN 'like' THEN 1 ELSE NULL END) as likes "
                        "FROM entryflags "
                        "GROUP BY entry_id"
                    ),
                )
            ).all()
        }

    @rxe.event(auth=require_admin)
    async def edit_topic_description(self, description: str):
        """Edit the topic description."""
        if self.topic is None:
            return
        async with rx.asession() as asession:
            self.topic.description = description
            asession.add(self.topic)
            await asession.commit()
        yield TopicState.load_entries


class UserFlagState(rx.State):
    user_entry_flags: rx.Field[dict[int, dict[str, bool]]]
    entry_flag_counts: rx.Field[dict[int, dict[str, int]]] = rxe.field(auth=require_admin_var)

    async def _load_user_flags(self, asession: AsyncSession, user_state: UserState):
        if not user_state._is_valid_user():
            self.user_entry_flags = {}
            return
        self.user_entry_flags = await self._load_user_entry_flags(asession, user_state.user_info.id)
        if user_state.is_admin:
            self.entry_flag_counts = {}
            return
        self.entry_flag_counts = await self._load_entry_flag_counts(asession)

    async def _load_entry_flag_counts(self, asession: AsyncSession) -> dict[int, dict[str, int]]:
        return {
            row[0]: {
                "flag": row[1],
            }
            for row in (
                await asession.execute(
                    sqlalchemy.text(
                        "SELECT "
                        "entry_id, "
                        "COUNT(CASE type WHEN 'flag' THEN 1 ELSE NULL END) as flags, "
                        "FROM entryflags "
                        "GROUP BY entry_id"
                    ),
                )
            ).all()
        }

    async def _load_user_entry_flags(self, asession: AsyncSession, user_id: int) -> dict[int, dict[str, bool]]:
        user_entry_flags = {}
        for row in (
            await asession.execute(
                sqlalchemy.text(
                    "SELECT entry_id, type "
                    "FROM entryflags "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": user_id},
            )
        ).all():
            user_entry_flags.setdefault(row[0], {})[row[1]] = True
        return user_entry_flags


class PostFormState(rx.State):
    """The base state for the App."""

    form_error: rx.Field[str]
    image_relative_path: rx.Field[str]

    @rx.event
    def set_form_error(self, error: str):
        self.form_error = error

    @rx.event
    async def handle_submit(self, form_data: dict[str, Any]):
        """Handle form submission."""
        form_data.pop(UPLOAD_ID, None)
        user_state = await self.get_state(UserState)
        if not user_state._is_valid_user():
            return
        if not form_data.get("text") and not self.image_relative_path:
            self.form_error = "You have to at least write something or upload an image."
            return
        loading = await self.get_state(LoadingState)
        loading.posting = True
        yield
        topic_state = await self.get_state(TopicState)
        try:
            async with rx.asession() as asession:
                entry = Entry(**form_data)
                entry.author_id = user_state.user_info.id
                entry.topic_id = topic_state.topic.id if topic_state.topic else None
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
            loading.posting = False

    @rx.event
    async def delete_uploaded_image(self):
        """If the user wants to delete the image before making a post."""
        if self.image_relative_path:
            try:
                (rx.get_upload_dir() / self.image_relative_path).unlink()
            except FileNotFoundError:
                pass
            self.image_relative_path = ""

class EntryActionState(rx.State):
    @rxe.event(auth=require_admin)
    async def delete_entry(self, entry_id: int):
        """Delete an entry from the database."""
        loading_state = await self.get_state(LoadingState)
        loading_state.deleting = entry_id
        yield
        async with rx.asession() as asession:
            entry = (
                await asession.exec(select(Entry).where(Entry.id == entry_id))
            ).first()
            if entry:
                entry.hidden = True
            asession.add(entry)
            await asession.commit()
        yield TopicState.load_entries

    async def _flag_entry(self, entry_id: int, type_: str):
        user_state = await self.get_state(UserState)
        if not user_state._is_valid_user():
            return
        async with rx.asession() as asession:
            asession.add(
                EntryFlags(user_id=user_state.user_info.id, entry_id=entry_id, type=type_)
            )
            await asession.commit()

    @rx.event
    async def like_entry(self, entry_id: int):
        """Like an entry."""
        loading_state = await self.get_state(LoadingState)
        loading_state.liking = entry_id
        yield
        await self._flag_entry(entry_id, "like")
        yield TopicState.load_entries

    @rx.event
    async def flag_entry(self, entry_id: int):
        """Flag an entry."""
        loading_state = await self.get_state(LoadingState)
        loading_state.flagging = entry_id
        yield
        await self._flag_entry(entry_id, "flag")
        yield TopicState.load_entries

    @rx.event
    async def unlike_entry(self, entry_id: int):
        """Unlike an entry."""
        user_state = await self.get_state(UserState)
        if not user_state._is_valid_user():
            return
        loading_state = await self.get_state(LoadingState)
        loading_state.liking = entry_id
        yield
        async with rx.asession() as asession:
            await asession.exec(
                delete(EntryFlags).where(
                    EntryFlags.user_id == user_state.user_info.id,
                    EntryFlags.entry_id == entry_id,
                    EntryFlags.type == "like",
                )
            )
            await asession.commit()
        yield TopicState.load_entries

    @rx.event
    async def unflag_entry(self, entry_id: int):
        """Unflag an entry."""

        user_state = await self.get_state(UserState)
        if not user_state._is_valid_user():
            return
        loading_state = await self.get_state(LoadingState)
        loading_state.flagging = entry_id
        yield
        query = delete(EntryFlags).where(
            EntryFlags.entry_id == entry_id,
            EntryFlags.type == "flag",
        )
        if not user_state.is_admin:
            # Only allow users to unflag their own flags.
            query = query.where(EntryFlags.user_id == user_state.user_info.id)
        async with rx.asession() as asession:
            await asession.exec(query)
            await asession.commit()
        yield TopicState.load_entries
