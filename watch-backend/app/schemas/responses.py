from datetime import datetime
from typing import Tuple, List, Dict, Any

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


class GapFillingResponse(BaseModel):
    user_id: int
    exercise_id: int
    node_id: int
    correct_answer_lemma: str
    select_list: List[Dict[str, Any]]
    distractors: List[str]


class VideoChosenWordsResponse(BaseResponse):
    # word_id, marked_as_learned, lemma, translation, sentence, record time
    chosen_words: List[Tuple[int, bool, str, str | None, str, datetime]]


class ExerciseResultUpdateResponse(BaseResponse):
    exercise_amount: int
    correct_amount: int
    correct_rate: float
