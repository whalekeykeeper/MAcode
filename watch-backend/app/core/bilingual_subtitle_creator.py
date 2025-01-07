from pathlib import Path

import srt
import webvtt

from app.core.logger import logger


def create_bilingual_vtt(video_id: str, static_folder: Path) -> Path:
    """Creates bilingual VTT file by merging Chinese and English subtitles."""
    # Get paths for source files
    path_zh = static_folder / video_id / f"{video_id}.zh-CN.vtt"
    path_en = static_folder / video_id / f"{video_id}.en.vtt"

    # Convert VTT to SRT for processing
    zh_srt_path = _convert_vtt_to_srt(path_zh, video_id, static_folder)
    en_srt_path = _convert_vtt_to_srt(path_en, video_id, static_folder)

    # Merge the subtitle files
    merged_srt_path = merge_subtitles(zh_srt_path, en_srt_path, video_id, static_folder)
    logger.debug(f"Merged subtitles saved at: {merged_srt_path}")

    # Convert back to VTT for frontend display
    return _convert_srt_to_vtt(merged_srt_path, video_id, static_folder)


def merge_subtitles(path1: Path, path2: Path, video_id: str, static_folder: Path) -> Path:
    """Merges two SRT files into one bilingual file."""

    # Read Chinese subtitles
    with open(path1, encoding="utf-8") as f1:
        subs_zh = {s.index: s for s in srt.parse(f1)}

    # Read English subtitles
    with open(path2, encoding="utf-8") as f2:
        subs_en = {s.index: s for s in srt.parse(f2)}

    # Debug: Print initial counts
    print(f"Chinese subtitles: {len(subs_zh)}")
    print(f"English subtitles: {len(subs_en)}")

    # Process Chinese subtitles - merge multi-line
    for idx, sub in subs_zh.items():
        if "\n" in sub.content:
            sub.content = sub.content.replace("\n", "")
        # Verify no "§§§" in Chinese content
        if "§§§" in sub.content:
            print(f"Warning: Found §§§ in Chinese subtitle: {sub.content}")
            sub.content = sub.content.replace("§§§", "")

    # Process English subtitles - merge multi-line
    for idx, sub in subs_en.items():
        if "\n" in sub.content:
            sub.content = sub.content.replace("\n", " ")
        # Verify no "§§§" in English content
        if "§§§" in sub.content:
            print(f"Warning: Found §§§ in English subtitle: {sub.content}")
            sub.content = sub.content.replace("§§§", "")

    # Process English subtitles and find closest Chinese match
    processed_zh_subs = set()  # Keep track of used Chinese subtitles
    merged_subs = []

    for sub_en in sorted(subs_en.values(), key=lambda x: x.start):
        # Find the closest Chinese subtitle that hasn't been used
        available_zh = [
            (abs(sub_en.start - zh.start), zh)
            for zh in subs_zh.values()
            if zh.index not in processed_zh_subs
        ]

        if available_zh:
            _, nearest_zh = min(available_zh, key=lambda x: x[0])
            # Ensure clean content before merging
            zh_content = nearest_zh.content.strip()
            en_content = sub_en.content.strip()

            # Verify contents are clean
            assert "§§§" not in zh_content, f"§§§ found in Chinese: {zh_content}"
            assert "§§§" not in en_content, f"§§§ found in English: {en_content}"

            merged_content = f"{zh_content}§§§{en_content}"

            # Create new subtitle with merged content
            merged_sub = srt.Subtitle(
                index=len(merged_subs) + 1,
                start=nearest_zh.start,
                end=nearest_zh.end,
                content=merged_content,
            )
            merged_subs.append(merged_sub)
            processed_zh_subs.add(nearest_zh.index)

    # Debug: Verify merged subtitles
    for sub in merged_subs:
        if sub.content.count("§§§") > 1:
            print(f"Error: Multiple §§§ found in merged subtitle: {sub.content}")
            # Fix the content by keeping only the first occurrence
            parts = sub.content.split("§§§", 1)
            sub.content = f"{parts[0]}§§§{parts[1]}"

    # Write merged subtitles
    output_path = static_folder / video_id / f"{video_id}_bilingual.srt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(merged_subs))

    # Final verification
    print(f"Total merged subtitles: {len(merged_subs)}")
    return output_path


def _convert_vtt_to_srt(vtt_path: Path, video_id: str, static_folder: Path) -> Path:
    """Converts VTT file to SRT format."""
    vtt = webvtt.read(str(vtt_path))
    srt_path = None
    srt_path = static_folder / video_id / Path(vtt_path.stem + '.srt')
    logger.info(f"Converting VTT to SRT: {vtt_path} -> {str(srt_path)}.")
    vtt.save_as_srt()
    return srt_path


def _convert_srt_to_vtt(srt_path: Path, video_id: str, static_folder: Path) -> Path:
    """Converts SRT file to VTT format."""
    with open(srt_path, encoding="utf8") as srt_file:  # default: "r
        lines = srt_file.read().splitlines()
    vtt_path = static_folder / video_id / Path(srt_path.stem + '.vtt')
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
    v_id = "ONs9FCY74p0"
    create_bilingual_vtt(v_id, Path("./static"))
