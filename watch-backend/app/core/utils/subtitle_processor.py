import asyncio
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

import spacy
import webvtt
from dotenv import load_dotenv
from spacy.tokens import Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import STATIC_DIR
from app.core.logger import logger
from app.core.utils.analyze_text import analyze_text
from app.core.utils.cefr_level_detector import load_cefr_lookup
from app.core.utils.nlp import get_nlp_en, get_nlp_zh
from app.core.utils.prevalence_detector import load_prevalence
from app.models import Line, Sentence, Word
from app.models import User, Video

NLP_EN = get_nlp_en()
NLP_ZH = get_nlp_zh()


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


# def extract_word_embedding_from_bert(word: str) -> Optional[List[float]]:


class SubtitleProcessor:
    def __init__(self):
        self.new_video_stats = {"zh": {}, "en": {}}

    async def process_subtitles(
            self,
            ytb_id: str,
            user_uuid: str,
            session: AsyncSession,
            similarity_threshold: float = 0.3,
    ) -> str:
        static_folder = STATIC_DIR
        """Parsing bilingual subtitle for a new video and update database."""
        # Get video and user
        stmt = select(Video).where(Video.ytb_id == ytb_id)
        video = (await session.execute(stmt)).scalar_one()
        logger.info(f"Found video: {video.id}")

        stmt = select(User).where(User.uuid == user_uuid)
        user = (await session.execute(stmt)).scalar_one()
        logger.info(f"Found user: {user.id}")

        # first, check if the video and the bilingual subtitle already exist in local static folder
        folder_path = static_folder / ytb_id
        bilingual_vtt_path = folder_path / f"{ytb_id}_bilingual.vtt"

        if bilingual_vtt_path.exists():
            logger.info(f"Found existing bilingual subtitle at {bilingual_vtt_path}, skipping download.")
            video.vtt_path = str(bilingual_vtt_path)
        else:
            # If the video and bilingual subtitle are not in the static folder, download it and create a bilingual
            # subtitle
            logger.warning(f"No local bilingual subtitle found. Downloading subtitles for {ytb_id}...")
            download_video_and_subtitles(ytb_id, video.url, static_folder)
            video.vtt_path = create_bilingual_vtt(ytb_id, static_folder)

        # Full processing for a new video
        logger.info(f"\nProcessing new video {ytb_id}...")
        # Parse the bilingual subtitle file into lines, full Chinese text, and full English text.
        subtitle_lines, full_zh_text, full_en_text = self._parse_subtitle_file(
            str(video.vtt_path)
        )
        logger.info(f"Successfully parsed subtitle file for video {ytb_id}")

        # Create lines (word_ids are empty for now) and return a mapping.
        lines_dict_bi = await self._create_line_entries(subtitle_lines, video.id, session)

        cefr_lookup = load_cefr_lookup()
        prevalence_lookup = load_prevalence()
        # Parse lines_dict to get sentences and tokens
        for language in ["zh", "en"]:
            sentence_collection, token_collection = analyze_text(
                lines_dict_bi[language], language, cefr_lookup, prevalence_lookup
            )
            # Create sentence entries and word entries basing on sentence_data_list and token_data_list
            await self._create_sentence_word_entries(sentence_collection, token_collection, language, video.id,
                                                     session)

        await self._update_word_ids_and_texts(
            video, user, full_zh_text, full_en_text, session
        )

        stats = await self.stats_for_subtitles(session, user.id)
        for key, value in stats.items():
            print(f"{key}: {value}")

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
        if not subtitle_path:
            logger.error(f"Subtitle file {subtitle_path} does not exist.")
            raise FileNotFoundError(
                f"The subtitle file at {subtitle_path} does not exist."
            )
        logger.info(f"File exists: {subtitle_path}")

        subtitle_lines = []
        zh_texts = []
        en_texts = []

        try:
            # Read VTT file
            vtt = webvtt.read(subtitle_path)
            logger.info(f"Successfully read subtitle file")

            for i, caption in enumerate(vtt):
                if "§§§" not in caption.text:
                    continue  # Skip lines without bilingual content
                zh_text, en_text = caption.text.split("§§§")
                zh_text = zh_text.strip()
                en_text = en_text.strip()

                if zh_text:
                    # TODO: for Chinese subtitles that the line which contains "翻译人员" and/or "校对人员" in TED Talks' videos
                    # are normally not punctuated. If the last character is not a punctuation in Chinese,
                    # add a period for now and this should be improved in the future.
                    if ("翻译人员" in zh_text or "校对人员" in zh_text) and not NLP_ZH(
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

    async def _create_line_entries(self,
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
        self.new_video_stats["zh"]["new_lines"] = len(lines_zh)
        self.new_video_stats["en"]["new_lines"] = len(lines_zh)
        return lines_dict_bi

    async def _create_sentence_word_entries(self,
                                            sentence_collection: List[Dict[str, List[int]]],
                                            token_collection: List[Dict[str, str]],
                                            language: str,
                                            video_id: int,
                                            session: AsyncSession,
                                            ) -> None:
        """Create Sentence and Word entries"""
        logger.info(f"Creating {len(sentence_collection)} sentences for language={language}...")

        # Step 1: Create sentences
        # Create all Sentence objects
        sentence_objs = []
        for sent in sentence_collection:
            sentence_entry = Sentence(
                video_id=video_id,
                language=language,
                line_ids=sent["line_ids"],
                sentence_text=sent["sentence_text"],  # ignore the Pycharm warning
            )
            session.add(sentence_entry)
            sentence_objs.append(sentence_entry)
        await session.flush()

        # Update sentence_id for Lines
        for sent_obj, sent in zip(sentence_objs, sentence_collection):
            for line_id in sent["line_ids"]:
                stmt = select(Line).where(Line.id == line_id)
                line = (await session.execute(stmt)).scalar_one()
                line.sentence_id = sent_obj.id
                session.add(line)
        await session.flush()
        logger.info(f"Created {len(sentence_objs)} Sentence entries for {language}.")

        # if language == "zh":
        #     self.new_video_stats["zh"]["new_sentences"] = len(sentence_collection)
        # if language == "en":
        #     self.new_video_stats["en"]["new_sentences"] = len(sentence_collection)
        # logger.info(f"Created {len(sentence_collection)} sentences for {language}.")

        # Step 2: Create words, filter early
        logger.info(f"Starting to create Word entries for {language}...")
        word_objs = []
        dropped_by_cefr = 0
        dropped_by_filter = 0

        # Create all Word objects
        for token_data in token_collection:
            cefr_level = token_data.get("cefr", "")

            word_vector = token_data.get("vector", None)
            if word_vector is not None:
                # Create word object
                word_obj = Word(
                    language=language,
                    word=token_data["text"],
                    lemma=token_data["lemma"],
                    pos=token_data["pos"],
                    line_id=token_data["line_id"],
                    video_id=video_id,
                    cefr=token_data.get("cefr", ""),
                    vector=word_vector,
                )
                word_objs.append(word_obj)
        session.add_all(word_objs)
        await session.flush()
        await session.commit()

        logger.info(f"=====Created {len(word_objs)} Word entries for {language}.")

        # Update internal stats
        self.new_video_stats[language]["new_sentences"] = len(sentence_objs)
        self.new_video_stats[language]["new_words"] = len(word_objs)

    @staticmethod
    async def stats_for_subtitles(session: AsyncSession, user_id: int) -> dict:
        """
        Generate statistics about subtitles, words, and families for a user, differentiating between "en" and "zh".

        Args:
            session: The database session.
            user_id: ID of the user for whom to calculate statistics.

        Returns:
            A dictionary with various statistics.
        """
        stats = {}

        # Fetch user
        user = await session.execute(select(User).where(User.id == user_id))
        user = user.scalar_one_or_none()
        if not user:
            return {"error": f"User with ID {user_id} not found."}

        # Count videos
        video_count = len(user.video_ids) if user.video_ids else 0
        stats["video_count"] = video_count

        # Count lines and sentences (for both languages)
        stmt = select(Line).where(Line.video_id.in_(user.video_ids))
        lines = (await session.execute(stmt)).scalars().all()
        line_count_en = sum(1 for line in lines if line.language == "en")
        line_count_zh = sum(1 for line in lines if line.language == "zh")
        stats["line_count_en"] = line_count_en
        stats["line_count_zh"] = line_count_zh

        stmt = select(Sentence).where(Sentence.video_id.in_(user.video_ids))
        sentences = (await session.execute(stmt)).scalars().all()
        sentence_count_en = sum(1 for sentence in sentences if sentence.language == "en")
        sentence_count_zh = sum(1 for sentence in sentences if sentence.language == "zh")
        stats["sentence_count_en"] = sentence_count_en
        stats["sentence_count_zh"] = sentence_count_zh

        # # Count words (for both languages)
        # stmt = select(Word).where(Word.video_id.in_(user.video_ids))
        # words = (await session.execute(stmt)).scalars().all()
        # words_en = [word for word in words if word.language == "en"]
        # words_zh = [word for word in words if word.language == "zh"]
        # stats["word_count_en"] = len(words_en)
        # stats["word_count_zh"] = len(words_zh)
        #
        # # Most frequent words (for English only)
        # word_freq_en = {}
        # for word in words_en:
        #     key = (word.lemma, word.pos)
        #     if (not NLP_EN.vocab[word.lemma].is_stop) and word.pos in ["NOUN", "VERB", "ADJ", "ADV",
        #                                                                "PROPN", "INTJ"]:
        #         word_freq_en[key] = word_freq_en.get(key, 0) + 1
        #
        # sorted_word_freq_en = sorted(word_freq_en.items(), key=lambda x: -x[1])
        # stats["most_frequent_words_en"] = sorted_word_freq_en[:10]

        return stats


if __name__ == "__main__":

    # Add project root to Python path BEFORE any app imports
    project_root = str(Path(__file__).parent.parent.parent)
    sys.path.append(project_root)

    # Now we can import app modules

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
        static_folder = STATIC_DIR

        async with async_session() as session:
            try:
                # Setup test data
                ytb_id = "wr6fQ4KpbRM"  # Replace with a valid YouTube ID
                url = f"https://www.youtube.com/watch?v={ytb_id}"

                # Get absolute paths
                project_root = Path(__file__).parent.parent.parent
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
                    ytb_id=ytb_id, user_uuid=user1.uuid,
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

                # Get all the words for current video when pos is in valid_pos, except word.lemma is stop word,
                # query to get all the lemmas and pos, compare the number of lemmas and unique lemma-pos pairs.
                stmt = select(Word).where(Word.video_id == video1.id)
                words = (await session.execute(stmt)).scalars().all()
                lemmas = set()
                lemma_pos_pairs = set()
                for word in words:
                    if (not NLP_EN.vocab[word.lemma].is_stop) and word.pos in ["NOUN", "VERB", "ADJ", "ADV",
                                                                               "PROPN", "INTJ"]:
                        lemmas.add(word.lemma)
                        lemma_pos_pairs.add((word.lemma, word.pos))
                print(f"\nTotal lemmas: {len(lemmas)}")
                print(f"Total lemma-pos pairs: {len(lemma_pos_pairs)}")

                print("\nTest completed successfully!")

            except Exception as e:
                await session.rollback()
                print(f"Error during test: {str(e)}")
                raise


    # Run the test
    start_time = time.time()
    asyncio.run(test_processor())
    end_time = time.time()
    print(f"Script execution time: {end_time - start_time} seconds")
