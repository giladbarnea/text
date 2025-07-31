#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy,pytest pytest
from pathlib import Path
import pytest

# Assuming the parser script is named 'parser.py' and is importable;
# adjust the import if needed (e.g., from .parser import get_toc)
from extract_toc import get_toc

# Hardcode the PDF path for testing; replace with the actual path to your test PDF
PDF_PATH = Path(__file__).parent / "what-foundational-models-found.pdf"

# Lists based on original labeled data
# "yes" cases: true headings that MUST be present in the inferred TOC
EXPECTED_PRESENT = [
    'What Has a Foundatio',  # doc title
    'Using Inductive Bias',  # doc title
    'Abstract',              # H1
    '1. Introduction',       # H1
    '2. Framework',          # H1
    'Data and tasks.',       # H4
    'Foundation models:',    # H4
    'World model:',          # H4
    '2.1. Comparing found',  # H2
    '2.2. Special case: f',  # H2
    '2.3. Inductive bias ',  # H2
    'Extrapolative predic',  # H4
    'Oracle foundation mo',  # H4
    'Inductive bias towar',  # H4
    '3. Orbital Mechanics',  # H1
    'Background.',           # H4
    'Data and pre-trainin',  # H4
    'Has the model recove',  # H4
    '4. Other Application',  # H1
    'Lattice.',              # H4
    'Othello.',              # H4
    'Models.',               # H4
    'Inductive bias probe',  # H4
    'What are the inducti',  # H4
    '5. Related Work',       # H1
    '6. Conclusion',         # H1
    'Acknowledgments',       # H1
    'References',            # H1
    'A. Model and Trainin',  # H1
    'B. Metric Implementa',  # H1
    'B.1. Physics',          # H2
    'B.2. Lattice and Oth',  # H2
    'C. Force Prediction ',  # H1
    'Force vector predict',  # H4
    'Force magnitude pred',  # H4
    'D. LLM Physics Exper',  # H1
    'E. Inductive Bias Ab',  # H1
    'F. Additional Transf',  # H1
    'G. Next Token Perfor',  # H1
    'H. What are models u',  # H1
]

# "no" + "kinda" cases: false positives that MUST NOT be present in the inferred TOC
EXPECTED_ABSENT = [
    'Keyon Vafa',            # no: author
    'Peter G. Chang',        # no: author
    'Ashesh Rambachan',      # no: author
    'Sendhil Mullainathan',  # no: author
    'Ground-truth law',      # no: table header (appears in multiple places/sizes)
    'Estimated laws',        # no: table header (appears in multiple places/sizes)
    'Lattice (5 States)',    # no: table header
    'Othello',               # no: table header (note: distinct from 'Othello.')
    'Majority Tiles',        # no: table header
    'Board Balance',         # no: table header
    'Edge Balance',          # no: table header
    'IB Correlation',        # no: table header
    'Per-orbit mean',        # no: table header
    'Previous position',     # no: table header
    '04',                    # no: table cell
    '14',                    # no: table cell
    '07',                    # no: table cell
    '11',                    # no: table cell
    '75',                    # no: table cell
    '56',                    # no: table cell
    'Lattice',               # no: table header
    'oracle model',          # no: tricky false positive
    'Inductive bias probe',  # kinda: chart title (bold=0 in original)
    'Example: Finite stat',  # kinda: chart title (bold=0 in original)
    'Oracle model',          # kinda: chart title (bold=0 in original)
    # Add any other "no" or "kinda" from original data if missed
]

@pytest.fixture
def inferred_toc():
    """Fixture to get the inferred TOC once for all tests."""
    toc = get_toc(PDF_PATH)
    # Extract just the titles (text) for simple membership checks
    titles = {entry[1].strip() for entry in toc}
    return titles

@pytest.mark.parametrize("title", EXPECTED_PRESENT)
def test_heading_present(inferred_toc, title):
    assert title in inferred_toc, f"Expected heading '{title}' is missing from TOC"

@pytest.mark.parametrize("title", EXPECTED_ABSENT)
def test_heading_absent(inferred_toc, title):
    assert title not in inferred_toc, f"Unexpected item '{title}' is present in TOC"