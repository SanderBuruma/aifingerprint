"""CLI entry point — parse args, read input, run analysis, output results."""

import argparse
import os
import sys

from guardrails.analyzer import analyze
from guardrails.report import generate_report, print_report


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
        return result.stdout
    if args.file:
        with open(args.file) as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Usage: guardrails [file.txt | --clipboard] [--report [PATH]]")
    print("       echo 'text' | guardrails")
    sys.exit(1)


def main():
    args = parse_args()
    text = read_input(args)
    if not text or not text.strip():
        print("No text provided.")
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
