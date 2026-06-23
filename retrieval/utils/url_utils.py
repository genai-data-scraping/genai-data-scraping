from collections import defaultdict
from urllib.parse import urlparse


def domain_for(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return ".".join(host.split(".")[-2:]) or "site"


def load_urls(path: str) -> dict:
    out = defaultdict(list)
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                out[domain_for(line)].append(line)
            except Exception:
                print(f"  Warning: cannot parse URL: {line}")
    return dict(out)
