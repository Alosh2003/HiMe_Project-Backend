"""
AI Services Module
==================
Handles embedding generation, text preprocessing, and matching logic
for the HiMe AI Matching & Analytics epic (Sprint 4).
"""

from .embedding_service import EmbeddingService
from .matching_service import MatchingService
from .text_preprocessor import TextPreprocessor

__all__ = ["EmbeddingService", "MatchingService", "TextPreprocessor"]
