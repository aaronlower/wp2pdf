from typing import Dict, Optional, List, Set
from bs4 import BeautifulSoup
import logging

from dataclasses import dataclass

class TextFormatter:
    @staticmethod
    def clean_for_path(text: str) -> str:
        """Format text for use in paths/filenames."""
        if not text:
            return "untitled"
        
        try:
            # Remove HTML tags if present
            if '<' in text and '>' in text:
                text = BeautifulSoup(text, 'html.parser').get_text()
            
            # Basic cleaning
            text = text.lower().strip()
            text = text.replace(' ', '_')
            # Allow only alphanumeric and underscore
            text = ''.join(char for char in text if char.isalnum() or char == '_')
            # Limit length and remove trailing underscores
            text = text[:50].rstrip('_')
            return text or "untitled"
        except Exception as e:
            logging.error(f"Error cleaning path text: {e}")
            return "untitled"

    @staticmethod
    def clean_for_display(text: str) -> str:
        """Format text for display in PDFs."""
        if not text:
            return ""
        
        try:
            # Remove HTML tags if present
            if '<' in text and '>' in text:
                text = BeautifulSoup(text, 'html.parser').get_text()
            
            # Normalize whitespace
            text = ' '.join(text.split())
            return text.strip()
        except Exception as e:
            logging.error(f"Error cleaning display text: {e}")
            return ""

    @staticmethod
    def clean_tags(tags: List[str]) -> str:
        """Format tag list for display."""
        try:
            # Clean each tag and filter out empty ones
            cleaned_tags = [
                TextFormatter.clean_for_display(tag) 
                for tag in tags 
                if tag and TextFormatter.clean_for_display(tag)
            ]
            return ', '.join(cleaned_tags)
        except Exception as e:
            logging.error(f"Error cleaning tags: {e}")
            return ""