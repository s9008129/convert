# -*- coding: utf-8 -*-
"""
Unit Tests for Whisper Transcription Functionality

This module contains comprehensive tests for the WhisperTranscriber class,
simulating audio recording and testing transcription capabilities.

Test Strategy:
1. Generate synthetic audio files with known content
2. Test transcription with mocked faster-whisper backend
3. Verify transcription result correctness
4. Test error handling and edge cases
5. Test caching functionality
"""

import json
import math
import os
import struct
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.whisper_transcriber import (
    AudioFileNotFoundError,
    TranscriptionError,
    TranscriptionResult,
    UnsupportedFormatError,
    WhisperTranscriber,
)


# ============================================================
# Constants for Test Data
# ============================================================

# File size constants
MOCK_MP3_FILE_SIZE = 1000
MOCK_FILE_SIZE = 100

# SHA256 hex digest length
SHA256_HEX_LENGTH = 64

# Test transcription text samples
TEST_SEGMENT_TEXT_1 = "這是測試語音"
TEST_SEGMENT_TEXT_2 = "用於驗證轉錄功能"
TEST_SEGMENT_TEXT_3 = "確保系統正常運作"


# ============================================================
# Test Fixtures and Utilities
# ============================================================


def generate_wav_file(
    filepath: str,
    duration_seconds: float = 1.0,
    sample_rate: int = 16000,
    frequency: float = 440.0,
) -> str:
    """
    Generate a synthetic WAV file with a sine wave tone.
    
    This simulates an audio recording for testing purposes.
    
    Args:
        filepath: Path to save the WAV file
        duration_seconds: Duration of the audio in seconds
        sample_rate: Sample rate in Hz
        frequency: Frequency of the sine wave in Hz
        
    Returns:
        Path to the generated file
    """
    num_samples = int(duration_seconds * sample_rate)
    
    with wave.open(filepath, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            t = i / sample_rate
            value = int(32767 * 0.5 * math.sin(2 * math.pi * frequency * t))
            data = struct.pack("<h", value)
            wav_file.writeframes(data)
    
    return filepath


@dataclass
class MockSegment:
    """Mock segment for faster-whisper output"""
    start: float
    end: float
    text: str


@dataclass
class MockTranscriptionInfo:
    """Mock transcription info for faster-whisper output"""
    language: str
    duration: float


class MockWhisperModel:
    """Mock WhisperModel for testing without actual model"""
    
    def __init__(self, model_name: str, device: str = "cpu", compute_type: str = "int8"):
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
    
    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        beam_size: int = 5,
        vad_filter: bool = True,
    ):
        """Mock transcription that returns predefined segments"""
        # Simulated transcription result
        segments = [
            MockSegment(0.0, 2.0, TEST_SEGMENT_TEXT_1),
            MockSegment(2.0, 4.0, TEST_SEGMENT_TEXT_2),
            MockSegment(4.0, 6.0, TEST_SEGMENT_TEXT_3),
        ]
        info = MockTranscriptionInfo(language=language or "zh", duration=6.0)
        
        return iter(segments), info


# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_audio_file(temp_dir):
    """Create a sample WAV audio file"""
    filepath = os.path.join(temp_dir, "test_audio.wav")
    generate_wav_file(filepath, duration_seconds=2.0)
    return filepath


@pytest.fixture
def sample_mp3_file(temp_dir):
    """Create a mock MP3 file (just an empty file with .mp3 extension)"""
    filepath = os.path.join(temp_dir, "test_audio.mp3")
    # Create a minimal file - in real testing this would be actual MP3 data
    with open(filepath, "wb") as f:
        f.write(b"\x00" * MOCK_MP3_FILE_SIZE)
    return filepath


@pytest.fixture
def mock_whisper_model():
    """Create a mock WhisperModel"""
    return MockWhisperModel("large-v3", "cpu", "int8")


# ============================================================
# Unit Tests: TranscriptionResult
# ============================================================


