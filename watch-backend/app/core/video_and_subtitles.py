from __future__ import unicode_literals

import os
import re
from pathlib import Path

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


def get_bilingual_vtt(video_url: str, uuid: str):  # -> list[str]
    """
    A function to download video, monolingual subtitles and then create bilingual subtitle.
    """
    ytb_id = get_ytb_id(video_url)

    static_folder = str(Path(__file__).parent.parent.parent) + "/static/"
    video_path = static_folder + ytb_id + "/" + ytb_id + ".mp4"

    video_existing = Path(video_path).exists()
    if not video_existing:
        # In theory, a video will always be downloaded together with its monolingual subtitles
        download_video_and_subtitles(ytb_id, video_url, static_folder)
    else:
        logger.info(f"The video file for YouTube video {ytb_id} exists.")

    en_vtt_existing = Path(static_folder + ytb_id + "/" + ytb_id + ".en.vtt").exists()

    # If the English subtitle doesn't exist, re-download subtitles.
    if not en_vtt_existing:
        _download_subtitles(ytb_id, static_folder)

    # bi_vtt_path = static_folder + ytb_id + "/" + ytb_id + ".bi.vtt"
    # bi_vtt_existing = Path(bi_vtt_path).exists()

    # if not bi_vtt_existing:
    #     bi_vtt_path = create_bilingual_vtt(ytb_id, static_folder, uuid)
    # else:
    #     logger.Info("The bilingual vtt file exists.")
    #
    # return [video_path, bi_vtt_path]


def get_ytb_id(video_url: str) -> str:
    """
    A function to extract ytb_id from video_url.
    """
    return extract.video_id(video_url)


def download_video_and_subtitles(
        ytb_id: str, video_url: str, static_folder: str
) -> None:
    """
    A function to download YouTube video and subtitles.
    """
    _download_youtube_video(ytb_id, video_url, static_folder)
    _download_subtitles(ytb_id, static_folder)


def _download_youtube_video(ytb_id: str, video_url: str, static_folder: str) -> None:
    """
    A function to download YouTube video.
    """
    ydl_opts = {
        "outtmpl": os.path.join(static_folder + ytb_id + "/" + ytb_id + ".mp4"),
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def _download_subtitles(ytb_id: str, static_folder: str):
    """
    A function to download simplified Chinese and English subtitles of a YouTube video
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(ytb_id)
    transcripts: Dict[str, List[Dict[str, str | float]]] = {}
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
        static_folder: str,
):
    """
    A function to save the subtitles in .vtt format
    """
    vtt = _convert_to_vtt(data)

    output_file_path = static_folder + ytb_id + "/" + ytb_id + "." + lan_code + ".vtt"
    logger.debug(f"-----\nvtt output_file_path: {output_file_path}")

    with open(output_file_path, "w", encoding="utf-8") as vtt_file:
        vtt_file.write(vtt)
    logger.debug(f".vtt file saved at: {output_file_path} for lan: {lan_code}")


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


def bilingual_subtitles_exist(ytb_id) -> bool:
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
    url = "https://www.youtube.com/watch?v=ONs9FCY74p0"
    # url = "https://www.youtube.com/watch?v=wr6fQ4KpbRM"
    id = get_ytb_id(url)
    print(bilingual_subtitles_exist(id))
    get_bilingual_vtt(url, "uuid")
