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

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, DateTime
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    """
    For each unique user, we create a new User object.
    """

    __tablename__ = "user_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True, default=lambda: str(uuid4())
    )

    vocabulary: Mapped["Vocabulary"] = relationship("Vocabulary", back_populates="user")
    family: Mapped["Family"] = relationship(
        "Family", back_populates="user", uselist=False
    )
    graph: Mapped["Graph"] = relationship("Graph", back_populates="user", uselist=False)


class Video(Base):
    """
    Represents YouTube videos.
    """

    __tablename__ = "video_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # YouTube video id
    ytb_id: Mapped[str] = mapped_column(String(15), nullable=False, unique=True)

    # YouTube link
    url: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)

    # local storage address
    video_path: Mapped[str] = mapped_column(String(250), nullable=False)
    # local storage address
    vtt_path: Mapped[str] = mapped_column(String(250), nullable=False)


class Line(Base):
    """
    Collect each line from subtitles.
    """
    __tablename__ = "line_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_model.id"), nullable=False)

    # language should be simplified Chinese if before "§§§", English if after "§§§".
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    line_text: Mapped[str] = mapped_column(String(500), nullable=False)
    # words contains the word_ids for each word in the line
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (Index("idx_line_language", "language"),)


class Sentence(Base):
    """
    Collect sentences which consists of lines.
    """

    __tablename__ = "sentence_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_model.id"), nullable=False)

    # language should be simplified Chinese if before "§§§", English if after "§§§".
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    sentence_text: Mapped[str] = mapped_column(String(500), nullable=False)

    __table_args__ = (Index("idx_sentence_video_language", "video_id", "language"),)


class Word(Base):
    """
    To collect words from subtitles.
    """

    __tablename__ = "word_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # languge should be either simplified Chinese or English. 
    # We use "zh" for simplified Chinese and "en" for English.
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    word: Mapped[str] = mapped_column(String(50), nullable=False)

    # lemma is the base form of the word, getting from Spacy
    lemma: Mapped[str] = mapped_column(String(50), nullable=False)

    # pos for (word, context) in Spacy
    pos: Mapped[str] = mapped_column(String(15), nullable=False)

    # translation is expected to be extracted from subtitle part of the other language in the bilingual subtitle.
    # We will use NLP method to align words, but when this is not possible, we will send the word and the context to query with Gemini API.
    translation: Mapped[str] = mapped_column(String(50), nullable=True)

    # cefr level if we find the same (lemma, pos) in the CEFR-J database, otherwise null
    cefr: Mapped[str] = mapped_column(String(10), nullable=True)

    # the frequency for this word in the subtitle of the video for which it was collected from.
    doc_frequency: Mapped[int] = mapped_column(Integer, nullable=True)

    # complexity is calculated based on the frequency of the word in the subtlexus.csv
    complexity: Mapped[float] = mapped_column(Float, nullable=True)

    __table_args__ = (
        Index('idx_word_language_word', 'language', 'word'),
    )



class WordContext(Base):
    """
    Context-specific data for a word.
    """
    __tablename__ = "word_context_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word_model.id"), nullable=False)
    line_id: Mapped[int] = mapped_column(ForeignKey("line_model.id"), nullable=False)
    sentence_id: Mapped[int] = mapped_column(ForeignKey("sentence_model.id"), nullable=False)


class ChosenWord(Base):
    """
    To collect chosen line by pressing space bar.
    We store the words in the line so that we can build a collection of words for future use.
    """

    __tablename__ = "chosen_word_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False)

    # Even if a word is chosen multiple times, we only store one record for each word.
    word_id: Mapped[int] = mapped_column(ForeignKey("word_model.id"), nullable=False, unique=True)

    # The sentence which contains the word when the word is chosen.
    sentence_id: Mapped[int] = mapped_column(ForeignKey("sentence_model.id"), nullable=False)

    # To allow user to mark the word as learned in the frontend.
    marked_as_learned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # record_time is the time when the word is chosen so that we can sort the words by time.
    record_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now)


class UserWordAssociation(Base):
    __tablename__ = "user_word_association"
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("word_model.id"), primary_key=True)


class UserVideoAssociation(Base):
    __tablename__ = "user_video_association"
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_model.id"), primary_key=True)


class Vocabulary(Base):
    """
    Each user has a vocabulary list.
    """

    __tablename__ = "vocabulary_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_model.id"), nullable=False, unique=True
    )
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    # key is unique word-pos pair
    # value is ()
    vocabulary_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    family_id: Mapped[int] = mapped_column(
        ForeignKey("family_model.id"), nullable=True, unique=True
    )

    # Relationships
    user = relationship("User", back_populates="vocabulary")
    family = relationship("Family", back_populates="vocabulary", uselist=False)


class Family(Base):
    """
    Each vocabulary list is used to construct a word family.
    """

    __tablename__ = "family_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_model.id"), nullable=False, unique=True
    )
    # key is unique word-pos pair
    # value is the word_id/word object of the word in the family
    family_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    vocabulary = relationship("Vocabulary", back_populates="family", uselist=False)
    user = relationship("User", back_populates="family")
    graph = relationship("Graph", back_populates="family", uselist=False)


class Graph(Base):
    """
    Each user has a graph object.
    """

    __tablename__ = "graph_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_model.id"), nullable=False, unique=True
    )
    family_id: Mapped[int] = mapped_column(
        ForeignKey("family_model.id"), nullable=True, unique=True
    )
    graph: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Relationships
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

    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False)
    correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
