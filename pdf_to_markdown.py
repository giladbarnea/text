#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,markdownify,bs4,lxml python3
"""
pdf_to_markdown.py FILE_OR_DIR [FILE_OR_DIR ...]
"""

import fitz  # type: ignore # PyMuPDF
import sys
import os
import re
from markdownify import markdownify as md  # type: ignore
import base64
from bs4 import BeautifulSoup  # type: ignore


def remove_line_wraps(text):
    """
    Rejoins paragraphs that were incorrectly split by line breaks.
    """
    lines = text.split("\n")
    rejoined_lines = []
    i = 0
    # Use a tuple for faster checking with .endswith()
    valid_endings = (".", "?", "!", '."', ".'", ".)", "”", ".**", "**.", ":")

    is_heading = re.compile(r"(^#+ +.+|^\*+.*?\*$)")
    is_list_item = re.compile(r"^(\d+\.|- |\* ).+")
    is_quote_block = re.compile(r"^> +")
    
    while i < len(lines):
        line = lines[i]
        clean_line = line.strip()

        # Rule out empty lines immediately
        if not clean_line:
            rejoined_lines.append(line)
            i += 1
            continue

        def get_stripped_and_marker(cline):
            for m in ["***", "**", "*", "___", "__", "_"]:
                if cline.startswith(m) and cline.endswith(m):
                    return cline[len(m) : -len(m)], m
            return cline, None

        def all_words_are_titlecase(l):  # noqa: E741
            return all(
                word.istitle()
                for word in l.split()
                if word
                not in (
                    # Words that don't require titlizing in titles
                    "a",
                    "about",
                    "above",
                    "after",
                    "an",
                    "and",
                    "around",
                    "as",
                    "at",
                    "before",
                    "behind",
                    "below",
                    "beyond",
                    "but",
                    "by",
                    "down",
                    "during",
                    "for",
                    "from",
                    "in",
                    "into",
                    "like",
                    "near",
                    "nor",
                    "of",
                    "off",
                    "on",
                    "onto",
                    "or",
                    "out",
                    "over",
                    "since",
                    "so",
                    "the",
                    "through",
                    "to",
                    "under",
                    "until",
                    "up",
                    "upon",
                    "with",
                    "within",
                    "without",
                    "yet",
                )
            )

        stripped, marker = get_stripped_and_marker(clean_line)
        is_heading = re.compile(r"(^#+ +.+|^\*+.*?\*$)")
        is_list_item = re.compile(r"^(\d+\.|- |\* ).+")
        is_quote_block = re.compile(r"^> +")
        is_regular_sentence = (
            not stripped.isupper()
            and not is_heading.match(stripped)
            and not is_list_item.match(stripped)
            and not is_quote_block.match(stripped)
            and not all_words_are_titlecase(stripped)
        )
        is_truncated = not stripped.endswith(valid_endings)
        leading_len = line.index(stripped[0]) if stripped else len(line)
        leading = line[:leading_len]

        paragraph_stripped = stripped
        paragraph_marker = marker
        i += 1
        line_count = len(lines)
        while i < line_count and is_regular_sentence and is_truncated:
            j = 0
            while i + j < line_count and not lines[i + j].strip():
                j += 1
            if i + j >= line_count:
                break
            next_line = lines[i + j]
            next_clean = next_line.strip()
            if not next_clean:
                i += j + 1
                continue
            next_stripped, next_marker = get_stripped_and_marker(next_clean)
            if next_marker != paragraph_marker:
                break
            paragraph_stripped += " " + next_stripped
            i += j + 1
            clean_stripped = paragraph_stripped.strip()
            is_truncated = not clean_stripped.endswith(valid_endings)

        if paragraph_marker:
            joined = paragraph_marker + paragraph_stripped.strip() + paragraph_marker
        else:
            joined = paragraph_stripped.strip()
        rejoined_lines.append(leading + joined)

    return "\n".join(rejoined_lines)


def apply_post_processing(markdown_content):
    """
    Applies a series of post-processing functions to the markdown content.
    """
    post_processors = [
        remove_line_wraps,
    ]
    for processor in post_processors:
        markdown_content = processor(markdown_content)
    return markdown_content


def convert_pdf_to_markdown(pdf_path):
    """
    Converts a single PDF file to a Markdown file.
    Returns True on success, False on failure.
    """
    if not pdf_path.lower().endswith(".pdf"):
        print(f"- Skipping non-PDF file: {pdf_path}")
        return False

    if not os.path.isfile(pdf_path):
        print(f"- Error: File not found at '{pdf_path}'")
        return False

    print(f"- Converting '{pdf_path}'...")
    try:
        doc = fitz.open(pdf_path)
        html_content = ""
        for page in doc:
            html_content += page.get_text("html")
        doc.close()

        # Create artifacts directory
        base_name = os.path.splitext(pdf_path)[0]
        artifacts_dir = base_name + "_artifacts"
        os.makedirs(artifacts_dir, exist_ok=True)

        # Parse HTML and extract images
        soup = BeautifulSoup(html_content, "lxml")
        image_count = 0
        for img in soup.find_all("img"):
            src = img.get("src")
            if src and src.startswith("data:image/"):
                # Extract format and base64 data
                format_part, base64_data = src.split(";base64,", 1)
                ext = format_part.split("/")[-1]  # png, jpeg, etc.
                image_data = base64.b64decode(base64_data)
                image_filename = f"image_{image_count:03d}.{ext}"
                image_path = os.path.join(artifacts_dir, image_filename)
                with open(image_path, "wb") as f:
                    f.write(image_data)
                # Replace src with relative path
                relative_path = os.path.join(
                    os.path.basename(artifacts_dir), image_filename
                )
                img["src"] = relative_path
                image_count += 1

        # Get modified HTML
        modified_html = str(soup)
        markdown_content = md(
            modified_html,
            heading_style="ATX",
            bullets="-",
            strong_em_symbol="**",
            em_symbol="_",
            wrap=False,
            table_infer_header=True,
        )

        markdown_content = apply_post_processing(markdown_content)

        output_filename = os.path.splitext(pdf_path)[0] + ".md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"  Successfully converted to '{output_filename}'")
        return True

    except Exception as e:
        print(f"  An error occurred while converting {pdf_path}: {e}")
        return False


def process_path(path):
    """
    Processes a given path, which can be a file or a directory.
    """
    if not os.path.exists(path):
        print(f"Error: Path does not exist: '{path}'")
        return

    if os.path.isfile(path):
        print(f"Processing file: {path}")
        convert_pdf_to_markdown(path)

    elif os.path.isdir(path):
        print(f"Processing directory: {path}")
        # Check if any PDFs exist before proceeding
        pdf_files = [f for f in os.listdir(path) if f.lower().endswith(".pdf")]
        if not pdf_files:
            print("  No PDF files found in this directory.")
            return

        for filename in sorted(pdf_files):
            file_path = os.path.join(path, filename)
            convert_pdf_to_markdown(file_path)
    else:
        print(f"Skipping '{path}' as it is not a regular file or directory.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pdf_to_markdown.py <path1> [path2] ...")
        print("  <path> can be a PDF file or a directory containing PDF files.")
        sys.exit(1)

    # Get all paths from command line arguments
    input_paths = sys.argv[1:]

    print("Starting PDF to Markdown conversion...")
    for path in input_paths:
        process_path(path)

    print("\nAll tasks finished.")
