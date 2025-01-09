from pydantic import BaseModel


class BaseRequest(BaseModel):
    # may define additional fields or config shared across requests
    pass


# class RefreshTokenRequest(BaseRequest):
#     refresh_token: str
#
#


class UserRequest(BaseRequest):
    uuid: str  # the user's uuid from localStorage if exists, else null


class VideoRequest(BaseModel):
    video_url: str
    uuid: str


class TranslationRequest(BaseRequest):
    uuid: str
    word: str
    sentence: str

# class StatisticsRequest(BaseRequest):
#     uuid: str
#     text: str
#
#
# class CorrectnessUpdateRequest(BaseModel):
#     uuid: str
#     is_correct: bool
