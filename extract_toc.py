#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF python3
import sys
import fitz  # PyMuPDF
import os
import statistics  # For mean calculation

def get_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    if not toc:
        potential_chapters = []
        all_sizes = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if block["type"] == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                size = span["size"]
                                all_sizes.append(size)
                                if len(text.split()) < 10:  # Likely a heading if short
                                    potential_chapters.append((page_num + 1, size, text))
        if all_sizes:
            mean_size = statistics.mean(all_sizes)
            threshold = mean_size * 1.2  # Arbitrary threshold for headings
            # Sort by size descending
            potential_chapters.sort(key=lambda x: -x[1])
            inferred_toc = []
            seen_texts = set()
            for page, size, text in potential_chapters:
                if size > threshold and text not in seen_texts:
                    inferred_toc.append([1, text, page])  # Level 1 for all
                    seen_texts.add(text)
            doc.close()
            return inferred_toc
        else:
            doc.close()
            return []
    doc.close()
    return toc

def main():
    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
    else:
        try:
            doc = fitz.open(pdf_path)
            toc = doc.get_toc()

            pdf_name = os.path.basename(pdf_path)

            if not toc:
                print("No embedded table of contents found. Attempting to infer potential chapters based on font sizes.")
                
                potential_chapters = []
                all_sizes = []

                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    dict_text = page.get_text("dict")
                    for block in dict_text["blocks"]:
                        if block["type"] == 0:  # text block
                            for line in block.get("lines", []):
                                for span in line["spans"]:
                                    text = span["text"].strip()
                                    if text:
                                        size = span["size"]
                                        all_sizes.append(size)
                                        if len(text.split()) < 10:  # Likely a heading if short
                                            potential_chapters.append((page_num + 1, size, text))

                if all_sizes:
                    mean_size = statistics.mean(all_sizes)
                    threshold = mean_size * 1.2  # Arbitrary threshold for headings

                    # Sort by size descending
                    potential_chapters.sort(key=lambda x: -x[1])

                    inferred_toc = []
                    seen_texts = set()
                    for page, size, text in potential_chapters:
                        if size > threshold and text not in seen_texts:
                            inferred_toc.append([1, text, page])  # Level 1 for all
                            seen_texts.add(text)

                    if inferred_toc:
                        print(f"Inferred Table of Contents for '{pdf_name}':")
                        for level, title, page in inferred_toc:
                            print(f"{'  ' * (level - 1)}{title} (Page {page})")
                    else:
                        print("Could not infer any potential chapters.")
                else:
                    print("No text found in the PDF.")
            else:
                print(f"Table of Contents for '{pdf_name}':")
                for level, title, page in toc:
                    print(f"{'  ' * (level - 1)}{title} (Page {page})")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()