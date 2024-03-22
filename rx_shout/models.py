"""Database models used by the app are defined in this module."""
from typing import List, Optional
import datetime

from sqlmodel import Field, DateTime, Column, func, Relationship

import reflex as rx


class Entry(rx.Model, table=True):
    ts: datetime.datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    author_id: int = Field(nullable=False, foreign_key="author.user_id", index=True)
    topic_id: int = Field(nullable=True, foreign_key="topic.id", index=True)
    text: str = Field(nullable=False)
    image: str = Field(nullable=True)
    hidden: bool = Field(default=False)

    author: Optional["Author"] = Relationship(
        back_populates="entries",
    )
    entry_flags: List["EntryFlags"] = Relationship(
        back_populates="entry",
    )
    topic: Optional["Topic"] = Relationship(
        back_populates="entries",
    )

    def dict(self, *args, **kwargs) -> dict:
        d = super().dict(*args, **kwargs)
        d["ts"] = self.ts.replace(microsecond=0).isoformat()
        return d


class UserInfo(rx.Model, table=True):
    ext_id: str = Field(nullable=False, unique=True, index=True)
    email: str = Field(nullable=False)
    enabled: bool = Field(default=True)

    author: Optional["Author"] = Relationship(back_populates="user_info")
    entry_flags: List["EntryFlags"] = Relationship(
        back_populates="user_info",
    )


class Author(rx.Model, table=True):
    user_id: int = Field(nullable=False, foreign_key="userinfo.id", index=True, unique=True, primary_key=True)
    name: str = Field(nullable=False)
    picture: str = Field(nullable=False)

    user_info: Optional[UserInfo] = Relationship(back_populates="author")
    entries: List[Entry] = Relationship(
        back_populates="author",
    )


class EntryFlags(rx.Model, table=True):
    user_id: int = Field(nullable=False, foreign_key="userinfo.id", index=True)
    entry_id: int = Field(nullable=False, foreign_key="entry.id", index=True)
    type: str = Field(nullable=False)

    user_info: UserInfo = Relationship(back_populates="entry_flags")
    entry: Entry = Relationship(back_populates="entry_flags")


class Topic(rx.Model, table=True):
    name: str = Field(nullable=False, unique=True, index=True)
    description: str = ""
    locked: bool = Field(default=False)

    entries: List[Entry] = Relationship(back_populates="topic")