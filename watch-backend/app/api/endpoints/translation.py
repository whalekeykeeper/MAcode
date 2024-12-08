# /app/api/endpoints/translation.py

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.translation_service import stat, translate
from app.models import Translation
from app.schemas.requests import StatisticsRequest, TranslationRequest
from app.schemas.responses import StatisticsResponse, TranslationResponse

router = APIRouter()


@router.post("/", response_model=TranslationResponse, status_code=201)
async def create_new_translation(
    new_translation: TranslationRequest,
    session: AsyncSession = Depends(deps.get_session),
):
    """Creates new translation. Only for logged users."""
    clean_word, word_translation = translate(
        new_translation.word, new_translation.sentence
    )

    trans = Translation(
        word=new_translation.word,
        sentence=new_translation.sentence,
        clean_word=clean_word,
        translation=word_translation,
    )
    session.add(trans)
    await session.commit()
    return trans


@router.get("/words", response_model=list[TranslationResponse], status_code=200)
async def get_all_my_translations(
    session: AsyncSession = Depends(deps.get_session),
):
    """Get list of clicked words for current user."""

    stmt = select(Translation).order_by(Translation.word)
    words = await session.execute(stmt)
    return words.scalars().all()


@router.post("/statistics", response_model=StatisticsResponse, status_code=201)
async def create_new_statistics(new_statistics: StatisticsRequest):
    """Creates new statistics. No user check."""
    number_sentences, number_words = (
        stat(new_statistics.text)[0],
        stat(new_statistics.text)[1],
    )

    statistics = StatisticsResponse(
        number_sentences=number_sentences, number_words=number_words
    )
    return statistics
