from pydantic import BaseModel, EmailStr


class BaseRequest(BaseModel):
    # may define additional fields or config shared across requests
    pass


class RefreshTokenRequest(BaseRequest):
    refresh_token: str


class UserUpdatePasswordRequest(BaseRequest):
    password: str


class UserCreateRequest(BaseRequest):
    email: EmailStr
    password: str


class VideoRequest(BaseRequest):
    video_url: str


class TranslationRequest(BaseRequest):
    word: str
    sentence: str


class StatisticsRequest(BaseRequest):
    text: str