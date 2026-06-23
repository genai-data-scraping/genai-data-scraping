import random
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "urls"
OUT = REPO_ROOT / "retrieval" / "eval_urls"

SOURCES = {
    "amazon.com.txt": "amazon.com.txt",
    "cars.com.txt": "cars.com.txt",
    "reuters.txt": "reuters.com.txt",
    "wikipedia.org.txt": "wikipedia.org.txt",
    "yahoo.finance.com.txt": "yahoo.finance.com.txt",
}


def sample_eval_urls(n: int = 100, seed: int = 42, out_dir: Path | None = None) -> list[Path]:

    out_dir = out_dir or OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(seed)
    written = []

    for src_name, out_name in SOURCES.items():
        src = SRC / src_name
        lines = [
            ln.strip()
            for ln in src.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        count = min(n, len(lines))
        if len(lines) < n:
            print(f"  Warning: {src_name} has only {len(lines)} URLs — using {count}")
        sample = random.sample(lines, count)
        path = out_dir / out_name
        path.write_text("\n".join(sample) + "\n")
        written.append(path)
        print(f"  {out_name}: {count} URLs")

    return written


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sample eval URLs per domain")
    parser.add_argument("-n", type=int, default=100, help="URLs per domain")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()
    print(f"Sampling {args.n} URLs per domain (seed={args.seed}) → {OUT}/")
    sample_eval_urls(n=args.n, seed=args.seed)


if __name__ == "__main__":
    main()
