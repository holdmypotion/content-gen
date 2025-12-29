import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def is_url(text: str) -> bool:
    """Check if text is a valid URL."""
    try:
        result = urlparse(text.strip())
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False


def scrape_webpage(url: str) -> str:
    """
    Scrape content from a webpage.
    Returns cleaned text content or empty string on failure.
    """
    try:
        headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
        response = requests.get(url.strip(), headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)

        # Limit to first 2000 chars to avoid overwhelming the API
        # content = content[:2000]

        logger.info(f"Successfully scraped {len(content)} characters from {url}")
        return content

    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to scrape {url}: {str(e)}")
        return ""
    except Exception as e:
        logger.warning(f"Error processing {url}: {str(e)}")
        return ""


def process_keywords(reference_keywords: str) -> str:
    """
    Process reference keywords.
    If input contains URLs, scrape them. If input is text, return as-is.
    Handles mixed input (URLs and text keywords).
    """
    if not reference_keywords or not reference_keywords.strip():
        return ""

    lines = reference_keywords.strip().split('\n')
    processed_content = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if is_url(line):
            # Scrape the URL
            logger.info(f"Detected URL: {line}")
            scraped = scrape_webpage(line)
            if scraped:
                processed_content.append(f"[From URL: {line}]\n{scraped}")
            else:
                # If scraping fails, use the URL itself as fallback
                processed_content.append(f"[URL - scraping failed]: {line}")
        else:
            # Regular text keyword
            processed_content.append(line)

    return "\n\n".join(processed_content)
