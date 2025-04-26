import os
from unittest.mock import MagicMock, patch

import pytest

from app.core.utils.video_subtitles_downloader import (
    download_video_and_subtitles,
    get_ytb_id,
    video_offered_with_zh_en_subtitles,
)


@pytest.fixture
def mock_static_folder(tmp_path):
    """Create a temporary directory for test files"""
    video_dir = tmp_path / "static"
    video_dir.mkdir()
    return str(video_dir) + "/"


@pytest.fixture
def sample_video_data():
    return {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "ytb_id": "dQw4w9WgXcQ"
    }


class TestVideoDownloader:
    @patch('app.core.video_subtitles_downloader.YoutubeDL')
    @patch('app.core.video_subtitles_downloader.YouTubeTranscriptApi')
    def test_download_video_and_subtitles_success(
            self,
            mock_transcript_api,
            mock_youtubedl,
            mock_static_folder,
            sample_video_data
    ):
        # Mock video availability check
        with patch('app.core.video_subtitles_downloader.video_offered_with_zh_en_subtitles') as mock_check:
            mock_check.return_value = True

            # Mock transcript list
            mock_transcript = MagicMock()
            mock_transcript.language_code = "zh-CN"
            mock_transcript.language = "Chinese"
            mock_transcript.is_generated = False
            mock_transcript.fetch.return_value = [{
                "text": "测试字幕",
                "start": 0.0,
                "duration": 2.0
            }]

            mock_transcript_en = MagicMock()
            mock_transcript_en.language_code = "en"
            mock_transcript_en.language = "English"
            mock_transcript_en.is_generated = False
            mock_transcript_en.fetch.return_value = [{
                "text": "Test subtitle",
                "start": 0.0,
                "duration": 2.0
            }]

            mock_transcript_list = MagicMock()
            mock_transcript_list.__iter__.return_value = [mock_transcript, mock_transcript_en]
            mock_transcript_api.list_transcripts.return_value = mock_transcript_list

            # Test the function
            download_video_and_subtitles(
                sample_video_data["ytb_id"],
                sample_video_data["url"],
                mock_static_folder
            )

            # Verify YoutubeDL was called
            mock_youtubedl.assert_called_once()

            # Check if files were created
            video_dir = os.path.join(mock_static_folder, sample_video_data["ytb_id"])
            assert os.path.exists(video_dir)

            # Verify transcript API was called
            mock_transcript_api.list_transcripts.assert_called_once_with(sample_video_data["ytb_id"])

    def test_get_ytb_id(self, sample_video_data):
        ytb_id = get_ytb_id(sample_video_data["url"])
        assert ytb_id == sample_video_data["ytb_id"]

    @patch('app.core.video_subtitles_downloader.YoutubeDL')
    def test_video_without_required_subtitles(
            self,
            mock_youtubedl,
            sample_video_data
    ):
        # Mock YoutubeDL to return info without required subtitles
        mock_instance = MagicMock()
        mock_instance.extract_info.return_value = {
            "subtitles": {
                "fr": [{"name": "French"}],
                "es": [{"name": "Spanish"}]
            }
        }
        mock_youtubedl.return_value.__enter__.return_value = mock_instance

        result = video_offered_with_zh_en_subtitles(sample_video_data["ytb_id"])
        assert result is False
