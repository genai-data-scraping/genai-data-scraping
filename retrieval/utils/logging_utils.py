import sys
import threading

_print_lock = threading.Lock()

_RESET = "\033[0m"
_STYLES = {
    "success": "\033[32m",
    "fail": "\033[31m",
    "warn": "\033[33m",
    "info": "\033[36m",
    "rung": "\033[94m",
    "retry": "\033[33m",
    "escalate": "\033[35m",
    "dim": "\033[2m",
    "bold": "\033[1m",
}

_color_enabled: bool | None = None


def _use_color() -> bool:
    global _color_enabled
    if _color_enabled is None:
        _color_enabled = sys.stdout.isatty()
    return _color_enabled


def style(text: str, *keys: str) -> str:

    if not _use_color() or not keys:
        return text
    prefix = "".join(_STYLES[k] for k in keys if k in _STYLES)
    if not prefix:
        return text
    return f"{prefix}{text}{_RESET}"


def tprint(msg: str):
    with _print_lock:
        print(msg, flush=True)


def tprint_block(header: str, body: str, domain: str = ""):

    tag = f"[{domain}] " if domain else ""
    border = style("─" * 70, "dim")
    with _print_lock:
        print(f"\n  {tag}{style(header, 'dim')}", flush=True)
        print(f"  {border}", flush=True)
        for line in body.splitlines():
            print(f"  │ {line}", flush=True)
        print(f"  {border}", flush=True)


def filter_html(raw: str) -> str:

    kept, skipped = [], 0
    for line in raw.splitlines():
        s = line.strip()
        is_noise = (
            s.startswith("<")
            or s.startswith("<!DOCTYPE")
            or (len(s) > 200 and " " not in s[:100])
        )
        if is_noise:
            skipped += 1
        else:
            if skipped:
                kept.append(f"[... {skipped} HTML/blob line(s) omitted ...]")
                skipped = 0
            kept.append(line)
    if skipped:
        kept.append(f"[... {skipped} HTML/blob line(s) omitted ...]")
    return "\n".join(kept).strip()
