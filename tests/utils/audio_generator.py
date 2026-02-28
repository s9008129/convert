#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試音檔產生工具。

此模組用來建立可重現的 WAV 測試音訊（例如純音、靜音與白噪音），
讓語音轉錄流程能在固定輸入下進行穩定驗證。

流程說明（給非技術同仁快速理解）：
1) 先依指定類型產生音訊樣本（tone/silence/noise/mixed）。
2) 再把樣本封裝成 WAV 檔，提供測試直接使用。
3) 透過 AudioGenerator 自動清除暫存檔，避免測試殘留。

關鍵分支與錯誤情境：
- content_type 支援 tone、silence、noise、mixed。
- 若傳入未知 content_type，會明確拋出 ValueError。
- 雜訊採固定亂數種子，確保每次測試結果可重現。
"""
import math
import random
import struct
import tempfile
import wave
from pathlib import Path
from typing import Optional, List, Tuple


def generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 16000,
    amplitude: float = 0.5
) -> List[int]:
    """
    Generate sine wave samples.
    
    Args:
        frequency: Frequency in Hz
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Amplitude (0-1)
    
    Returns:
        List of 16-bit integer samples
    """
    num_samples = int(duration * sample_rate)
    samples = []
    
    for i in range(num_samples):
        t = i / sample_rate
        value = amplitude * math.sin(2 * math.pi * frequency * t)
        # 轉成 16-bit 整數，符合常見 WAV 儲存格式。
        sample = int(value * 32767)
        samples.append(sample)
    
    return samples


def generate_silence(duration: float, sample_rate: int = 16000) -> List[int]:
    """
    Generate silence samples.
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        List of 16-bit integer samples (zeros)
    """
    num_samples = int(duration * sample_rate)
    return [0] * num_samples


def generate_white_noise(
    duration: float,
    sample_rate: int = 16000,
    amplitude: float = 0.1
) -> List[int]:
    """
    Generate white noise samples (deterministic for testing).
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        amplitude: Amplitude (0-1)
    
    Returns:
        List of 16-bit integer samples
    """
    # 固定亂數種子，讓測試每次產生相同白噪音內容。
    rng = random.Random(42)
    
    num_samples = int(duration * sample_rate)
    samples = []
    
    for _ in range(num_samples):
        value = (rng.random() * 2 - 1) * amplitude
        sample = int(value * 32767)
        samples.append(sample)
    
    return samples


def generate_tone_sequence(
    frequencies: List[float],
    duration_per_tone: float,
    sample_rate: int = 16000
) -> List[int]:
    """
    Generate a sequence of tones.
    
    Args:
        frequencies: List of frequencies in Hz
        duration_per_tone: Duration of each tone in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        List of 16-bit integer samples
    """
    samples = []
    for freq in frequencies:
        tone = generate_sine_wave(freq, duration_per_tone, sample_rate)
        samples.extend(tone)
    return samples


def create_test_wav_file(
    output_path: Path,
    duration: float = 1.0,
    sample_rate: int = 16000,
    channels: int = 1,
    sample_width: int = 2,
    content_type: str = "tone"
) -> Path:
    """
    Create a test WAV file with synthetic audio.
    
    Args:
        output_path: Path to save the WAV file
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        channels: Number of audio channels (1=mono, 2=stereo)
        sample_width: Sample width in bytes (2 for 16-bit)
        content_type: Type of content ("tone", "silence", "noise", "mixed")
    
    Returns:
        Path to the created WAV file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 依指定內容類型建立樣本資料。
    if content_type == "tone":
        # 產生 440Hz 純音（A4）作為標準訊號。
        samples = generate_sine_wave(440, duration, sample_rate)
    elif content_type == "silence":
        samples = generate_silence(duration, sample_rate)
    elif content_type == "noise":
        samples = generate_white_noise(duration, sample_rate)
    elif content_type == "mixed":
        # Mix of tone, silence, and noise
        tone_duration = duration / 3
        samples = []
        samples.extend(generate_sine_wave(440, tone_duration, sample_rate))
        samples.extend(generate_silence(tone_duration, sample_rate))
        samples.extend(generate_white_noise(tone_duration, sample_rate, amplitude=0.1))
    else:
        raise ValueError(f"Unknown content_type: {content_type}")
    
    # 將音訊樣本寫入 WAV 檔案。
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        # 把整數樣本打包成二進位資料後寫入檔案。
        if channels == 1:
            packed_samples = struct.pack(f'<{len(samples)}h', *samples)
        else:
            # 雙聲道時，把同一批樣本複製到左右聲道。
            stereo_samples = []
            for s in samples:
                stereo_samples.extend([s, s])
            packed_samples = struct.pack(f'<{len(stereo_samples)}h', *stereo_samples)
        
        wav_file.writeframes(packed_samples)
    
    return output_path


def create_temp_wav_file(
    duration: float = 1.0,
    content_type: str = "tone",
    suffix: str = ".wav"
) -> Tuple[Path, tempfile.NamedTemporaryFile]:
    """
    Create a temporary WAV file for testing.
    
    Args:
        duration: Duration in seconds
        content_type: Type of content
        suffix: File suffix
    
    Returns:
        Tuple of (path to temp file, temp file object)
    
    Note:
        The caller is responsible for cleaning up the temporary file.
        Use `path.unlink()` to delete the file when done.
        
        For automatic cleanup, consider using AudioGenerator context manager instead:
        
        >>> with AudioGenerator() as generator:
        ...     wav_file = generator.generate("test.wav")
        ...     # wav_file is automatically cleaned up after the with block
    """
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.close()
    path = Path(tmp.name)
    create_test_wav_file(path, duration=duration, content_type=content_type)
    return path, tmp


class AudioGenerator:
    """
    Context manager for generating test audio files.
    
    Automatically cleans up generated files after use.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the generator.
        
        Args:
            base_dir: Base directory for generated files.
                     If None, uses system temp directory.
        """
        self.base_dir = base_dir
        self.generated_files: List[Path] = []
        self._temp_dir = None
    
    def __enter__(self):
        if self.base_dir is None:
            self._temp_dir = tempfile.mkdtemp(prefix="test_audio_")
            self.base_dir = Path(self._temp_dir)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清理本次產生的測試音檔。
        for file_path in self.generated_files:
            if file_path.exists():
                file_path.unlink()
        
        # 若本類別建立了暫存資料夾，也一併移除。
        if self._temp_dir and Path(self._temp_dir).exists():
            import shutil
            shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def generate(
        self,
        filename: str = "test_audio.wav",
        duration: float = 1.0,
        content_type: str = "tone"
    ) -> Path:
        """
        Generate a test audio file.
        
        Args:
            filename: Name of the file to generate
            duration: Duration in seconds
            content_type: Type of content
        
        Returns:
            Path to the generated file
        """
        output_path = self.base_dir / filename
        create_test_wav_file(output_path, duration=duration, content_type=content_type)
        self.generated_files.append(output_path)
        return output_path
    
    def generate_multiple(
        self,
        count: int = 3,
        duration: float = 1.0,
        prefix: str = "test_audio"
    ) -> List[Path]:
        """
        Generate multiple test audio files.
        
        Args:
            count: Number of files to generate
            duration: Duration of each file in seconds
            prefix: Filename prefix
        
        Returns:
            List of paths to generated files
        """
        files = []
        for i in range(count):
            path = self.generate(f"{prefix}_{i}.wav", duration)
            files.append(path)
        return files
