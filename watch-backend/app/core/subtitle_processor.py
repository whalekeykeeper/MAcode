import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict

import spacy
import webvtt
from spacy.tokens import Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models import (
    Line, Sentence, User, Word, Video, WordContext,
)


@dataclass
class SubtitleLine:
    """Represents a line from bilingual subtitles."""
    line_number: int
    timestamp: str
    zh_text: Optional[str]
    en_text: Optional[str]


class SubtitleProcessor:
    def __init__(self):
        self.nlp_en = spacy.load("en_core_web_lg")
        self.nlp_zh = spacy.load("zh_core_web_lg")

    async def process_subtitles(
            self,
            ytb_id: str,
            user_uuid: str,
            session: AsyncSession,
    ) -> str:
        """Parsing bilingual subtitle for a new video and update database."""
        # Get video and user
        stmt = select(Video).where(Video.ytb_id == ytb_id)
        video = (await session.execute(stmt)).scalar_one()

        stmt = select(User).where(User.uuid == user_uuid)
        user = (await session.execute(stmt)).scalar_one()

        # Full processing for a new video
        logger.info(f"\nProcessing new video {ytb_id}...")
        # Parse the bilingual subtitle file into lines, full chinese text, and full english text.
        subtitle_lines, full_zh_text, full_en_text = self._parse_subtitle_file(video.vtt_path)

        # Update column zh_text and en_text for this video object.
        video.full_zh_text = full_zh_text
        video.full_en_text = full_en_text
        session.add(video)
        await session.flush()

        # Create lines (word_ids are empty for now) and return a mapping.
        line_map = await self._create_line_entries_without_wordids(subtitle_lines, video.id, session)
        # Create sentence entries (all fields updated) and return List[Tuple(spacy sentence, sentence entry)].
        zh_sentences = await self._process_text_to_create_and_update_sentence_entries(
            full_zh_text, "zh", video.id, session
        )
        en_sentences = await self._process_text_to_create_and_update_sentence_entries(
            full_en_text, "en", video.id, session
        )

        # Update Word, WordContext, and update word_ids for Line entries.
        words = await self._create_and_update_words_contexts_linewordids(
            zh_sentences=zh_sentences,
            en_sentences=en_sentences,
            line_map=line_map,
            video_id=video.id,
            session=session
        )

        # Update user and video word associations
        word_ids = [word.id for word in words]
        user.word_ids.extend(word_ids)
        video.word_ids.extend(word_ids)
        user.video_ids.append(video.id)

        # Ensure no duplicates
        user.word_ids = list(set(user.word_ids))
        video.word_ids = list(set(video.word_ids))
        user.video_ids = list(set(user.video_ids))

        session.add(user)
        session.add(video)
        await session.flush()

        return video.vtt_path

    def _parse_subtitle_file(self, subtitle_path: str) -> Tuple[List[SubtitleLine], str, str]:
        """Extract content from bilingual VTT file.

        Arguments:
            subtitle_path: Path to the bilingualsubtitle file.
        Returns:
            subtitle_lines: List of subtitle lines.
            full_zh_text: Full Chinese text.
            full_en_text: Full English text.
        """
        logger.info(f"\nAttempting to read subtitle file: {subtitle_path}")
        if not Path(subtitle_path).exists():
            logger.error(f"Subtitle file {subtitle_path} does not exist.")
            raise FileNotFoundError(f"The subtitle file at {subtitle_path} does not exist.")
        logger.info(f"File exists: {Path(subtitle_path).exists()}")

        subtitle_lines = []
        zh_texts = []
        en_texts = []

        try:
            # Read VTT file
            vtt = webvtt.read(subtitle_path)
            logger.info(f"Successfully read subtitle file")

            for i, caption in enumerate(vtt):
                if '§§§' in caption.text:
                    zh_text, en_text = caption.text.split('§§§')
                    zh_text = zh_text.strip()
                    en_text = en_text.strip()
                else:
                    # Handle single language case
                    text = caption.text.strip()
                    if any('\u4e00' <= char <= '\u9fff' for char in text):
                        zh_text = text
                        en_text = None
                    else:
                        zh_text = None
                        en_text = text

                # Add line markers for tracking
                if zh_text:
                    # TODO: for Chinese subtitles that the line which contains "翻译人员" and/or "校对人员" in TED Talks' videos
                    #  are normally not punctuated. If the last character is not a punctuation in Chinese, add a period for now and this should be improved in the future.
                    if ("翻译人员" in zh_text or "校对人员" in zh_text) and not spacy.isPunct(self.nlp_zh(zh_text)[-1]):
                        zh_text += '。'
                    marked_zh_text = f"[L{i + 1}]{zh_text}[/L{i + 1}]"
                    zh_texts.append(marked_zh_text)

                if en_text:
                    marked_en_text = f"[L{i + 1}]{en_text}[/L{i + 1}]"
                    en_texts.append(marked_en_text)

                # Store original text in subtitle_lines
                subtitle_lines.append(SubtitleLine(
                    line_number=i + 1,
                    timestamp=caption.start,
                    zh_text=zh_text,
                    en_text=en_text
                ))

            # Join texts without extra spaces for Chinese, with spaces for English
            full_zh_text = ''.join(zh_texts)
            full_en_text = ' '.join(en_texts)
            print("------\n\n" + full_zh_text + "\n\n")
            print("------\n\n" + full_en_text + "\n\n")
            return subtitle_lines, full_zh_text, full_en_text

        except Exception as e:
            logger.error(f"Error reading subtitle file: {str(e)}")
            raise

    async def _create_line_entries_without_wordids(
            self,
            sub_lines: List[SubtitleLine],
            video_id: int,
            session: AsyncSession
    ) -> Dict[str, Line]:
        """Create Line entries for each subtitle line and return a mapping."""
        line_map = {}

        # Create Line entries and update Line's text, language, video_id, then flush it to get the ID
        # Line entries still have column word_ids as an empty list.
        for line in sub_lines:
            if line.zh_text:
                zh_line = await self._add_subtitle_line(line.zh_text, "zh", video_id, session)
                line_map[f"zh_{line.line_number}"] = zh_line

            if line.en_text:
                en_line = await self._add_subtitle_line(line.en_text, "en", video_id, session)
                line_map[f"en_{line.line_number}"] = en_line

        await session.flush()  # Ensure all lines have IDs
        return line_map

    async def _create_and_update_words_contexts_linewordids(
            self,
            zh_sentences: List[Tuple[spacy.tokens.Span, Sentence]],
            en_sentences: List[Tuple[spacy.tokens.Span, Sentence]],
            line_map: Dict,
            video_id: int,
            session: AsyncSession
    ) -> List[Word]:
        """Process words and their contexts, return all processed words."""
        processed_words = []

        # Process both languages
        for sentences, language in [(zh_sentences, "zh"), (en_sentences, "en")]:
            for spacy_sent, sentence_entry, line_numbers in sentences:
                # Get relevant lines for this sentence
                relevant_lines = [
                    line_map[f"{language}_{line_num}"]
                    for line_num in line_numbers
                    if f"{language}_{line_num}" in line_map
                ]

                for token in spacy_sent:
                    if self._is_valid_word_token(token):
                        # Create new word entry
                        word = await self._create_word_entry(token, language, session)
                        processed_words.append(word)

                        # Create word contexts and update word_ids for Line entries
                        for line in relevant_lines:
                            if token.text in line.line_text:
                                # Create word context
                                context = WordContext(
                                    word_id=word.id,
                                    line_id=line.id,
                                    sentence_id=sentence_entry.id
                                )
                                session.add(context)

                                # Update word_ids for Line entry
                                if word.id not in line.word_ids:
                                    line.word_ids.append(word.id)
        await session.flush()  # Ensure all word contexts and line updates are committed
        return processed_words

    async def _create_and_update_sentences(
            self,
            full_zh: str,
            full_en: str,
            video_id: int,
            session: AsyncSession
    ) -> Tuple[List[Tuple[spacy.tokens.Span, Sentence]], List[Tuple[spacy.tokens.Span, Sentence]]]:
        """Create Sentence entries for each sentence in the full text."""
        zh_sentences = self._process_text_to_create_and_update_sentence_entries(full_zh, "zh", video_id, session)
        en_sentences = self._process_text_to_create_and_update_sentence_entries(full_en, "en", video_id, session)

        await session.flush()  # Ensure all sentences have IDs
        return zh_sentences, en_sentences

    def _process_text_to_create_and_update_sentence_entries(
            self,
            text: str,
            language: str,
            video_id: int,
            session: AsyncSession
    ) -> List[Tuple[spacy.tokens.Span, Sentence]]:
        """
        Process text to extract sentences and create Sentence entries.
        """
        nlp = self.nlp_zh if language == "zh" else self.nlp_en
        doc = nlp(text)
        sentences = []

        for sent in doc.sents:
            # Extract line numbers from the sentence text using regex
            line_numbers = []
            sent_text = sent.text
            for match in re.finditer(r'\[L(\d+)\].*?\[/L\1\]', sent_text):
                line_numbers.append(int(match.group(1)))

            # Clean the sentence text by removing markers
            clean_text = re.sub(r'\[L\d+\]|\[/L\d+\]', '', sent_text)

            # Create Sentence entry
            sentence_entry = Sentence(
                video_id=video_id,
                language=language,
                sentence_text=clean_text
            )
            session.add(sentence_entry)
            sentences.append((sent, sentence_entry, line_numbers))

        return sentences

    def _is_valid_word_token(self, token) -> bool:
        """Determine if a token should be processed as a word."""
        return (
                not token.is_punct and  # Skip punctuation
                not token.is_space and  # Skip whitespace
                not token.like_num and  # Skip pure numbers
                len(token.text.strip()) > 1  # Skip single characters
        )

    def _find_lines_containing_text(sentence_text: str, lang: str, line_map: Dict) -> List[int]:
        """Find all line IDs that contain parts of this sentence."""
        line_ids = []
        for key, line in line_map.items():
            if key.startswith(f"{lang}_") and sentence_text in line.line_text:
                line_ids.append(line.id)
        return line_ids

    async def _create_word_entry(
            self,
            token: spacy.tokens.Token,
            language: str,
            session: AsyncSession
    ) -> Word:
        """Create new word entry."""
        word = Word(
            language=language,
            word=token.text,
            lemma=token.lemma_,
            pos=token.pos_,
            translation=None,
            complexity=None,
            cefr=None,
        )
        session.add(word)
        await session.flush()
        return word

    async def _add_subtitle_line(
            self, text: str, language: str, video_id: int, session: AsyncSession
    ) -> Line:
        """Create a new Line entry."""
        line = Line(
            video_id=video_id,
            language=language,
            line_text=text,
            word_ids=[]
        )
        session.add(line)
        return line


