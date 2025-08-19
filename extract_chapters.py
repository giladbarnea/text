#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF python3
import fitz  # PyMuPDF
import re
import sys
from pathlib import Path
import extract_toc


# --- Helper Functions ---
def sanitize_filename(name):
    """Sanitizes a string to be a valid filename."""
    name = name.lower()
    name = re.sub(r"[\s\W-]+", "-", name).strip("-")
    return name


# --- Main Extraction Logic ---
def extract_chapters_individually(doc, toc, output_dir, *, no_clobber=False):
    """Extracts each top-level chapter into its own PDF file."""
    print("Extracting chapters individually...")
    top_level_chapters = [item for item in toc if item[0] == 1]

    for i, chapter in enumerate(top_level_chapters):
        level, title, start_page = chapter
        filename = f"{i + 1:02d}-{sanitize_filename(title)}.pdf"
        output_dir_path = Path(output_dir)
        output_path = output_dir_path / filename
        if no_clobber and output_path.exists():
            print(f"  - Skipping '{title}' because it already exists")
            continue

        # Find the end page
        if i + 1 < len(top_level_chapters):
            end_page = top_level_chapters[i + 1][2] - 1
        else:
            end_page = doc.page_count

        # Create a new PDF for the chapter
        chapter_doc = fitz.open()  # New empty PDF
        chapter_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)

        # Save the chapter
        chapter_doc.save(str(output_path))
        chapter_doc.close()

        print(f"  - Extracted '{title}' to '{output_path}'")


def extract_chapters_in_batches(doc, toc, batch_size, output_dir):
    """Extracts chapters in batches of a specified page size.
    Note: this function has never been tried and probably doesn't work."""
    print(f"Extracting chapters in batches of {batch_size} pages...")
    top_level_chapters = [item for item in toc if item[0] == 1]

    batches = []
    current_batch_chapters = []
    current_batch_pages = 0
    chapter_details = []

    # First pass: Get details for all chapters
    for i, chapter in enumerate(top_level_chapters):
        level, title, start_page = chapter
        if i + 1 < len(top_level_chapters):
            end_page = top_level_chapters[i + 1][2] - 1
        else:
            end_page = doc.page_count
        page_count = end_page - start_page + 1
        chapter_details.append(
            {
                "title": title,
                "start": start_page,
                "end": end_page,
                "count": page_count,
            }
        )

    # Second pass: Create batches
    current_batch_start_page = -1
    current_batch_end_page = -1
    current_batch_start_title = ""
    current_batch_last_title = ""

    for i, details in enumerate(chapter_details):
        if not current_batch_chapters:
            current_batch_start_page = details["start"]
            current_batch_start_title = details["title"]

        if (
            current_batch_pages + details["count"] > batch_size
            and current_batch_chapters
        ):
            # Finalize and save the current batch
            batch_doc = fitz.open()
            batch_doc.insert_pdf(
                doc,
                from_page=current_batch_start_page - 1,
                to_page=current_batch_end_page - 1,
            )
            filename = f"batch-{len(batches) + 1:02d}-{sanitize_filename(current_batch_start_title)}-to-{sanitize_filename(current_batch_last_title)}.pdf"
            output_dir_path = Path(output_dir)
            output_path = output_dir_path / filename
            batch_doc.save(str(output_path))
            batch_doc.close()
            print(f"  - Extracted batch to '{output_path}'")
            batches.append(current_batch_chapters)

            # Start a new batch
            current_batch_chapters = []
            current_batch_pages = 0
            current_batch_start_page = details["start"]
            current_batch_start_title = details["title"]

        current_batch_chapters.append(details["title"])
        current_batch_pages += details["count"]
        current_batch_end_page = details["end"]
        current_batch_last_title = details["title"]

    # Save the last remaining batch
    if current_batch_chapters:
        batch_doc = fitz.open()
        batch_doc.insert_pdf(
            doc,
            from_page=current_batch_start_page - 1,
            to_page=current_batch_end_page - 1,
        )
        filename = f"batch-{len(batches) + 1:02d}-{sanitize_filename(current_batch_start_title)}-to-{sanitize_filename(current_batch_last_title)}.pdf"
        output_dir_path = Path(output_dir)
        output_path = output_dir_path / filename
        batch_doc.save(str(output_path))
        batch_doc.close()
        print(f"  - Extracted batch to '{output_path}'")


# --- Main Script ---
if __name__ == "__main__":
    import argparse

    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Extract chapters from PDF")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        metavar="N",
        default=None,
        help="If set, extract in batches of N pages (default is individual mode)",
    )
    parser.add_argument(
        "--no-clobber",
        action="store_true",
        help="Skip files that already exist (individual mode only)",
    )

    args = parser.parse_args()

    # Determine mode and pdf_path
    if args.pdf_path is None:
        parser.print_help()
        sys.exit(1)

    pdf_path = args.pdf_path
    if not Path(pdf_path).is_file():
        print(f"Error: File not found at '{pdf_path}'", file=sys.stderr)
        sys.exit(1)
    mode = "batch" if args.batch_size else "individual"

    # --- Output Directory Setup ---
    pdf_path_p = Path(pdf_path)
    base_name = pdf_path_p.name
    dir_name = pdf_path_p.stem
    output_dir = pdf_path_p.parent / f"{dir_name}_chapters"

    if not output_dir.exists():
        output_dir.mkdir()
        print(f"Created output directory: {output_dir} (did not exist)")

    # --- PDF Processing ---
    try:
        doc = fitz.open(str(pdf_path_p))
        toc = extract_toc.get_toc(str(pdf_path_p))
        if toc:
            print("Extracted TOC")
        else:
            print(
                "No table of contents found or could be inferred in this PDF.",
                file=sys.stderr,
            )
            sys.exit(1)

        # --- Mode Execution ---
        if mode == "batch":
            extract_chapters_in_batches(doc, toc, args.batch_size, output_dir)
        else:
            extract_chapters_individually(
                doc, toc, output_dir, no_clobber=args.no_clobber
            )

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)

    print("Done.")
