#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy,pytest python3.13 -m pytest
from pathlib import Path
import pytest

# Assuming the parser script is named 'parser.py' and is importable;
# adjust the import if needed (e.g., from .parser import get_toc)
from extract_toc import get_toc, Page, Text

# Hardcode the PDF path for testing; replace with the actual path to your test PDF
PDF_PATH = Path(__file__).parent / "what-foundational-models-found.pdf"

# Lists based on original labeled data
# "yes" cases: true headings that MUST be present in the inferred TOC
EXPECTED_PRESENT: list[tuple[Text, Page]] = [
    ("What Has a Foundatio", 1),
    ("Using Inductive Bias", 1),
    ("Abstract", 1),
    ("1. Introduction", 1),
    ("2. Framework", 2),
    ("Data and tasks.", 2),
    ("Foundation models:", 2),
    ("World model:", 2),
    ("2.1. Comparing found", 2),
    ("2.2. Special case: f", 3),
    ("2.3. Inductive bias ", 4),
    ("Extrapolative predic", 5),
    ("Oracle foundation mo", 5),
    ("Inductive bias towar", 5),
    ("3. Orbital Mechanics", 5),
    ("Background.", 5),
    ("Data and pre-trainin", 6),
    ("Has the model recove", 6),
    ("4. Other Application", 7),
    ("Lattice.", 7),
    ("Othello.", 7),
    ("Models.", 7),
    ("Inductive bias probe", 8),
    ("What are the inducti", 8),
    ("5. Related Work", 9),
    ("6. Conclusion", 10),
    ("Acknowledgments", 10),
    ("References", 10),
    ("A. Model and Trainin", 13),
    ("B. Metric Implementa", 13),
    ("B.1. Physics", 13),
    ("B.2. Lattice and Oth", 13),
    ("C. Force Prediction ", 14),
    ("Force vector predict", 14),
    ("Force magnitude pred", 14),
    ("D. LLM Physics Exper", 15),
    ("LLM Prompt", 17),
    ("E. Inductive Bias Ab", 17),
    ("F. Additional Transf", 17),
    ("G. Next Token Perfor", 17),
    ("H. What are models u", 19),
]

# "no" + "kinda" cases: false positives that MUST NOT be present in the inferred TOC
EXPECTED_ABSENT: list[tuple[Text, Page]] = [
    ("Keyon Vafa", 1),
    ("Peter G. Chang", 1),
    ("Ashesh Rambachan", 1),
    ("Sendhil Mullainathan", 1),
    ("World model:", 3),
    ("Inductive bias probe", 3),
    ("Foundation model:", 3),
    ("Example: Finite stat", 4),
    ("Ground-truth law", 7),
    ("Estimated laws", 7),
    ("Lattice (5 States)", 8),
    ("Othello", 8),
    ("Oracle model", 15),
    ("oracle model", 15),
    ("Ground-truth law", 16),
    ("Estimated laws", 16),
    ("Per-orbit mean", 18),
    ("Previous position", 18),
    ("04", 18),
    ("14", 18),
    ("07", 18),
    ("11", 18),
    ("75", 18),
    ("56", 18),
    ("Lattice", 19),
    ("Othello", 19),
    ("Majority Tiles", 19),
    ("Board Balance", 19),
    ("Edge Balance", 19),
    ("IB Correlation", 19),
]

@pytest.fixture(scope="session")
def inferred_toc():
    """Fixture to get the inferred TOC once for all tests."""
    toc = get_toc(PDF_PATH)
    return toc

@pytest.mark.parametrize("title, page", EXPECTED_PRESENT)
def test_heading_present(inferred_toc, title, page):
    assert any(entry[1].strip().startswith(title) and entry[2] == page for entry in inferred_toc), f"Expected heading starting with '{title}' on page {page} is missing from TOC"

@pytest.mark.parametrize("title, page", EXPECTED_ABSENT)
def test_heading_absent(inferred_toc, title, page):
    assert not any(entry[1].strip().startswith(title) and entry[2] == page for entry in inferred_toc), f"Unexpected heading starting with '{title}' on page {page} is present in TOC"