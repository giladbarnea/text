#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF python3
import fitz  # PyMuPDF
import os
import re
import sys
import extract_toc

# --- Helper Functions ---
def sanitize_filename(name):
    """Sanitizes a string to be a valid filename."""
    name = name.lower()
    name = re.sub(r'[\s\W-]+', '-', name).strip('-')
    return name

# --- Main Extraction Logic ---
def extract_chapters_individually(doc, toc, output_dir):
    """Extracts each top-level chapter into its own PDF file."""
    print("Extracting chapters individually...")
    top_level_chapters = [item for item in toc if item[0] == 1]

    for i, chapter in enumerate(top_level_chapters):
        level, title, start_page = chapter

        # Find the end page
        if i + 1 < len(top_level_chapters):
            end_page = top_level_chapters[i + 1][2] - 1
        else:
            end_page = doc.page_count

        # Create a new PDF for the chapter
        chapter_doc = fitz.open()  # New empty PDF
        chapter_doc.insert_pdf(doc, from_page=start_page - 1, to_page=end_page - 1)

        # Save the chapter
        filename = f"{i + 1:02d}-{sanitize_filename(title)}.pdf"
        output_path = os.path.join(output_dir, filename)
        chapter_doc.save(output_path)
        chapter_doc.close()

        print(f"  - Extracted '{title}' to '{output_path}'")

def extract_chapters_in_batches(doc, toc, batch_size, output_dir):
    """Extracts chapters in batches of a specified page size."""
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
        chapter_details.append({'title': title, 'start': start_page, 'end': end_page, 'count': page_count})

    # Second pass: Create batches
    current_batch_start_page = -1
    current_batch_end_page = -1
    current_batch_start_title = ""

    for i, details in enumerate(chapter_details):
        if not current_batch_chapters:
            current_batch_start_page = details['start']
            current_batch_start_title = details['title']

        if current_batch_pages + details['count'] > batch_size and current_batch_chapters:
            # Finalize and save the current batch
            batch_doc = fitz.open()
            batch_doc.insert_pdf(doc, from_page=current_batch_start_page - 1, to_page=current_batch_end_page - 1)
            filename = f"batch-{len(batches) + 1:02d}-{sanitize_filename(current_batch_start_title)}-to-{sanitize_filename(current_batch_last_title)}.pdf"
            output_path = os.path.join(output_dir, filename)
            batch_doc.save(output_path)
            batch_doc.close()
            print(f"  - Extracted batch to '{output_path}'")
            batches.append(current_batch_chapters)
            
            # Start a new batch
            current_batch_chapters = []
            current_batch_pages = 0
            current_batch_start_page = details['start']
            current_batch_start_title = details['title']

        current_batch_chapters.append(details['title'])
        current_batch_pages += details['count']
        current_batch_end_page = details['end']
        current_batch_last_title = details['title']

    # Save the last remaining batch
    if current_batch_chapters:
        batch_doc = fitz.open()
        batch_doc.insert_pdf(doc, from_page=current_batch_start_page - 1, to_page=current_batch_end_page - 1)
        filename = f"batch-{len(batches) + 1:02d}-{sanitize_filename(current_batch_start_title)}-to-{sanitize_filename(current_batch_last_title)}.pdf"
        output_path = os.path.join(output_dir, filename)
        batch_doc.save(output_path)
        batch_doc.close()
        print(f"  - Extracted batch to '{output_path}'")

# --- Main Script ---
if __name__ == "__main__":
    # --- Argument Parsing ---
    if len(sys.argv) not in [2, 4]:
        print("Usage:")
        print("  python extract_chapters.py <path_to_pdf>")
        print("  python extract_chapters.py batch <size> <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[-1]

    if not os.path.isfile(pdf_path):
        print(f"Error: File not found at '{pdf_path}'")
        sys.exit(1)

    # --- Output Directory Setup ---
    base_name = os.path.basename(pdf_path)
    dir_name = os.path.splitext(base_name)[0]
    output_dir = os.path.join(os.path.dirname(pdf_path), f"{dir_name}_chapters")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # --- PDF Processing ---
    try:
        doc = fitz.open(pdf_path)
        toc = extract_toc.get_toc(pdf_path)

        if not toc:
            print("No table of contents found or could be inferred in this PDF.")
            sys.exit(1)

        # --- Mode Execution ---
        if len(sys.argv) == 4:
            if sys.argv[1].lower() == 'batch' and sys.argv[2].isdigit():
                batch_size = int(sys.argv[2])
                extract_chapters_in_batches(doc, toc, batch_size, output_dir)
            else:
                print("Invalid arguments for batch mode.")
                print("Usage: python extract_chapters.py batch <size> <path_to_pdf>")
                sys.exit(1)
        else:
            extract_chapters_individually(doc, toc, output_dir)

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

    print("Done.")
