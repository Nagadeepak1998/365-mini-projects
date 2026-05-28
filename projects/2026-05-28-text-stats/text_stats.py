#!/usr/bin/env python3
"""Print basic statistics for a text file."""

from pathlib import Path
import sys


def analyze_text(text: str) -> dict[str, float | int | str]:
    lines = text.splitlines()
    words = text.split()
    longest_word = max(words, key=len) if words else ""

    return {
        "lines": len(lines),
        "words": len(words),
        "characters": len(text),
        "average_words_per_line": round(len(words) / len(lines), 2) if lines else 0,
        "longest_word": longest_word.strip(".,!?;:"),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 text_stats.py <file>")
        return 1

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"File not found: {path}")
        return 1

    stats = analyze_text(path.read_text(encoding="utf-8"))
    print(f"Lines: {stats['lines']}")
    print(f"Words: {stats['words']}")
    print(f"Characters: {stats['characters']}")
    print(f"Average words per line: {stats['average_words_per_line']}")
    print(f"Longest word: {stats['longest_word']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
