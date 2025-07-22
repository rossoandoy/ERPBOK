"""
File handling utilities for ERPFTS Phase1 MVP

Provides file validation, type detection, upload handling,
and storage management utilities.
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Tuple, Union
import uuid
import shutil

from ..core.config import settings
from ..core.exceptions import ValidationError, FileStorageError


def get_file_type(filename: str) -> Tuple[str, str]:
    """
    Get file extension and MIME type from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        Tuple of (file_extension, mime_type)
    """
    file_path = Path(filename)
    extension = file_path.suffix.lower()
    
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    return extension, mime_type


def validate_file(filename: str, content: bytes) -> bool:
    """
    Validate uploaded file against security and size constraints.
    
    Args:
        filename: Original filename
        content: File content as bytes
        
    Returns:
        True if file is valid
        
    Raises:
        ValidationError: If file fails validation
    """
    if not filename:
        raise ValidationError(
            message="Filename cannot be empty",
            error_code="EMPTY_FILENAME"
        )
    
    # Check file extension
    extension, _ = get_file_type(filename)
    if extension not in settings.supported_file_types:
        raise ValidationError(
            message=f"Unsupported file type: {extension}",
            error_code="UNSUPPORTED_FILE_TYPE",
            details={
                "extension": extension,
                "supported_types": settings.supported_file_types
            }
        )
    
    # Check file size
    file_size_mb = len(content) / (1024 * 1024)
    if file_size_mb > settings.max_file_size_mb:
        raise ValidationError(
            message=f"File too large: {file_size_mb:.1f}MB (max: {settings.max_file_size_mb}MB)",
            error_code="FILE_TOO_LARGE",
            details={
                "size_mb": file_size_mb,
                "max_size_mb": settings.max_file_size_mb
            }
        )
    
    # Check for empty files
    if len(content) == 0:
        raise ValidationError(
            message="File is empty",
            error_code="EMPTY_FILE"
        )
    
    # Basic content validation for text files
    if extension in ['.txt', '.html']:
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            raise ValidationError(
                message="Text file contains invalid UTF-8 content",
                error_code="INVALID_TEXT_ENCODING"
            )
    
    return True


def save_uploaded_file(
    content: bytes, 
    filename: str,
    subdirectory: str = "uploads"
) -> Tuple[str, str]:
    """
    Save uploaded file to storage with unique name.
    
    Args:
        content: File content as bytes
        filename: Original filename
        subdirectory: Subdirectory within storage root
        
    Returns:
        Tuple of (unique_filename, full_file_path)
        
    Raises:
        FileStorageError: If file cannot be saved
    """
    # Validate file first
    validate_file(filename, content)
    
    # Generate unique filename
    file_id = str(uuid.uuid4())
    extension = Path(filename).suffix.lower()
    unique_filename = f"{file_id}_{filename}"
    
    # Determine storage directory
    storage_dir = settings.storage_path / subdirectory
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    # Full file path
    file_path = storage_dir / unique_filename
    
    try:
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return unique_filename, str(file_path)
    
    except Exception as e:
        raise FileStorageError(
            message=f"Failed to save file: {str(e)}",
            error_code="FILE_SAVE_ERROR",
            details={
                "filename": filename,
                "path": str(file_path),
                "error": str(e)
            }
        )


def get_file_size(file_path: Union[str, Path]) -> int:
    """
    Get file size in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
        
    Raises:
        FileStorageError: If file doesn't exist or cannot be accessed
    """
    try:
        return os.path.getsize(file_path)
    except OSError as e:
        raise FileStorageError(
            message=f"Cannot access file: {str(e)}",
            error_code="FILE_ACCESS_ERROR",
            details={"path": str(file_path)}
        )


def delete_file(file_path: Union[str, Path]) -> bool:
    """
    Delete a file from storage.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        True if file was deleted successfully
        
    Raises:
        FileStorageError: If file cannot be deleted
    """
    try:
        file_path = Path(file_path)
        if file_path.exists():
            file_path.unlink()
            return True
        else:
            return False  # File didn't exist
    except Exception as e:
        raise FileStorageError(
            message=f"Failed to delete file: {str(e)}",
            error_code="FILE_DELETE_ERROR",
            details={"path": str(file_path)}
        )


def move_file(source_path: Union[str, Path], dest_path: Union[str, Path]) -> bool:
    """
    Move a file from source to destination.
    
    Args:
        source_path: Source file path
        dest_path: Destination file path
        
    Returns:
        True if file was moved successfully
        
    Raises:
        FileStorageError: If file cannot be moved
    """
    try:
        source_path = Path(source_path)
        dest_path = Path(dest_path)
        
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(source_path), str(dest_path))
        return True
    
    except Exception as e:
        raise FileStorageError(
            message=f"Failed to move file: {str(e)}",
            error_code="FILE_MOVE_ERROR",
            details={
                "source": str(source_path),
                "destination": str(dest_path)
            }
        )


def ensure_storage_directories():
    """Ensure all required storage directories exist."""
    directories = [
        settings.storage_path,
        settings.upload_path,
        settings.cache_path,
        settings.storage_path / "processed",
        settings.storage_path / "temp",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def clean_filename(filename: str) -> str:
    """
    Clean filename to be safe for file system storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename safe for storage
    """
    if not filename:
        return "unnamed_file"
    
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove excessive dots and spaces
    filename = filename.strip('. ')
    
    # Ensure filename is not too long
    if len(filename) > 200:
        name_part = Path(filename).stem[:150]
        suffix_part = Path(filename).suffix
        filename = name_part + suffix_part
    
    # Ensure filename is not empty after cleaning
    if not filename or filename.startswith('.'):
        filename = f"file_{uuid.uuid4().hex[:8]}" + (Path(filename).suffix or ".txt")
    
    return filename


def get_storage_stats() -> dict:
    """
    Get storage usage statistics.
    
    Returns:
        Dictionary with storage statistics
    """
    stats = {
        "total_files": 0,
        "total_size_bytes": 0,
        "directories": {},
    }
    
    if not settings.storage_path.exists():
        return stats
    
    for root, dirs, files in os.walk(settings.storage_path):
        root_path = Path(root)
        relative_path = root_path.relative_to(settings.storage_path)
        
        dir_stats = {
            "files": len(files),
            "size_bytes": 0,
        }
        
        for file in files:
            file_path = root_path / file
            try:
                file_size = file_path.stat().st_size
                dir_stats["size_bytes"] += file_size
                stats["total_size_bytes"] += file_size
            except OSError:
                continue
        
        stats["directories"][str(relative_path)] = dir_stats
        stats["total_files"] += dir_stats["files"]
    
    # Convert to MB for readability
    stats["total_size_mb"] = stats["total_size_bytes"] / (1024 * 1024)
    
    return stats