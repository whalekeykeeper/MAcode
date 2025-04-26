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
from typing import List
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    video_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    vocabulary_id: Mapped[int] = mapped_column(Integer, nullable=True)


class Video(Base):
    """
    Represents YouTube videos.
    """

    __tablename__ = "video_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # YouTube video id
    ytb_id: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)

    # YouTube link
    url: Mapped[str] = mapped_column(String(250), nullable=False, unique=True)

    # store Path to the video file
    video_path: Mapped[str] = mapped_column(String(250), nullable=False)
    # local storage address
    vtt_path: Mapped[str] = mapped_column(String(250), nullable=False)

    # full chinese subtitle
    zh_text: Mapped[str] = mapped_column(String(1000000), nullable=True)
    # full english subtitle
    en_text: Mapped[str] = mapped_column(String(1000000), nullable=True)

    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class Line(Base):
    """
    Collect each line from subtitles.
    """

    __tablename__ = "line_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("video_model.id"), nullable=False)

    # language should be simplified Chinese if before "§§§", English if after "§§§".
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    # original line number in the subtitle file, so that we can align lines in two languages.
    original_line_number: Mapped[int] = mapped_column(Integer, nullable=False)

    line_text: Mapped[str] = mapped_column(String(50000), nullable=False)
    start_timestamp: Mapped[str] = mapped_column(String(100), nullable=False)
    end_timestamp: Mapped[str] = mapped_column(String(100), nullable=False)

    sentence_id: Mapped[int] = mapped_column(ForeignKey("sentence_model.id"), nullable=True)
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
    line_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    sentence_text: Mapped[str] = mapped_column(String(50000), nullable=False)

    __table_args__ = (Index("idx_sentence_video_language", "video_id", "language"),)


class Word(Base):
    """
    To collect words from subtitles.
    """

    __tablename__ = "word_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # language should be either simplified Chinese or English.
    # We use "zh" for simplified Chinese and "en" for English.
    language: Mapped[str] = mapped_column(String(50), nullable=False)

    word: Mapped[str] = mapped_column(String(50), nullable=False)

    # lemma is the base form of the word, getting from Spacy
    lemma: Mapped[str] = mapped_column(String(50), nullable=False)

    # pos for (word, context) in Spacy
    pos: Mapped[str] = mapped_column(String(15), nullable=False)

    # cefr level if we find the same (lemma, pos) in the CEFR-J database, otherwise null
    cefr: Mapped[str] = mapped_column(String(10), nullable=True)

    # record the line id for the line where this word is found
    line_id: Mapped[int] = mapped_column(ForeignKey("line_model.id"), nullable=False)

    video_id: Mapped[int] = mapped_column(ForeignKey("video_model.id"), nullable=False)

    # translation is expected to be extracted from subtitle in the other language in the bilingual subtitle.
    # ToDo: a word_selection problem. Partial word alignment.
    translation: Mapped[str] = mapped_column(String(50), nullable=True)

    vector: Mapped[list] = mapped_column(JSON, nullable=True)

    # complexity is calculated based on the frequency of the word in the subtlexus.csv
    complexity: Mapped[float] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("idx_word_language_word", "language", "word"),)


class ChosenWords(Base):
    """
    To collect chosen words by pressing space bar.
    We store the words in the chosen line so that we can build a collection of words for future use.
    """

    __tablename__ = "chosen_words_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False)

    # Even if a word is chosen multiple times, we only store its id once here.
    word_id: Mapped[int] = mapped_column(ForeignKey("word_model.id"), nullable=False)

    # We store lemma here, because if a lemma is marked as learned, we then update it as "acquired" in the GraphNode
    # table.
    lemma: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # TODO: We store the sentence and translation for given word_id just for convenience. This should be improved in
    #  the future.
    sentence: Mapped[str] = mapped_column(String(500), nullable=False)
    translation: Mapped[str] = mapped_column(String(50), nullable=True)

    # marked_as_learned is used to mark the word as learned by the user in the frontend.
    # It is user-specific.
    marked_as_learned: Mapped[bool] = mapped_column(Boolean, nullable=True, default=False)

    graph_node_id: Mapped[int] = mapped_column(ForeignKey("graph_node.id"), nullable=True)
    # record_time is the time when the word (lemma) is chosen so that we can sort the words by time.
    record_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now)


class Vocabulary(Base):
    """
       Each user has a vocabulary object.
       It contains all the open class words that this user has encountered.
       Except stop words.
    """

    __tablename__ = "vocabulary_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False, unique=True)
    # key is "lemma" + ";" + "pos.upper()", value is a list of [word.id, word.lemma].
    # Each user has one vocabulary entry.
    vocabulary: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )


class Families(Base):
    """
    Each user has a families object
    """

    __tablename__ = "families_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    # Each user has multiple node entries.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_model.id"), nullable=False
    )
    lemma: Mapped[str] = mapped_column(String(50), nullable=False)
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    __table_args__ = (Index("idx_families_user_id", "user_id"),)


class Graph(Base):
    """
     Each user has a graph object.
     """
    __tablename__ = "graph_model"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False, unique=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now())


class GraphNode(Base):
    __tablename__ = "graph_node"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graph_model.id"), nullable=False)
    # TODO: connect to the word_model table
    lemma: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    mastery: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    word_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    acquired: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        # Make lemma unique within a graph
        UniqueConstraint('graph_id', 'lemma', name='unique_lemma_per_graph'),
    )


class GraphEdge(Base):
    __tablename__ = "graph_edge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    graph_id: Mapped[int] = mapped_column(ForeignKey("graph_model.id"), nullable=False)
    node1_id: Mapped[int] = mapped_column(ForeignKey("graph_node.id"), nullable=False)
    node2_id: Mapped[int] = mapped_column(ForeignKey("graph_node.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)


class GapFillingTable(Base):
    """
    Store multi-gap filling exercises.
    """

    __tablename__ = "gap_filling_model"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_model.id"), nullable=False)
    node_id: Mapped[int] = mapped_column(ForeignKey("graph_node.id"), nullable=False)
    correct_answer_lemma: Mapped[str] = mapped_column(String(50), nullable=False)
    select_list: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    distractors: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    correct_or_not: Mapped[bool] = mapped_column(Boolean, nullable=True, default=None)
