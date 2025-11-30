#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Audio Generation Utility for Testing

This module provides utilities to generate synthetic WAV audio files
for deterministic testing of the Whisper transcription system.
"""
import struct
import wave
from pathlib import Path
from typing import Optional, List, Tuple
import math
import tempfile


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
        # Convert to 16-bit integer
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
    import random
    # Use fixed seed for deterministic testing
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
    
    # Generate samples based on content type
    if content_type == "tone":
        # Generate 440Hz sine wave (A4 note)
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
    
    # Write WAV file
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        # Pack samples as bytes
        if channels == 1:
            packed_samples = struct.pack(f'<{len(samples)}h', *samples)
        else:
            # For stereo, duplicate samples to both channels
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
        Note: The caller is responsible for closing the temp file
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
        # Clean up all generated files
        for file_path in self.generated_files:
            if file_path.exists():
                file_path.unlink()
        
        # Clean up temp directory if we created one
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
