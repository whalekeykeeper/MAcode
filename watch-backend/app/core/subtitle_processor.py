from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from uuid import uuid4

import spacy
import webvtt
from spacy.tokens import Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models import User, Video, Vocabulary, Families
from utils.cefr_level_detector import detect_cefrj_level


@dataclass
class SubtitleLine:
    """Represents a line from bilingual subtitles."""

    line_number: int
    start_timestamp: str
    end_timestamp: str
    zh_text: Optional[str]
    en_text: Optional[str]


@dataclass
class SentenceData:
    """A collection of sentence data"""

    sent: spacy.tokens.Span
    sentence_id: int
    line_numbers: List[int]


def analyze_text(
        lines_dict: dict[int, str], language: str
) -> Tuple[List[Dict[str, List[int]]], List[Dict[str, str]]]:
    """
    Analyzes the text to map sentences and tokens to lines.

    Args:
        lines_dict: Dictionary where keys are unique line IDs and values are the text lines
        language: The language of the text (either "zh" or "en")

    Returns:
        - A collection of sentences where each sentence has:
          line_ids and sentence_text.
        - A collection of tokens where each token has:
          line_id, text, lemma, and pos.
    """
    nlp_en = spacy.load("en_core_web_lg")
    nlp_zh = spacy.load("zh_core_web_lg")
    nlp = nlp_zh if language == "zh" else nlp_en

    # Different joining strategy for Chinese and English
    joined_text = "".join(lines_dict.values()) if language == "zh" else " ".join(lines_dict.values())
    doc = nlp(joined_text)

    sentence_collection = []
    token_collection = []

    # Convert dictionary values to list while keeping track of IDs
    line_ids = list(lines_dict.keys())
    lines = list(lines_dict.values())

    # Create a mapping of positions to line IDs
    position_to_line = {}
    current_pos = 0

    for i, line in enumerate(lines):
        line_length = len(line)
        for pos in range(current_pos, current_pos + line_length):
            position_to_line[pos] = line_ids[i]
        current_pos += line_length
        if language == "en" and i < len(lines) - 1:
            # Account for the space we added between lines
            current_pos += 1

    # Process sentences
    for sent in doc.sents:
        start_idx = sent.start_char
        end_idx = sent.end_char

        # Find all unique line IDs that this sentence spans
        sentence_line_ids = set()
        for pos in range(start_idx, end_idx):
            if pos < len(joined_text):  # Ensure we don't go past the end of text
                line_id = position_to_line.get(pos)
                if line_id is not None:
                    sentence_line_ids.add(line_id)

        sentence_collection.append({
            "line_ids": sorted(list(sentence_line_ids)),
            "sentence_text": sent.text.strip()
        })

    # Process tokens
    for token in doc:
        start_idx = token.idx
        end_idx = start_idx + len(token.text)

        # Find the line ID for this token
        token_line_ids = set()
        for pos in range(start_idx, end_idx):
            if pos < len(joined_text):  # Ensure we don't go past the end of text
                line_id = position_to_line.get(pos)
                if line_id is not None:
                    token_line_ids.add(line_id)

        for line_id in token_line_ids:
            token_collection.append({
                "line_id": line_id,
                "text": token.text,
                "lemma": token.lemma_,
                "pos": token.pos_,
                "vector": token.vector.tolist() if token.has_vector else None
            })

    return sentence_collection, token_collection


