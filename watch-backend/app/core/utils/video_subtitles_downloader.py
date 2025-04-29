from __future__ import unicode_literals

import re
from pathlib import Path

from fastapi import HTTPException
from pytube import extract
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

from app.core.logger import logger

Element = list[dict[str, str | float]]
Transcript = dict[str, list[dict[str, str | float]]]

# For research reason, we only use zh-CN and en to have a unified language code for processing.
# ToDo: allow more language codes for future use.

# Patterns for matching language codes
ENGLISH_PATTERNS = [
    r"^en$",
    # r"^en-.*$",
    # r"^eng$",
]  # en  # en-US, en-GB, etc.  # eng

SIMPLIFIED_CHINESE_PATTERNS = [
    # r"^zh$",  # zh
    # r"^zh-Hans$",  # Simplified Chinese
    r"^zh-CN$",  # Chinese (China)
    # r'^zh-.*$',  # Other Chinese variants
    # r'^chi$'  # chi
]


def download_video_and_subtitles(
        ytb_id: str, video_url: str, static_folder: Path
) -> None:
    """
    A function to download YouTube video and subtitles.
    """
    logger.debug(f"-----Downloading video and subtitles for video: {ytb_id}")
    if not video_offered_with_zh_en_subtitles(ytb_id):
        raise HTTPException(
            status_code=400,
            detail="The video was not offered with subtitles with lang_code zh-CN and en.",
        )
    _download_youtube_video(ytb_id, video_url, static_folder)
    _download_subtitles(ytb_id, static_folder)


def get_ytb_id(video_url: str) -> str:
    """
    A function to extract ytb_id from video_url.
    """
    try:
        return extract.video_id(video_url)
    except RegexMatchError:
        raise ValueError("Invalid YouTube URL format")


def _download_youtube_video(ytb_id: str, video_url: str, static_folder: Path) -> None:
    """
    A function to download YouTube video.
    """
    # Create directory if it doesn't exist
    output_dir = static_folder / ytb_id
    output_dir.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "outtmpl": str(output_dir / f"{ytb_id}.mp4"),
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])
        logger.info(f"Video downloaded at: {output_dir / f'{ytb_id}.mp4'}")


def _download_subtitles(ytb_id: str, static_folder: Path):
    """
    A function to download simplified Chinese and English subtitles of a YouTube video
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(ytb_id)
    # transcripts: Dict[str, List[Dict[str, str | float]]] = {}
    for element in transcript_list:
        # ToDo: check YouTube API if it is necessary to check if the transcript is generated
        if (
                _matches_patterns(element.language_code, SIMPLIFIED_CHINESE_PATTERNS)
                or _matches_patterns(element.language_code, ENGLISH_PATTERNS)
        ) and element.is_generated != True:
            lan = element.language
            data = element.fetch()
            logger.debug(
                f"The current transcript is in {lan}, it has: {len(data)} rows of lines"
            )

            _save_subtitle(ytb_id, element.language_code, data, static_folder)
        else:
            continue


def _save_subtitle(
        ytb_id: str,
        lan_code: str,
        data: Element,
        static_folder: Path,
):
    """
    A function to save the subtitles in .vtt format
    """
    vtt = _convert_to_vtt(data)

    output_file_path = Path(static_folder) / ytb_id / f"{ytb_id}.{lan_code}.vtt"

    with open(output_file_path, "w", encoding="utf-8") as vtt_file:
        vtt_file.write(vtt)
    logger.info(
        f"Subtitle file in {lan_code} for video {ytb_id} saved at: {output_file_path}."
    )


def _convert_to_vtt(data: Element) -> str:
    """
    A function to convert the subtitles to .vtt format
    """
    vtt_content = "WEBVTT\n\n"

    for item in data:
        start_time = _format_time(item["start"])
        end_time = _format_time(item["start"] + item["duration"])
        text = item["text"]

        vtt_content += f"{start_time} --> {end_time}\n{text}\n\n"
    return vtt_content


def _format_time(time: float) -> str:
    minutes = int(time // 60)
    seconds = int(time % 60)
    milliseconds = int((time % 1) * 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


def video_offered_with_zh_en_subtitles(ytb_id) -> bool:
    """
    A function to check if the given YouTube video has bilingual subtitles
    """
    ydl_opts = {
        "skip_download": True,
        "quiet": True,
        "extract_flat": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={ytb_id}", download=False
            )
            subtitles = info.get("subtitles", {})

            has_english = any(
                _matches_patterns(lang_code, ENGLISH_PATTERNS)
                for lang_code in subtitles.keys()
            )

            has_chinese = any(
                _matches_patterns(lang_code, SIMPLIFIED_CHINESE_PATTERNS)
                for lang_code in subtitles.keys()
            )

            # Create a readable format of available languages for debugging
            available_langs = {}
            for lang_code, sub_info in subtitles.items():
                available_langs[lang_code] = {
                    "name": sub_info[0].get("name", "Unknown"),
                    "type": "manual",
                }
            logger.debug(f"Available languages: {available_langs}")

            return has_english and has_chinese

    except Exception as e:
        print(
            f"Encountered error when checking if video {ytb_id} has both simplified Chinese and English subtitles:"
            f" {str(e)}"
        )
        return False


def _matches_patterns(lang_code, patterns):
    return any(re.match(pattern, lang_code) for pattern in patterns)


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=ONs9FCY74p0"
    # video_url = "https://www.youtube.com/watch?v=wr6fQ4KpbRM"
    ytb_id = get_ytb_id(video_url)
    logger.info(
        "The video has both zh and en subtitles: ",
        video_offered_with_zh_en_subtitles(ytb_id),
    )
    static_folder = Path("app/static/")
    download_video_and_subtitles(ytb_id, video_url, static_folder)
