from typing import Dict, Optional, List, Set
from fpdf import FPDF, XPos, YPos  # Ensure you are importing from fpdf2
from bs4 import BeautifulSoup
import logging
from datetime import datetime
import json
import aiofiles
import asyncio
from pathlib import Path
from pdf_generator import PDFGenerator
from processing_result import ProcessingResult
from config import Config
from image_processor import ImageProcessor
from blog_api import BlogAPI
from my_secrets import Secrets
from dataclasses import dataclass
from text_formatter import TextFormatter

class BatchProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.formatter = TextFormatter()
        self.base_dir = Path(config.OUTPUT_DIR)
        self.errors_dir = self.base_dir / "errors"
        self.processed_file = self.base_dir / "processed_posts.json"
        self.results_file = self.base_dir / "processing_results.json"
        self.setup_directories()
        
        # Define font attributes
        self.font_name = 'NotoSans'
        self.font_path = Path("/Users/aaron.lower/Desktop/code/wp2PDF/fonts")
        self.register_fonts()

    def setup_directories(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

    def get_post_directory(self, post: Dict) -> Path:
        """Create and return directory for post."""
        post_id = post.get('id', 'unknown')
        title = post.get('title', {}).get('rendered', 'untitled')
        dir_name = f"{post_id}_{self.formatter.clean_for_path(title)}"
        dir_path = self.base_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    def register_fonts(self):
        """Register Noto Sans fonts with FPDF."""
        try:
            self.pdf = FPDF()
            self.pdf.add_font(self.font_name, '', str(self.font_path / 'NotoSans-Regular.ttf'), uni=True)
            self.pdf.add_font(self.font_name, 'B', str(self.font_path / 'NotoSans-Bold.ttf'), uni=True)
            self.pdf.add_font(self.font_name, 'I', str(self.font_path / 'NotoSans-Italic.ttf'), uni=True)
            self.pdf.add_font(self.font_name, 'BI', str(self.font_path / 'NotoSans-BoldItalic.ttf'), uni=True)
            logging.info("Successfully registered fonts")
        except Exception as e:
            logging.error(f"Failed to register fonts: {e}")
            raise

    async def create_error_pdf(self, post: Dict, error_msg: str) -> Optional[Path]:
        try:
            pdf = self._create_base_pdf()
            
            title = self.formatter.clean_for_display(
                post.get('title', {}).get('rendered', 'Unknown Title')
            )
            
            # Format error PDF content
            pdf.set_font(self.font_name, 'B', 16)
            pdf.cell(0, 10, text="Error Processing Post", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align='C')
            pdf.ln(10)
            
            pdf.set_font(self.font_name, '', 12)
            pdf.cell(0, 10, text=f"Post ID: {post.get('id', 'Unknown')}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.cell(0, 10, text=f"Title: {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            
            date = post.get('date', 'Unknown date')
            if date and date != 'Unknown date':
                try:
                    parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                    date = parsed_date.strftime('%B %d, %Y')
                except Exception as e:
                    logging.error(f"Error formatting date: {e}")
            
            pdf.cell(0, 10, text=f"Original Date: {date}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(10)
            
            pdf.set_font(self.font_name, 'B', 12)
            pdf.cell(0, 10, text="Error Details:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font(self.font_name, '', 12)
            pdf.multi_cell(0, 10, text=error_msg)
            
            # Save with formatted filename
            post_id = post.get('id', 'unknown')
            filename = f"error_{post_id}_{self.formatter.clean_for_path(title)}.pdf"
            error_file = self.errors_dir / filename
            pdf.output(str(error_file))
            return error_file
            
        except Exception as e:
            logging.error(f"Error creating error PDF: {e}")
            
    def _create_base_pdf(self) -> FPDF:
        """Create a basic PDF with registered fonts and basic settings."""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        # Register fonts for this instance
        pdf.add_font(self.font_name, '', str(self.font_path / 'NotoSans-Regular.ttf'), uni=True)
        pdf.add_font(self.font_name, 'B', str(self.font_path / 'NotoSans-Bold.ttf'), uni=True)
        pdf.add_font(self.font_name, 'I', str(self.font_path / 'NotoSans-Italic.ttf'), uni=True)
        pdf.add_font(self.font_name, 'BI', str(self.font_path / 'NotoSans-BoldItalic.ttf'), uni=True)
        pdf.add_page()
        return pdf
        
    def setup_directories(self) -> None:
        """Create necessary directory structure for output files."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

    async def process_posts(self) -> None:
        """Main processing function with throttling and error handling."""
        api = BlogAPI(Secrets.site_url, Secrets.username, Secrets.password)
        processed_posts = await self.load_processed_posts()
        page = 1
        per_page = self.config.BATCH_SIZE
        total_processed = 0
        retry_delay = self.config.RETRY_DELAY

        while True:
            try:
                logging.info(f"Fetching page {page}")
                posts = await api.get_posts(page=page, per_page=per_page)
                
                if not posts:
                    logging.info("No more posts to process")
                    break

                for post in posts:
                    post_id = post.get('id')
                    
                    if post_id in processed_posts:
                        logging.debug(f"Skipping already processed post {post_id}")
                        continue

                    try:
                        # Create output directory using the post object instead of post_date
                        output_dir = self.get_post_directory(post)
                        
                        logging.info(f"Processing post {post_id}")
                        pdf_generator = PDFGenerator(output_dir)
                        
                        soup = BeautifulSoup(post['content']['rendered'], 'html.parser')
                        image_urls = [img['src'] for img in soup.find_all('img')]
                        images = await asyncio.gather(
                            *[ImageProcessor.download_and_process_image(url) for url in image_urls]
                        )
                        
                        pdf_path = await asyncio.to_thread(pdf_generator.create_pdf, post, images)
                        
                        result = ProcessingResult(
                            post_id=post_id,
                            title=post['title']['rendered'],
                            date=post['date'],
                            success=True,
                            pdf_path=str(pdf_path)
                        )
                        
                        await self.save_processed_post(post_id)
                        
                    except Exception as e:
                        error_msg = str(e)
                        logging.error(f"Error processing post {post_id}: {error_msg}")
                        
                        error_pdf = await self.create_error_pdf(post, error_msg)
                        
                        result = ProcessingResult(
                            post_id=post_id,
                            title=post['title']['rendered'],
                            date=post['date'],
                            success=False,
                            error_message=error_msg,
                            pdf_path=str(error_pdf) if error_pdf else None
                        )
                    
                    await self.save_result(result)
                    total_processed += 1
                    await asyncio.sleep(1)
                
                page += 1
                logging.info(f"Moving to page {page}")
                await asyncio.sleep(5)
                
            except Exception as e:
                logging.error(f"Error processing page {page}: {e}")
                logging.info(f"Waiting {retry_delay} seconds before retry...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, self.config.MAX_RETRY_DELAY)
                continue

            if total_processed % 50 == 0:
                logging.info(f"Processed {total_processed} posts")

    async def load_processed_posts(self) -> Set[int]:
        """Load the set of previously processed post IDs."""
        try:
            if self.processed_file.exists():
                async with aiofiles.open(self.processed_file, 'r') as f:
                    content = await f.read()
                    return set(json.loads(content))
            return set()
        except Exception as e:
            logging.error(f"Error loading processed posts: {e}")
            return set()

    async def save_processed_post(self, post_id: int) -> None:
        """Save a post ID to the processed posts file."""
        processed_posts = await self.load_processed_posts()
        processed_posts.add(post_id)
        async with aiofiles.open(self.processed_file, 'w') as f:
            await f.write(json.dumps(list(processed_posts)))

    async def save_result(self, result: ProcessingResult) -> None:
        """Save processing result to the results file."""
        try:
            results = []
            if self.results_file.exists():
                async with aiofiles.open(self.results_file, 'r') as f:
                    content = await f.read()
                    results = json.loads(content)
            
            results.append(result.__dict__)  # Convert dataclass to dictionary
            async with aiofiles.open(self.results_file, 'w') as f:
                await f.write(json.dumps(results, indent=2))
        except Exception as e:
            logging.error(f"Error saving result: {e}")