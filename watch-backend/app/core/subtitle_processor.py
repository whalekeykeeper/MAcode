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
        lines_dict = await self._create_line_entries(subtitle_lines, video.id, session)

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
                    # are normally not punctuated. If the last character is not a punctuation in Chinese,
                    # add a period for now and this should be improved in the future.
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

    @staticmethod
    async def _create_line_entries(
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
                )
                session.add(zh_line)
                line_objects.append(("zh", zh_line))

            if line.en_text:
                en_line = Line(
                    video_id=video_id,
                    language="en",
                    line_text=line.en_text,
                )
                session.add(en_line)
                line_objects.append(("en", en_line))

        # Flush to get all IDs
        await session.flush()  # After this line, each line_obj in line_objects has its id populated

        # Now create the mappings with the guaranteed IDs
        for language, line_obj in line_objects:
            if language == "zh":
                lines_zh[line_obj.id] = line_obj.line_text  # Here we can access line_obj.id
            else:
                lines_en[line_obj.id] = line_obj.line_text  # Here we can access line_obj.id

        lines['zh'] = lines_zh
        lines['en'] = lines_en
        return lines

    async def _process_text_to_create_and_update_sentence_entries(
            self,
            lines_dict: Dict[int, str],
            full_text: str,
            language: str,
            video_id: int,
            session: AsyncSession
    ) -> List[SentenceData]:
        """Process text to extract sentences and create Sentence entries."""
        sentences_data = []
        nlp = self.nlp_zh if language == "zh" else self.nlp_en
        doc = nlp(full_text)

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
        sentences = {}
        for (sent, sentence_entry) in sentence_objects:
            sentences[sentence_entry.id] = sent

        # Now we want to use variable sentences to create word entries and objects
        word_objects = []
        for sentence_id, sent in sentences.items():
            for token in sent:
                if not self._is_valid_word_token(token):
                    continue

                word_entry = Word(
                    language=language,
                    word=token.text,
                    lemma=token.lemma_,
                    pos=token.pos_,
                    sentence_id=sentence_id
                )
                session.add(word_entry)
                word_objects.append((sentence_id, word_entry))
        # Flush to get all word IDs
        await session.flush()
        #
        # # Now create SentenceData with guaranteed IDs
        # line_ids = list(lines_dict.keys())
        # lines = list(lines_dict.values())
        # logger.info("----- In total lines: ", len(line_ids))
        # logger.info("----- In total sentence: ", len(sentence_objects))
        #
        # if language == "zh":
        #     all_text = ''.join(lines)
        # else:
        #     all_text = ' '.join(lines)
        # current_pos = 0
        #
        # for sent, sentence_entry in sentence_objects:
        #     # Find which lines contain this sentence
        #     if len(sent.text.strip()) == 0:
        #         continue
        #
        #     # Find where this sentence starts in the complete text
        #     sentence_start = all_text.index(sent.text, current_pos)
        #     sentence_end = sentence_start + len(sent.text)
        #     current_pos = sentence_end
        #
        #     # Find which lines contain parts of this sentence
        #     current_line_start = 0
        #     line_numbers = []
        #
        #     for i, line in enumerate(lines):
        #         current_line_end = current_line_start + len(line)
        #
        #         # Check if this line overlaps with the sentence
        #         if (current_line_start < sentence_end and
        #                 current_line_end > sentence_start):
        #             line_numbers.append(line_ids[i])  # Append the line ID instead of index
        #
        #         current_line_start = current_line_end
        #
        #     sentences_data.append(SentenceData(
        #         sent=sent,
        #         sentence_id=sentence_entry.id,  # Now we have the ID
        #         line_numbers=line_numbers  # This is going to be updated.
        #     ))

        return sentences_data

    async def _create_and_update_words_contexts_linewordids(
            self,
            zh_sentences: List[SentenceData],
            en_sentences: List[SentenceData],
            lines_dict: dict[str, dict[int, str]],
            session: AsyncSession
    ) -> List[Word]:
        """Process words and their contexts, return all processed words."""
        # Step 1: Create all word entries first
        word_objects = {}  # {sentence_id: [word_objects]}
        processed_words = []

        # Create words for both languages
        for sentences, language in [(zh_sentences, "zh"), (en_sentences, "en")]:
            for sentence_data in sentences:
                words_in_sentence = []
                for token in sentence_data.sent:
                    if not self._is_valid_word_token(token):
                        continue

                    word = Word(
                        language=language,
                        word=token.text,
                        lemma=token.lemma_,
                        pos=token.pos_,
                    )
                    session.add(word)
                    words_in_sentence.append(word)
                    processed_words.append(word)

                word_objects[sentence_data.sentence_id] = words_in_sentence

        # Flush to get all word IDs
        await session.flush()

        # Step 2: Create word contexts by aligning words with lines
        word_line_sentence = []  # Will store (line_id, sentence_id, word_id) tuples

        for sentences, language in [(zh_sentences, "zh"), (en_sentences, "en")]:
            lines = lines_dict[language]  # lines: {line_id: line_text}

            # 此处开始循环句子，每次处理一个句子
            for sentence_data in sentences:
                # Get words for this sentence
                sentence_words = word_objects.get(sentence_data.sentence_id, [])
                if not sentence_words:
                    continue

                remaining_words = sentence_words.copy()
                word_idx = 0  # Track which word we're looking for

                # Process each line in the sentence
                for line_id in sentence_data.line_numbers:
                    if not remaining_words:  # All words found
                        break

                    line_text = lines[line_id]
                    current_pos = 0

                    # Try to find words in order in this line
                    while remaining_words and current_pos < len(line_text):
                        word = remaining_words[0]
                        word_text = word.word

                        # Try to find the word in the current line from current_pos
                        pos = line_text.find(word_text, current_pos)
                        if pos != -1:
                            # Word found, create mapping
                            word_line_sentence.append((
                                line_id,
                                sentence_data.sentence_id,
                                word.id
                            ))

                            # Move position past this word and remove it from remaining
                            current_pos = pos + len(word_text)
                            remaining_words.pop(0)
                        else:
                            # Word not found in this line, move to next line
                            break

                # All words should be found within their sentence's lines
                assert not remaining_words, (
                    f"Not all words found for sentence {sentence_data.sentence_id}:\n"
                    f"Remaining words: {[w.word for w in remaining_words]}\n"
                    f"Sentence text: {sentence_data.sent.text}\n"
                    f"Lines: {[lines[lid] for lid in sentence_data.line_numbers]}"
                )

        # Create all WordContext entries
        for line_id, sentence_id, word_id in word_line_sentence:
            context = WordContext(
                word_id=word_id,
                line_id=line_id,
                sentence_id=sentence_id
            )
            session.add(context)

        # Final flush to save all WordContext entries
        await session.flush()
        return processed_words

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
        )
        session.add(word)
        await session.flush()
        return word

    @staticmethod
    def _is_valid_word_token(token: Token) -> bool:
        """Determine if a token should be processed as a word."""
        return (
                not token.is_punct and  # Skip punctuation
                not token.is_space and  # Skip whitespace
                not token.like_num  # Skip pure numbers
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
