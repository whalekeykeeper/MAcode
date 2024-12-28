import re
from pathlib import Path
from typing import Dict

import jieba
import srt
import webvtt


def create_bilingual_vtt(video_id: str, static_folder: str) -> str:
    """Creates bilingual VTT file by merging Chinese and English subtitles."""

    # Get paths for source files
    path_zh = static_folder + f"/{video_id}/{video_id}.zh-CN.vtt"
    path_en = static_folder + f"/{video_id}/{video_id}.en.vtt"

    # Convert VTT to SRT for processing
    zh_srt_path = _convert_vtt_to_srt(path_zh)
    en_srt_path = _convert_vtt_to_srt(path_en)

    # Merge the subtitle files
    merged_srt_path = merge_subtitles(zh_srt_path, en_srt_path, video_id, static_folder)

    # Convert back to VTT for frontend display
    return _convert_srt_to_vtt(merged_srt_path)


def merge_subtitles(path1: str, path2: str, video_id: str, static_folder: str) -> str:
    """Merges two SRT files into one bilingual file."""

    # Read Chinese subtitles
    with open(path1, encoding="utf-8") as f1:
        subs_zh = {s.index: s for s in srt.parse(f1)}

    # Read English subtitles
    with open(path2, encoding="utf-8") as f2:
        subs_en = {s.index: s for s in srt.parse(f2)}

    # Process Chinese subtitles - merge multi-line and tokenize
    for idx, sub in subs_zh.items():
        if "\n" in sub.content:
            sub.content = sub.content.replace("\n", "")
        #     # ToDo: the following is commented out because not sure if it is necessary and if it will conflict with the tokenization of Spacy in the next step.
        # sub.content = _tokenize_zh(sub.content)

    # Process English subtitles - merge multi-line
    for idx, sub in subs_en.items():
        if "\n" in sub.content:
            sub.content = sub.content.replace("\n", " ")

    # Merge based on closest timestamp
    for idx, sub_en in subs_en.items():
        nearest_zh = min(subs_zh.values(), key=lambda x: abs(x.start - sub_en.start))
        nearest_zh.content = f"{nearest_zh.content}§\n{sub_en.content}"

    # Write merged subtitles
    output_path = f"{static_folder}/{video_id}/{video_id}_bilingual.srt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(list(subs_zh.values())))

    return output_path


def _tokenize_zh(text: str) -> str:
    """Tokenize Chinese text using jieba."""
    words_list = list(jieba.cut(text, use_paddle=True))
    return " ".join(words_list)


def _convert_vtt_to_srt(vtt_path: str) -> str:
    """Converts VTT file to SRT format."""
    vtt = webvtt.read(vtt_path)
    srt_path = vtt_path[:-4] + ".srt"
    vtt.save_as_srt()
    return srt_path


def _convert_srt_to_vtt(srt_path: str) -> str:
    """Converts SRT file to VTT format."""
    with open(srt_path, "r", encoding="utf8") as srt_file:
        lines = srt_file.read().splitlines()

    vtt_path = srt_path[:-4] + ".vtt"
    with open(vtt_path, "w", encoding="utf8") as vtt_file:
        vtt_file.write("WEBVTT\n\n")

        i = 0
        while i < len(lines):
            if "-->" in lines[i]:
                # Only convert timestamp format from SRT (00:00:00,000) to VTT (00:00:00.000)
                line = lines[i].replace(",", ".")
                vtt_file.write(line + "\n")
            else:
                # Keep all other lines unchanged
                vtt_file.write(lines[i] + "\n")
            i += 1

    return vtt_path


if __name__ == "__main__":
    id = "wr6fQ4KpbRM"
    create_bilingual_vtt(id, "./static")