if __name__ == "__main__":
    sub_lines, full_zh, full_en = SubtitleProcessor()._parse_subtitle_file(
        "../../static/wr6fQ4KpbRM/wr6fQ4KpbRM_bilingual.vtt"
    )
    print(sub_lines)
    print(full_zh)
    print(full_en)
    # import sys
    # from pathlib import Path
    # import os
    # from dotenv import load_dotenv
    #
    # # Add project root to Python path BEFORE any app imports
    # project_root = str(Path(__file__).parent.parent.parent)
    # sys.path.append(project_root)
    #
    # # Now we can import app modules
    # import asyncio
    # from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    # from sqlalchemy.orm import sessionmaker
    #
    # # Load environment variables
    # load_dotenv()
    #
    # # Use normal database URL
    # DATABASE_URL = os.getenv(
    #     "DATABASE_URL",
    #     f"postgresql+asyncpg://{os.getenv('DEFAULT_DATABASE_USER')}:{os.getenv('DEFAULT_DATABASE_PASSWORD')}@localhost:{os.getenv('DEFAULT_DATABASE_PORT')}/{os.getenv('DEFAULT_DATABASE_DB')}"
    # )
    #
    #
    # async def test_processor():
    #     """Test the subtitle processor with different scenarios."""
    #     # Create test engine and session
    #     engine = create_async_engine(DATABASE_URL)
    #     async_session = sessionmaker(engine, class_=AsyncSession)
    #
    #     async with async_session() as session:
    #         try:
    #             # Setup test data
    #             ytb_id = "wr6fQ4KpbRM"
    #             url = f"https://www.youtube.com/watch?v={ytb_id}"
    #
    #             # Get absolute paths
    #             project_root = Path(__file__).parent.parent.parent
    #             static_folder = project_root / "static"
    #             video_folder = static_folder / ytb_id
    #             vtt_path = video_folder / f"{ytb_id}_bilingual.vtt"
    #
    #             # Print debug information
    #             print("\nPath Information:")
    #             print(f"Project Root: {project_root}")
    #             print(f"Static Folder: {static_folder}")
    #             print(f"Video Folder: {video_folder}")
    #             print(f"VTT Path: {vtt_path}")
    #             print(f"VTT exists: {vtt_path.exists()}")
    #
    #             # Initialize processor
    #             processor = SubtitleProcessor()
    #
    #             # Test Scenario 1: New video, first user
    #             print("\n=== Scenario 1: New video, first user ===")
    #             # Create first video and user
    #             video1 = Video(
    #                 ytb_id=ytb_id,
    #                 url=url,
    #                 video_path=str(video_folder / f"{ytb_id}.mp4"),
    #                 vtt_path=str(vtt_path)
    #             )
    #             session.add(video1)
    #             user1 = User()
    #             session.add(user1)
    #             await session.flush()
    #             print(f"Created video with ID: {video1.id}")
    #             print(f"Created first user with UUID: {user1.uuid}")
    #
    #             # Process with existed_video_for_unwatched_user=False (default)
    #             await processor.process_subtitles(
    #                 ytb_id=ytb_id,
    #                 user_uuid=user1.uuid,
    #                 session=session
    #             )
    #
    #             # Test Scenario 2: Existing video, new user
    #             print("\n=== Scenario 2: Existing video, new user ===")
    #             user2 = User()
    #             session.add(user2)
    #             await session.flush()
    #             print(f"Created second user with UUID: {user2.uuid}")
    #
    #             # Process with existed_video_for_unwatched_user=True
    #             await processor.process_subtitles(
    #                 ytb_id=ytb_id,
    #                 user_uuid=user2.uuid,
    #                 session=session,
    #                 existed_video_for_unwatched_user=True
    #             )
    #
    #             # Test Scenario 3: Existing video, existing user
    #             print("\n=== Scenario 3: Existing video, existing user ===")
    #             # Try to process again for user1
    #             await processor.process_subtitles(
    #                 ytb_id=ytb_id,
    #                 user_uuid=user1.uuid,
    #                 session=session,
    #                 existed_video_for_unwatched_user=False
    #             )
    #
    #             # Print final statistics
    #             print("\nFinal Database Statistics:")
    #             words = (await session.execute(select(Word))).scalars().all()
    #             lines = (await session.execute(select(Line))).scalars().all()
    #             sentences = (await session.execute(select(Sentence))).scalars().all()
    #             contexts = (await session.execute(select(WordContext))).scalars().all()
    #             user_word_assocs = (await session.execute(
    #                 select(UserWordAssociation)
    #             )).scalars().all()
    #             user_video_assocs = (await session.execute(
    #                 select(UserVideoAssociation)
    #             )).scalars().all()
    #
    #             print(f"Words: {len(words)}")
    #             print(f"Lines: {len(lines)}")
    #             print(f"Sentences: {len(sentences)}")
    #             print(f"Word Contexts: {len(contexts)}")
    #             print(f"User-Word Associations: {len(user_word_assocs)}")
    #             print(f"User-Video Associations: {len(user_video_assocs)}")
    #
    #             if words:
    #                 print("\nSample Chinese words:")
    #                 zh_words = [w for w in words if w.language == "zh"][:5]
    #                 for word in zh_words:
    #                     print(f"Word: {word.word}, POS: {word.pos}")
    #
    #                 print("\nSample English words:")
    #                 en_words = [w for w in words if w.language == "en"][:5]
    #                 for word in en_words:
    #                     print(f"Word: {word.word}, POS: {word.pos}")
    #
    #             await session.commit()
    #             print("\nTest completed successfully!")
    #
    #         except Exception as e:
    #             await session.rollback()
    #             print(f"Error during test: {str(e)}")
    #             raise
    #
    #
    # """
    # Command to re-initialize the database:
    # docker compose down -v
    # docker compose up -d
    # rm -rf alembic/versions/*
    # alembic revision --autogenerate -m "initial"
    # alembic upgrade head
    #
    # Expected:
    # Final Database Statistics:
    # Words: 654
    # Lines: 157
    # Sentences: 77
    # Word Contexts: 517
    # User-Word Associations: 1308
    # User-Video Associations: 2
    #
    # """
    #
    # # Run the test
    # asyncio.run(test_processor())
