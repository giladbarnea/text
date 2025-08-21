from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple, NewType, TypedDict

if TYPE_CHECKING:
    import numpy as np

Text = NewType("Text", str)
Size = NewType("Size", float)
IsBold = NewType("IsBold", bool)
Page = NewType("Page", int)
HeadingLevel = NewType("HeadingLevel", int)


class Span(NamedTuple):
    page: Page
    size: Size
    text: Text
    is_bold: IsBold
    y_pos: float


class RawData(TypedDict):
    embedded_toc: list[tuple[HeadingLevel, Text, Page]]
    all_font_sizes: list[Size]
    spans: list[Span]


class RawStats(TypedDict):
    mean: Size
    median: Size
    some_threshold: Size
    general_heading_threshold: Size
    max_size: Size
    h1_threshold: Size
    frequency: Counter[Size]
    kde_x: "np.ndarray"
    kde_y: "np.ndarray"
    size_percentile_min_threshold: float
    freq_max_threshold: int


class AnalysisData(TypedDict):
    raw_stats: RawStats
    merged_stats: dict[str, dict[Size, int]]
    kde_data: tuple


Strategy = Callable[[RawData, AnalysisData], list[tuple[HeadingLevel, Text, Page]]]


