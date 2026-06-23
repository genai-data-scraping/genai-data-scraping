import json
import threading
import time
import requests
import logging
from typing import Dict

from config.settings import get_api_config, openrouter_app_title, OPENROUTER_REFERER
from models.data_models import create_api_request_payload

logger = logging.getLogger(__name__)

def make_api_request(target_url: str, prompt: str) -> str:

    try:
        thread_id = threading.current_thread().ident
        logger.info(f"[Thread {thread_id}] Making API request for URL: {target_url[:100]}...")

        api_config = get_api_config()

        payload = create_api_request_payload(
            prompt=prompt,
            target_url=target_url,
            model=api_config["model"],
            temperature=api_config["temperature"]
        )

        start = time.perf_counter()
        response = requests.post(
            url=api_config["base_url"],
            headers={
                "Authorization": f"Bearer {api_config['api_key']}",
                "Content-Type": "application/json",
                "HTTP-Referer": OPENROUTER_REFERER,
                "X-Title": openrouter_app_title(url=target_url),
            },
            data=json.dumps(payload),
            timeout=api_config["timeout"]
        )
        elapsed = round(time.perf_counter() - start, 3)

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        response_data = response.json()

        if 'error' in response_data:
            raise Exception(response_data['error'])

        result = response_data['choices'][0]['message']['content']
        logger.info(
            f"[Thread {thread_id}] Successfully got API response for URL ({elapsed}s)"
        )
        return result, elapsed

    except Exception as e:
        thread_id = threading.current_thread().ident
        logger.error(f"[Thread {thread_id}] Failed to process URL {target_url}: {str(e)}")
        raise Exception(f"Failed to process URL: {str(e)}")

def validate_api_response(response_data: Dict) -> str:

    if 'error' in response_data:
        raise Exception(response_data['error'])

    if 'choices' not in response_data or not response_data['choices']:
        raise Exception("No choices in API response")

    if 'message' not in response_data['choices'][0]:
        raise Exception("No message in API response choice")

    if 'content' not in response_data['choices'][0]['message']:
        raise Exception("No content in API response message")

    return response_data['choices'][0]['message']['content']
