import logging
import re
from pathlib import Path

import pytest

from extract_toc import Page, Text, get_toc

logger = logging.getLogger(__name__)


PDF_PATH = Path(__file__).parent / "lee-frumer-thesis-fibromyalgia.pdf"


@pytest.fixture(scope="session")
def inferred_toc():
    if not PDF_PATH.is_file():
        pytest.fail(f"Test PDF not found at: {PDF_PATH}")
    return get_toc(PDF_PATH)


def _matches(
    entry_text: str, expected_string: str, lenient_match: re.Pattern | None
) -> bool:
    matches_exactly: bool = (
        entry_text.strip().lower().startswith(expected_string.strip().lower())
    )
    if matches_exactly:
        return True
    if lenient_match is None:
        return False
    matches_lenient: bool = lenient_match.match(entry_text) is not None
    if matches_lenient:
        logger.warning(
            f"Title '{entry_text}' matches leniently but not exactly as '{expected_string}'"
        )
    return matches_lenient


def test_h1_group_therapy_present(inferred_toc):
    expected_prefix = "Group therapy for fibromyalgia"
    expected_page = 1
    assert any(
        _matches(title, expected_prefix, None) and page == expected_page
        for _level, title, page in inferred_toc
    ), (
        f"Expected H1 starting with '{expected_prefix}' on page {expected_page} is missing from TOC"
    )


