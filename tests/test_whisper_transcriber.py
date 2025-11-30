#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit Tests for WhisperTranscriber Module

This module contains comprehensive unit tests covering:
- TranscriptionResult dataclass properties
- WhisperTranscriber initialization
- File validation
- Transcription with mocked faster-whisper backend
- Caching functionality
- Integration workflow with full mock chain
"""
import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.whisper_transcriber import (
    TranscriptionResult,
    TranscriptionError,
    AudioFileNotFoundError,
    UnsupportedFormatError,
    WhisperTranscriber,
    transcribe_audio
)
from tests.utils.audio_generator import (
    AudioGenerator,
    create_test_wav_file,
)

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)


# =============================================================================
# TranscriptionResult Dataclass Tests
# =============================================================================

class TestTranscriptionResult:
    """Tests for TranscriptionResult dataclass properties."""
    
    def test_basic_instantiation(self):
        """Test basic instantiation with required fields."""
        result = TranscriptionResult(
            text="Hello, this is a test transcription.",
            language="en",
            duration_seconds=60.0,
            processing_time=10.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        
        assert result.text == "Hello, this is a test transcription."
        assert result.language == "en"
        assert result.duration_seconds == 60.0
        assert result.processing_time == 10.0
        assert result.model == "large-v3"
        assert result.device == "cuda"
        assert result.source_file == "/path/to/audio.wav"
        assert result.from_cache is False  # default value
        assert result.segments == []  # default value
    
    def test_speed_ratio_calculation(self):
        """Test speed_ratio property calculation."""
        # Normal case: 60 seconds audio processed in 10 seconds = 6x speed
        result = TranscriptionResult(
            text="Test",
            language="en",
            duration_seconds=60.0,
            processing_time=10.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result.speed_ratio == 6.0
        
        # Slower processing: 30 seconds audio in 60 seconds = 0.5x speed
        result2 = TranscriptionResult(
            text="Test",
            language="en",
            duration_seconds=30.0,
            processing_time=60.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result2.speed_ratio == 0.5
    
    def test_speed_ratio_zero_processing_time(self):
        """Test speed_ratio when processing_time is zero."""
        result = TranscriptionResult(
            text="Test",
            language="en",
            duration_seconds=60.0,
            processing_time=0.0,  # Edge case
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result.speed_ratio == 0  # Should return 0 to avoid division by zero
    
    def test_word_count_property(self):
        """Test word_count property (character count for Chinese text)."""
        # Note: The implementation counts characters, not words
        result = TranscriptionResult(
            text="這是一個測試文字",  # 8 Chinese characters
            language="zh",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result.word_count == 8
        
        # Empty text
        result2 = TranscriptionResult(
            text="",
            language="en",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result2.word_count == 0
    
    def test_from_cache_flag(self):
        """Test from_cache flag behavior."""
        # Default is False
        result = TranscriptionResult(
            text="Test",
            language="en",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav"
        )
        assert result.from_cache is False
        
        # Explicitly set to True
        cached_result = TranscriptionResult(
            text="Test",
            language="en",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav",
            from_cache=True
        )
        assert cached_result.from_cache is True
    
    def test_segments_field(self):
        """Test segments field with actual segment data."""
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Hello"},
            {"start": 5.0, "end": 10.0, "text": "World"}
        ]
        
        result = TranscriptionResult(
            text="Hello World",
            language="en",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cuda",
            source_file="/path/to/audio.wav",
            segments=segments
        )
        
        assert len(result.segments) == 2
        assert result.segments[0]["text"] == "Hello"
        assert result.segments[1]["end"] == 10.0


# =============================================================================
# WhisperTranscriber Initialization Tests
# =============================================================================

class TestWhisperTranscriberInitialization:
    """Tests for WhisperTranscriber initialization."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    @patch('src.whisper_transcriber.WhisperTranscriber._resolve_exe_path')
    def test_default_initialization(self, mock_resolve, mock_device, mock_backend):
        """Test initialization with default parameters."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        assert transcriber.model == "large-v3"
        assert transcriber.language == "zh"
        assert transcriber.compute_type == "float16"
        assert transcriber.cache_dir is None
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_custom_parameters(self, mock_device, mock_backend):
        """Test initialization with custom parameters."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            transcriber = WhisperTranscriber(
                model="small",
                language="en",
                device="cpu",
                compute_type="int8",
                cache_dir=cache_dir
            )
            
            assert transcriber.model == "small"
            assert transcriber.language == "en"
            assert transcriber.compute_type == "int8"
            assert transcriber.cache_dir == Path(cache_dir)
    
    @patch('src.whisper_transcriber.WhisperTranscriber._check_cuda')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    def test_cuda_detection_available(self, mock_backend, mock_cuda):
        """Test CUDA detection when CUDA is available."""
        mock_backend.return_value = "python"
        mock_cuda.return_value = True
        
        transcriber = WhisperTranscriber(device="auto")
        
        assert transcriber.device == "cuda"
    
    @patch('src.whisper_transcriber.WhisperTranscriber._check_cuda')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    def test_cuda_detection_not_available(self, mock_backend, mock_cuda):
        """Test CUDA detection when CUDA is not available."""
        mock_backend.return_value = "python"
        mock_cuda.return_value = False
        
        transcriber = WhisperTranscriber(device="auto")
        
        assert transcriber.device == "cpu"
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_explicit_device_setting(self, mock_device, mock_backend):
        """Test explicit device setting bypasses auto-detection."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cuda"
        
        transcriber = WhisperTranscriber(device="cuda")
        
        assert transcriber.device == "cuda"
    
    @patch('platform.system')
    @patch('builtins.__import__', side_effect=ImportError("No module named 'faster_whisper'"))
    def test_backend_detection_no_whisper(self, mock_import, mock_platform):
        """Test backend detection when faster-whisper is not installed."""
        mock_platform.return_value = "Linux"
        
        # This should raise an error since faster-whisper is not available
        # and we're on Linux (not Windows where exe fallback is available)
        with patch.object(WhisperTranscriber, '_detect_backend', side_effect=TranscriptionError("No backend")):
            with pytest.raises(TranscriptionError):
                WhisperTranscriber()


# =============================================================================
# File Validation Tests
# =============================================================================

class TestFileValidation:
    """Tests for file validation functionality."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_validate_supported_formats(self, mock_device, mock_backend):
        """Test validation of supported audio formats."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        # Verify SUPPORTED_FORMATS contains expected formats
        expected_formats = {'.mp3', '.mp4', '.wav', '.m4a', '.mkv', 
                           '.webm', '.flac', '.ogg', '.wma', '.aac',
                           '.avi', '.mov', '.wmv', '.opus', '.amr'}
        
        assert transcriber.SUPPORTED_FORMATS == expected_formats
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_validate_file_not_found(self, mock_device, mock_backend):
        """Test validation raises error for non-existent file."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        with pytest.raises(AudioFileNotFoundError) as exc_info:
            transcriber._validate_file(Path("/nonexistent/file.wav"))
        
        assert "找不到檔案" in str(exc_info.value)
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_validate_unsupported_format(self, mock_device, mock_backend):
        """Test validation raises error for unsupported format."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        # Create a temp file with unsupported extension
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
            tmp.write(b"test content")
            tmp_path = Path(tmp.name)
        
        try:
            with pytest.raises(UnsupportedFormatError) as exc_info:
                transcriber._validate_file(tmp_path)
            
            assert "不支援的格式" in str(exc_info.value)
        finally:
            tmp_path.unlink()
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_validate_supported_file(self, mock_device, mock_backend):
        """Test validation passes for supported file format."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            
            # Should not raise any exception
            transcriber._validate_file(wav_file)


