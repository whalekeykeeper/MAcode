from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

import spacy
import webvtt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Line, Sentence, User, Word, Video, WordContext,
    UserWordAssociation, UserVideoAssociation
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
            existed_video_for_unwatched_user: bool = False
    ) -> str:
        """Process bilingual subtitles and update database.
        
        Args:
            ytb_id: YouTube video ID
            user_uuid: UUID of the user
            session: SQLAlchemy session
            existed_video_for_unwatched_user: True if video exists but hasn't been watched by this user
        """
        # Get video and user
        stmt = select(Video).where(Video.ytb_id == ytb_id)
        video = (await session.execute(stmt)).scalar_one()

        stmt = select(User).where(User.uuid == user_uuid)
        user = (await session.execute(stmt)).scalar_one()

        # Check if user has already watched this video
        stmt = select(UserVideoAssociation).where(
            UserVideoAssociation.user_id == user.id,
            UserVideoAssociation.video_id == video.id
        )
        existing_association = (await session.execute(stmt)).scalar_one_or_none()

        if existing_association:
            print(f"\nUser {user_uuid} has already watched video {ytb_id}")
            return video.vtt_path

        # Check if video content has been processed before
        stmt = select(Line).where(Line.video_id == video.id)
        existing_lines = (await session.execute(stmt)).scalars().all()

        # Extract content for processing
        subtitle_lines, full_zh_text, full_en_text = self._extract_subtitle_content(video.vtt_path)

        if existed_video_for_unwatched_user or existing_lines:
            print(f"\nVideo {ytb_id} exists. Creating user associations only...")
            # Process user associations using existing words
            await self._process_user_associations(
                user.id,
                video.id,
                full_zh_text,
                full_en_text,
                session
            )
            return video.vtt_path

        # If video content hasn't been processed, do full processing
        print(f"\nProcessing new video {ytb_id}...")

        # Create Line entries first (preserve original subtitles)
        line_map = {}  # Map to store line entries by number
        for sub_line in subtitle_lines:
            if sub_line.zh_text:
                zh_line = await self._create_line(sub_line.zh_text, "zh", video.id, session)
                line_map[f"zh_{sub_line.line_number}"] = zh_line
            if sub_line.en_text:
                en_line = await self._create_line(sub_line.en_text, "en", video.id, session)
                line_map[f"en_{sub_line.line_number}"] = en_line

        print(f"\nProcessing full texts into sentences...")

        print(f"full_zh_text: {full_zh_text}")
        print(f"full_en_text: {full_en_text}")

        # Process full texts into sentences
        zh_sentences = []
        for index, sent in enumerate(self.nlp_zh(full_zh_text).sents):
            sentence = await self._create_sentence(sent.text, "zh", video.id, session)
            zh_sentences.append((sent, sentence))
            # print(f"{index}: {sent}")

        en_sentences = []
        for sent in self.nlp_en(full_en_text).sents:
            sentence = await self._create_sentence(sent.text, "en", video.id, session)
            en_sentences.append((sent, sentence))
            # print(f"{index}: {sent}")
            
        

        # Process words with proper context tracking
        await self._process_words_with_context(
            zh_sentences, "zh", line_map, user.id, video.id, session
        )
        await self._process_words_with_context(
            en_sentences, "en", line_map, user.id, video.id, session
        )

        return video.vtt_path

    async def _process_words_with_context(
            self,
            sentences: List[Tuple[spacy.tokens.Span, Sentence]],
            language: str,
            line_map: Dict,
            user_id: int,
            video_id: int,
            session: AsyncSession
    ):
        """Process words while maintaining proper context across lines."""
        for spacy_sent, sentence_entry in sentences:
            # Find all lines that contain parts of this sentence
            sent_text = spacy_sent.text
            line_ids = []
            for key, line in line_map.items():
                if key.startswith(f"{language}_"):
                    # Check if any part of the sentence appears in this line
                    if any(part in line.line_text for part in sent_text.split('，')):
                        # Extract line number from key (e.g., "zh_1" -> 1)
                        line_number = int(key.split('_')[1])
                        line_ids.append(line_number)

            # Process words in the sentence
            for token in spacy_sent:
                if self._should_process_token(token):
                    # Create or get word
                    word = await self._get_or_create_word(token, language, session)

                    # Create word context for each line containing this word
                    for line_number in line_ids:
                        key = f"{language}_{line_number}"
                        if key in line_map and token.text in line_map[key].line_text:
                            context = WordContext(
                                word_id=word.id,
                                line_id=line_map[key].id,
                                sentence_id=sentence_entry.id
                            )
                            session.add(context)

                    # Create user-word association
                    await self._create_user_word_association(user_id, word.id, session)

    def _should_process_token(self, token) -> bool:
        """Determine if a token should be processed as a word."""
        return (
                not token.is_punct and  # Skip punctuation
                not token.is_space and  # Skip whitespace
                not token.like_num and  # Skip pure numbers
                len(token.text.strip()) > 1  # Skip single characters
        )

    def _find_containing_lines(self, sentence_text: str, lang: str, line_map: Dict) -> List[int]:
        """Find all line IDs that contain parts of this sentence."""
        line_ids = []
        for key, line in line_map.items():
            if key.startswith(f"{lang}_") and sentence_text in line.line_text:
                line_ids.append(line.id)
        return line_ids

    def _extract_bilingual_lines(self, vtt_path: str) -> List[Tuple[str, str]]:
        """Extract paired Chinese and English lines from bilingual VTT."""
        bilingual_lines = []
        vtt = webvtt.read(vtt_path)

        for caption in vtt:
            if '§§§' in caption.text:
                zh_text, en_text = caption.text.split('§§§')
                bilingual_lines.append((zh_text.strip(), en_text.strip()))

        return bilingual_lines

    async def _process_bilingual_line(
            self,
            zh_text: str,
            en_text: str,
            video_id: int,
            user_id: int,
            session: AsyncSession
    ):
        """Process a pair of Chinese and English lines."""
        # Create Line entries
        zh_line = await self._create_line(zh_text, "zh", video_id, session)
        en_line = await self._create_line(en_text, "en", video_id, session)
        await session.flush()  # Ensure lines have IDs

        # Process sentences
        zh_sentences = list(self.nlp_zh(zh_text).sents)
        en_sentences = list(self.nlp_en(en_text).sents)

        # Create Sentence entries and process words
        for zh_sent, en_sent in zip(zh_sentences, en_sentences):
            zh_sentence = await self._create_sentence(zh_sent.text, "zh", video_id, session)
            en_sentence = await self._create_sentence(en_sent.text, "en", video_id, session)
            await session.flush()  # Ensure sentences have IDs

            # Process words in both languages
            await self._process_words(zh_sent, "zh", zh_line.id, zh_sentence.id, user_id, session)
            await self._process_words(en_sent, "en", en_line.id, en_sentence.id, user_id, session)

    async def _process_words(
            self,
            sent: spacy.tokens.Span,
            language: str,
            line_id: int,
            sentence_id: int,
            user_id: int,
            session: AsyncSession
    ):
        """Process words in a sentence and create necessary associations."""
        for token in sent:
            if self._should_process_token(token):
                # Get or create word
                word = await self._get_or_create_word(token, language, session)
                await session.flush()  # Ensure word has ID

                # Create word context
                context = WordContext(
                    word_id=word.id,
                    line_id=line_id,
                    sentence_id=sentence_id
                )
                session.add(context)
                await session.flush()

                # Create user-word association if not exists
                await self._create_user_word_association(user_id, word.id, session)
                await session.flush()

    async def _get_or_create_word(
            self,
            token: spacy.tokens.Token,
            language: str,
            session: AsyncSession
    ) -> Word:
        """Get existing word or create new one."""
        stmt = select(Word).where(
            Word.word == token.text,
            Word.language == language
        )
        word = (await session.execute(stmt)).scalar_one_or_none()

        if not word:
            word = Word(
                language=language,
                word=token.text,
                lemma=token.lemma_,
                pos=token.pos_,
                translation=None,  # Will be filled later
                complexity=None  # Will be calculated later
            )
            session.add(word)
            await session.flush()  # Make sure word gets an ID

        return word

    async def _create_line(
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

    async def _create_sentence(
            self, text: str, language: str, video_id: int, session: AsyncSession
    ) -> Sentence:
        """Create a new Sentence entry."""
        sentence = Sentence(
            video_id=video_id,
            language=language,
            sentence_text=text
        )
        session.add(sentence)
        return sentence

    async def _get_or_create_video(
            self, video_id: str, vtt_path: str, session: AsyncSession
    ) -> Video:
        """Get existing video, or download one and update database."""
        stmt = select(Video).where(Video.ytb_id == video_id)
        video = (await session.execute(stmt)).scalar_one_or_none()

        if not video:
            video = Video(
                ytb_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                video_path=f"static/{video_id}/{video_id}.mp4",
                vtt_path=vtt_path
            )
            session.add(video)
            await session.flush()  # Make sure video gets an ID

        return video

    async def _create_user_word_association(
            self, user_id: int, word_id: int, session: AsyncSession
    ):
        """Create user-word association if not exists."""
        stmt = select(UserWordAssociation).where(
            UserWordAssociation.user_id == user_id,
            UserWordAssociation.word_id == word_id
        )
        exists = (await session.execute(stmt)).scalar_one_or_none()

        if not exists:
            assoc = UserWordAssociation(user_id=user_id, word_id=word_id)
            session.add(assoc)

    async def _create_user_video_association(
            self, user_id: int, video_id: int, session: AsyncSession
    ):
        """Create user-video association if not exists."""
        stmt = select(UserVideoAssociation).where(
            UserVideoAssociation.user_id == user_id,
            UserVideoAssociation.video_id == video_id
        )
        exists = (await session.execute(stmt)).scalar_one_or_none()

        if not exists:
            assoc = UserVideoAssociation(user_id=user_id, video_id=video_id)
            session.add(assoc)

    async def _get_words_from_text(
            self,
            text: str,
            language: str,
            video_id: int,
            session: AsyncSession
    ) -> List[Word]:
        """Get existing words from text without creating new entries."""
        nlp = self.nlp_zh if language == "zh" else self.nlp_en
        doc = nlp(text)
        words = []

        for token in doc:
            if self._should_process_token(token):
                stmt = select(Word).where(
                    Word.word == token.text,
                    Word.language == language
                )
                word = (await session.execute(stmt)).scalar_one_or_none()
                if word:
                    words.append(word)

        return words

    def _extract_subtitle_content(self, subtitle_path: str) -> Tuple[List[SubtitleLine], str, str]:
        """Extract content from bilingual VTT file."""
        print(f"\nAttempting to read subtitle file: {subtitle_path}")
        print(f"File exists: {Path(subtitle_path).exists()}")

        subtitle_lines = []
        zh_texts = []
        en_texts = []

        try:
            # Read VTT file
            vtt = webvtt.read(subtitle_path)
            print(f"Successfully read subtitle file")

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

                # Create subtitle line
                subtitle_lines.append(SubtitleLine(
                    line_number=i + 1,
                    timestamp=caption.start,
                    zh_text=zh_text,
                    en_text=en_text
                ))

                # Add to full text if content exists
                if zh_text:
                    # Process Chinese text with spaCy for punctuation check
                    zh_doc = self.nlp_zh(zh_text)
                    # Special case: for Chinese subtitles that the line which contains "翻译人员" and "校对人员" in TED Talks' videos are normally not punctuated.
                    # TODO: This is a temporary fix.
                    if "翻译人员" in zh_text and "校对人员" in zh_text:
                        zh_text = zh_text + '。'
                    zh_texts.append(zh_text)

                if en_text:
                    # Process English text with spaCy for punctuation check
                    en_doc = self.nlp_en(en_text)
                    en_texts.append(en_text)

            # Join texts without extra spaces for Chinese, with spaces for English
            full_zh_text = ''.join(zh_texts)
            full_en_text = ' '.join(en_texts)

            return subtitle_lines, full_zh_text, full_en_text

        except Exception as e:
            print(f"Error reading subtitle file: {str(e)}")
            raise

    async def _process_user_associations(
            self,
            user_id: int,
            video_id: int,
            zh_text: str,
            en_text: str,
            session: AsyncSession
    ):
        """Process user associations for existing words.
        
        Args:
            user_id: ID of the user
            video_id: ID of the video
            zh_text: Full Chinese text
            en_text: Full English text
            session: Database session
        """
        # Get existing words from Chinese text
        zh_words = await self._get_words_from_text(
            zh_text,
            "zh",
            video_id,
            session
        )

        # Get existing words from English text
        en_words = await self._get_words_from_text(
            en_text,
            "en",
            video_id,
            session
        )

        # Create user associations for all words
        for word in zh_words + en_words:
            await self._create_user_word_association(user_id, word.id, session)

        # Create user-video association
        await self._create_user_video_association(user_id, video_id, session)

        print(f"Created associations for {len(zh_words)} Chinese words and {len(en_words)} English words")


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
        engine = create_async_engine(DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession)

        async with async_session() as session:
            try:
                # Setup test data
                ytb_id = "wr6fQ4KpbRM"
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

                # Initialize processor
                processor = SubtitleProcessor()

                # Test Scenario 1: New video, first user
                print("\n=== Scenario 1: New video, first user ===")
                # Create first video and user
                video1 = Video(
                    ytb_id=ytb_id,
                    url=url,
                    video_path=str(video_folder / f"{ytb_id}.mp4"),
                    vtt_path=str(vtt_path)
                )
                session.add(video1)
                user1 = User()
                session.add(user1)
                await session.flush()
                print(f"Created video with ID: {video1.id}")
                print(f"Created first user with UUID: {user1.uuid}")

                # Process with existed_video_for_unwatched_user=False (default)
                await processor.process_subtitles(
                    ytb_id=ytb_id,
                    user_uuid=user1.uuid,
                    session=session
                )

                # Test Scenario 2: Existing video, new user
                print("\n=== Scenario 2: Existing video, new user ===")
                user2 = User()
                session.add(user2)
                await session.flush()
                print(f"Created second user with UUID: {user2.uuid}")

                # Process with existed_video_for_unwatched_user=True
                await processor.process_subtitles(
                    ytb_id=ytb_id,
                    user_uuid=user2.uuid,
                    session=session,
                    existed_video_for_unwatched_user=True
                )

                # Test Scenario 3: Existing video, existing user
                print("\n=== Scenario 3: Existing video, existing user ===")
                # Try to process again for user1
                await processor.process_subtitles(
                    ytb_id=ytb_id,
                    user_uuid=user1.uuid,
                    session=session,
                    existed_video_for_unwatched_user=False
                )

                # Print final statistics
                print("\nFinal Database Statistics:")
                words = (await session.execute(select(Word))).scalars().all()
                lines = (await session.execute(select(Line))).scalars().all()
                sentences = (await session.execute(select(Sentence))).scalars().all()
                contexts = (await session.execute(select(WordContext))).scalars().all()
                user_word_assocs = (await session.execute(
                    select(UserWordAssociation)
                )).scalars().all()
                user_video_assocs = (await session.execute(
                    select(UserVideoAssociation)
                )).scalars().all()

                print(f"Words: {len(words)}")
                print(f"Lines: {len(lines)}")
                print(f"Sentences: {len(sentences)}")
                print(f"Word Contexts: {len(contexts)}")
                print(f"User-Word Associations: {len(user_word_assocs)}")
                print(f"User-Video Associations: {len(user_video_assocs)}")

                if words:
                    print("\nSample Chinese words:")
                    zh_words = [w for w in words if w.language == "zh"][:5]
                    for word in zh_words:
                        print(f"Word: {word.word}, POS: {word.pos}")

                    print("\nSample English words:")
                    en_words = [w for w in words if w.language == "en"][:5]
                    for word in en_words:
                        print(f"Word: {word.word}, POS: {word.pos}")

                await session.commit()
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
    User-Word Associations: 1308
    User-Video Associations: 2

    """

    # Run the test
    asyncio.run(test_processor())
