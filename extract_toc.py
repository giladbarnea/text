import fitz  # PyMuPDF
import os

pdf_path = "/Users/giladbarnea/Documents/psychology-research/rethinking-narcissism-by-dr-craig-malkin.pdf"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
else:
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()

        if not toc:
            print("No table of contents found in this PDF.")
        else:
            print("Table of Contents for 'rethinking-narcissism-by-dr-craig-malkin.pdf':")
            for level, title, page in toc:
                print(f"{ '  ' * (level - 1)}{title} (Page {page})")
    except Exception as e:
        print(f"An error occurred: {e}")
