from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessingResult:
    """Container for post processing results and metadata."""
    post_id: int
    title: str
    date: str
    success: bool
    error_message: Optional[str] = None
    pdf_path: Optional[str] = None