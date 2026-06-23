from typing import Dict, List, Optional
from pathlib import Path

def create_image_content_item(base64_image: str, image_format: str = "image/jpeg") -> Dict:

    return {
        "type": "image_url",
        "image_url": {"url": f"data:{image_format};base64,{base64_image}"}
    }

def create_text_content_item(text: str) -> Dict:

    return {
        "type": "text",
        "text": text
    }

def create_api_message(prompt: str, image_count: int, image_content: List[Dict]) -> List[Dict]:

    message_content = [
        create_text_content_item(
            f"{prompt}\n\nThe images below are consecutive vertical sections of "
            f"the same web page ({image_count} sections, top to bottom)."
        )
    ]
    message_content.extend(image_content)
    return message_content

def create_api_request_payload(message_content: List[Dict], model: str,
                               temperature: float = None) -> Dict:

    from config.settings import API_TEMPERATURE
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message_content}],
        "temperature": API_TEMPERATURE if temperature is None else temperature,
    }
    return payload

def create_processing_result(success: bool, data: Optional[Dict] = None,
                           error: Optional[str] = None,
                           image_count: int = 0,
                           folder_path: str = "") -> Dict:

    result = {
        "success": success,
        "image_count": image_count,
        "folder_path": folder_path,
        "timestamp": None
    }

    if success and data:
        result["data"] = data
    elif error:
        result["error"] = error

    return result

def create_image_info(file_path: Path, success: bool, error: Optional[str] = None) -> Dict:

    return {
        "filename": file_path.name,
        "full_path": str(file_path),
        "success": success,
        "error": error,
        "size_bytes": file_path.stat().st_size if file_path.exists() and success else 0
    }

def create_summary_stats(total_found: int, successfully_processed: int,
                        failed: int, folder_path: str) -> Dict:

    return {
        "total_images_found": total_found,
        "successfully_processed": successfully_processed,
        "failed_to_process": failed,
        "success_rate": (successfully_processed / total_found * 100) if total_found > 0 else 0,
        "folder_path": folder_path
    }