# Subset of true positives from the explicit TOC page.
# Each tuple is (exact match, lenient match because this is WIP and we want to know if we're making progress, page number)
EXPECTED_TOC: list[tuple[Text, re.Pattern | None, Page]] = [
    ("Abstract", None, 8),
    ("Introduction", None, 12),
    ("1. Fibromyalgia", re.compile(r"^(1\. )?Fibromyalgia"), 13),
    (
        "2. Stress, Stress-Related Medical Conditions, and Psychological Interventions",
        re.compile(r"^(2\. )?Stress, Stress-Related Medical Conditions"),
        14,
    ),
    (
        "2.1. Stress and Rheumatic Diseases",
        re.compile(r"^(2\.1\. )?Stress and Rheumatic Diseases"),
        14,
    ),
    (
        "2.2. Stress and Chronic Pain Conditions",
        re.compile(r"^(2\.2\. )?Stress and Chronic Pain Conditions"),
        15,
    ),
    (
        "3. Cognitive Behavioral Therapy",
        re.compile(r"^(3\. )?Cognitive Behavioral Therapy"),
        16,
    ),
    (
        "3.1. CBT Studies among FM Patients",
        re.compile(r"^(3\.1 )?CBT Studies among FM Patients"),
        18,
    ),
    ("4. Mindfulness", re.compile(r"^(4\. )?Mindfulness"), 20),
    (
        "4.1. Mindfulness-Based Stress Reduction (MBSR)",
        re.compile(r"^(4\.1 )?Mindfulness-Based Stress Reduction (MBSR)"),
        21,
    ),
    (
        "4.2. MBSR Studies among FM Patients",
        re.compile(r"^(4\.2 )?MBSR Studies among FM Patients"),
        22,
    ),
    (
        "5. Comparison between CBT and MBSR for FM",
        re.compile(r"^(5\. )?Comparison between CBT and MBSR for FM"),
        23,
    ),
    (
        "6. Internet Based Psychological Therapy for FM",
        re.compile(r"^(6\. )?Internet Based Psychological Therapy for FM"),
        24,
    ),
    (
        "7. Adapting Generic Treatment Protocols for FM Patients",
        re.compile(r"^(7\. )?Adapting Generic Treatment Protocols for FM Patients"),
        26,
    ),
    (
        "8. Mechanisms of Change in FM Psychotherapy",
        re.compile(r"^(8\. )?Mechanisms of Change in FM Psychotherapy"),
        27,
    ),
    (
        "8.1. Psychological Inflexibility in Pain as a Mechanism of Change",
        re.compile(
            r"^(8\.1 )?Psychological Inflexibility in Pain as a Mechanism of Change"
        ),
        28,
    ),
    (
        "8.2. Pain Catastrophizing as a Mechanism of Change",
        re.compile(r"(8\.2 )?Pain Catastrophizing as a Mechanism of Change"),
        30,
    ),
    (
        "8.3. Emotion regulation as a Mechanism of Change",
        re.compile(r"(8\.3 )?Emotion regulation as a Mechanism of Change"),
        31,
    ),
    ("Research Questions and Hypotheses", None, 34),
    ("Materials and Methods", None, 36),
    (
        "1. Participants and Procedure",
        re.compile(r"^(1\. )?Participants and Procedure"),
        36,
    ),
    (
        "2. Randomization and Measurement",
        re.compile(r"^(2\. )?Randomization and Measurement"),
        40,
    ),
    ("3. Treatment protocols", re.compile(r"^(3\. )?Treatment protocols"), 40),
    ("3.1. MBSR protocol", re.compile(r"^(3\.1 )?MBSR protocol"), 40),
    ("3.2. CBT protocol", re.compile(r"^(3\.2 )?CBT protocol"), 41),
    ("4. Measures", re.compile(r"^(4\. )?Measures"), 41),
    ("Results", None, 44),
    (
        "1. Pre- to Post-treatment Differences Between the CBT, MBSR and WL groups",
        re.compile(r"^(1\. )?Pre- to Post-treatment Differences Between the CBT"),
        44,
    ),
    (
        "2. Long-Term Effectiveness of CBT and MBSR",
        re.compile(r"^(2\. )?Long-Term Effectiveness of CBT and MBSR"),
        49,
    ),
    (
        "2.1. Long-Term Effectiveness of MBSR",
        re.compile(r"^(2\.1 )?Long-Term Effectiveness of MBSR"),
        49,
    ),
    (
        "2.2. Long-Term Effectiveness of CBT",
        re.compile(r"^(2\.2 )?Long-Term Effectiveness of CBT"),
        51,
    ),
    (
        "3. Pre to Post-treatment Differences Between face-to-face and online therapy",
        re.compile(
            r"^(3\. )?Pre to Post-treatment Differences Between face-to-face and online therapy"
        ),
        51,
    ),
    (
        "3.1. Pre- to Post-treatment Differences Between the MBSR, MBSR ZOOM and WL groups",
        re.compile(r"^(3\.1 )?Pre- to Post-treatment Differences Between the MBSR"),
        52,
    ),
    (
        "3.2. Long-Term Effectiveness of MBSR and MBSR ZOOM",
        re.compile(r"^(3\.2 )?Long-Term Effectiveness of MBSR and MBSR ZOOM"),
        56,
    ),
    (
        "3.3. Pre- to Post-treatment Differences Between the CBT, CBT ZOOM and WL groups",
        re.compile(r"^(3\.3 )?Pre- to Post-treatment Differences Between the CBT"),
        59,
    ),
    (
        "3.4. Long-Term Effectiveness of CBT and CBT ZOOM",
        re.compile(r"^(3\.4 )?Long-Term Effectiveness of CBT and CBT ZOOM"),
        62,
    ),
    (
        "4. Potentials Mechanisms of Change",
        re.compile(r"^(4\. )?Potentials Mechanisms of Change"),
        64,
    ),
    ("General Discussion", None, 69),
    (
        "1. The Effectiveness of CBT and MBSR for FM Patients",
        re.compile(r"^(1\. )?The Effectiveness of CBT and MBSR for FM Patients"),
        70,
    ),
    (
        "1.1. The Effectiveness of MBSR for FM Patients",
        re.compile(r"^(1\.1 )?The Effectiveness of MBSR for FM Patients"),
        70,
    ),
    (
        "1.2. The Effectiveness of CBT for FM Patients",
        re.compile(r"^(1\.2 )?The Effectiveness of CBT for FM Patients"),
        72,
    ),
    (
        "1.3. The Comparison between CBT and MBSR",
        re.compile(r"^(1\.3 )?The Comparison between CBT and MBSR"),
        72,
    ),
    (
        "2. Differences Between Face-to-Face and Online Therapy",
        re.compile(r"^(2\. )?Differences Between Face-to-Face and Online Therapy"),
        74,
    ),
    (
        "3. Potentials Mechanisms of Change in MBSR and CBT",
        re.compile(r"^(3\. )?Potentials Mechanisms of Change in MBSR and CBT"),
        78,
    ),
    (
        "1.1. The Relationship between Potential Therapeutic Mechanisms Outcome Measures",
        re.compile(r"^(1\.1 )?The Relationship between Potential Therapeutic"),
        79,
    ),
    (
        "1.2. Potential Therapeutic Mechanisms in MBSR",
        re.compile(r"^(1\.2 )?Potential Therapeutic Mechanisms in MBSR"),
        79,
    ),
    (
        "1.3. Potential Therapeutic Mechanisms in CBT",
        re.compile(r"^(1\.3 )?Potential Therapeutic Mechanisms in CBT"),
        82,
    ),
    (
        "Importance and Contribution of the Study, Limitations, and Future Directions",
        None,
        86,
    ),
    ("References", None, 89),
    ("Appendix", None, 111),
]


@pytest.mark.parametrize("title, lenient_match, page", EXPECTED_TOC)
def test_toc_headings_present(
    inferred_toc, title: Text, lenient_match: re.Pattern | None, page: Page
):
    assert any(
        _matches(entry_title, title, lenient_match) and entry_page == page
        for _level, entry_title, entry_page in inferred_toc
    ), f"Expected heading matching '{title}' on page {page} is missing from TOC"