class SubtitleProcessor:
    def __init__(self):
        self.nlp_en = spacy.load("en_core_web_lg")
        self.nlp_zh = spacy.load("zh_core_web_lg")

    async def process_subtitles(
            self,
            ytb_id: str,
            user_uuid: str,
            valid_pos: List[str],
            session: AsyncSession,
    ) -> str:
        """Parsing bilingual subtitle for a new video and update database."""
        # Get video and user
        stmt = select(Video).where(Video.ytb_id == ytb_id)
        video = (await session.execute(stmt)).scalar_one()
        logger.info(f"Found video: {video.id}")

        stmt = select(User).where(User.uuid == user_uuid)
        user = (await session.execute(stmt)).scalar_one()
        logger.info(f"Found user: {user.id}")

        # Full processing for a new video
        logger.info(f"\nProcessing new video {ytb_id}...")
        # Parse the bilingual subtitle file into lines, full Chinese text, and full English text.
        subtitle_lines, full_zh_text, full_en_text = self._parse_subtitle_file(
            video.vtt_path
        )

        # Create lines (word_ids are empty for now) and return a mapping.
        lines_dict_bi = await self._create_line_entries(
            subtitle_lines, video.id, session
        )

        # Parse lines_dict to get sentences and tokens
        for language in ["zh", "en"]:
            sentence_collection, token_collection = analyze_text(
                lines_dict_bi[language], language
            )
            # Create sentence entries and word entries basing on sentence_data_list and token_data_list
            await self._create_sentence_word_entries(
                sentence_collection, token_collection, language, video.id, session
            )

        await self._update_word_ids_and_texts(
            video, user, full_zh_text, full_en_text, session
        )

        if user.vocabulary_id is None:

            vocabulary_dict = await self._initiate_vocabulary(user.id, valid_pos, session)
            logger.info(
                f"Created vocabulary for user {user.id}, the length of the vocabulary is {len(vocabulary_dict)}")

            families_dict = await self._initiate_family(user.id, vocabulary_dict, session)
            logger.info(f"Created families for user {user.id}, the length of the families is {len(families_dict)}")

        else:
            pass
        return video.vtt_path

    @staticmethod
    async def _update_word_ids_and_texts(
            video: Video,
            user: User,
            full_zh_text: str,
            full_en_text: str,
            session: AsyncSession,
    ) -> None:
        # Update full_zh_text and full_en_text for video
        video.zh_text = full_zh_text
        video.en_text = full_en_text

        # Update video_ids for user
        if user.video_ids is None:
            user.video_ids = []
        user.video_ids = list(
            set(user.video_ids + [video.id])
        )  # Ensure unique video IDs
        session.add(video)
        session.add(user)
        await session.flush()
        await session.commit()

        # Here update word_ids for video and user
        # Get all words for this video
        stmt = select(Word.id).where(Word.video_id == video.id)
        result = await session.execute(stmt)
        video_word_ids = [row[0] for row in result]
        # Update video's word_ids
        if video.word_ids is None:
            video.word_ids = []
        video.word_ids = list(
            set(video.word_ids + video_word_ids)
        )  # Ensure unique word IDs

        # Update user's word_ids
        if user.word_ids is None:
            user.word_ids = []
        user.word_ids = list(
            set(user.word_ids + video_word_ids)
        )  # Ensure unique word IDs

        logger.info(f"Added {len(video_word_ids)} words to video and user")
        logger.info(f"Video now has {len(video.word_ids)} total words")
        logger.info(f"User now has {len(user.word_ids)} total words")

        # Final commit for all changes
        session.add(video)
        session.add(user)
        await session.flush()
        await session.commit()
        # # Verify the updates
        # await session.refresh(video)
        # await session.refresh(user)
        # logger.info("\nFinal state verification:")
        # logger.info(f"Video word_ids count: {len(video.word_ids) if video.word_ids else 0}")
        # logger.info(f"User video_ids: {user.video_ids}")
        # logger.info(f"User word_ids count: {len(user.word_ids) if user.word_ids else 0}")

    def _parse_subtitle_file(
            self, subtitle_path: str
    ) -> Tuple[List[SubtitleLine], str, str]:
        """Extract content from bilingual VTT file.

        Arguments:
            subtitle_path: Path to the bilingual subtitle file.
        Returns:
            subtitle_lines: List of subtitle lines.
            full_zh_text: Full Chinese text.
            full_en_text: Full English text.
        """
        logger.info(f"\nAttempting to read subtitle file: {subtitle_path}")
        if not Path(subtitle_path).exists():
            logger.error(f"Subtitle file {subtitle_path} does not exist.")
            raise FileNotFoundError(
                f"The subtitle file at {subtitle_path} does not exist."
            )
        logger.info(f"File exists: {Path(subtitle_path).exists()}")

        subtitle_lines = []
        zh_texts = []
        en_texts = []

        try:
            # Read VTT file
            vtt = webvtt.read(subtitle_path)
            logger.info(f"Successfully read subtitle file")

            for i, caption in enumerate(vtt):
                if "§§§" in caption.text:
                    zh_text, en_text = caption.text.split("§§§")
                    zh_text = zh_text.strip()
                    en_text = en_text.strip()
                else:
                    # For single language line, ignore it, to make sure we have bilingual lines only
                    continue

                if zh_text:
                    # TODO: for Chinese subtitles that the line which contains "翻译人员" and/or "校对人员" in TED Talks' videos
                    # are normally not punctuated. If the last character is not a punctuation in Chinese,
                    # add a period for now and this should be improved in the future.
                    if ("翻译人员" in zh_text or "校对人员" in zh_text) and not self.nlp_zh(
                            zh_text
                    )[-1].is_punct:
                        zh_text += "。"
                    zh_texts.append(zh_text)

                if en_text:
                    en_texts.append(en_text)

                # Store original text in subtitle_lines
                subtitle_lines.append(
                    SubtitleLine(
                        line_number=i + 1,
                        start_timestamp=caption.start,
                        end_timestamp=caption.end,
                        zh_text=zh_text,
                        en_text=en_text,
                    )
                )

            # Join texts without extra spaces for Chinese, with spaces for English
            full_zh_text = "".join(zh_texts)
            full_en_text = " ".join(en_texts)

            return subtitle_lines, full_zh_text, full_en_text

        except Exception as e:
            logger.error(f"Error reading subtitle file: {str(e)}")
            raise

    @staticmethod
    async def _create_line_entries(
            sub_lines: List[SubtitleLine], video_id: int, session: AsyncSession
    ) -> dict[str, dict[int, str]]:
        """Create Line entries for each subtitle line and return a mapping."""
        lines_dict_bi = {}
        lines_zh = {}
        lines_en = {}

        # Create all Line objects first
        line_objects = []
        for line in sub_lines:
            if line.zh_text:
                zh_line = Line(
                    video_id=video_id,
                    language="zh",
                    line_text=line.zh_text,
                    start_timestamp=line.start_timestamp,
                    end_timestamp=line.end_timestamp,
                    original_line_number=line.line_number,
                )
                session.add(zh_line)
                line_objects.append(("zh", zh_line))

            if line.en_text:
                en_line = Line(
                    video_id=video_id,
                    language="en",
                    line_text=line.en_text,
                    start_timestamp=line.start_timestamp,
                    end_timestamp=line.end_timestamp,
                    original_line_number=line.line_number,
                )
                session.add(en_line)
                line_objects.append(("en", en_line))

        # Flush to get all IDs
        await session.flush()  # After this line, each line_obj in line_objects has its id populated

        # Now create the mappings with the guaranteed IDs
        for language, line_obj in line_objects:
            if language == "zh":
                lines_zh[
                    line_obj.id
                ] = line_obj.line_text  # Here we can access line_obj.id
            else:
                lines_en[
                    line_obj.id
                ] = line_obj.line_text  # Here we can access line_obj.id

        lines_dict_bi["zh"] = lines_zh
        lines_dict_bi["en"] = lines_en
        return lines_dict_bi

    @staticmethod
    async def _create_sentence_word_entries(
            sentence_collection: List[Dict[str, List[int]]],
            token_collection: List[Dict[str, str]],
            language: str,
            video_id: int,
            session: AsyncSession,
    ) -> None:
        """Create Sentence and Word entries for each sentence and token."""
        # Create all Sentence objects
        for sent in sentence_collection:
            sentence_entry = Sentence(
                video_id=video_id,
                language=language,
                line_ids=sent["line_ids"],
                sentence_text=sent["sentence_text"],
            )
            session.add(sentence_entry)
        # Flush to get all sentence IDs
        await session.flush()

        logger.info(f"Created {len(sentence_collection)} sentences for {language}.")

        logger.info(f"Starting to create words for {language}...")
        if language == "en":
            logger.info("Detecting CEFR levels for English words...")
        # Create all Word objects
        for token_data in token_collection:
            # Calculate the CEFR level
            cefr = (
                detect_cefrj_level(token_data["text"], token_data["pos"], "pos")
                if language == "en"
                else ""
            )

            # Create word object
            word = Word(
                language=language,
                word=token_data["text"],
                lemma=token_data["lemma"],
                pos=token_data["pos"],
                line_id=token_data["line_id"],
                video_id=video_id,
                cefr=cefr,
                vector=token_data.get("vector", None),
            )
            session.add(word)
        logger.info(f"Created {len(token_collection)} words for {language}.")
        # Final flush to save all Word and WordContext entries
        await session.flush()

    async def _initiate_vocabulary(self, user_id: int, valid_pos: List[str], session: AsyncSession) -> Dict[str,
    List[List[Union[int, str]]]]:
        """Select user as current user and return word_ids."""
        # Select all “en” words for the user for later learning purpose
        stmt = select(User).where(User.id == user_id)
        user = (await session.execute(stmt)).scalar_one()

        # Using word_ids to retrieve all words
        stmt = select(Word).where(Word.id.in_(user.word_ids))
        words = (await session.execute(stmt)).scalars().all()

        # Filter words: remove stop words and keep only certain POS
        filtered_words = [
            word for word in words
            if ((word.language == "en" and not self.nlp_en.vocab[word.word].is_stop
                 and word.pos in valid_pos))
        ]

        # Create dictionary with lemma+pos as key, a list of (id, lemma) as value
        vocabulary_dict: Dict[str, List[List[Union[int, str]]]] = {}
        for word in filtered_words:
            key = f"{word.lemma};{word.pos}"
            if key not in vocabulary_dict:
                vocabulary_dict[key] = []
            vocabulary_dict[key].append([word.id, word.lemma])

        # If any value in words has more than 5 words, logger it
        for key, value in vocabulary_dict.items():
            if len(value) > 5:
                logger.info(f"Family {key} has {len(value)} words.")

        # Create vocabulary entry and update User table
        vocabulary_entry = Vocabulary(
            user_id=user_id,
            vocabulary=vocabulary_dict
        )
        session.add(vocabulary_entry)
        await session.flush()

        # Update User table
        user.vocabulary_id = vocabulary_entry.id
        session.add(user)
        await session.flush()
        await session.commit()

        return vocabulary_dict

    @staticmethod
    async def _initiate_family(
            user_id: int,
            vocabulary_dict: Dict[str, List[List[Union[int, str]]]],
            session: AsyncSession) -> Dict[str, List[int]]:
        # Create Nodes. Each node is a dictionary with lemma as key, a list of word_ids as value. Each node is a family, i.e, an entry in the family table.
        families = {}
        for ele in vocabulary_dict.values():
            for id_lemma_list in ele:  # id_lemma_list = [word_id_list, word_lemma]
                word_id = id_lemma_list[0]
                word_lemma = id_lemma_list[1]
                if word_lemma not in families:
                    families[word_lemma] = []
                families[word_lemma].append(word_id)

        # Update the family table with multiple family
        for key, value in families.items():
            family_entry = Families(
                user_id=user_id,
                family={key: value},
                mastery=0.5,
                acquired=False,
            )
            session.add(family_entry)
        await session.flush()
        await session.commit()

        return families