class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass"""
    
    def test_speed_ratio_calculation(self):
        """Test speed ratio calculation"""
        result = TranscriptionResult(
            text="Test text",
            language="zh",
            duration_seconds=60.0,
            processing_time=30.0,
            model="large-v3",
            device="cuda",
            source_file="/test/file.wav"
        )
        
        assert result.speed_ratio == 2.0
    
    def test_speed_ratio_zero_processing_time(self):
        """Test speed ratio when processing time is zero"""
        result = TranscriptionResult(
            text="Test text",
            language="zh",
            duration_seconds=60.0,
            processing_time=0,
            model="large-v3",
            device="cuda",
            source_file="/test/file.wav"
        )
        
        assert result.speed_ratio == 0
    
    def test_word_count_chinese(self):
        """Test word count for Chinese text"""
        result = TranscriptionResult(
            text="這是測試文字共有十個字",
            language="zh",
            duration_seconds=5.0,
            processing_time=2.0,
            model="large-v3",
            device="cpu",
            source_file="/test/file.wav"
        )
        
        assert result.word_count == 11  # Character count for Chinese
    
    def test_from_cache_flag(self):
        """Test from_cache flag"""
        result = TranscriptionResult(
            text="Cached text",
            language="zh",
            duration_seconds=10.0,
            processing_time=0,
            model="large-v3",
            device="cached",
            source_file="/test/file.wav",
            from_cache=True
        )
        
        assert result.from_cache is True


# ============================================================
# Unit Tests: WhisperTranscriber Initialization
# ============================================================


class TestWhisperTranscriberInit:
    """Tests for WhisperTranscriber initialization"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_init_with_defaults(self, mock_detect_backend, mock_check_cuda):
        """Test initialization with default parameters"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber()
        
        assert transcriber.model == "large-v3"
        assert transcriber.language == "zh"
        assert transcriber.compute_type == "float16"
        assert transcriber.device == "cpu"
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_init_with_custom_model(self, mock_detect_backend, mock_check_cuda):
        """Test initialization with custom model"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber(model="small", language="en")
        
        assert transcriber.model == "small"
        assert transcriber.language == "en"
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_init_with_cache_dir(self, mock_detect_backend, mock_check_cuda, temp_dir):
        """Test initialization with cache directory"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber(cache_dir=temp_dir)
        
        assert transcriber.cache_dir == Path(temp_dir)
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_init_cuda_device_detection(self, mock_detect_backend, mock_check_cuda):
        """Test CUDA device detection when available"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = True
        
        transcriber = WhisperTranscriber(device="auto")
        
        assert transcriber.device == "cuda"


# ============================================================
# Unit Tests: File Validation
# ============================================================


