from pydantic import BaseModel, ConfigDict, EmailStr


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
    id: str
    email: EmailStr


class VideoResponse(BaseResponse):
    id: int
    video_id: str


class TranslationResponse(BaseResponse):
    id: int
    word: str
    sentence: str
    clean_word: str
    translation: str


class StatisticsResponse(BaseResponse):
    number_sentences: int
    number_words: int


class GapFillingResponse(BaseResponse):
    id: int
    id_in_translation_model: int
    gapped_sentence: str
    options: list[str]
    correct_frequency: int
