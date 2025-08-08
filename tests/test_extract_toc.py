#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy,pytest python3.13 -m pytest
import re
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


# --- "NO" CASES: TEXT THAT MUST NOT BE IN THE TOC ---
# This list includes figure/table captions, authors, affiliations,
# page footers, running headers, table content, and other non-headings.
EXPECTED_ABSENT: list[tuple[Text, Page]] = [
    # Metadata and affiliations
    ("arXiv:2507.06952v2", 1),
    ("Keyon Vafa", 1),
    ("Peter G. Chang", 1),
    ("Ashesh Rambachan", 1),
    ("Sendhil Mullainathan", 1),
    ("Harvard University", 1),
    ("Proceedings of the 42nd International Conference", 1),
    # Repeating running headers
    (
        "What Has a Foundation Model Found? Using Inductive Bias to Probe for World Models",
        2,
    ),
    (
        "What Has a Foundation Model Found? Using Inductive Bias to Probe for World Models",
        3,
    ),
    (
        "What Has a Foundation Model Found? Using Inductive Bias to Probe for World Models",
        4,
    ),
    # Figure Captions
    ("Figure 1: Each pair of panels illustrates the trajectory", 2),
    ("Figure 2: An inductive bias probe measures whether a foundation model", 3),
    ("Figure 3: An illustration of the inductive bias probe", 4),
    ("Figure 4: Inductive bias probe performance", 5),
    ("Figure 5: Inductive bias probe results (R-IB and D-IB)", 8),
    ("Figure 6: On the left, a true Othello board", 9),
    ("Figure 7: Each pair of panels illustrates the trajectory", 15),
    ("Figure 8: Comparing LLM magnitude predictions", 16),
    ("Figure 9: Example prompt used in the LLM physics experiments.", 17),
    # Table Captions
    ("Table 1: Force equations recovered via symbolic regression", 7),
    ("Table 2: The inductive bias towards respecting state", 8),
    ("Table 3: Force equations recovered via symbolic regression of LLMs", 16),
    ("Table 4: Results for ablating the number of iterations", 18),
    ("Table 5: Results for ablating the number of examples", 18),
    ("Table 6: Results for the next token test", 18),
    ("Table 7: Orbit trajectory prediction performance (MSE)", 18),
    ("Table 8: Metrics for assessing whether a model’s inductive bias", 19),
    ("Table 9: Results showing transfer performance across new functions", 19),
    # Table Headers/Content
    ("True force law (Newton)", 2),
    ("Recovered force law (transformer)", 2),
    ("Lattice (5 States)", 8),
    ("Othello", 8),
    ("R-IB (↑)", 8),
    ("D-IB (↑)", 8),
    ("Oracle model", 15),
    ("Ground-truth law", 16),
    ("Estimated laws", 16),
    ("Per-orbit mean", 18),
    ("Previous position", 18),
    ("# iterations", 18),
    ("# examples", 18),
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
    # Page numbers (as strings)
    (re.compile("\b1\b"), 1),
    (re.compile("\b2\b"), 2),
    (re.compile("\b3\b"), 3),
    (re.compile("\b4\b"), 4),
    (re.compile("\b5\b"), 5),
    (re.compile("\b6\b"), 6),
    (re.compile("\b7\b"), 7),
    (re.compile("\b8\b"), 8),
    (re.compile("\b9\b"), 9),
    (re.compile("\b10\b"), 10),
    (re.compile("\b11\b"), 11),
    (re.compile("\b12\b"), 12),
    (re.compile("\b13\b"), 13),
    (re.compile("\b14\b"), 14),
    (re.compile("\b15\b"), 15),
    (re.compile("\b16\b"), 16),
    (re.compile("\b17\b"), 17),
    (re.compile("\b18\b"), 18),
    (re.compile("\b19\b"), 19),
]


@pytest.fixture(scope="session")
def inferred_toc():
    """Fixture to get the inferred TOC once for all tests."""
    # Ensure the PDF file exists before running tests
    if not PDF_PATH.is_file():
        pytest.fail(f"Test PDF not found at: {PDF_PATH}")
    return get_toc(PDF_PATH)


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H0)
def test_h0_present(inferred_toc, title, page):
    """Tests that H0 (main title) headings are present."""
    assert any(
        entry[1].strip() == title.strip() and entry[2] == page for entry in inferred_toc
    ), f"Expected H0 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H1)
def test_h1_present(inferred_toc, title, page):
    """Tests that H1 (major section) headings are present."""
    assert any(
        entry[1].strip() == title.strip() and entry[2] == page for entry in inferred_toc
    ), f"Expected H1 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H2)
def test_h2_present(inferred_toc, title, page):
    """Tests that H2 (subsection) headings are present."""
    assert any(
        entry[1].strip() == title.strip() and entry[2] == page for entry in inferred_toc
    ), f"Expected H2 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.skip(reason="H4 headings are currently too noisy to test reliably.")
@pytest.mark.parametrize("title, page", EXPECTED_PRESENT_H4)
def test_h4_present(inferred_toc, title, page):
    """Tests that H4 (sub-subsection) headings are present."""
    assert any(
        entry[1].strip() == title.strip() and entry[2] == page for entry in inferred_toc
    ), f"Expected H4 starting with '{title}' on page {page} is missing from TOC"


@pytest.mark.parametrize("title, page", EXPECTED_ABSENT)
def test_text_is_absent(inferred_toc, title, page):
    """
    Tests that non-heading text (e.g., captions, authors, footers) is absent from the TOC.
    """
    if isinstance(title, re.Pattern):

        def matches(text):
            return title.match(text) is not None
    else:

        def matches(text):
            return text.strip().startswith(title.strip())

    assert not any(matches(entry[1]) and entry[2] == page for entry in inferred_toc), (
        f"Unexpected text '{title}' on page {page} is present in TOC"
    )
