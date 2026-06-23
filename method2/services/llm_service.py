import json
import time
import requests
from config.settings import (
    OPENROUTER_API_KEY, MODEL_NAME, API_TIMEOUT,
    API_TEMPERATURE, API_URL, OPENROUTER_REFERER, openrouter_app_title
)
from config.logging_config import get_logger

logger = get_logger(__name__)


def extract_with_llm(cleaned_content, prompt, url=""):

    logger.info("Starting LLM extraction")

    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        raise ValueError("API key not found")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_REFERER,
        "X-Title": openrouter_app_title(url=url),
    }

    data = json.dumps({
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "user",
                "content": f"{prompt}\n\nContent:\n{cleaned_content}"
            }
        ],
        "temperature": API_TEMPERATURE
    })

    try:
        start = time.perf_counter()
        response = requests.post(
            url=API_URL,
            headers=headers,
            data=data,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        elapsed = round(time.perf_counter() - start, 3)

        result = response.json()['choices'][0]['message']['content']
        logger.info(f"LLM extraction completed successfully ({elapsed}s)")
        return result, elapsed

    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except KeyError as e:
        logger.error(f"Unexpected API response format: {e}")
        raise
