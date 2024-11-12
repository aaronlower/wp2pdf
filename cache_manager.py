from pathlib import Path
import requests
import logging
from PIL import Image
from io import BytesIO
import json
import hashlib
from typing import Optional

class CacheManager:
    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.emoji_mapping_file = self.cache_dir / "emoji_mapping.json"
        self.emoji_mapping = self._load_emoji_mapping()
        
        # Base URL for emoji images (using Twemoji as an example)
        self.emoji_base_url = "https://cdn.jsdelivr.net/gh/twitter/twemoji@latest/assets/72x72"

    def _load_emoji_mapping(self) -> dict:
        """Load emoji mapping from cache file."""
        if self.emoji_mapping_file.exists():
            try:
                with open(self.emoji_mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Error loading emoji mapping: {str(e)}")
        return {}

    def _save_emoji_mapping(self) -> None:
        """Save emoji mapping to cache file."""
        try:
            with open(self.emoji_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.emoji_mapping, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving emoji mapping: {str(e)}")

    def _get_emoji_filename(self, emoji_char: str) -> str:
        """Generate a filename for an emoji character."""
        # Create a unique filename based on the emoji character
        emoji_hash = hashlib.md5(emoji_char.encode('utf-8')).hexdigest()
        return f"emoji_{emoji_hash}.png"

    def _download_emoji_image(self, emoji_char: str) -> Optional[bytes]:
        """Download emoji image from Twemoji."""
        try:
            # Convert emoji to code points
            code_points = '-'.join(f"{ord(char):x}" for char in emoji_char)
            url = f"{self.emoji_base_url}/{code_points}.png"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logging.error(f"Error downloading emoji image: {str(e)}")
            return None

    def get_emoji_image(self, emoji_char: str) -> Optional[Path]:
        """Get emoji image from cache or download if necessary."""
        try:
            # Check if emoji is in mapping
            if emoji_char not in self.emoji_mapping:
                filename = self._get_emoji_filename(emoji_char)
                cache_path = self.cache_dir / filename
                
                if not cache_path.exists():
                    # Download and save emoji image
                    image_data = self._download_emoji_image(emoji_char)
                    if image_data:
                        # Process image before saving
                        img = Image.open(BytesIO(image_data))
                        img = img.convert('RGBA')
                        
                        # Save processed image
                        img.save(cache_path, 'PNG')
                        
                        # Update mapping
                        self.emoji_mapping[emoji_char] = str(filename)
                        self._save_emoji_mapping()
                    else:
                        return None
                
                self.emoji_mapping[emoji_char] = str(filename)
                self._save_emoji_mapping()
            
            # Return path to cached image
            return self.cache_dir / self.emoji_mapping[emoji_char]
            
        except Exception as e:
            logging.error(f"Error processing emoji image: {str(e)}")
            return None