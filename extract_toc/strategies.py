from __future__ import annotations

import functools
from .types import Strategy, RawData, AnalysisData, HeadingLevel, Text, Page


def strategy(func: Strategy) -> Strategy:
    """Decorator label for strategies, with light type checking."""

    @functools.wraps(func)
    def wrapper(
        raw_data: RawData, analysis_data: AnalysisData
    ) -> list[tuple[HeadingLevel, Text, Page]]:
        return func(RawData(raw_data), AnalysisData(analysis_data))

    return wrapper


@strategy
def embedded_strategy(
    raw_data: RawData, _: AnalysisData
) -> list[tuple[HeadingLevel, Text, Page]]:
    """Default strategy: use embedded TOC if provided by the PDF."""
    return raw_data.get("embedded_toc", [])


