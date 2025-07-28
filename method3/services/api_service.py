import requests
import json
import logging
from typing import Dict, List

from config.settings import get_api_config
from models.data_models import create_api_request_payload, create_api_message

logger = logging.getLogger(__name__)

def make_vision_api_request(prompt: str, image_content: List[Dict]) -> Dict:
    """Make API request to process images with vision model."""
    try:
        logger.info(f"Making vision API request with {len(image_content)} images...")
        
        api_config = get_api_config()
        
        # Create message content
        message_content = create_api_message(prompt, len(image_content), image_content)
        
        # Create request payload
        payload = create_api_request_payload(message_content, api_config["model"])
        
        # Make API request
        response = requests.post(
            url=api_config["base_url"],
            headers={
                "Authorization": f"Bearer {api_config['api_key']}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=api_config["timeout"]
        )
        
        if response.status_code != 200:
            error_msg = f"API request failed with status {response.status_code}: {response.text}"
            logger.error(error_msg)
            return {"error": error_msg}
        
        api_response = response.json()
        
        if 'error' in api_response:
            logger.error(f"API returned error: {api_response['error']}")
            return {"error": api_response['error']}
        
        logger.info("Successfully received API response")
        return extract_content_from_response(api_response)
        
    except requests.exceptions.Timeout:
        error_msg = "API request timed out"
        logger.error(error_msg)
        return {"error": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error in API request: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def extract_content_from_response(api_response: Dict) -> Dict:
    """Extract and parse content from API response."""
    try:
        if 'choices' not in api_response or not api_response['choices']:
            return {"error": "No choices in API response"}
        
        content = api_response['choices'][0]['message']['content']
        logger.info("Processing API response content...")
        
        # Try to parse as JSON first
        try:
            parsed_content = json.loads(content)
            logger.info("Successfully parsed response as JSON")
            return {"data": parsed_content}
        except json.JSONDecodeError:
            logger.info("Response is not valid JSON, attempting to extract JSON from text")
            return extract_json_from_text(content)
            
    except Exception as e:
        error_msg = f"Failed to extract content from response: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def extract_json_from_text(content: str) -> Dict:
    """Extract JSON from text response using regex."""
    import re
    
    try:
        # Look for JSON-like content in the response
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed_content = json.loads(json_str)
            logger.info("Successfully extracted and parsed JSON from text")
            return {"data": parsed_content}
        else:
            logger.warning("No JSON found in response, returning raw content")
            return {"data": {"raw_response": content}}
            
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse extracted JSON: {e}, returning raw content")
        return {"data": {"raw_response": content}}
    except Exception as e:
        error_msg = f"Error extracting JSON from text: {str(e)}"
        logger.error(error_msg)
        return {"error": error_msg}

def validate_api_response(response: Dict) -> bool:
    """Validate API response structure."""
    return (
        isinstance(response, dict) and
        'choices' in response and
        isinstance(response['choices'], list) and
        len(response['choices']) > 0 and
        'message' in response['choices'][0] and
        'content' in response['choices'][0]['message']
    )