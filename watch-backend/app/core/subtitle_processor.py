from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from uuid import uuid4

import spacy
import webvtt
from spacy.tokens import Token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import logger
from app.models import (
    Word
)


@dataclass
class SubtitleLine:
    """Represents a line from bilingual subtitles."""
    line_number: int
    timestamp: str
    zh_text: Optional[str]
    en_text: Optional[str]


@dataclass
class SentenceData:
    """A collection of sentence data"""
    sent: spacy.tokens.Span
    sentence_id: int
    line_numbers: List[int]


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
        # Parse the bilingual subtitle file into lines, full Chinese text, and full English text.
        subtitle_lines, full_zh_text, full_en_text = (
            self._parse_subtitle_file(video.vtt_path))

        # Update columns zh_text and en_text for this video object.
        video.full_zh_text = full_zh_text
        video.full_en_text = full_en_text
        session.add(video)
        await session.flush()

        # Create lines (word_ids are empty for now) and return a mapping.

        lines_dict = await self._create_line_entries_without_wordids(subtitle_lines, video.id, session)

        # Create sentence entries (all fields updated)
        lines_zh = lines_dict['zh']
        sentence_data_list_zh = await self._process_text_to_create_and_update_sentence_entries(
            lines_zh, full_zh_text, "zh", video.id, session
        )

        lines_en = lines_dict['en']
        sentence_data_list_en = await self._process_text_to_create_and_update_sentence_entries(
            lines_en, full_en_text, "en", video.id, session
        )

        words = await self._create_and_update_words_contexts_linewordids(
            zh_sentences=sentence_data_list_zh,
            en_sentences=sentence_data_list_en,
            lines_dict=lines_dict,
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
            subtitle_path: Path to the bilingual subtitle file.
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

                if zh_text:
                    # TODO: for Chinese subtitles that the line which contains "翻译人员" and/or "校对人员" in TED Talks' videos
                    # are normally not punctuated. If the last character is not a punctuation in Chinese, add a period for now and this should be improved in the future.
                    if ("翻译人员" in zh_text or "校对人员" in zh_text) and not self.nlp_zh(zh_text)[-1].is_punct:
                        zh_text += '。'
                    zh_texts.append(zh_text)

                if en_text:
                    en_texts.append(en_text)

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
            # marked_full_zh_text = ''.join(marked_zh_texts)
            # marked_full_en_text = ' '.join(marked_en_texts)

            return subtitle_lines, full_zh_text, full_en_text  # , marked_full_zh_text, marked_full_en_text

        except Exception as e:
            logger.error(f"Error reading subtitle file: {str(e)}")
            raise

    async def _create_line_entries_without_wordids(
            self,
            sub_lines: List[SubtitleLine],
            video_id: int,
            session: AsyncSession
    ) -> dict[str, dict[int, str]]:
        """Create Line entries for each subtitle line and return a mapping."""
        lines = {}
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
                    word_ids=[]
                )
                session.add(zh_line)
                line_objects.append(("zh", zh_line))

            if line.en_text:
                en_line = Line(
                    video_id=video_id,
                    language="en",
                    line_text=line.en_text,
                    word_ids=[]
                )
                session.add(en_line)
                line_objects.append(("en", en_line))

        # Flush to get all IDs
        await session.flush()

        # Now create the mappings with the guaranteed IDs
        for language, line_obj in line_objects:
            if language == "zh":
                lines_zh[line_obj.id] = line_obj.line_text
            else:
                lines_en[line_obj.id] = line_obj.line_text

        lines['zh'] = lines_zh
        lines['en'] = lines_en

        return lines

    async def _create_and_update_words_contexts_linewordids(
            self,
            zh_sentences: List[SentenceData],
            en_sentences: List[SentenceData],
            lines_dict: dict[str, dict[int, str]],
            video_id: int,
            session: AsyncSession
    ) -> List[Word]:
        """Process words and their contexts, return all processed words."""
        processed_words = []

        # Process both languages
        for sentences, language in [(zh_sentences, "zh"), (en_sentences, "en")]:
            lines = lines_dict[language]

            for sentence_data in sentences:
                # Get the text of all relevant lines for this sentence in order
                sentence_lines = []
                for line_id in sentence_data.line_numbers:
                    if line_id in lines:
                        sentence_lines.append((line_id, lines[line_id]))

                if not sentence_lines:
                    continue

                # Initialize position trackers
                current_line_idx = 0
                current_line_id, current_line_text = sentence_lines[0]
                current_pos_in_line = 0

                # Collect word objects and their contexts for batch processing
                word_objects = []
                context_objects = []
                line_updates = {}  # {line_id: [word_ids_to_add]}

                # Process each token in the sentence
                for token in sentence_data.sent:
                    if not self._is_valid_word_token(token):
                        continue

                    token_text = token.text
                    found = False

                    # Search for token in current and subsequent lines
                    while current_line_idx < len(sentence_lines):
                        current_line_id, current_line_text = sentence_lines[current_line_idx]

                        # Try to find token in current line starting from current position
                        token_pos = current_line_text.find(token_text, current_pos_in_line)

                        if token_pos != -1:
                            # Token found in current line
                            found = True
                            current_pos_in_line = token_pos + len(token_text)

                            # Create word entry
                            word = Word(
                                language=language,
                                word=token_text,
                                lemma=token.lemma_,
                                pos=token.pos_,
                                translation=None,
                                complexity=None,
                                cefr=None,
                            )
                            session.add(word)
                            word_objects.append(word)

                            # Store context creation info for later
                            context_objects.append((word, current_line_id, sentence_data.sentence_id))

                            # Store line update info for later
                            if current_line_id not in line_updates:
                                line_updates[current_line_id] = []
                            line_updates[current_line_id].append(word)

                            break
                        else:
                            # Token not found in current line, move to next line
                            current_line_idx += 1
                            if current_line_idx < len(sentence_lines):
                                current_pos_in_line = 0

                    if not found:
                        logger.warning(
                            f"Token '{token_text}' not found in any line of sentence: {sentence_data.sent.text}"
                        )

                # Flush to ensure all words have IDs
                await session.flush()
                processed_words.extend(word_objects)

                # Create all WordContext objects now that we have word IDs
                for word, line_id, sentence_id in context_objects:
                    context = WordContext(
                        word_id=word.id,
                        line_id=line_id,
                        sentence_id=sentence_id
                    )
                    session.add(context)

                # Update Line.word_ids now that we have word IDs
                for line_id, words in line_updates.items():
                    stmt = select(Line).where(Line.id == line_id)
                    line = (await session.execute(stmt)).scalar_one()
                    for word in words:
                        if word.id not in line.word_ids:
                            line.word_ids.append(word.id)
                    session.add(line)

                # Flush to save contexts and line updates
                await session.flush()

        return processed_words

    async def _process_text_to_create_and_update_sentence_entries(
            self,
            lines: Dict[int, str],
            full_text: str,
            language: str,
            video_id: int,
            session: AsyncSession
    ) -> List[SentenceData]:
        """Process text to extract sentences and create Sentence entries."""
        sentences_data = []
        nlp = self.nlp_zh if language == "zh" else self.nlp_en
        doc = nlp(full_text)

        # Create all sentence objects first
        sentence_objects = []
        for sent in doc.sents:
            # Create Sentence entry
            sentence_entry = Sentence(
                video_id=video_id,
                language=language,
                sentence_text=sent.text.strip()
            )
            session.add(sentence_entry)
            sentence_objects.append((sent, sentence_entry))

        # Flush to get all sentence IDs
        await session.flush()

        # Now create SentenceData with guaranteed IDs
        for sent, sentence_entry in sentence_objects:
            # Find which lines contain this sentence
            line_numbers = []
            for line_id, line_text in lines.items():
                if sent.text in line_text:
                    line_numbers.append(line_id)

            sentences_data.append(SentenceData(
                sent=sent,
                sentence_id=sentence_entry.id,  # Now we have the ID
                line_numbers=line_numbers
            ))

        return sentences_data

    @staticmethod
    async def _create_word_entry(
            token: Token,
            clean_text: str,
            language: str,
            session: AsyncSession
    ) -> Word:
        """Create new word entry with clean text."""
        word = Word(
            language=language,
            word=clean_text,
            lemma=token.lemma_,
            pos=token.pos_,
            translation=None,
            complexity=None,
            cefr=None,
        )
        session.add(word)
        await session.flush()
        return word

    @staticmethod
    async def _is_valid_word_token(token: Token) -> bool:
        """Determine if a token should be processed as a word."""
        return (
                not token.is_punct and  # Skip punctuation
                not token.is_space and  # Skip whitespace
                not token.like_num and  # Skip pure numbers
                len(token.text.strip()) > 1  # Skip single characters
        )

    @staticmethod
    async def _add_subtitle_line(
            text: str, language: str, video_id: int, session: AsyncSession
    ) -> int:
        """Create a new Line entry."""
        line = Line(
            video_id=video_id,
            language=language,
            line_text=text,
            word_ids=[]
        )
        session.add(line)
        return line.id


