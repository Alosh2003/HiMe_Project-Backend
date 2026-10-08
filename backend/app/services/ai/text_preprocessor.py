"""
Text Preprocessor
=================
Cleans and normalizes text before embedding generation.
"""

import re
import string
from typing import List


class TextPreprocessor:
    """Clean and normalize text for embedding generation."""

    def __init__(self):
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+])+')
        self.email_pattern = re.compile(r'\S+@\S+')
        self.number_pattern = re.compile(r'\b\d+\b')
        self.whitespace_pattern = re.compile(r'\s+')
        self.special_chars = re.compile(r'[^\w\s]')

    def clean(self, text: str) -> str:
        """Apply all cleaning steps to text."""
        if not text:
            return ""
        text = text.lower().strip()
        text = self.url_pattern.sub(' ', text)
        text = self.email_pattern.sub(' ', text)
        text = self.special_chars.sub(' ', text)
        text = self.whitespace_pattern.sub(' ', text)
        return text.strip()

    def normalize_skills(self, skills: List[str]) -> List[str]:
        """Normalize skill names for better matching."""
        normalized = []
        for skill in skills:
            skill = skill.lower().strip()
            skill = self.special_chars.sub('', skill)
            if skill:
                normalized.append(skill)
        return list(set(normalized))

    def extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """Extract most frequent meaningful words from text."""
        cleaned = self.clean(text)
        words = cleaned.split()
        stop_words = self._get_stop_words()
        words = [w for w in words if w not in stop_words and len(w) > 2]
        word_freq = {}
        for word in words:
            word_freq[word] = word_freq.get(word, 0) + 1
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, _ in sorted_words[:top_n]]

    def _get_stop_words(self) -> set:
        """Common English and Arabic stop words."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were',
            'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'shall',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it',
            'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'its', 'our', 'their', 'ما', 'في', 'من', 'على', 'إلى',
            'عن', 'أن', 'هذا', 'هذه', 'ذلك', 'التي', 'الذي', 'كان', 'كانت',
        }
