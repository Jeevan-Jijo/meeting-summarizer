import os
import pytest
from app.services.transcriber import Transcriber, detect_device_and_compute_type

def test_transcriber_initialization():
    transcriber = Transcriber()
    assert hasattr(transcriber, "device")
    assert hasattr(transcriber, "compute_type")
    assert hasattr(transcriber, "model_name")
    assert transcriber.model_name == "nvidia/parakeet-tdt-0.6b-v2"

def test_transcriber_non_existent_file():
    transcriber = Transcriber()
    with pytest.raises(FileNotFoundError):
        transcriber.transcribe("non_existent_file.wav")
