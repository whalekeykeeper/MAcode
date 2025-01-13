from datetime import datetime
from typing import Tuple, List

from pydantic import BaseModel, ConfigDict


class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AccessTokenResponse(BaseResponse):
    token_type: str
    access_token: str
    expires_at: int
    issued_at: int
    refresh_token: str
    refresh_token_expires_at: int
    refresh_token_issued_at: int


class UserResponse(BaseResponse):
    uuid: str
    exists: bool


class VideoResponse(BaseResponse):
    id: int
    ytb_id: str
    url: str
    video_path: str
    vtt_path: str
    uuid: str


class StatisticsResponse(BaseResponse):
    number_sentences: int
    number_words: int


class GapFillingResponse(BaseResponse):
    id: int
    id_in_translation_model: int
    gapped_sentence: str
    options: list[str]
    correct_frequency: int
    incorrect_frequency: int


class VideoChosenWordsResponse(BaseResponse):
    # word_id, marked_as_learned, lemma, translation, sentence
    chosen_words: List[Tuple[int, bool, str, str | None, str, datetime]]
