# type: ignore
import re
from pathlib import Path

import pytest

from extract_toc import Page, Text, get_toc

PDF_PATH = Path(__file__).parent / "03-1-reliable-scalable-and-maintainable-applications.pdf"


# --- "YES" CASES: TRUE HEADINGS THAT MUST BE IN THE TOC ---
EXPECTED_PRESENT_H0: list[tuple[Text, Page]] = [
    ("Chapter 1. Reliable, Scalable, and Maintainable Applications", 1),
]

EXPECTED_PRESENT_H1: list[tuple[Text, Page]] = [
    
]

EXPECTED_PRESENT_H2: list[tuple[Text, Page]] = [
    
]

EXPECTED_PRESENT_H4: list[tuple[Text, Page]] = [
    
]


# --- "NO" CASES: TEXT THAT MUST NOT BE IN THE TOC ---
# This list includes figure/table captions, authors, affiliations,
# page footers, running headers, table content, and other non-headings.
EXPECTED_ABSENT: list[tuple[Text, Page]] = [
    # ("...", 1),
    # Page numbers (as strings)
    # (re.compile("\b1\b"), 1),
    
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
