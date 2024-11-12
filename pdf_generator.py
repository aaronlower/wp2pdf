from typing import Dict, List, Optional, Tuple
from pathlib import Path
from fpdf import FPDF
from bs4 import BeautifulSoup
from PIL import Image
import logging
import warnings
from datetime import datetime
import re
import html
import emoji
from cache_manager import CacheManager

class PDFGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.font_name = "NotoSans"
        self.emoji_scale = 0.85
        
        # Setup emoji cache directory
        self.cache_dir = Path(__file__).parent / "emoji_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_manager = CacheManager(self.cache_dir)
        
        # Configure logging
        logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
        
        # Store font paths
        self.font_dir = Path(__file__).parent / "fonts"
        self.fonts = {
            '': str(self.font_dir / 'NotoSans-Regular.ttf'),
            'B': str(self.font_dir / 'NotoSans-Bold.ttf'),
            'I': str(self.font_dir / 'NotoSans-Italic.ttf')
        }

    def _write_text_with_emojis(self, pdf: FPDF, text: str, font_size: int = 12, style: str = '') -> None:
        """Write text to PDF with improved line spacing and emoji handling."""
        if not text:
            return

        # Calculate sizes
        emoji_size = font_size * self.emoji_scale * (pdf.k / 72)
        line_height = font_size * 1.5  # Increased line height for better readability
        
        segments = self._split_text_and_emojis(text)
        x_start = pdf.l_margin  # Start from left margin
        y_position = pdf.get_y()
        current_x = x_start
        line_width = 0
        line_segments = []
        
        # First pass: calculate line breaks
        for is_emoji, content in segments:
            if is_emoji:
                segment_width = emoji_size
            else:
                pdf.set_font(self.font_name, style, font_size)
                segment_width = pdf.get_string_width(content)
            
            # Check if we need to start a new line
            if current_x + segment_width > pdf.w - pdf.r_margin:
                # Write the current line
                self._write_line(pdf, line_segments, x_start, y_position, line_height, font_size, style)
                # Reset for new line
                y_position += line_height
                current_x = x_start
                line_segments = []
                
            line_segments.append((is_emoji, content))
            current_x += segment_width
        
        # Write any remaining segments
        if line_segments:
            self._write_line(pdf, line_segments, x_start, y_position, line_height, font_size, style)
            y_position += line_height
        
        # Update PDF position
        pdf.set_y(y_position)

    def _split_text_and_emojis(self, text: str) -> List[Tuple[bool, str]]:
        """Split text into segments of regular text and emojis."""
        segments = []
        current_text = ""
        
        i = 0
        while i < len(text):
            if any(text[i:].startswith(em) for em in emoji.EMOJI_DATA):
                # Found an emoji
                if current_text:
                    segments.append((False, current_text))
                    current_text = ""
                
                # Find the complete emoji
                for em in emoji.EMOJI_DATA:
                    if text[i:].startswith(em):
                        segments.append((True, em))
                        i += len(em)
                        break
            else:
                current_text += text[i]
                i += 1
        
        if current_text:
            segments.append((False, current_text))
        
        return segments

    def create_pdf(self, post: Dict, images: List[Optional[Image.Image]]) -> Path:
        """Create a PDF from a blog post and its images."""
        try:
            pdf = self._create_pdf_instance()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)

            # Add title (centered)
            title = self._clean_html_text(post.get('title', {}).get('rendered', 'Untitled'))
            pdf.set_font(self.font_name, 'B', 16)
            pdf.cell(0, 10, title, ln=True, align='C')
            pdf.ln(5)

            # Add horizontal line after title
            pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
            pdf.ln(5)

            # Add formatted date (centered)
            date = self._format_date(post.get('date', 'Unknown date'))
            pdf.set_font(self.font_name, '', 12)
            pdf.cell(0, 10, date, ln=True, align='C')
            pdf.ln(5)

            # Add horizontal line after date
            pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
            pdf.ln(5)

            # Add tags with emoji support
            tags = self._extract_tags(post)
            if tags:
                pdf.set_font(self.font_name, 'I', 12)
                pdf.cell(0, 10, f"Tags: {tags}", ln=True, align='C')
                pdf.ln(5)
                # Add horizontal line after tags
                pdf.line(20, pdf.get_y(), pdf.w - 20, pdf.get_y())
                pdf.ln(10)
            else:
                pdf.ln(10)

            # Add content with improved paragraph handling
            content = post.get('content', {}).get('rendered', '')
            paragraphs = self._process_content(content)
            
            pdf.set_font(self.font_name, '', 12)
            first_paragraph = True
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    if not first_paragraph:
                        # Add consistent spacing between paragraphs
                        pdf.ln(8)  # Adjust this value to control paragraph spacing
                    
                    # Calculate if we need a page break
                    if pdf.get_y() + 20 > pdf.h - pdf.b_margin:  # 20 is approximate height needed
                        pdf.add_page()
                    
                    # Write paragraph with proper line height
                    self._write_text_with_emojis(pdf, paragraph, font_size=12)
                    first_paragraph = False

            # Handle images with improved spacing
            for image in images:
                if image:
                    try:
                        pdf.add_page()
                        available_height = pdf.h - pdf.t_margin - pdf.b_margin
                        available_width = pdf.w - (2 * 20)  # 20px margin on each side
                        
                        # Calculate dimensions while maintaining aspect ratio
                        img_width = available_width
                        aspect = image.height / image.width
                        img_height = img_width * aspect
                        
                        # Adjust if image is too tall
                        if img_height > available_height:
                            img_height = available_height
                            img_width = img_height / aspect
                        
                        # Center the image horizontally
                        x_pos = (pdf.w - img_width) / 2
                        # Add some top margin
                        y_pos = pdf.t_margin + 10
                        
                        pdf.image(image, x=x_pos, y=y_pos, w=img_width)
                    except Exception as e:
                        logging.warning(f"Failed to add image to PDF: {str(e)}")

            # Save PDF
            filename = self._get_filename(post)
            pdf_path = self.output_dir / filename
            pdf.output(str(pdf_path))
            
            logging.info(f"Successfully created PDF: {filename}")
            return pdf_path

        except Exception as e:
            logging.error(f"Failed to create PDF: {str(e)}")
            raise

    def _clean_html_text(self, html_text: str) -> str:
        """Clean HTML text and decode entities."""
        if not html_text:
            return ""
        # First decode HTML entities
        text = html.unescape(html_text)
        # Then remove any remaining HTML tags
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text()

    def _format_date(self, date_str: str) -> str:
        """Format date string to YYYYMMDD @ HH:MM format."""
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%Y%m%d @ %H:%M')
        except Exception as e:
            logging.error(f"Error formatting date: {str(e)}")
            return date_str

    def _get_filename(self, post: Dict) -> str:
        """Generate filename in YYYYMMDD_title format."""
        try:
            date_str = post.get('date', '')
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            date_part = dt.strftime('%Y%m%d')
            
            title = self._clean_html_text(post.get('title', {}).get('rendered', 'untitled'))
            # Clean title for filename
            title = re.sub(r'[^\w\s-]', '', title)
            title = re.sub(r'[-\s]+', '_', title)
            title = title[:50].strip('_')
            
            return f"{date_part}_{title}.pdf"
        except Exception as e:
            logging.error(f"Error creating filename: {str(e)}")
            return f"unknown_date_{post.get('id', 'unknown')}.pdf"

    def _extract_tags(self, post: Dict) -> str:
        """Extract and format tags and categories from post data."""
        tags = []
        try:
            logging.info("Starting tag extraction")
            logging.info(f"Post data keys: {post.keys()}")
            
            if '_embedded' in post:
                logging.info("Found _embedded in post")
                embedded_terms = post['_embedded'].get('wp:term', [])
                logging.info(f"Embedded terms: {embedded_terms}")
                
                for term_group in embedded_terms:
                    if isinstance(term_group, list):
                        for term in term_group:
                            if isinstance(term, dict):
                                taxonomy = term.get('taxonomy', '')
                                name = term.get('name', '')
                                if name:
                                    # You can customize how different taxonomies are displayed
                                    if taxonomy == 'category':
                                        tags.append(f"📁 {name}")  # Using emoji for categories
                                    elif taxonomy == 'post_tag':
                                        tags.append(f"🏷️ {name}")  # Using emoji for tags
                                    else:
                                        tags.append(name)
                                    logging.info(f"Added {taxonomy}: {name}")
            
            # Remove duplicates while preserving order
            tags = list(dict.fromkeys(tags))
            logging.info(f"Final extracted tags: {tags}")
            
        except Exception as e:
            logging.error(f"Error extracting tags: {str(e)}", exc_info=True)
        
        result = ', '.join(tags) if tags else ''
        logging.info(f"Returning tags string: {result}")
        return result

    def _process_content(self, html_content: str) -> List[str]:
        """Process HTML content into clean paragraphs with proper spacing."""
        if not html_content:
            return ["No content available"]
            
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(['script', 'style']):
                element.decompose()
            
            paragraphs = []
            current_text = []
            
            # Process elements in order they appear
            for element in soup.children:
                if element.name in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote']:
                    # If we have accumulated text, add it as a paragraph
                    if current_text:
                        combined_text = ' '.join(current_text).strip()
                        if combined_text:
                            paragraphs.append(combined_text)
                        current_text = []
                    
                    # Process the block element
                    text = element.get_text(strip=True)
                    if text:
                        paragraphs.append(html.unescape(text))
                
                elif element.name == 'br':
                    # Handle line breaks
                    if current_text:
                        combined_text = ' '.join(current_text).strip()
                        if combined_text:
                            paragraphs.append(combined_text)
                        current_text = []
                
                elif isinstance(element, str):
                    # Handle text nodes
                    text = element.strip()
                    if text:
                        current_text.append(html.unescape(text))
            
            # Add any remaining text
            if current_text:
                combined_text = ' '.join(current_text).strip()
                if combined_text:
                    paragraphs.append(combined_text)
            
            # Clean up paragraphs
            cleaned_paragraphs = []
            for para in paragraphs:
                # Normalize whitespace
                cleaned = ' '.join(para.split())
                if cleaned:
                    cleaned_paragraphs.append(cleaned)
            
            return cleaned_paragraphs if cleaned_paragraphs else ["No content available"]
                
        except Exception as e:
            logging.error(f"Error processing content: {str(e)}")
            return ["Error processing content"]
            
    def _create_pdf_instance(self) -> FPDF:
        """Create a new PDF instance with registered fonts."""
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=UserWarning)
            
            pdf = FPDF()
            for style, path in self.fonts.items():
                pdf.add_font(family=self.font_name, style=style, fname=path, uni=True)
            return pdf
        
    def _write_line(self, pdf: FPDF, segments: List[Tuple[bool, str]], x: float, y: float, line_height: float, font_size: int, style: str) -> None:
        """Helper method to write a single line with mixed text and emojis."""
        current_x = x
        
        for is_emoji, content in segments:
            if is_emoji:
                try:
                    emoji_image = self.cache_manager.get_emoji_image(content)
                    if emoji_image:
                        emoji_size = font_size * self.emoji_scale * (pdf.k / 72)
                        pdf.image(emoji_image, x=current_x, y=y + (line_height - emoji_size)/2, h=emoji_size)
                        current_x += emoji_size
                except Exception as e:
                    logging.warning(f"Failed to add emoji image: {str(e)}")
            else:
                pdf.set_xy(current_x, y)
                pdf.set_font(self.font_name, style, font_size)
                pdf.write(line_height, content)
                current_x = pdf.get_x()