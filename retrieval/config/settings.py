import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
SCRAPINGBEE_API_KEY = os.getenv("SCRAPINGBEE_API_KEY", "")

LLM_MODEL = "anthropic/claude-sonnet-4.6"
MAX_CODE_TOKENS = 1500
REQUEST_TIMEOUT = 15
URL_TIMEOUT = 300

HTML_OUTPUT_DIR = None
DEFAULT_MODE = "ladder"


CODE_LEVELS = ["requests_basic", "requests_headers", "playwright", "scrapingbee"]


INTER_URL_DELAY_SECONDS = 2.0


RETRY_MAX_ATTEMPTS_CODE = 3
RETRY_MAX_ATTEMPTS_L4 = 5
RETRY_BACKOFF_BASE_SECONDS = 1.0
RETRY_BACKOFF_MAX_SECONDS = 30.0
RETRY_JITTER_FRACTION = 0.25

LLM_COST_PER_TOKEN_INPUT = 3.0 / 1_000_000
LLM_COST_PER_TOKEN_OUTPUT = 15.0 / 1_000_000

OPENROUTER_REFERER = "https://github.com/genai-data-scraping"
OPENROUTER_METHOD = "retrieval"

LEVELS = ["requests_basic", "requests_headers", "playwright", "scrapingbee"]

LEVEL_LABELS = {
    "requests_basic": "L1: Plain Requests",
    "requests_headers": "L2: Requests + Headers",
    "playwright": "L3: Playwright (Stealth)",
    "scrapingbee": "L4: ScrapingBee (Premium Proxy)",
}

JUDGE_HEAD_CHARS = 6000
JUDGE_MID_HALF_CHARS = 1000
JUDGE_MID_SLICE_CHARS = 2000
JUDGE_MAX_TOKENS = 150
JUDGE_MAX_ATTEMPTS = 2
JUDGE_RETRY_BACKOFF_SECONDS = 1.0

JUDGE_SYSTEM_PROMPT = (
    "You are a web page retrieval validator.\n"
    "You receive a URL and two HTML snippets (head + mid-document sample) from a "
    "fetch attempt. The snippets may be truncated; base your judgment on what is "
    "present, not on what might exist below the fold.\n\n"
    "Classify the fetch as SUCCESS or FAILURE.\n\n"
    "FAILURE — the page was NOT successfully retrieved. Examples:\n"
    "- Bot protection / CAPTCHA / 'verify you are human' challenges\n"
    "- Cloudflare or similar interstitials ('Checking your browser', "
    "'Enable JavaScript and cookies', cf-browser-verification)\n"
    "- Access denied, blocked, 403-style 'you have been blocked' pages\n"
    "- Empty JavaScript shells: minimal HTML with no meaningful body content "
    "(e.g. root div with no text, only script tags and loading spinners)\n"
    "- Error pages with no primary site content\n\n"
    "SUCCESS — the page's primary content appears to be present. "
    "Real article text, product listings, search results, or other substantive "
    "page body — even if navigation, ads, or scripts are also present.\n\n"
    "When uncertain between a thin but real page and a block/shell, choose FAILURE.\n"
    "Do not infer success from page title or meta tags alone.\n\n"
    "Reply with ONLY valid JSON, no markdown:\n"
    '{"ok": true|false, "reason": "one short sentence explaining the classification"}'
)

RETRIEVAL_HTML_PATH_ENV = "RETRIEVAL_HTML_PATH"

SYSTEM_PROMPT = (
    "You are an expert Python web scraping engineer.\n"
    "Return ONLY raw executable Python code. No markdown, no explanation.\n"
    "Write everything at top level — no functions, no classes.\n\n"
    "OUTPUT CONTRACT (mandatory — the runner depends on this exactly):\n"
    f"1. Read the target HTML path from os.environ['{RETRIEVAL_HTML_PATH_ENV}'].\n"
    "2. Fetch the page using the level-specific instructions in the user message.\n"
    "3. Write the raw response body (HTML string) to that path as UTF-8 text.\n"
    "4. Print EXACTLY ONE line to stdout — the last line must be:\n"
    "     print(json.dumps(result))\n"
    "   where result = {\n"
    '     "success": bool,          # True only if HTML was fetched AND written to the file\n'
    '     "bytes_written": int,     # len of HTML written (0 on failure)\n'
    '     "error": str_or_null,     # concise failure reason; null on success\n'
    '     "http_status": int_or_null,  # HTTP status if a response was received; null if no HTTP response\n'
    '     "failure_code": str_or_null,  # on failure: timeout | connection_error | http_error | script_error\n'
    '     "retry_after_seconds": float_or_null  # optional; honor server Retry-After on 429\n'
    "   }\n"
    "5. Do NOT print the HTML to stdout. Do NOT embed HTML in the JSON.\n"
    "6. On any failure, still print the JSON line (success=false, bytes_written=0).\n"
    "7. Set failure_code on failure: timeout (request timed out), connection_error "
    "(connection/network failure before a response), http_error (non-2xx HTTP response), "
    "script_error (any other failure before a usable HTTP response).\n\n"
    "FETCH RULES:\n"
    f"- For requests/HTTP calls: always set timeout={REQUEST_TIMEOUT}.\n"
    "- Raise or handle HTTP errors explicitly; set http_status and put status code "
    "plus a short body snippet in error on non-2xx.\n"
    "- Allowed imports: standard library, requests, bs4, playwright.sync_api.\n"
    "- At L4 (ScrapingBee): SCRAPINGBEE_API_KEY is in os.environ. "
    "Endpoint: https://app.scrapingbee.com/api/v1/ . "
    "The response body IS the page HTML (response.text), not JSON.\n"
)

