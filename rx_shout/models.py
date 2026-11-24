"""Database models used by the app are defined in this module."""

from typing import Any
import datetime

import sqlalchemy
from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedAsDataclass,
    mapped_column,
    relationship,
)

import reflex as rx


class Base(MappedAsDataclass, DeclarativeBase):
    """Base class for the app's tables."""


rx.ModelRegistry.register(Base)


class Entry(Base):
    __tablename__ = "entry"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    ts: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        init=False,
        server_default=func.now(),
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("author.user_id"), index=True)
    text: Mapped[str]
    topic_id: Mapped[int | None] = mapped_column(
        ForeignKey("topic.id"), index=True, default=None
    )
    image: Mapped[str | None] = mapped_column(default=None)
    hidden: Mapped[bool] = mapped_column(default=False)

    author: Mapped["Author"] = relationship(
        back_populates="entries", init=False, repr=False
    )
    entry_flags: Mapped[list["EntryFlags"]] = relationship(
        back_populates="entry", default_factory=list, repr=False
    )
    topic: Mapped["Topic | None"] = relationship(
        back_populates="entries", init=False, repr=False
    )


class UserInfo(Base):
    __tablename__ = "userinfo"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    ext_id: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=True)

    author: Mapped["Author | None"] = relationship(
        back_populates="user_info", init=False, repr=False
    )
    entry_flags: Mapped[list["EntryFlags"]] = relationship(
        back_populates="user_info", default_factory=list, repr=False
    )


class Author(Base):
    __tablename__ = "author"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("userinfo.id"),
        index=True,
        unique=True,
        primary_key=True,
    )
    name: Mapped[str]
    picture: Mapped[str]

    user_info: Mapped[UserInfo] = relationship(
        back_populates="author", init=False, repr=False
    )
    entries: Mapped[list[Entry]] = relationship(
        back_populates="author", default_factory=list, repr=False
    )


class EntryFlags(Base):
    __tablename__ = "entryflags"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("userinfo.id"), index=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entry.id"), index=True)
    type: Mapped[str]

    user_info: Mapped[UserInfo] = relationship(
        back_populates="entry_flags", init=False, repr=False
    )
    entry: Mapped[Entry] = relationship(
        back_populates="entry_flags", init=False, repr=False
    )


class Topic(Base):
    __tablename__ = "topic"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, index=True)
    description: Mapped[str] = mapped_column(default="")
    locked: Mapped[bool] = mapped_column(default=False)

    entries: Mapped[list[Entry]] = relationship(
        back_populates="topic", default_factory=list, repr=False
    )


@rx.serializer
def serialize_model(model: Base) -> dict[str, Any]:
    """Send a model's loaded columns and relationships to the frontend."""
    state = sqlalchemy.inspect(model)
    return {
        attr.key: attr.value for attr in state.attrs if attr.key not in state.unloaded
    }


@rx.serializer
def serialize_entry(entry: Entry) -> dict[str, Any]:
    """Send an entry with its timestamp truncated to whole seconds."""
    data = serialize_model(entry)
    if (ts := data.get("ts")) is not None:
        data["ts"] = ts.replace(microsecond=0).isoformat()
    return data
