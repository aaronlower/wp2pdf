from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration settings for the PDF generation process."""
    BATCH_SIZE: int = 10         # Number of posts to process in one batch
    START_INDEX: int = 50         # Starting index for post processing
    NUM_WORKERS: int = 5         # Number of concurrent workers
    MAX_RETRIES: int = 3         # Maximum number of retry attempts
    TIMEOUT: int = 25            # Request timeout in seconds
    IMAGE_MAX_SIZE: tuple = (800, 800)  # Maximum dimensions for images
    OUTPUT_DIR: Path = Path("test_output")  # Base output directory
    LOG_FILE: Path = Path("test_debug.log")  # Log file location
    RETRY_DELAY: int = 30        # Initial retry delay in seconds
    MAX_RETRY_DELAY: int = 300   # Maximum retry delay in seconds