LEVEL_PROMPTS = {
    "requests_basic": (
        "Level: plain requests, no special headers.\n"
        "Raise on bad HTTP status.\nURL: {url}\n"
    ),
    "requests_headers": (
        "Level: requests.Session with realistic browser headers "
        "(Chrome User-Agent, Accept, Accept-Language, Referer).\n"
        "Raise on bad status.\nURL: {url}\n"
    ),
    "playwright": (
        "Level: Playwright Chromium headless.\n"
        "Apply stealth: from playwright_stealth import stealth_sync; "
        "stealth_sync(page) right after page creation.\n"
        "Viewport 1280x800. wait_until='domcontentloaded', "
        "then page.wait_for_timeout(3000).\n"
        "Return page.content() as html.\nURL: {url}\n"
    ),
    "scrapingbee": (


        "Level: ScrapingBee REST API.\n"
        "Key: os.environ['SCRAPINGBEE_API_KEY']\n"
        "Endpoint: https://app.scrapingbee.com/api/v1/\n"
        "Params: api_key=<api_key>, url=<url>, render_js=True, premium_proxy=True, block_resources=False.\n"
        "Make a GET request with these as query params using requests.get(..., timeout=60).\n"
        "The response body IS the page HTML (not JSON): use response.text as the html.\n"
        "On non-200: success=False, include status + body in error.\n"
        "If prior attempts failed, vary the ScrapingBee params (render_js, premium_proxy, "
        "stealth_proxy, country_code, block_resources) — do not repeat the same configuration.\n"
        "URL: {url}\n"
    ),
}

SELECTOR_SYSTEM_PROMPT = (
    "You are a web-scraping strategist. Given a URL and the available retrieval "
    "infrastructure levels, choose the SINGLE best level to try NEXT to fetch "
    "the page's full HTML. Balance likelihood of success against cost/latency: "
    "prefer the cheapest level that is likely to work, and escalate to heavier "
    "infrastructure only when the page or prior failures justify it.\n"
    "Reply with ONLY the level key (e.g. 'requests_basic' or 'scrapingbee'). "
    "No other text.\n"
)

AGENT_SELECTOR_SYSTEM_PROMPT = (
    "You are a web retrieval agent. At each step you must choose exactly ONE "
    "action to fetch a page's full HTML.\n\n"
    "Available actions:\n"
    "1. Generate Python fetch code at a code level:\n"
    "   - requests_basic (L1): plain HTTP GET, cheapest\n"
    "   - requests_headers (L2): HTTP GET with browser headers\n"
    "   - playwright (L3): headless Chromium with stealth + JS execution\n"
    "2. Generate Python fetch code at scrapingbee (L4): ScrapingBee REST API with "
    "premium proxy + JS rendering. Most reliable for heavy anti-bot sites; most "
    "expensive. Only choose when cheaper levels failed or the site is known "
    "to be heavily protected.\n\n"
    "Reply with ONLY a JSON object (no markdown):\n"
    '  {"action": "code", "level": "<requests_basic|requests_headers|playwright|scrapingbee>"}\n'
    '  {"action": "scrapingbee"}  (equivalent to code at scrapingbee)\n\n'
    "Prefer the cheapest action likely to succeed. Use scrapingbee when prior "
    "failures show bot blocks, empty JS shells, or timeouts.\n"
)

LEVEL_DESCRIPTIONS = {
    "requests_basic": (
        "requests_basic (L1): plain HTTP GET, no special headers. Cheapest and "
        "fastest. Good for simple, unprotected, server-rendered pages."
    ),
    "requests_headers": (
        "requests_headers (L2): HTTP GET with realistic browser headers. Beats "
        "naive User-Agent blocks. Still no JavaScript execution."
    ),
    "playwright": (
        "playwright (L3): headless Chromium with stealth. Executes JavaScript; "
        "handles client-rendered and lightly protected sites. Slower."
    ),
    "scrapingbee": (
        "scrapingbee (L4): premium proxy + JS rendering via ScrapingBee. Most "
        "powerful and most expensive. For heavy anti-bot defenses (e.g. "
        "Cloudflare) or sites the cheaper levels can't reach."
    ),
}


def openrouter_app_title(site: str) -> str:

    return f"{OPENROUTER_METHOD} - {site or 'unknown'}"
