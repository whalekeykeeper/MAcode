from pathlib import Path
from typing import Dict, List, Tuple, Optional
import webvtt
import spacy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bilingual_vtt import create_bilingual_vtt
from app.models import (
    Line, Sentence, User, Word, Video, WordContext,
    UserWordAssociation, UserVideoAssociation
)

class SubtitleProcessor:
    def __init__(self):
        self.nlp_en = spacy.load("en_core_web_lg")
        self.nlp_zh = spacy.load("zh_core_web_lg")

    async def process_subtitles(
        self, 
        video_id: str, 
        static_folder: str,
        user_uuid: str,
        session: AsyncSession
    ) -> str:
        """Process bilingual subtitles and update database."""
        
        # Create bilingual VTT for frontend display
        vtt_path = create_bilingual_vtt(video_id, static_folder)
        
        # Extract bilingual lines from VTT
        bilingual_lines = self._extract_bilingual_lines(vtt_path)
        
        async with session.begin():
            # Get user
            stmt = select(User).where(User.uuid == user_uuid)
            user = (await session.execute(stmt)).scalar_one()
            
            # Get or create video
            video = await self._get_or_create_video(video_id, vtt_path, session)
            
            # Create user-video association if not exists
            await self._create_user_video_association(user.id, video.id, session)
            
            # Process each bilingual line
            for zh_text, en_text in bilingual_lines:
                await self._process_bilingual_line(
                    zh_text, en_text, video.id, user.id, session
                )
        
        return vtt_path

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
        
        # Process sentences
        zh_sentences = list(self.nlp_zh(zh_text).sents)
        en_sentences = list(self.nlp_en(en_text).sents)
        
        # Create Sentence entries and process words
        for zh_sent, en_sent in zip(zh_sentences, en_sentences):
            zh_sentence = await self._create_sentence(zh_sent.text, "zh", video_id, session)
            en_sentence = await self._create_sentence(en_sent.text, "en", video_id, session)
            
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
                
                # Create word context
                context = WordContext(
                    word_id=word.id,
                    line_id=line_id,
                    sentence_id=sentence_id
                )
                session.add(context)
                
                # Create user-word association if not exists
                await self._create_user_word_association(user_id, word.id, session)

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
                # translation will be filled later
                translation=None,
                # complexity will be calculated later
                complexity=None
            )
            session.add(word)
        
        return word

    def _should_process_token(self, token: spacy.tokens.Token) -> bool:
        """Determine if token should be processed as a word."""
        return not (
            token.is_punct or 
            token.is_space or 
            token.is_digit or 
            token.is_stop
        )

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
        """Get existing video or create new one."""
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


if __name__ == "__main__":
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.session import SQLALCHEMY_DATABASE_URL
    
    async def test_processor():
        # Create test engine and session
        engine = create_async_engine(SQLALCHEMY_DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession)
        
        # Create a test user
        async with async_session() as session:
            user = User()  # This will auto-generate UUID
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"Created test user with UUID: {user.uuid}")
            
            # Initialize processor
            processor = SubtitleProcessor()
            
            # Process existing subtitle file
            video_id = "wr6fQ4KpbRM"
            vtt_path = await processor.process_subtitles(
                video_id=video_id,
                static_folder="static",
                user_uuid=user.uuid,
                session=session
            )
            
            print(f"Processed subtitles, VTT path: {vtt_path}")
            
            # Print some stats
            words = (await session.execute(select(Word))).scalars().all()
            lines = (await session.execute(select(Line))).scalars().all()
            sentences = (await session.execute(select(Sentence))).scalars().all()
            contexts = (await session.execute(select(WordContext))).scalars().all()
            
            print(f"\nStats:")
            print(f"Words: {len(words)}")
            print(f"Lines: {len(lines)}")
            print(f"Sentences: {len(sentences)}")
            print(f"Word Contexts: {len(contexts)}")
            
            # Print sample data
            if words:
                print("\nSample words:")
                for word in words[:5]:
                    print(f"Word: {word.word}, Language: {word.language}, POS: {word.pos}")
    
    # Run the test
    asyncio.run(test_processor())
