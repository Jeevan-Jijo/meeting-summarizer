import os
import pytest
from unittest.mock import MagicMock, patch

from app.services.deepgram_service import DeepgramService, transcribe_with_deepgram
from app.core.config import settings


def test_deepgram_unconfigured_key():
    """Verify that unconfigured or placeholder API key raises ValueError before making API calls."""
    service = DeepgramService(api_key="")
    assert service.is_configured() is False

    with pytest.raises(ValueError, match="DEEPGRAM_API_KEY is missing or unconfigured"):
        service.get_client()

    service_placeholder = DeepgramService(api_key="your_deepgram_api_key_here")
    assert service_placeholder.is_configured() is False
    with pytest.raises(ValueError):
        service_placeholder.get_client()


def test_deepgram_non_existent_file():
    """Verify that transcribing a non-existent file raises FileNotFoundError."""
    service = DeepgramService(api_key="valid_mock_key")
    with pytest.raises(FileNotFoundError, match="Audio recording file not found"):
        service.transcribe_file("non_existent_file_path_12345.wav")


def test_parse_deepgram_diarized_utterances():
    """Test parsing Deepgram diarized utterances response into MIS segments."""
    service = DeepgramService(api_key="valid_mock_key")

    mock_response = MagicMock()
    mock_results = MagicMock()
    mock_response.results = mock_results

    # Mock channels with detected language
    mock_channel = MagicMock()
    mock_channel.detected_language = "en"
    mock_results.channels = [mock_channel]

    # Mock utterances
    utt1 = MagicMock()
    utt1.transcript = "Good morning everyone. Welcome to the architecture sync."
    utt1.start = 0.5
    utt1.end = 5.2
    utt1.speaker = 0
    utt1.confidence = 0.98

    utt2 = MagicMock()
    utt2.transcript = "Thanks Marcus. I have reviewed the performance metrics."
    utt2.start = 5.5
    utt2.end = 9.8
    utt2.speaker = 1
    utt2.confidence = 0.94

    mock_results.utterances = [utt1, utt2]

    segments, language = service.parse_deepgram_response(mock_response, "test.wav")

    assert language == "en"
    assert len(segments) == 2

    assert segments[0]["start"] == 0.5
    assert segments[0]["end"] == 5.2
    assert segments[0]["text"] == "Good morning everyone. Welcome to the architecture sync."
    assert segments[0]["speaker_tag"] == "SPEAKER_00"
    assert segments[0]["speaker_label"] == "Speaker 1"
    assert segments[0]["confidence"] == 0.98

    assert segments[1]["start"] == 5.5
    assert segments[1]["end"] == 9.8
    assert segments[1]["text"] == "Thanks Marcus. I have reviewed the performance metrics."
    assert segments[1]["speaker_tag"] == "SPEAKER_01"
    assert segments[1]["speaker_label"] == "Speaker 2"
    assert segments[1]["confidence"] == 0.94


def test_parse_deepgram_dict_payload():
    """Test parsing raw dict response payload (e.g. JSON returned by Deepgram REST API)."""
    service = DeepgramService(api_key="valid_mock_key")

    dict_response = {
        "results": {
            "channels": [{"detected_language": "en"}],
            "utterances": [
                {
                    "transcript": "Let's review the API endpoint design.",
                    "start": 1.2,
                    "end": 4.5,
                    "speaker": 2,
                    "confidence": 0.96
                }
            ]
        }
    }

    segments, language = service.parse_deepgram_response(dict_response, "test.wav")

    assert language == "en"
    assert len(segments) == 1
    assert segments[0]["speaker_tag"] == "SPEAKER_02"
    assert segments[0]["speaker_label"] == "Speaker 3"
    assert segments[0]["text"] == "Let's review the API endpoint design."


def test_parse_deepgram_empty_response_fallback():
    """Test fallback when Deepgram returns empty utterances or empty results."""
    service = DeepgramService(api_key="valid_mock_key")

    mock_response = MagicMock()
    mock_response.results = None

    segments, language = service.parse_deepgram_response(mock_response, "silent.wav")

    assert language == "en"
    assert len(segments) == 1
    assert segments[0]["text"] == "[No audible speech detected in recording]"
    assert segments[0]["speaker_tag"] == "SPEAKER_00"
    assert segments[0]["speaker_label"] == "Unknown Speaker"


def test_deepgram_api_error_handling(tmp_path):
    """Test handling of 401 authentication error when calling transcribe_file."""
    dummy_file = tmp_path / "dummy.wav"
    dummy_file.write_bytes(b"RIFF dummy wav header data")

    service = DeepgramService(api_key="invalid_test_key")

    with patch("app.services.deepgram_service.DeepgramClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance
        mock_instance.listen.v1.media.transcribe_file.side_effect = Exception("401 Unauthorized: Invalid API key")

        with pytest.raises(ValueError, match="Deepgram API authentication failed"):
            service.transcribe_file(str(dummy_file))
