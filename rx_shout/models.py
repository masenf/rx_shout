"""Database models used by the app are defined in this module."""

import datetime

from sqlmodel import Field, DateTime, Column, func

import reflex as rx


class Entry(rx.Model, table=True):
    ts: datetime.datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )
    author: str = Field(nullable=False)
    text: str = Field(nullable=False)
    image: str = Field(nullable=True)

    def dict(self, *args, **kwargs) -> dict:
        d = super().dict(*args, **kwargs)
        d["ts"] = self.ts.replace(microsecond=0).isoformat()
        return d
