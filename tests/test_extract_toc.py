#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy,pytest python3.13 -m pytest
from pathlib import Path

import pytest

# Assuming the parser script is named 'extract_toc.py' and is importable;
# adjust the import if needed.
from extract_toc import Page, Text, get_toc

# Hardcode the PDF path for testing.
PDF_PATH = Path(__file__).parent / "what-foundational-models-found.pdf"


# --- "YES" CASES: TRUE HEADINGS THAT MUST BE IN THE TOC ---

# H0 - Document titles (font size ~14.35)
EXPECTED_PRESENT_H0: list[tuple[Text, Page]] = [
    ("What Has a Foundation Model Found?", 1),
    ("Using Inductive Bias to Probe for World Models", 1),
]

# H1 - Major sections (font size ~11.96)
EXPECTED_PRESENT_H1: list[tuple[Text, Page]] = [
    ("Abstract", 1),
    ("1. Introduction", 1),
    ("2. Framework", 2),
    ("3. Orbital Mechanics", 5),
    ("4. Other Applications", 7),
    ("5. Related Work", 9),
    ("6. Conclusion", 10),
    ("Acknowledgments", 10),
    ("References", 10),
    ("A. Model and Training Details", 13),
    ("B. Metric Implementation Details", 13),
    ("C. Force Prediction Implementation Details", 14),
    ("D. LLM Physics Experiments", 15),
    ("E. Inductive Bias Ablations", 17),
    ("F. Additional Transfer Results", 17),
    ("G. Next Token Performance", 17),
    ("H. What are models using to extrapolate?", 19),
]

# H2 - Subsections (font size ~9.96)
EXPECTED_PRESENT_H2: list[tuple[Text, Page]] = [
    ("2.1. Comparing foundation models to world models", 2),
    ("2.2. Special case: finite state space and binary outputs.", 3),
    ("2.3. Inductive bias probe", 4),
    ("B.1. Physics", 13),
    ("B.2. Lattice and Othello", 13),
    ("LLM Prompt", 17),
]

# H4 - Sub-subsections (font size ~9.9-10.1)
# These are often bolded text within paragraphs.
EXPECTED_PRESENT_H4: list[tuple[Text, Page]] = [
    ("Data and tasks.", 2),
    ("Foundation models:", 2),
    ("World model:", 2),
    ("Extrapolative predictability.", 5),
    ("Oracle foundation model.", 5),
    ("Inductive bias towards the world model.", 5),
    ("Background.", 5),
    ("Data and pre-training.", 6),
    ("Has the model recovered Newtonian mechanics?", 6),
    ("Lattice.", 7),
    ("Othello.", 7),
    ("Models.", 7),
    ("Inductive bias probe results.", 8),
    ("What are the inductive biases?", 8),
    ("Force vector prediction.", 14),
    ("Force magnitude prediction and symbolic regression.", 14),
]

# "no" cases: false positives that MUST NOT be present in the inferred TOC
EXPECTED_ABSENT_HEADINGS: list[tuple[Text, Page]] = [
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

EXPECTED_ABSENT_TABLE_CELLS: list[tuple[Text, Page]] = [
    ("Per-orbit mean", 18),
    ("Previous position", 18),
]


@pytest.fixture(scope="session")
def inferred_toc():
    """Fixture to get the inferred TOC once for all tests."""
    return get_toc(PDF_PATH)


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H0)
def test_h0_present(inferred_toc, title, page):
    assert any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Expected H0 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H1)
def test_h1_present(inferred_toc, title, page):
    assert any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Expected H1 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H2)
def test_h2_present(inferred_toc, title, page):
    assert any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Expected H2 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.skip(reason="H4 is noise for now")
@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H4)
def test_h4_present(inferred_toc, title, page):
    assert any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Expected H4 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_ABSENT_HEADINGS)
def test_heading_absent(inferred_toc, title, page):
    assert not any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Unexpected heading starting with '{title}' on page {page} is present in TOC"


@pytest.mark.parametrize("title, page", EXPECTED_ABSENT_TABLE_CELLS)
def test_table_cell_absent(inferred_toc, title, page):
    assert not any(
        entry[1].strip().startswith(title) and entry[2] == page
        for entry in inferred_toc
    ), f"Unexpected table cell starting with '{title}' on page {page} is present in TOC"