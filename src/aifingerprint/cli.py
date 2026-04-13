"""CLI entry point — parse args, read input, run analysis, output results."""

import argparse
import os
import sys

from aifingerprint.analyzer import analyze
from aifingerprint.report import generate_report, print_report


def parse_args():
    parser = argparse.ArgumentParser(description="AI writing fingerprint analyzer")
    parser.add_argument("file", nargs="?", help="Text file to analyze (reads stdin if omitted)")
    parser.add_argument("--clipboard", action="store_true", help="Read from clipboard")
    parser.add_argument("--report", nargs="?", const=True, default=False,
                        metavar="PATH", help="Generate markdown report (optionally specify output path)")
    return parser.parse_args()


def read_input(args):
    if args.clipboard:
        import subprocess
        result = subprocess.run(
            ["xclip", "-selection", "clipboard", "-o"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["xsel", "--clipboard", "--output"],
                capture_output=True, text=True,
            )
        if result.returncode != 0:
            print("Error: could not read clipboard. Install xclip or xsel.", file=sys.stderr)
            sys.exit(1)
        return result.stdout
    if args.file:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            text = f.read(2_000_000)  # 2 MB cap — prevents memory exhaustion
        if len(text) >= 2_000_000:
            print("Warning: file truncated to 2 MB", file=sys.stderr)
        return text
    if not sys.stdin.isatty():
        text = sys.stdin.read(2_000_000)  # 2 MB cap — matches file input limit
        if len(text) >= 2_000_000:
            print("Warning: stdin truncated to 2 MB", file=sys.stderr)
        return text
    from aifingerprint import __version__
    print(f"aifingerprint {__version__} — AI writing fingerprint analyzer")
    print(f"https://pypi.org/project/aifingerprint/")
    print(f"https://github.com/sanderburuma/aifingerprint")
    print()
    print("Usage:")
    print("  aifingerprint file.txt              Analyze a file")
    print("  aifingerprint --clipboard           Analyze clipboard contents")
    print("  echo 'text' | aifingerprint         Analyze from stdin")
    print("  aifingerprint file.txt --report      Generate markdown report")
    print("  aifingerprint file.txt --report out.md")
    print()
    print("Checks: compression, sentence rhythm, tone, punctuation diversity,")
    print("  connective density, word burstiness, vocabulary, structure, phrases,")
    print("  formatting (10 weighted heuristics, no API keys or model downloads)")
    print()
    print("Score interpretation:")
    print("   0–20  CLEAN       Looks human")
    print("  21–40  MILD        A few AI-ish traits, probably human")
    print("  41–60  NOTICEABLE  Smells like AI")
    print("  61–80  OBVIOUS     Yeah, that's AI")
    print("  81–100 BLATANT     Copy-pasted straight from ChatGPT")
    sys.exit(1)


def main():
    args = parse_args()
    text = read_input(args)
    if not text or not text.strip():
        from aifingerprint import __version__
        print(f"aifingerprint {__version__} — no text provided.")
        print("Run 'aifingerprint --help' for usage information.")
        sys.exit(1)

    score, results = analyze(text)

    if args.report is not False:
        if args.file:
            source_name = os.path.basename(args.file)
        elif args.clipboard:
            source_name = "clipboard"
        else:
            source_name = "stdin"

        if args.report is True:
            if args.file:
                base = os.path.splitext(args.file)[0]
                report_path = f"{base}.report.md"
            else:
                report_path = "report.md"
        else:
            report_path = args.report

        md = generate_report(score, results, text, source_name)
        with open(report_path, "w") as f:
            f.write(md)
        print(f"Report written to {report_path}")
    else:
        print_report(score, results)