if __name__ == "__main__":

    import sys
    from pathlib import Path
    import os
    from dotenv import load_dotenv

    # Add project root to Python path BEFORE any app imports
    project_root = str(Path(__file__).parent.parent.parent)
    sys.path.append(project_root)

    # Now we can import app modules
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    from app.models import User, Video, Word, Line, Sentence, WordContext

    # Load environment variables
    load_dotenv()

    # Use normal database URL
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        f"postgresql+asyncpg://{os.getenv('DEFAULT_DATABASE_USER')}:{os.getenv('DEFAULT_DATABASE_PASSWORD')}@localhost:{os.getenv('DEFAULT_DATABASE_PORT')}/{os.getenv('DEFAULT_DATABASE_DB')}"
    )


    async def test_processor():
        """Test the subtitle processor with different scenarios."""
        # Create test engine and session
        engine = create_async_engine(DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

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
                    print("Subtitle file does not exist. Please ensure the VTT file is present.")
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
                    word_ids=[]  # Initialize as empty list
                )
                session.add(video1)
                await session.flush()
                print(f"Created video with ID: {video1.id}")

                # Process subtitles for the first user and video
                vtt_processed_path = await processor.process_subtitles(
                    ytb_id=ytb_id,
                    user_uuid=user1.uuid,
                    session=session
                )
                print(f"Processed subtitles for video: {vtt_processed_path}")

                # Test Scenario 2: Existing video, new user
                print("\n=== Scenario 2: Existing video, new user ===")
                user2 = User(uuid=str(uuid4()))
                session.add(user2)
                await session.flush()
                print(f"Created second user with UUID: {user2.uuid}")

                # Associate video with second user
                video1.word_ids.extend(video1.word_ids)  # Assuming words are already processed
                user2.word_ids.extend(video1.word_ids)
                user2.video_ids.append(video1.id)

                await session.flush()
                print(f"Associated video ID {video1.id} with user ID {user2.id}")

                # Test Scenario 3: Existing video, existing user
                print("\n=== Scenario 3: Existing video, existing user ===")
                # Attempt to process subtitles again for user1 (should handle idempotency)
                vtt_processed_path = await processor.process_subtitles(
                    ytb_id=ytb_id,
                    user_uuid=user1.uuid,
                    session=session
                )
                print(f"Re-processed subtitles for video: {vtt_processed_path}")

                # Commit all changes
                await session.commit()

                # Print final statistics with top 10 examples
                print("\nFinal Database Statistics:")

                # Top 10 Words
                words = (await session.execute(select(Word).order_by(Word.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 Words:")
                for word in words:
                    print(
                        f"ID: {word.id}, Language: {word.language}, Word: {word.word}, POS: {word.pos}, Lemma: {word.lemma}")

                # Top 10 Lines
                lines = (await session.execute(select(Line).order_by(Line.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 Lines:")
                for line in lines:
                    print(f"ID: {line.id}, Language: {line.language}, Line Text: {line.line_text}")

                # Top 10 Sentences
                sentences = (
                    await session.execute(select(Sentence).order_by(Sentence.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 Sentences:")
                for sentence in sentences:
                    print(f"ID: {sentence.id}, Language: {sentence.language}, Sentence Text: {sentence.sentence_text}")

                # Top 10 WordContexts
                contexts = (
                    await session.execute(select(WordContext).order_by(WordContext.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 WordContexts:")
                for context in contexts:
                    print(
                        f"ID: {context.id}, Word ID: {context.word_id}, Line ID: {context.line_id}, Sentence ID: {context.sentence_id}")

                # Top 10 Users
                users = (await session.execute(select(User).order_by(User.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 Users:")
                for user in users:
                    print(f"ID: {user.id}, UUID: {user.uuid}, Video IDs: {user.video_ids}, Word IDs: {user.word_ids}")

                # Top 10 Videos
                videos = (await session.execute(select(Video).order_by(Video.id.asc()).limit(10))).scalars().all()
                print(f"\nTop 10 Videos:")
                for video in videos:
                    print(
                        f"ID: {video.id}, YouTube ID: {video.ytb_id}, URL: {video.url}, Video Path: {video.video_path}, VTT Path: {video.vtt_path}, Word IDs: {video.word_ids}")

                print("\nTest completed successfully!")

            except Exception as e:
                await session.rollback()
                print(f"Error during test: {str(e)}")
                raise


    """
    Command to re-initialize the database:
    docker compose down -v
    docker compose up -d
    rm -rf alembic/versions/*
    alembic revision --autogenerate -m "initial"
    alembic upgrade head
    
    Expected:
    Final Database Statistics:
    Words: 654
    Lines: 157
    Sentences: 77
    Word Contexts: 517
    
    """

    # Run the test
    asyncio.run(test_processor())
