import json
import requests
from config.settings import (
    OPENROUTER_API_KEY, MODEL_NAME, API_TIMEOUT, 
    API_TEMPERATURE, API_URL
)
from config.logging_config import get_logger

logger = get_logger(__name__)


def extract_with_llm(cleaned_content, prompt):
    """Extract information using LLM API."""
    logger.info("Starting LLM extraction")
    
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY environment variable not set")
        raise ValueError("API key not found")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
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
        response = requests.post(
            url=API_URL,
            headers=headers,
            data=data,
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        
        result = response.json()['choices'][0]['message']['content']
        logger.info("LLM extraction completed successfully")
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        raise
    except KeyError as e:
        logger.error(f"Unexpected API response format: {e}")
        raise