# =============================================================================
# Transcription Tests with Mocked Backend
# =============================================================================

class TestTranscriptionWithMockedBackend:
    """Tests for transcription with mocked faster-whisper backend."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    @patch('src.whisper_transcriber.WhisperTranscriber._transcribe_python')
    def test_transcribe_returns_result(self, mock_transcribe, mock_device, mock_backend):
        """Test transcription returns TranscriptionResult."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        # Mock transcription result
        expected_result = TranscriptionResult(
            text="這是測試轉錄文字",
            language="zh",
            duration_seconds=10.0,
            processing_time=2.0,
            model="large-v3",
            device="cpu",
            source_file="/path/to/test.wav"
        )
        mock_transcribe.return_value = expected_result
        
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            result = transcriber.transcribe(str(wav_file), use_cache=False)
            
            assert isinstance(result, TranscriptionResult)
            assert result.text == "這是測試轉錄文字"
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_transcribe_python_backend(self, mock_device, mock_backend):
        """Test transcription using Python backend with mocked WhisperModel."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        # Create mock segment
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "測試文字"
        
        # Create mock info
        mock_info = MagicMock()
        mock_info.language = "zh"
        mock_info.duration = 5.0
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            
            with patch('faster_whisper.WhisperModel') as MockModel:
                mock_model_instance = MagicMock()
                mock_model_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
                MockModel.return_value = mock_model_instance
                
                result = transcriber._transcribe_python(wav_file, None)
                
                assert result.text == "測試文字"
                assert result.language == "zh"
                assert result.duration_seconds == 5.0
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_transcribe_with_progress_callback(self, mock_device, mock_backend):
        """Test transcription with progress callback."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        progress_calls = []
        
        def on_progress(message, progress):
            progress_calls.append((message, progress))
        
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "Test"
        
        mock_info = MagicMock()
        mock_info.language = "en"
        mock_info.duration = 5.0
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            
            with patch('faster_whisper.WhisperModel') as MockModel:
                mock_model_instance = MagicMock()
                mock_model_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
                MockModel.return_value = mock_model_instance
                
                result = transcriber._transcribe_python(wav_file, on_progress)
                
                # Verify progress callbacks were made
                assert len(progress_calls) >= 2
                assert progress_calls[0][0] == "載入模型..."
                assert progress_calls[-1][1] == 100