class TestFileValidation:
    """Tests for file validation functionality"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_validate_nonexistent_file(self, mock_detect_backend, mock_check_cuda):
        """Test validation of nonexistent file"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber()
        
        with pytest.raises(AudioFileNotFoundError):
            transcriber._validate_file(Path("/nonexistent/file.wav"))
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_validate_unsupported_format(
        self, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test validation of unsupported file format"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Create a file with unsupported extension
        unsupported_file = os.path.join(temp_dir, "test.xyz")
        with open(unsupported_file, "w") as f:
            f.write("test content")
        
        transcriber = WhisperTranscriber()
        
        with pytest.raises(UnsupportedFormatError):
            transcriber._validate_file(Path(unsupported_file))
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_validate_supported_formats(
        self, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test validation of all supported formats"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber()
        
        supported_extensions = [".wav", ".mp3", ".mp4", ".m4a", ".flac", ".ogg"]
        
        for ext in supported_extensions:
            filepath = os.path.join(temp_dir, f"test{ext}")
            with open(filepath, "wb") as f:
                f.write(b"\x00" * MOCK_FILE_SIZE)
            
            # Should not raise an exception
            transcriber._validate_file(Path(filepath))


# ============================================================
# Unit Tests: Transcription with Mock
# ============================================================


class TestTranscriptionWithMock:
    """Tests for transcription functionality using mocked backend"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    @patch("faster_whisper.WhisperModel")
    def test_transcribe_audio_file(
        self, MockWhisperModelClass, mock_detect_backend, mock_check_cuda, sample_audio_file
    ):
        """Test transcription of audio file with mocked model"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Setup mock model
        mock_model_instance = MagicMock()
        mock_segments = [
            MockSegment(0.0, 2.0, "這是第一段測試"),
            MockSegment(2.0, 4.0, "這是第二段測試"),
        ]
        mock_info = MockTranscriptionInfo(language="zh", duration=4.0)
        mock_model_instance.transcribe.return_value = (iter(mock_segments), mock_info)
        MockWhisperModelClass.return_value = mock_model_instance
        
        transcriber = WhisperTranscriber()
        result = transcriber.transcribe(sample_audio_file, use_cache=False)
        
        assert "這是第一段測試" in result.text
        assert "這是第二段測試" in result.text
        assert result.language == "zh"
        assert result.duration_seconds == 4.0
        assert result.from_cache is False
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    @patch("faster_whisper.WhisperModel")
    def test_transcribe_with_progress_callback(
        self, MockWhisperModelClass, mock_detect_backend, mock_check_cuda, sample_audio_file
    ):
        """Test transcription with progress callback"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Setup mock model
        mock_model_instance = MagicMock()
        mock_segments = [MockSegment(0.0, 2.0, "測試進度")]
        mock_info = MockTranscriptionInfo(language="zh", duration=2.0)
        mock_model_instance.transcribe.return_value = (iter(mock_segments), mock_info)
        MockWhisperModelClass.return_value = mock_model_instance
        
        progress_calls = []
        
        def progress_callback(message: str, progress: float):
            progress_calls.append((message, progress))
        
        transcriber = WhisperTranscriber()
        result = transcriber.transcribe(
            sample_audio_file,
            use_cache=False,
            on_progress=progress_callback
        )
        
        assert len(progress_calls) > 0
        assert result.text == "測試進度"
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    @patch("faster_whisper.WhisperModel")
    def test_transcribe_empty_result(
        self, MockWhisperModelClass, mock_detect_backend, mock_check_cuda, sample_audio_file
    ):
        """Test transcription with empty result"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Setup mock model returning empty segments
        mock_model_instance = MagicMock()
        mock_info = MockTranscriptionInfo(language="zh", duration=0)
        mock_model_instance.transcribe.return_value = (iter([]), mock_info)
        MockWhisperModelClass.return_value = mock_model_instance
        
        transcriber = WhisperTranscriber()
        result = transcriber.transcribe(sample_audio_file, use_cache=False)
        
        assert result.text == ""
        assert result.duration_seconds == 0


# ============================================================
# Unit Tests: Caching Functionality
# ============================================================


class TestCachingFunctionality:
    """Tests for caching functionality"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_cache_path_generation(
        self, mock_detect_backend, mock_check_cuda, sample_audio_file, temp_dir
    ):
        """Test cache path generation"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber(cache_dir=temp_dir)
        cache_path = transcriber._get_cache_path(Path(sample_audio_file))
        
        assert cache_path is not None
        assert cache_path.parent == Path(temp_dir)
        assert cache_path.suffix == ".json"
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_cache_path_none_without_cache_dir(
        self, mock_detect_backend, mock_check_cuda, sample_audio_file
    ):
        """Test cache path is None when cache_dir not set"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber(cache_dir=None)
        cache_path = transcriber._get_cache_path(Path(sample_audio_file))
        
        assert cache_path is None
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_file_hash_calculation(
        self, mock_detect_backend, mock_check_cuda, sample_audio_file
    ):
        """Test file hash calculation is consistent"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber()
        
        hash1 = transcriber._calculate_file_hash(Path(sample_audio_file))
        hash2 = transcriber._calculate_file_hash(Path(sample_audio_file))
        
        assert hash1 == hash2
        assert len(hash1) == SHA256_HEX_LENGTH
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_save_and_load_cache(
        self, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test saving and loading cache"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber(cache_dir=temp_dir, model="large-v3")
        
        cache_path = Path(temp_dir) / "test_cache.json"
        
        result = TranscriptionResult(
            text="快取測試文字",
            language="zh",
            duration_seconds=10.0,
            processing_time=5.0,
            model="large-v3",
            device="cpu",
            source_file="/test/file.wav",
            segments=[{"start": 0, "end": 10, "text": "快取測試文字"}]
        )
        
        # Save cache
        transcriber._save_cache(cache_path, result)
        
        assert cache_path.exists()
        
        # Load cache
        loaded = transcriber._load_cache(cache_path)
        
        assert loaded is not None
        assert loaded.text == "快取測試文字"
        assert loaded.from_cache is True
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_cache_model_mismatch(
        self, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test cache invalidation on model mismatch"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Save cache with one model
        transcriber1 = WhisperTranscriber(cache_dir=temp_dir, model="large-v3")
        cache_path = Path(temp_dir) / "test_cache.json"
        
        result = TranscriptionResult(
            text="Test",
            language="zh",
            duration_seconds=5.0,
            processing_time=2.0,
            model="large-v3",
            device="cpu",
            source_file="/test/file.wav"
        )
        transcriber1._save_cache(cache_path, result)
        
        # Try to load with different model
        transcriber2 = WhisperTranscriber(cache_dir=temp_dir, model="small")
        loaded = transcriber2._load_cache(cache_path)
        
        assert loaded is None  # Cache should be invalidated


# ============================================================
# Unit Tests: Error Handling
# ============================================================


class TestErrorHandling:
    """Tests for error handling"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_transcribe_nonexistent_file(
        self, mock_detect_backend, mock_check_cuda
    ):
        """Test transcription of nonexistent file raises error"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        transcriber = WhisperTranscriber()
        
        with pytest.raises(AudioFileNotFoundError):
            transcriber.transcribe("/nonexistent/path/audio.wav")
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    def test_transcribe_unsupported_format(
        self, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test transcription of unsupported format raises error"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        unsupported_file = os.path.join(temp_dir, "test.txt")
        with open(unsupported_file, "w") as f:
            f.write("Not an audio file")
        
        transcriber = WhisperTranscriber()
        
        with pytest.raises(UnsupportedFormatError):
            transcriber.transcribe(unsupported_file)


# ============================================================
# Integration-like Tests (with full mock chain)
# ============================================================


class TestTranscriptionIntegration:
    """Integration-like tests for full transcription workflow"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    @patch("faster_whisper.WhisperModel")
    def test_full_transcription_workflow(
        self, MockWhisperModelClass, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test complete transcription workflow with caching"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Create test audio file
        audio_path = os.path.join(temp_dir, "workflow_test.wav")
        generate_wav_file(audio_path, duration_seconds=3.0)
        
        # Setup mock model
        mock_model_instance = MagicMock()
        expected_text = "會議摘要測試 討論項目一 決議通過"
        mock_segments = [
            MockSegment(0.0, 3.0, expected_text),
        ]
        mock_info = MockTranscriptionInfo(language="zh", duration=3.0)
        mock_model_instance.transcribe.return_value = (iter(mock_segments), mock_info)
        MockWhisperModelClass.return_value = mock_model_instance
        
        # Initialize transcriber with cache
        cache_dir = os.path.join(temp_dir, "cache")
        transcriber = WhisperTranscriber(cache_dir=cache_dir, model="large-v3")
        
        # First transcription (should hit model)
        result1 = transcriber.transcribe(audio_path, use_cache=True)
        
        assert result1.text == expected_text
        assert result1.from_cache is False
        assert result1.model == "large-v3"
        
        # Second transcription (should hit cache)
        result2 = transcriber.transcribe(audio_path, use_cache=True)
        
        assert result2.text == expected_text
        assert result2.from_cache is True
    
    @patch("src.whisper_transcriber.WhisperTranscriber._check_cuda")
    @patch("src.whisper_transcriber.WhisperTranscriber._detect_backend")
    @patch("faster_whisper.WhisperModel")
    def test_multiple_segment_transcription(
        self, MockWhisperModelClass, mock_detect_backend, mock_check_cuda, temp_dir
    ):
        """Test transcription with multiple segments (simulating long audio)"""
        mock_detect_backend.return_value = "python"
        mock_check_cuda.return_value = False
        
        # Create test audio file
        audio_path = os.path.join(temp_dir, "multi_segment.wav")
        generate_wav_file(audio_path, duration_seconds=5.0)
        
        # Setup mock model with multiple segments
        mock_model_instance = MagicMock()
        mock_segments = [
            MockSegment(0.0, 30.0, "主席宣布會議開始"),
            MockSegment(30.0, 60.0, "首先討論預算案"),
            MockSegment(60.0, 90.0, "全體無異議通過"),
            MockSegment(90.0, 120.0, "第二議題關於人事案"),
            MockSegment(120.0, 150.0, "經討論後決議延期審議"),
        ]
        mock_info = MockTranscriptionInfo(language="zh", duration=150.0)
        mock_model_instance.transcribe.return_value = (iter(mock_segments), mock_info)
        MockWhisperModelClass.return_value = mock_model_instance
        
        transcriber = WhisperTranscriber()
        result = transcriber.transcribe(audio_path, use_cache=False)
        
        # Verify all segments are included
        assert "主席宣布會議開始" in result.text
        assert "首先討論預算案" in result.text
        assert "全體無異議通過" in result.text
        assert "經討論後決議延期審議" in result.text
        
        # Verify metadata
        assert result.duration_seconds == 150.0
        assert len(result.segments) == 5


# ============================================================
# Convenience Function Tests
# ============================================================


class TestConvenienceFunction:
    """Tests for the transcribe_audio convenience function"""
    
    @patch("src.whisper_transcriber.WhisperTranscriber")
    def test_transcribe_audio_function(self, MockTranscriberClass, temp_dir):
        """Test the transcribe_audio convenience function"""
        from src.whisper_transcriber import transcribe_audio
        
        # Create test audio file
        audio_path = os.path.join(temp_dir, "convenience_test.wav")
        generate_wav_file(audio_path)
        
        # Setup mock
        mock_instance = MagicMock()
        mock_result = TranscriptionResult(
            text="便捷函數測試",
            language="zh",
            duration_seconds=1.0,
            processing_time=0.5,
            model="large-v3",
            device="cpu",
            source_file=audio_path
        )
        mock_instance.transcribe.return_value = mock_result
        MockTranscriberClass.return_value = mock_instance
        
        result = transcribe_audio(audio_path, model="large-v3", language="zh")
        
        assert result == "便捷函數測試"


# ============================================================
# Run Tests
# ============================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