if __name__ == "__main__":
    import os
    import sys
    import time
    from pathlib import Path

    from dotenv import load_dotenv

    # Add project root to Python path BEFORE any app imports
    project_root = str(Path(__file__).parent.parent.parent)
    sys.path.append(project_root)

    # Now we can import app modules
    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import Line, Sentence, User, Video, Word

    # Load environment variables
    load_dotenv()

    # Use normal database URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{os.getenv('DEFAULT_DATABASE_USER')}:{os.getenv('DEFAULT_DATABASE_PASSWORD')}@localhost:{os.getenv('DEFAULT_DATABASE_PORT')}/{os.getenv('DEFAULT_DATABASE_DB')}",
    )


    async def test_processor():
        """Test the subtitle processor with different scenarios."""
        # Create test engine and session
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

        async with async_session() as session:
            try:
                # Setup test data
                ytb_id = "wr6fQ4KpbRM"  # Replace with a valid YouTube ID
                url = f"https://www.youtube.com/watch?v={ytb_id}"

                # Get absolute paths
                project_root = Path(__file__).parent.parent.parent
                static_folder = project_root / "static"
                video_folder = static_folder / ytb_id
                vtt_path = video_folder / f"{ytb_id}_bilingual.vtt"

                # Print debug information
                print("\nPath Information:")
                print(f"Project Root: {project_root}")
                print(f"Static Folder: {static_folder}")
                print(f"Video Folder: {video_folder}")
                print(f"VTT Path: {vtt_path}")
                print(f"VTT exists: {vtt_path.exists()}")

                if not vtt_path.exists():
                    print(
                        "Subtitle file does not exist. Please ensure the VTT file is present."
                    )
                    return

                # Initialize processor
                processor = SubtitleProcessor()

                # Test Scenario 1: New video, first user
                print("\n=== Scenario 1: New video, first user ===")
                user1 = User(uuid=str(uuid4()))
                session.add(user1)
                await session.flush()
                print(f"Created first user with UUID: {user1.uuid}")

                video1 = Video(
                    ytb_id=ytb_id,
                    url=url,
                    video_path=str(video_folder / f"{ytb_id}.mp4"),
                    vtt_path=str(vtt_path),
                    zh_text="",
                    en_text="",
                    word_ids=[],  # Initialize as empty list
                )
                session.add(video1)
                await session.flush()
                print(f"Created video with ID: {video1.id}")

                # Process subtitles for the first user and video
                vtt_processed_path = await processor.process_subtitles(
                    ytb_id=ytb_id, user_uuid=user1.uuid, valid_pos=["NOUN", "VERB", "ADJ", "ADV", "PROPN", "INTJ"],
                    session=session
                )
                print(f"Processed subtitles for video: {vtt_processed_path}")

                # Commit all changes
                await session.commit()

                # Print final statistics with top 3 examples
                print("\nFinal Database Statistics:")

                # Top 3 Words
                words = (
                    (
                        await session.execute(
                            select(Word).order_by(Word.id.asc()).limit(3)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Words:")
                for word in words:
                    print(
                        f"ID: {word.id}, Language: {word.language}, Word: {word.word}, POS: {word.pos}, "
                        f"Lemma: {word.lemma}, Line ID: {word.line_id}, Video ID: {word.video_id}"
                    )

                # Top 3 Lines
                lines = (
                    (
                        await session.execute(
                            select(Line).order_by(Line.id.asc()).limit(10)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Lines:")
                for line in lines:
                    print(
                        f"ID: {line.id}, Language: {line.language}, Line Text: {line.line_text}"
                    )

                # Top 3 Sentences
                sentences = (
                    (
                        await session.execute(
                            select(Sentence).order_by(Sentence.id.asc()).limit(3)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Sentences:")
                for sentence in sentences:
                    print(
                        f"ID: {sentence.id}, Language: {sentence.language}, Sentence Text length: "
                        f"{len(sentence.sentence_text)}, Line IDs: {sentence.line_ids}"
                    )

                # Top 3 Users
                users = (
                    (
                        await session.execute(
                            select(User).order_by(User.id.asc()).limit(3)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Users:")
                for user in users:
                    print(
                        f"ID: {user.id}, UUID: {user.uuid}, Video IDs: {user.video_ids}, amount of Word IDs: "
                        f"{len(user.word_ids)}"
                    )

                # Top 3 Videos
                videos = (
                    (
                        await session.execute(
                            select(Video).order_by(Video.id.asc()).limit(3)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Videos:")
                for video in videos:
                    print(
                        f"ID: {video.id}, YouTube ID: {video.ytb_id}, URL: {video.url}, Video Path: "
                        f"{video.video_path}, VTT Path: {video.vtt_path}, Amount of Word IDs: {len(video.word_ids)}",
                        f"length of ZH Text: {len(video.zh_text)}, length of EN Text: {len(video.en_text)}",
                    )
                # User's vocabulary, there should only be one vocabulary for this current user (one vocabulary per user)
                vocabulary = (
                    (
                        await session.execute(
                            select(Vocabulary).where(Vocabulary.user_id == user1.id)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nVocabulary:")
                for v in vocabulary:
                    print(
                        f"ID: {v.id}, User ID: {v.user_id}, length of Vocabulary: {len(v.vocabulary)}",
                    )

                # Top 3 Families
                families = (
                    (
                        await session.execute(
                            select(Families).order_by(Families.id.asc()).limit(3)
                        )
                    )
                    .scalars()
                    .all()
                )
                print(f"\nTop 3 Families:")
                for family in families:
                    print(
                        f"ID: {family.id}, User ID: {family.user_id}, Family: {family.family}, Mastery: {family.mastery}, Acquired: {family.acquired}",
                    )

                print("\nTest completed successfully!")

            except Exception as e:
                await session.rollback()
                print(f"Error during test: {str(e)}")
                raise


    """
    Expected:
    Final Database Statistics:
    Words: 654
    Lines: 157
    Sentences: 77
    Word Contexts: 517

    """

    # Run the test
    start_time = time.time()
    asyncio.run(test_processor())
    end_time = time.time()
    print(f"Script execution time: {end_time - start_time} seconds")
