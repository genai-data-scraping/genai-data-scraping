from typing import List, Dict, Optional
import threading

def create_file_result(filename: str, full_path: str, url: str = "", 
                      status: str = "failed", error: Optional[str] = None, 
                      llm_response: Optional[str] = None) -> Dict:
    """Create a file result dictionary."""
    return {
        "filename": filename,
        "full_path": full_path,
        "url": url,
        "status": status,
        "error": error,
        "llm_response": llm_response,
        "thread_id": threading.current_thread().ident
    }

def create_batch_results(directory: str, num_files: int, max_workers: int) -> Dict:
    """Create initial batch results structure."""
    return {
        "processed_files": [],
        "summary": {
            "total_requested": num_files,
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "directory": directory,
            "max_workers": max_workers
        }
    }

def update_batch_summary(results: Dict, file_result: Dict) -> None:
    """Update batch results summary with a processed file result."""
    if file_result["status"] == "success":
        results["summary"]["successful"] += 1
    else:
        results["summary"]["failed"] += 1
    
    results["processed_files"].append(file_result)
    results["summary"]["total_processed"] += 1

def get_success_rate(results: Dict) -> float:
    """Calculate success rate from batch results."""
    total_processed = results["summary"]["total_processed"]
    if total_processed == 0:
        return 0.0
    return (results["summary"]["successful"] / total_processed) * 100

def create_api_request_payload(prompt: str, target_url: str, model: str, temperature: float) -> Dict:
    """Create API request payload."""
    return {
        "model": model,
        "messages": [{"role": "user", "content": f"{prompt}\n\nTarget URL: {target_url}"}],
        "temperature": temperature
    }

def create_error_result(file_path: str, error_message: str) -> Dict:
    """Create an error result for a failed file processing."""
    from pathlib import Path
    
    return {
        "filename": Path(file_path).name,
        "full_path": file_path,
        "url": "",
        "status": "failed",
        "error": error_message,
        "llm_response": None,
        "thread_id": None
    }