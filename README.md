this readme was auto-created using Bing Copilot and enhanced by GitHub Copilot

# WP2PDF

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

WP2PDF is a Python-based script to fetch posts from a WordPress site and generate PDFs for each post. This project supports batch processing and parallel PDF creation, using asyncio and other modern libraries.

## Table of Contents
- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Features

- **Fetch WordPress Posts**: Fetches posts from a WordPress site using the REST API.
- **Batch Processing**: Processes posts in customizable batch sizes.
- **Parallel PDF Creation**: Utilizes parallel workers to speed up PDF generation.
- **Image Handling**: Downloads and includes images from posts in the generated PDFs.
- **Customizable Configuration**: Easily adjustable batch size, starting batch, and number of workers.

## Requirements

- Python 3.9+
- aiohttp
- BeautifulSoup4
- FPDF
- PIL (Pillow)
- tenacity
- tqdm

## Installation

Clone the repository and navigate into the project directory:
```bash
git clone https://github.com/aaronlower/wp2pdf.git
cd wp2pdf
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Update the `config.py` file with your WordPress site URL and credentials. You may also need to adjust the batch size, start batch, and max workers according to your needs.

## Usage

Run the main script to start processing posts:
```bash
python claude.py
```
The script will fetch posts, download images, and generate PDFs in batches. Each batch will be saved in the `wordpress_downloads/batch_{BATCH_NUMBER}` directory.

## Logging

Logs for each batch will be saved in `wordpress_downloads/batch_{BATCH_NUMBER}/logs/app.log`. The log files include detailed information about the processing steps and any errors encountered.

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository.
2. Create a new branch.
3. Make your changes.
4. Submit a pull request.

If you have any ideas, suggestions, or issues, feel free to open an issue or a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

Special thanks to the developers of the libraries used in this project.
