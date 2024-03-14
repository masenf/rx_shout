"""Database models used by the app are defined in this module."""
from typing import List, Optional
import datetime

from sqlmodel import Field, DateTime, Column, func, Relationship

import reflex as rx


class Entry(rx.Model, table=True):
    ts: datetime.datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    author_id: int = Field(nullable=False, foreign_key="userinfo.id", index=True)
    text: str = Field(nullable=False)
    image: str = Field(nullable=True)
    hidden: bool = Field(default=False)

    user_info: Optional["UserInfo"] = Relationship(
        back_populates="entries",
    )

    def dict(self, *args, **kwargs) -> dict:
        d = super().dict(*args, **kwargs)
        d["ts"] = self.ts.replace(microsecond=0).isoformat()
        return d


class UserInfo(rx.Model, table=True):
    ext_id: str = Field(nullable=False, unique=True, index=True)
    name: str = Field(nullable=False)
    email: str = Field(nullable=False)
    picture: str = Field(nullable=False)
    enabled: bool = Field(default=True)

    entries: List[Entry] = Relationship(
        back_populates="user_info",
    )


class EntryFlags(rx.Model, table=True):
    user_id: int = (Field(nullable=False, foreign_key="userinfo.id", index=True),)
    entry_id: int = (Field(nullable=False, foreign_key="entry.id", index=True),)
    type: str = (Field(nullable=False),)
