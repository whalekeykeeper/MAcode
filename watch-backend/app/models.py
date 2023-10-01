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
    video_url: Mapped[str] = mapped_column(String(250), nullable=False)
    video_id: Mapped[str] = mapped_column(String(30), nullable=False)


class Word(Base):
    __tablename__ = "word_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_form: Mapped[str] = mapped_column(String(50), nullable=False)
    word_translation: Mapped[str] = mapped_column(String(150), nullable=False)


class Sentence(Base):
    __tablename__ = "sentence_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    word_id: Mapped[str] = mapped_column(
        ForeignKey("word_model.id", ondelete="CASCADE"),
    )
    clicked_sentence: Mapped[str] = mapped_column(String(300), nullable=False)
