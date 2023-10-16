# app/models.py

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "user_model"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda _: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(254), nullable=False, unique=True, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)


class Video(Base):
    __tablename__ = "video_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_url: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)
    video_id: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    video_path: Mapped[str] = mapped_column(String(150), nullable=False)
    vtt_path: Mapped[str] = mapped_column(String(150), nullable=False)


class Translation(Base):
    __tablename__ = "translation_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    sentence: Mapped[str] = mapped_column(String(300), nullable=False)
    translation: Mapped[str] = mapped_column(String(500), nullable=False)