from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    html: str = ""
    error: str = ""
    http_status: int | None = None
    failure_code: str | None = None
    content_rejected: bool = False
    retry_after_seconds: float | None = None
    judge_unavailable: bool = False
    llm_cost_usd: float = 0.0
