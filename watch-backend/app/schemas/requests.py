from pydantic import BaseModel


class BaseRequest(BaseModel):
    # may define additional fields or config shared across requests
    pass


class UserRequest(BaseRequest):
    uuid: str  # the user's uuid from localStorage if exists, else create a new user


class VideoRequest(BaseModel):
    video_url: str


class VideoChosenWordsRequest(BaseRequest):
    video_id: int
    start_time: str
    end_time: str


class ExerciseResultUpdateRequest(BaseRequest):
    node_id: int
    exercise_id: int
    correct_or_not: bool


class CloudRequest(BaseModel):
    min_mastery: float
    max_mastery: float
