import pytest
from pathlib import Path

from extract_toc import get_toc, Page, Text


PDF_PATH = Path(__file__).parent / "lee-frumer-thesis-fibromyalgia.pdf"


@pytest.fixture(scope="session")
def inferred_toc():
    if not PDF_PATH.is_file():
        pytest.fail(f"Test PDF not found at: {PDF_PATH}")
    return get_toc(PDF_PATH)


def _startswith_match(entry_text: str, expected_prefix: str) -> bool:
    return entry_text.strip().lower().startswith(expected_prefix.strip().lower())


def test_h1_group_therapy_present(inferred_toc):
    expected_prefix = "Group therapy for fibromyalgia"
    expected_page = 1
    assert any(
        _startswith_match(title, expected_prefix) and page == expected_page
        for _level, title, page in inferred_toc
    ), f"Expected H1 starting with '{expected_prefix}' on page {expected_page} is missing from TOC"


# Subset of true positives from the explicit TOC page. Matching is prefix-based
# because some PDFs split long lines into multiple spans.
EXPECTED_TOC: list[tuple[Text, Page]] = [
    ("Abstract", 8),
    ("Introduction", 12),
    ("1. Fibromyalgia", 13),
    ("2. Stress, Stress-Related Medical Conditions, and Psychological Interventions", 14),
    ("2.1. Stress and Rheumatic Diseases", 14),
    ("2.2. Stress and Chronic Pain Conditions", 15),
    ("3. Cognitive Behavioral Therapy", 16),
    ("3.1 CBT Studies among FM Patients", 18),
    ("4. Mindfulness", 20),
    ("4.1 Mindfulness-Based Stress Reduction (MBSR)", 21),
    ("4.2 MBSR Studies among FM Patients", 22),
    ("5. Comparison between CBT and MBSR for FM", 23),
    ("6. Internet Based Psychological Therapy for FM", 24),
    ("7. Adapting Generic Treatment Protocols for FM Patients", 26),
    ("8. Mechanisms of Change in FM Psychotherapy", 27),
    ("8.1 Psychological Inflexibility in Pain as a Mechanism of Change", 28),
    ("8.2 Pain Catastrophizing as a Mechanism of Change", 30),
    ("8.3 Emotion regulation as a Mechanism of Change", 31),
    ("Research Questions and Hypotheses", 34),
    ("Materials and Methods", 36),
    ("1. Participants and Procedure", 36),
    ("2. Randomization and Measurement", 40),
    ("3. Treatment protocols", 40),
    ("3.1 MBSR protocol", 40),
    ("3.2 CBT protocol", 41),
    ("4. Measures", 41),
    ("Results", 44),
    ("1. Pre- to Post-treatment Differences Between the CBT, MBSR and WL groups", 44),
    ("2. Long-Term Effectiveness of CBT and MBSR", 49),
    ("2.1 Long-Term Effectiveness of MBSR", 49),
    ("2.2 Long-Term Effectiveness of CBT", 51),
    ("3. Pre to Post-treatment Differences Between face-to-face and online therapy", 51),
    ("3.1 Pre- to Post-treatment Differences Between the MBSR, MBSR ZOOM and WL groups", 52),
    ("3.2 Long-Term Effectiveness of MBSR and MBSR ZOOM", 56),
    ("3.3 Pre- to Post-treatment Differences Between the CBT, CBT ZOOM and WL groups", 59),
    ("3.4 Long-Term Effectiveness of CBT and CBT ZOOM", 62),
    ("4. Potentials Mechanisms of Change", 64),
    ("General Discussion", 69),
    ("1. The Effectiveness of CBT and MBSR for FM Patients", 70),
    ("1.1 The Effectiveness of MBSR for FM Patients", 70),
    ("1.2 The Effectiveness of CBT for FM Patients", 72),
    ("1.3 The Comparison between CBT and MBSR", 72),
    ("2. Differences Between Face-to-Face and Online Therapy", 74),
    ("3. Potentials Mechanisms of Change in MBSR and CBT", 78),
    ("1.1 The Relationship between Potential Therapeutic Mechanisms Outcome Measures", 79),
    ("1.2 Potential Therapeutic Mechanisms in MBSR", 79),
    ("1.3 Potential Therapeutic Mechanisms in CBT", 82),
    ("Importance and Contribution of the Study, Limitations, and Future Directions", 86),
    ("References", 89),
    ("Appendix", 111),
]


@pytest.mark.parametrize("title, page", EXPECTED_TOC)
def test_toc_headings_present(inferred_toc, title: Text, page: Page):
    assert any(
        _startswith_match(entry_title, title) and entry_page == page
        for _level, entry_title, entry_page in inferred_toc
    ), f"Expected heading starting with '{title}' on page {page} is missing from TOC"


