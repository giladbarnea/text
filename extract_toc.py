#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF python3
import sys
import fitz  # PyMuPDF
import os
import statistics  # For mean calculation

def get_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    if not toc:
        potential_headings = []
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
                                if "a state space" in text:
                                    print(f"Debug: Found normal text on page {page_num + 1}, size {size}, text: '{text}', bold: {(span['flags'] & 16) != 0}")
                                if "2. Framework" in text or "A. Model and Training Details" in text:
                                    print(f"Debug: Found h1 text on page {page_num + 1}, size {size}, text: '{text}', bold: {(span['flags'] & 16) != 0}")
                                if "Data and tasks." in text:
                                    print(f"Debug: Found h3 text on page {page_num + 1}, size {size}, text: '{text}', bold: {(span['flags'] & 16) != 0}")
                                
                                all_sizes.append(size)
                                if len(text.split()) < 10 and len(text) > 1:  # Short, non-empty, likely heading
                                    potential_headings.append((page_num + 1, size, text))
                                    if "Comparing foundation models to world models" in text or "B.1. Physics" in text:
                                        print(f"Debug: Found h2 text on page {page_num + 1}, size {size}, text: '{text}', bold: {(span['flags'] & 16) != 0}")
                                    
        if all_sizes:
            mean_size = statistics.mean(all_sizes)
            median_size = statistics.median(all_sizes)
            threshold = mean_size * 1.2
            print(f"Debug:\n · Mean size: {mean_size}\n · median size: {median_size}\n · threshold: {threshold}\n · {sorted(all_sizes).index(median_size)=}\n · {len(all_sizes)=}")

            # Deduplicate by text and page
            unique_headings = []
            seen = set()
            for page, size, text in potential_headings:
                key = (text, page)
                if key not in seen:
                    seen.add(key)
                    unique_headings.append((page, size, text))

            if unique_headings:
                # Find max size
                max_size = max(h[1] for h in unique_headings)

                # Assign levels
                inferred_toc = []
                for page, size, text in unique_headings:
                    if size > threshold:
                        if size >= max_size * 0.9:
                            level = 1
                        else:
                            level = 2
                        inferred_toc.append([level, text, page])

                # Sort by page number to maintain document order
                inferred_toc.sort(key=lambda x: x[2])

                doc.close()
                return inferred_toc
            else:
                doc.close()
                return []
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
            toc = get_toc(pdf_path)
            pdf_name = os.path.basename(pdf_path)

            if not toc:
                print(f"No table of contents found or could be inferred in '{pdf_name}'.")
            else:
                print(f"Table of Contents for '{pdf_name}' (inferred if no embedded TOC):")
                for level, title, page in toc:
                    print(f"{'  ' * (level - 1)}{title} (Page {page})")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()