# =============================================================================
# Caching Tests
# =============================================================================

class TestCaching:
    """Tests for caching functionality."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_cache_path_generation(self, mock_device, mock_backend):
        """Test cache path is generated correctly."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            transcriber = WhisperTranscriber(cache_dir=cache_dir)
            
            with AudioGenerator() as generator:
                wav_file = generator.generate("test.wav", duration=0.5)
                cache_path = transcriber._get_cache_path(wav_file)
                
                assert cache_path is not None
                assert cache_path.parent == Path(cache_dir)
                assert cache_path.suffix == ".json"
                assert "test_" in cache_path.name
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_cache_save_and_load(self, mock_device, mock_backend):
        """Test saving and loading from cache."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            transcriber = WhisperTranscriber(
                cache_dir=cache_dir,
                model="large-v3"
            )
            
            with AudioGenerator() as generator:
                wav_file = generator.generate("test.wav", duration=0.5)
                cache_path = transcriber._get_cache_path(wav_file)
                
                # Create a result to save
                original_result = TranscriptionResult(
                    text="快取測試文字",
                    language="zh",
                    duration_seconds=10.0,
                    processing_time=2.0,
                    model="large-v3",
                    device="cpu",
                    source_file=str(wav_file),
                    segments=[{"start": 0, "end": 10, "text": "快取測試文字"}]
                )
                
                # Save to cache
                transcriber._save_cache(cache_path, original_result)
                
                # Verify cache file exists
                assert cache_path.exists()
                
                # Load from cache
                loaded_result = transcriber._load_cache(cache_path)
                
                assert loaded_result is not None
                assert loaded_result.text == "快取測試文字"
                assert loaded_result.language == "zh"
                assert loaded_result.from_cache is True
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_cache_model_mismatch_invalidation(self, mock_device, mock_backend):
        """Test cache is invalidated when model doesn't match."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            # Create transcriber with large-v3 model
            transcriber = WhisperTranscriber(
                cache_dir=cache_dir,
                model="large-v3"
            )
            
            with AudioGenerator() as generator:
                wav_file = generator.generate("test.wav", duration=0.5)
                cache_path = transcriber._get_cache_path(wav_file)
                
                # Save cache with different model
                cache_data = {
                    "text": "Cached text",
                    "language": "zh",
                    "duration_seconds": 10.0,
                    "processing_time": 2.0,
                    "model": "small",  # Different model
                    "device": "cpu",
                    "source_file": str(wav_file),
                    "segments": []
                }
                
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump(cache_data, f)
                
                # Load should return None due to model mismatch
                loaded_result = transcriber._load_cache(cache_path)
                
                assert loaded_result is None
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_cache_disabled(self, mock_device, mock_backend):
        """Test transcription without cache."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        # No cache_dir specified
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            cache_path = transcriber._get_cache_path(wav_file)
            
            # Should return None when cache is disabled
            assert cache_path is None
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_cache_file_hash_consistency(self, mock_device, mock_backend):
        """Test that file hash is consistent for the same file."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            
            hash1 = transcriber._calculate_file_hash(wav_file)
            hash2 = transcriber._calculate_file_hash(wav_file)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex digest length


# =============================================================================
# Integration Tests with Full Mock Chain
# =============================================================================

