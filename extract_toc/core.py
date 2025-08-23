#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy python3.13

import argparse
import os

from . import HeadingLevel, Page, RawData, Text
from .analysis import FontStatisticalAnalyzer
from .parsing import parse_pdf_document
from .strategies import embedded_strategy

"""Core API surface for extract_toc.

This module intentionally keeps a thin orchestrator that delegates to
specialized submodules for parsing, analysis and strategies.
"""


# Orchestrator
def get_toc(
    pdf_path: str, *, visualize: bool = False, debug: bool = False
) -> list[tuple[HeadingLevel, Text, Page]]:
    raw_data: RawData = parse_pdf_document(pdf_path, debug=debug)
    if embedded_toc := raw_data.get("embedded_toc"):
        return embedded_toc

    analyzer = FontStatisticalAnalyzer()
    analyzer.analyze(raw_data["all_font_sizes"], visualize=visualize)

    if visualize:
        analyzer.generate_visualizations(raw_data["all_font_sizes"])

    # Prefer embedded strategy if not visualizing
    if not visualize:
        embedded = embedded_strategy(raw_data, {})
        if embedded:
            return embedded
    return analyzer.font_strategy(raw_data)


# Main
def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Extract or infer TOC from PDF")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate and save font size visualizations",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Print detailed diagnostics for pages that look like Table of Contents",
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found at {args.pdf_path}")
        return

    toc: list[tuple[HeadingLevel, Text, Page]] = get_toc(
        args.pdf_path, visualize=args.visualize, debug=args.debug
    )
    pdf_name = os.path.basename(args.pdf_path)

    if not toc:
        print(f"No table of contents found or could be inferred in '{pdf_name}'.")
    else:
        print(f"Table of Contents for '{pdf_name}' (inferred if no embedded TOC):")
        for level, title, page in toc:
            if isinstance(level, int):
                indent = "#" * level + " "
                indent = "\n" + indent if level == 1 else indent
            else:
                indent = "##* "
            print(f"{indent}{title} (Page {page})")


if __name__ == "__main__":
    main_cli()