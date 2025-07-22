"""
Text processing utilities for ERPFTS Phase1 MVP

Provides text cleaning, chunking, language detection, and content hashing
utilities for document processing and embedding generation.
"""

import re
import hashlib
from typing import List, Tuple, Optional
from langdetect import detect, DetectorFactory
import tiktoken

from ..core.config import settings
from ..core.exceptions import ValidationError

# Set seed for consistent language detection
DetectorFactory.seed = 0

# Initialize tokenizer for token counting
try:
    encoding = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/GPT-4 encoding
except Exception:
    encoding = None


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    
    # Remove or replace special characters
    text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\"\'\n]', '', text)
    
    # Normalize quotes
    text = re.sub(r'["""]', '"', text)
    text = re.sub(r'['']', "'", text)
    
    # Remove empty lines
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    text = '\n'.join(lines)
    
    return text


def chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
    preserve_sentences: bool = True
) -> List[Tuple[str, int]]:
    """
    Split text into chunks for embedding generation.
    
    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        chunk_overlap: Overlap between consecutive chunks
        preserve_sentences: Whether to avoid breaking sentences
        
    Returns:
        List of (chunk_text, start_position) tuples
    """
    if not text:
        return []
    
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    if len(text) <= chunk_size:
        return [(text, 0)]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk
            chunk = text[start:]
            chunks.append((chunk, start))
            break
        
        if preserve_sentences:
            # Find the last sentence boundary within the chunk
            chunk_text = text[start:end]
            sentence_endings = ['.', '!', '?', '\n']
            
            best_split = -1
            for i in range(len(chunk_text) - 1, max(len(chunk_text) - 200, 0), -1):
                if chunk_text[i] in sentence_endings:
                    # Avoid splitting on abbreviations (simple heuristic)
                    if chunk_text[i] == '.' and i > 0 and chunk_text[i-1].isupper():
                        continue
                    best_split = i + 1
                    break
            
            if best_split > 0:
                end = start + best_split
        
        chunk = text[start:end]
        chunks.append((chunk, start))
        
        # Move start position with overlap
        start = end - chunk_overlap
        if start < 0:
            start = 0
    
    return chunks


def detect_language(text: str) -> Optional[str]:
    """
    Detect the language of text content.
    
    Args:
        text: Text to analyze
        
    Returns:
        ISO 639-1 language code (e.g., 'en', 'ja') or None if detection fails
    """
    if not text or len(text.strip()) < 10:
        return None
    
    try:
        # Use only first 1000 characters for faster detection
        sample = text[:1000].strip()
        language = detect(sample)
        return language
    except Exception:
        return None


def calculate_content_hash(content: str) -> str:
    """
    Calculate SHA-256 hash of content for deduplication.
    
    Args:
        content: Text content to hash
        
    Returns:
        Hexadecimal hash string
    """
    if not content:
        return ""
    
    # Normalize content before hashing
    normalized = clean_text(content).lower()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count tokens in text using tiktoken.
    
    Args:
        text: Text to count tokens for
        model: Model to use for token counting
        
    Returns:
        Number of tokens
    """
    if not text:
        return 0
    
    if encoding is None:
        # Fallback to rough estimation
        return len(text.split())
    
    try:
        tokens = encoding.encode(text)
        return len(tokens)
    except Exception:
        # Fallback to word count
        return len(text.split())


def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """
    Extract important keywords from text (simple implementation).
    
    Args:
        text: Text to extract keywords from
        max_keywords: Maximum number of keywords to return
        
    Returns:
        List of keyword strings
    """
    if not text:
        return []
    
    # Simple keyword extraction based on word frequency
    # In production, consider using more sophisticated methods like TF-IDF
    
    # Clean and tokenize
    cleaned = clean_text(text).lower()
    words = re.findall(r'\b[a-z]{3,}\b', cleaned)
    
    # Common stop words to filter out
    stop_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
        'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before',
        'after', 'above', 'below', 'between', 'among', 'throughout', 'during',
        'this', 'that', 'these', 'those', 'can', 'could', 'should', 'would',
        'will', 'shall', 'may', 'might', 'must', 'ought', 'need', 'have',
        'has', 'had', 'been', 'being', 'am', 'is', 'are', 'was', 'were'
    }
    
    # Filter and count
    word_freq = {}
    for word in words:
        if word not in stop_words and len(word) >= 3:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, _ in sorted_words[:max_keywords]]


def validate_text_content(content: str) -> bool:
    """
    Validate that text content is suitable for processing.
    
    Args:
        content: Text content to validate
        
    Returns:
        True if content is valid
        
    Raises:
        ValidationError: If content is invalid
    """
    if not content:
        raise ValidationError(
            message="Content cannot be empty",
            error_code="EMPTY_CONTENT"
        )
    
    if len(content.strip()) < 10:
        raise ValidationError(
            message="Content too short for meaningful processing",
            error_code="CONTENT_TOO_SHORT"
        )
    
    # Check for minimum readable content (not just special characters)
    readable_chars = re.findall(r'[a-zA-Z0-9]', content)
    if len(readable_chars) < 5:
        raise ValidationError(
            message="Content lacks sufficient readable characters",
            error_code="INSUFFICIENT_READABLE_CONTENT"
        )
    
    return True