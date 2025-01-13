from pydantic import BaseModel


class BaseRequest(BaseModel):
    # may define additional fields or config shared across requests
    pass


class UserRequest(BaseRequest):
    uuid: str  # the user's uuid from localStorage if exists, else create a new user


class VideoRequest(BaseModel):
    video_url: str


# class TranslationRequest(BaseRequest):
#     uuid: str
#     word: str
#     sentence: str


class CorrectnessUpdateRequest(BaseModel):
    # Define the fields for CorrectnessUpdateRequest
    word_id: int  # to look for the node to increase the mastery score
    is_correct: bool


class VideoChosenWordsRequest(BaseRequest):
    video_id: int
    start_time: str
    end_time: str
