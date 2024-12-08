from __future__ import unicode_literals

import os
from pathlib import Path

from pytube import extract
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

from app.core.bilingual_vtt import create_bilingual_vtt

Element = list[dict[str, str | float]]
Transcript = dict[str, list[dict[str, str | float]]]


def get_bilingual_vtt(video_url: str) -> list[str]:
    """
    A function to download video, monolingual subtitles and then create bilingual subtitle.
    """
    video_id = get_video_id(video_url)

    static_folder = str(Path(__file__).parent.parent.parent) + "/static/"
    video_path = static_folder + video_id + "/" + video_id + ".mp4"

    video_existing = Path(video_path).exists()
    if not video_existing:
        # In theory, a video will always be downloaded together with its monolingual subtitles
        download_video_and_subtitles(video_id, video_url, static_folder)
    else:
        print("The video file exists.")

    en_vtt_existing = Path(
        static_folder + video_id + "/" + video_id + ".en.vtt"
    ).exists()

    # If the English subtitle doesn't exist, re-download subtitles.
    if not en_vtt_existing:
        __download_subtitles(video_id, static_folder)

    bi_vtt_path = static_folder + video_id + "/" + video_id + ".bi.vtt"
    bi_vtt_existing = Path(bi_vtt_path).exists()

    if not bi_vtt_existing:
        bi_vtt_path = create_bilingual_vtt(video_id, static_folder)
    else:
        print("The bilingual vtt file exists.")

    return video_path, bi_vtt_path


def get_video_id(video_url: str) -> str:
    """
    A function to extract video_id from video_url.
    """
    return extract.video_id(video_url)


def download_video_and_subtitles(
    video_id: str, video_url: str, static_folder: str
) -> None:
    """
    A function to download YouTube video and subtitles separately.
    """
    __download_youtube_video(video_id, video_url, static_folder)
    __download_subtitles(video_id, static_folder)


def __download_youtube_video(video_id: str, video_url: str, static_folder: str) -> None:
    """
    A function to download YouTube video.
    """
    ydl_opts = {
        "outtmpl": os.path.join(static_folder + video_id + "/" + video_id + ".mp4"),
    }
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])


def __download_subtitles(video_id: str, static_folder: str) -> Transcript:
    """
    A function to download subtitles of a YouTube video
    """
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    transcripts: Dict[str, List[Dict[str, str | float]]] = {}
    for element in transcript_list:
        # ToDo: check if other ways of describing Chinese subtitles, no matter simplified of traditional
        # Todo: add exception handler to deal with videos without Chinese subtitles
        if (
            str(element.language).startswith("Chinese")
            or str(element.language_code).startswith("zh")
            or (str(element.language_code) == "en" and element.is_generated != True)
        ):
            lan = element.language
            lan_code = element.language_code
            data = element.fetch()
            no_of_lines = len(data)
            print(
                "The current transcript is in :",
                lan,
                "\nit has: ",
                no_of_lines,
                " rows of lines",
            )

            transcripts = __save_subtitle(
                video_id, lan_code, data, transcripts, static_folder
            )

        else:
            continue
    return transcripts


def __save_subtitle(
    video_id: str,
    lan_code: str,
    data: Element,
    transcripts: Transcript,
    static_folder: str,
) -> Transcript:
    transcripts[lan_code] = data
    vtt = __convert_to_vtt(data)

    output_file_path = (
        static_folder + video_id + "/" + video_id + "." + lan_code + ".vtt"
    )
    print("-----\nvtt output_file_path: ", output_file_path)

    with open(output_file_path, "w", encoding="utf-8") as vtt_file:
        vtt_file.write(vtt)
    # print(f".vtt file saved at: {output_file_path}")
    return transcripts


def __convert_to_vtt(data: Element) -> str:
    vtt_content = "WEBVTT\n\n"

    for item in data:
        start_time = __format_time(item["start"])
        end_time = __format_time(item["start"] + item["duration"])
        text = item["text"]

        vtt_content += f"{start_time} --> {end_time}\n{text}\n\n"
    return vtt_content


def __format_time(time: float) -> str:
    minutes = int(time // 60)
    seconds = int(time % 60)
    milliseconds = int((time % 1) * 1000)
    return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=SYia4zqcE4g"
    # url = "https://www.youtube.com/watch?v=wr6fQ4KpbRM"
    id = get_video_id(url)
    print(id)
    print(get_bilingual_vtt(url))
