from typing import Optional, Tuple
from PIL import Image, ImageOps, UnidentifiedImageError
from io import BytesIO
import logging
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed
import re

class ImageProcessor:
    @staticmethod
    def _get_full_size_url(thumbnail_url: str) -> str:
        """Convert thumbnail URL to full-size image URL."""
        # Remove size suffix like -150x150 from the URL
        return re.sub(r'-\d+x\d+(\.[^.]+)$', r'\1', thumbnail_url)

    @staticmethod
    async def _download_image(url: str, session: aiohttp.ClientSession) -> bytes:
        """Download image with proper headers."""
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Cache-Control': 'no-cache',
        }
        
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"Failed to download image: HTTP {response.status}")
            return await response.read()

    @staticmethod
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def download_and_process_image(url: str) -> Optional[Image.Image]:
        """Download and process image with improved error handling."""
        try:
            # Try to get full-size image URL
            full_url = ImageProcessor._get_full_size_url(url)
            logging.info(f"Attempting to download image from: {full_url}")
            
            async with aiohttp.ClientSession() as session:
                try:
                    # Try full-size image first
                    image_data = await ImageProcessor._download_image(full_url, session)
                except Exception as e:
                    logging.warning(f"Failed to download full-size image, trying original URL: {str(e)}")
                    # Fall back to original URL if full-size fails
                    image_data = await ImageProcessor._download_image(url, session)

                img = Image.open(BytesIO(image_data))
                img = ImageOps.exif_transpose(img)
                
                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                
                return img

        except UnidentifiedImageError:
            logging.error(f"Unidentified image error for {url}")
        except Exception as e:
            logging.error(f"Image processing error for {url}: {str(e)}")
        
        return None