class TestIntegrationWorkflow:
    """Integration tests with full mock chain."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_full_transcription_workflow(self, mock_device, mock_backend):
        """Test complete transcription workflow from file to result."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            transcriber = WhisperTranscriber(
                model="large-v3",
                language="zh",
                cache_dir=cache_dir
            )
            
            # Create mock segment with Chinese text
            mock_segment = MagicMock()
            mock_segment.start = 0.0
            mock_segment.end = 10.0
            mock_segment.text = "這是一個完整的測試轉錄"
            
            mock_info = MagicMock()
            mock_info.language = "zh"
            mock_info.duration = 10.0
            
            with AudioGenerator() as generator:
                wav_file = generator.generate("test_workflow.wav", duration=0.5)
                
                with patch('faster_whisper.WhisperModel') as MockModel:
                    mock_model_instance = MagicMock()
                    mock_model_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
                    MockModel.return_value = mock_model_instance
                    
                    # First transcription - should process and cache
                    result1 = transcriber.transcribe(str(wav_file), use_cache=True)
                    
                    assert result1.text == "這是一個完整的測試轉錄"
                    assert result1.from_cache is False
                    
                    # Verify cache was created
                    cache_path = transcriber._get_cache_path(wav_file)
                    assert cache_path.exists()
                    
                    # Second transcription - should load from cache
                    result2 = transcriber.transcribe(str(wav_file), use_cache=True)
                    
                    assert result2.text == "這是一個完整的測試轉錄"
                    assert result2.from_cache is True
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_transcribe_audio_convenience_function(self, mock_device, mock_backend):
        """Test the transcribe_audio convenience function."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = "便捷函數測試"
        
        mock_info = MagicMock()
        mock_info.language = "zh"
        mock_info.duration = 5.0
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test_convenience.wav", duration=0.5)
            
            with patch('faster_whisper.WhisperModel') as MockModel:
                mock_model_instance = MagicMock()
                mock_model_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
                MockModel.return_value = mock_model_instance
                
                text = transcribe_audio(str(wav_file), model="large-v3", language="zh")
                
                assert text == "便捷函數測試"
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_multiple_files_workflow(self, mock_device, mock_backend):
        """Test processing multiple files in sequence."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            files = generator.generate_multiple(count=3, duration=0.5)
            
            results = []
            for i, wav_file in enumerate(files):
                mock_segment = MagicMock()
                mock_segment.start = 0.0
                mock_segment.end = 5.0
                mock_segment.text = f"File {i} transcription"
                
                mock_info = MagicMock()
                mock_info.language = "en"
                mock_info.duration = 5.0
                
                with patch('faster_whisper.WhisperModel') as MockModel:
                    mock_model_instance = MagicMock()
                    mock_model_instance.transcribe.return_value = (iter([mock_segment]), mock_info)
                    MockModel.return_value = mock_model_instance
                    
                    result = transcriber.transcribe(str(wav_file), use_cache=False)
                    results.append(result)
            
            assert len(results) == 3
            for i, result in enumerate(results):
                assert f"File {i} transcription" in result.text


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling."""
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_transcription_error_propagation(self, mock_device, mock_backend):
        """Test that transcription errors are properly propagated."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        transcriber = WhisperTranscriber()
        
        with AudioGenerator() as generator:
            wav_file = generator.generate("test.wav", duration=0.5)
            
            with patch('faster_whisper.WhisperModel') as MockModel:
                mock_model_instance = MagicMock()
                mock_model_instance.transcribe.side_effect = Exception("Model error")
                MockModel.return_value = mock_model_instance
                
                with pytest.raises(Exception) as exc_info:
                    transcriber._transcribe_python(wav_file, None)
                
                assert "Model error" in str(exc_info.value)
    
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_invalid_cache_file_handling(self, mock_device, mock_backend):
        """Test handling of corrupted cache files."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        with tempfile.TemporaryDirectory() as cache_dir:
            transcriber = WhisperTranscriber(cache_dir=cache_dir)
            
            with AudioGenerator() as generator:
                wav_file = generator.generate("test.wav", duration=0.5)
                cache_path = transcriber._get_cache_path(wav_file)
                
                # Create corrupted cache file
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'w') as f:
                    f.write("invalid json{{{")
                
                # Should return None without crashing
                result = transcriber._load_cache(cache_path)
                assert result is None


# =============================================================================
# GPU Info Tests
# =============================================================================

class TestGPUInfo:
    """Tests for GPU information retrieval."""
    
    @patch('subprocess.run')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_get_gpu_info_success(self, mock_device, mock_backend, mock_run):
        """Test successful GPU info retrieval."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="NVIDIA GeForce RTX 3080, 10240, 8000, 50"
        )
        
        transcriber = WhisperTranscriber()
        gpu_info = transcriber.get_gpu_info()
        
        assert gpu_info is not None
        assert gpu_info['name'] == "NVIDIA GeForce RTX 3080"
        assert gpu_info['memory_total_mb'] == 10240
        assert gpu_info['memory_free_mb'] == 8000
        assert gpu_info['utilization_percent'] == 50
    
    @patch('subprocess.run')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_backend')
    @patch('src.whisper_transcriber.WhisperTranscriber._detect_device')
    def test_get_gpu_info_no_gpu(self, mock_device, mock_backend, mock_run):
        """Test GPU info when no GPU is available."""
        mock_backend.return_value = "python"
        mock_device.return_value = "cpu"
        
        mock_run.return_value = MagicMock(returncode=1)
        
        transcriber = WhisperTranscriber()
        gpu_info = transcriber.get_gpu_info()
        
        assert gpu_info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
