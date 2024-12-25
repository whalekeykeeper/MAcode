# app/models.py

# SQL Alchemy models declaration.
# https://docs.sqlalchemy.org/en/20/orm/quickstart.html#declare-models
# mapped_column syntax from SQLAlchemy 2.0.

# https://alembic.sqlalchemy.org/en/latest/tutorial.html
# Note, it is used by alembic migrations logic, see `alembic/env.py`

# Alembic shortcuts:
# # create migration
# alembic revision --autogenerate -m "migration_name"

# # apply all migrations
# alembic upgrade head

from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import JSON, JSONB, Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    For each unique user, we create a new User object.
    """

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )

    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    video_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    chosen_word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    chosen_sentence_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )

    vocabulary: Mapped["Vocabulary"] = relationship("Vocabulary", back_populates="user")
    family: Mapped["Family"] = relationship(
        "Family", back_populates="user", uselist=False
    )
    graph: Mapped["Graph"] = relationship(
        "Graphs", back_populates="user", uselist=False
    )


class Video(Base):
    """
    Represents YouTube videos.
    """

    __tablename__ = "video_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    YouTube_id: Mapped[str] = mapped_column(
        String(10), nullable=False, unique=True
    )  # YouTube video id
    url: Mapped[str] = mapped_column(
        String(250), nullable=False, unique=True
    )  # YouTube link
    video_path: Mapped[str] = mapped_column(
        String(250), nullable=False
    )  # local storage address
    vtt_path: Mapped[str] = mapped_column(
        String(250), nullable=False
    )  # local storage address


# We might not need the following table since it is only used for displaying.
class Lines(Base):
    """
    Collect each line from subtitles. Just for display reason.
    """

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    line_text: Mapped[str] = mapped_column(String(500), nullable=False)

    sentence_ids: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )  # a line might belong to two or three sentences


class Sentence(Base):
    """
    Collect sentences which consists of lines.
    """

    __tablename__ = "sentence_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    sentence_text_in_lower: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # after lower()

    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Words(Base):
    """
    To collect words from subtitles.
    """

    __tablename__ = "word_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    raw_word: Mapped[str] = mapped_column(String(50), nullable=False)
    lemma: Mapped[str] = mapped_column(String(50), nullable=False)
    pos: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # pos for (word, context) in Spacy
    translation: Mapped[str] = mapped_column(String(50), nullable=False)

    cefr: Mapped[str] = mapped_column(String(10), nullable=True)  # could be null
    doc_frequency: Mapped[int] = mapped_column(Integer, nullable=False)
    complexity: Mapped[float] = mapped_column(Float, nullable=False)

    sentence_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class ChosenWord(Base):
    """
    To collect chosen words by mouse clicking.
    """

    __tablename__ = "chosen_word_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word_model.id"), nullable=False)
    sentence_id: Mapped[int] = mapped_column(
        ForeignKey("sentence_model.id"), nullable=False
    )
    marked_learned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ChosenSentence(Base):
    """
    To collect chosen sentences by pressing space bar.
    """

    __tablename__ = "chosen_sentence_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sentence_id: Mapped[int] = mapped_column(
        ForeignKey("sentence_model.id"), nullable=False
    )


class Vocabulary(Base):
    """
    Each user has a vocabulary list.
    """

    __tablename__ = "vocabulary_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id = mapped_column(Integer, nullable=False)
    # List of word IDs associated with this user's vocabulary
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    family_id: Mapped[int] = mapped_column(
        ForeignKey("family_model.id"), nullable=True, unique=True
    )

    # Relationship
    user = relationship("User", back_populates="vocabulary")
    family = relationship("Family", back_populates="vocabulary", uselist=False)


class Family(Base):
    """
    Each vocabulary list is used to construct a word family.
    """

    __tablename__ = "family_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    family_data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )  # Store word family data as JSON

    # Relationship
    vocabulary = relationship("Vocabulary", back_populates="family", uselist=False)
    user = relationship("User", back_populates="family")
    graph = relationship("Graphs", back_populates="family", uselist=False)


class Graphs(Base):
    """
    Each user has a graph object.
    """

    __tablename__ = "graph_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    graph: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Relationship
    family = relationship("Family", back_populates="graph", uselist=False)
    user = relationship("User", back_populates="graph")


class GapFillingTable(Base):
    """
    Store multi-gap filling exercises.
    """

    __tablename__ = "gap_filling_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    word_pos_pair: Mapped[dict] = mapped_column(
        JSON, nullable=False
    )  # Store as JSON for word-pos pair

    gapped_sentences: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    distractors: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )  # Store as JSON for distractors

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
