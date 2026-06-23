#!/usr/bin/env bash
# Convenience wrapper — same as: python eval.py "$@"
cd "$(dirname "$0")"
exec python eval.py "$@"
