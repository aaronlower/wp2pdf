from pathlib import Path
from typing import Dict, Set, List, Optional
from bs4 import BeautifulSoup
import logging
import asyncio
from pdf_generator import PDFGenerator
from batch_processor import BatchProcessor
from image_processor import ImageProcessor
from config import Config

async def process_batch(posts: List[Dict], output_dir: Path):
    """Process a batch of posts asynchronously."""
    pdf_generator = PDFGenerator(output_dir)
    
    for post in posts:
        try:
            soup = BeautifulSoup(post['content']['rendered'], 'html.parser')
            image_urls = [img['src'] for img in soup.find_all('img')]
            
            # Download images concurrently
            images = await asyncio.gather(
                *[ImageProcessor.download_and_process_image(url) for url in image_urls]
            )
            
            await asyncio.to_thread(pdf_generator.create_pdf, post, images)
            logging.info(f"Successfully processed post {post['id']}")
            
        except Exception as e:
            logging.error(f"Failed to process post {post['id']}: {str(e)}")

async def main() -> None:
    """Main entry point for the script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )
    
    processor = BatchProcessor(Config)
    await processor.process_posts()

if __name__ == "__main__":
    asyncio.run(main())