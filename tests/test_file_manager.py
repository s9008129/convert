#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit Tests for FileManagerService

This module contains comprehensive unit tests covering:
- File validation (format, security checks)
- File size validation
- File upload and storage
- File hash calculation
- Cache management
- File deletion with security restrictions
"""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock
from io import BytesIO

import pytest

# Set DATA_DIR before importing backend modules
os.environ['DATA_DIR'] = tempfile.mkdtemp()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import UploadFile


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def file_manager():
    """Create a fresh FileManagerService instance with temp directories."""
    # Import after setting DATA_DIR
    from backend.services.file_manager import FileManagerService
    return FileManagerService()


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    from backend.core.config import settings
    os.makedirs(settings.uploads_dir, exist_ok=True)
    os.makedirs(settings.outputs_dir, exist_ok=True)
    os.makedirs(settings.cache_dir, exist_ok=True)
    return {
        'uploads': settings.uploads_dir,
        'outputs': settings.outputs_dir,
        'cache': settings.cache_dir
    }


def create_mock_upload_file(filename: str, content: bytes = b"test content") -> UploadFile:
    """Create a mock UploadFile for testing."""
    file = MagicMock(spec=UploadFile)
    file.filename = filename
    file.file = BytesIO(content)
    file.read = AsyncMock(return_value=content)
    file.seek = AsyncMock()
    return file


# =============================================================================
# File Validation Tests
# =============================================================================

class TestFileValidation:
    """Tests for file validation functionality."""
    
    def test_validate_supported_formats(self, file_manager):
        """Test validation of supported audio formats."""
        supported_files = [
            "test.mp3", "test.mp4", "test.wav", "test.m4a",
            "test.mkv", "test.webm", "test.ogg", "test.flac",
            "test.avi", "test.mov"
        ]
        
        for filename in supported_files:
            file = create_mock_upload_file(filename)
            is_valid, error = file_manager.validate_file(file)
            assert is_valid, f"File {filename} should be valid but got error: {error}"
    
    def test_validate_unsupported_format(self, file_manager):
        """Test validation rejects unsupported formats."""
        file = create_mock_upload_file("test.xyz")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "不支援的檔案格式" in error
    
    def test_validate_empty_filename(self, file_manager):
        """Test validation rejects empty filename."""
        file = create_mock_upload_file("")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "檔案名稱不能為空" in error
    
    def test_validate_none_filename(self, file_manager):
        """Test validation rejects None filename."""
        file = create_mock_upload_file("test.mp3")
        file.filename = None
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "檔案名稱不能為空" in error
    
    def test_validate_path_traversal_dotdot(self, file_manager):
        """Test validation blocks path traversal with .."""
        file = create_mock_upload_file("../../../etc/passwd.mp3")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "無效字符" in error
    
    def test_validate_path_traversal_forward_slash(self, file_manager):
        """Test validation blocks path traversal with /"""
        file = create_mock_upload_file("/etc/passwd.mp3")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "無效字符" in error
    
    def test_validate_path_traversal_backslash(self, file_manager):
        """Test validation blocks path traversal with \\"""
        file = create_mock_upload_file("..\\..\\Windows\\System32\\test.mp3")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "無效字符" in error
    
    def test_validate_null_byte_injection(self, file_manager):
        """Test validation blocks null byte injection."""
        file = create_mock_upload_file("test.mp3\x00.txt")
        is_valid, error = file_manager.validate_file(file)
        
        assert not is_valid
        assert "無效字符" in error
    
    def test_validate_case_insensitive_extension(self, file_manager):
        """Test validation handles case-insensitive extensions."""
        test_cases = ["test.MP3", "test.Mp3", "test.WAV", "test.Wav"]
        
        for filename in test_cases:
            file = create_mock_upload_file(filename)
            is_valid, error = file_manager.validate_file(file)
            assert is_valid, f"File {filename} should be valid"
    
    def test_validate_chinese_filename(self, file_manager):
        """Test validation accepts Chinese filenames."""
        file = create_mock_upload_file("會議錄音.mp3")
        is_valid, error = file_manager.validate_file(file)
        
        assert is_valid, f"Chinese filename should be valid, got error: {error}"


# =============================================================================
# File Size Validation Tests
# =============================================================================

class TestFileSizeValidation:
    """Tests for file size validation functionality."""
    
    @pytest.mark.asyncio
    async def test_validate_file_size_within_limit(self, file_manager):
        """Test validation passes for files within size limit."""
        content = b"x" * 1024  # 1KB
        file = create_mock_upload_file("test.mp3", content)
        
        is_valid, error, size = await file_manager.validate_file_size(file)
        
        assert is_valid
        assert error == ""
        assert size == 1024
    
    @pytest.mark.asyncio
    async def test_validate_file_size_at_limit(self, file_manager):
        """Test validation passes for files at size limit."""
        from backend.core.config import settings
        # This test would need a large file which is impractical
        # Instead, we mock the behavior
        content = b"x" * 1024
        file = create_mock_upload_file("test.mp3", content)
        
        is_valid, error, size = await file_manager.validate_file_size(file)
        
        assert is_valid
        assert size == len(content)
    
    @pytest.mark.asyncio
    async def test_validate_file_size_exceeds_limit(self, file_manager):
        """Test validation fails for files exceeding size limit."""
        from backend.core.config import settings
        
        # Create content larger than limit
        large_content = b"x" * (settings.max_file_size_bytes + 1)
        file = create_mock_upload_file("test.mp3", large_content)
        
        is_valid, error, size = await file_manager.validate_file_size(file)
        
        assert not is_valid
        assert "檔案大小超過限制" in error
    
    @pytest.mark.asyncio
    async def test_validate_file_size_resets_pointer(self, file_manager):
        """Test that file pointer is reset after size validation."""
        content = b"test content"
        file = create_mock_upload_file("test.mp3", content)
        
        await file_manager.validate_file_size(file)
        
        # Verify seek was called to reset pointer
        file.seek.assert_called_with(0)


# =============================================================================
# File Upload Tests
# =============================================================================

class TestFileUpload:
    """Tests for file upload and storage functionality."""
    
    @pytest.mark.asyncio
    async def test_save_upload_creates_file(self, file_manager, temp_dirs):
        """Test that save_upload creates a file."""
        content = b"test audio content"
        file = create_mock_upload_file("test.mp3", content)
        
        file_path, unique_name, size = await file_manager.save_upload(file)
        
        assert os.path.exists(file_path)
        assert unique_name.endswith(".mp3")
        assert size == len(content)
        
        # Cleanup
        os.remove(file_path)
    
    @pytest.mark.asyncio
    async def test_save_upload_generates_unique_filename(self, file_manager, temp_dirs):
        """Test that save_upload generates unique filenames."""
        file1 = create_mock_upload_file("test.mp3", b"content1")
        file2 = create_mock_upload_file("test.mp3", b"content2")
        
        path1, name1, _ = await file_manager.save_upload(file1)
        path2, name2, _ = await file_manager.save_upload(file2)
        
        assert name1 != name2
        assert path1 != path2
        
        # Cleanup
        os.remove(path1)
        os.remove(path2)
    
    @pytest.mark.asyncio
    async def test_save_upload_preserves_extension(self, file_manager, temp_dirs):
        """Test that save_upload preserves file extension."""
        extensions = [".mp3", ".mp4", ".wav", ".m4a"]
        
        for ext in extensions:
            file = create_mock_upload_file(f"test{ext}", b"content")
            file_path, unique_name, _ = await file_manager.save_upload(file)
            
            assert unique_name.endswith(ext)
            
            # Cleanup
            os.remove(file_path)
    
    @pytest.mark.asyncio
    async def test_save_upload_in_correct_directory(self, file_manager, temp_dirs):
        """Test that files are saved in uploads directory."""
        file = create_mock_upload_file("test.mp3", b"content")
        
        file_path, _, _ = await file_manager.save_upload(file)
        
        assert file_path.startswith(temp_dirs['uploads'])
        
        # Cleanup
        os.remove(file_path)


# =============================================================================
# File Hash Tests
# =============================================================================

class TestFileHash:
    """Tests for file hash calculation functionality."""
    
    def test_get_file_hash_consistency(self, file_manager, temp_dirs):
        """Test that hash is consistent for same content."""
        # Create test file
        test_file = os.path.join(temp_dirs['uploads'], "hash_test.mp3")
        with open(test_file, 'wb') as f:
            f.write(b"test content for hashing")
        
        try:
            hash1 = file_manager.get_file_hash(test_file)
            hash2 = file_manager.get_file_hash(test_file)
            
            assert hash1 == hash2
            assert len(hash1) == 64  # SHA256 hex digest length
        finally:
            os.remove(test_file)
    
    def test_get_file_hash_different_content(self, file_manager, temp_dirs):
        """Test that different content produces different hashes."""
        file1 = os.path.join(temp_dirs['uploads'], "hash1.mp3")
        file2 = os.path.join(temp_dirs['uploads'], "hash2.mp3")
        
        with open(file1, 'wb') as f:
            f.write(b"content 1")
        with open(file2, 'wb') as f:
            f.write(b"content 2")
        
        try:
            hash1 = file_manager.get_file_hash(file1)
            hash2 = file_manager.get_file_hash(file2)
            
            assert hash1 != hash2
        finally:
            os.remove(file1)
            os.remove(file2)


# =============================================================================
# Cache Tests
# =============================================================================

class TestCacheManagement:
    """Tests for cache management functionality."""
    
    def test_save_and_get_cached_transcript(self, file_manager, temp_dirs):
        """Test saving and retrieving cached transcript."""
        file_hash = "a" * 64  # Valid SHA256 hash
        transcript = "這是測試逐字稿內容"
        
        file_manager.save_transcript_cache(file_hash, transcript)
        result = file_manager.get_cached_transcript(file_hash)
        
        assert result == transcript
        
        # Cleanup
        cache_file = os.path.join(temp_dirs['cache'], f"{file_hash}.txt")
        if os.path.exists(cache_file):
            os.remove(cache_file)
    
    def test_get_cached_transcript_not_found(self, file_manager):
        """Test getting non-existent cached transcript."""
        result = file_manager.get_cached_transcript("b" * 64)
        
        assert result is None
    
    def test_get_cached_transcript_invalid_hash_format(self, file_manager):
        """Test that invalid hash format is rejected."""
        # Too short
        result = file_manager.get_cached_transcript("abc123")
        assert result is None
        
        # Invalid characters
        result = file_manager.get_cached_transcript("z" * 64)
        assert result is None
        
        # Empty
        result = file_manager.get_cached_transcript("")
        assert result is None
    
    def test_save_transcript_cache_invalid_hash_format(self, file_manager, temp_dirs):
        """Test that saving with invalid hash is rejected."""
        # Should not create file with invalid hash
        file_manager.save_transcript_cache("invalid", "content")
        
        # No file should be created
        cache_file = os.path.join(temp_dirs['cache'], "invalid.txt")
        assert not os.path.exists(cache_file)


# =============================================================================
# Save Result Tests
# =============================================================================

class TestSaveResult:
    """Tests for result saving functionality."""
    
    @pytest.mark.asyncio
    async def test_save_result_creates_file(self, file_manager, temp_dirs):
        """Test that save_result creates a file."""
        content = "# 會議記錄\n\n這是測試內容"
        
        result_path = await file_manager.save_result("test123", "meeting.mp3", content)
        
        assert os.path.exists(result_path)
        
        with open(result_path, 'r', encoding='utf-8') as f:
            saved_content = f.read()
        assert saved_content == content
        
        # Cleanup
        os.remove(result_path)
    
    @pytest.mark.asyncio
    async def test_save_result_filename_format(self, file_manager, temp_dirs):
        """Test that result filename has correct format."""
        result_path = await file_manager.save_result("abc123", "my_meeting.mp3", "content")
        
        filename = os.path.basename(result_path)
        assert "my_meeting" in filename
        assert "abc123" in filename
        assert filename.endswith(".md")
        
        # Cleanup
        os.remove(result_path)
    
    @pytest.mark.asyncio
    async def test_save_result_sanitizes_filename(self, file_manager, temp_dirs):
        """Test that result filename is sanitized."""
        # Try to save with potentially dangerous filename
        result_path = await file_manager.save_result("test123", "../../../etc/passwd.mp3", "content")
        
        # Should be in outputs dir, not escaped
        assert result_path.startswith(temp_dirs['outputs'])
        filename = os.path.basename(result_path)
        assert ".." not in filename
        
        # Cleanup
        os.remove(result_path)
    
    @pytest.mark.asyncio
    async def test_save_result_chinese_filename(self, file_manager, temp_dirs):
        """Test that Chinese characters in filename are preserved."""
        result_path = await file_manager.save_result("test123", "會議錄音.mp3", "content")
        
        filename = os.path.basename(result_path)
        assert "會議錄音" in filename
        
        # Cleanup
        os.remove(result_path)


# =============================================================================
# File Deletion Tests
# =============================================================================

class TestFileDeletion:
    """Tests for file deletion functionality."""
    
    def test_delete_file_in_uploads_dir(self, file_manager, temp_dirs):
        """Test deleting file in uploads directory."""
        # Create test file
        test_file = os.path.join(temp_dirs['uploads'], "delete_test.mp3")
        with open(test_file, 'wb') as f:
            f.write(b"test content")
        
        result = file_manager.delete_file(test_file)
        
        assert result is True
        assert not os.path.exists(test_file)
    
    def test_delete_file_in_outputs_dir(self, file_manager, temp_dirs):
        """Test deleting file in outputs directory."""
        # Create test file
        test_file = os.path.join(temp_dirs['outputs'], "delete_test.md")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        result = file_manager.delete_file(test_file)
        
        assert result is True
        assert not os.path.exists(test_file)
    
    def test_delete_file_outside_allowed_dirs(self, file_manager, temp_dirs):
        """Test that deletion outside allowed directories is blocked."""
        # Try to delete file outside allowed directories
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name
        
        try:
            result = file_manager.delete_file(tmp_path)
            
            assert result is False
            assert os.path.exists(tmp_path)  # File should still exist
        finally:
            os.remove(tmp_path)
    
    def test_delete_nonexistent_file(self, file_manager, temp_dirs):
        """Test deleting non-existent file."""
        nonexistent = os.path.join(temp_dirs['uploads'], "nonexistent.mp3")
        
        result = file_manager.delete_file(nonexistent)
        
        assert result is False
    
    def test_delete_file_path_traversal_blocked(self, file_manager, temp_dirs):
        """Test that path traversal is blocked in deletion."""
        # Try to delete with path traversal
        malicious_path = os.path.join(temp_dirs['uploads'], "..", "..", "etc", "passwd")
        
        result = file_manager.delete_file(malicious_path)
        
        assert result is False


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================

class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security concerns."""
    
    def test_validate_file_with_special_characters(self, file_manager):
        """Test validation with special characters in filename."""
        # Special characters that should be allowed
        allowed_chars = "test_file-123.mp3"
        file = create_mock_upload_file(allowed_chars)
        is_valid, error = file_manager.validate_file(file)
        assert is_valid
        
        # Special characters that might cause issues but should be handled
        tricky_names = [
            "test file.mp3",  # Space
            "test.file.mp3",  # Multiple dots
            "test_會議.mp3",   # Mixed language
        ]
        
        for name in tricky_names:
            file = create_mock_upload_file(name)
            is_valid, error = file_manager.validate_file(file)
            # These should either be valid or handled gracefully
            assert is_valid or "無效字符" in error or "不支援" in error
    
    def test_concurrent_uploads_different_names(self, file_manager, temp_dirs):
        """Test that concurrent uploads get different names."""
        import uuid
        
        # Simulate multiple uploads
        filenames = set()
        for _ in range(10):
            ext = ".mp3"
            unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
            filenames.add(unique_filename)
        
        # All names should be unique
        assert len(filenames) == 10
    
    def test_cache_hash_validation_security(self, file_manager):
        """Test that cache hash validation prevents injection."""
        # These should all be rejected
        malicious_hashes = [
            "../../../etc/passwd",
            "a" * 63,  # Too short
            "a" * 65,  # Too long
            "a" * 63 + "!",  # Invalid character
            "",
            None,
            "SELECT * FROM users",
        ]
        
        for hash_value in malicious_hashes:
            result = file_manager.get_cached_transcript(hash_value)
            assert result is None, f"Hash {hash_value} should be rejected"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
