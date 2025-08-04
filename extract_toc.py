#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy python3.13

# Imports grouped by domain
# Parsing: import fitz  # PyMuPDF
import argparse
import os
import statistics
import functools

# Analysis: from collections import Counter; import statistics; import numpy as np; from scipy.stats import gaussian_kde
from collections import Counter, defaultdict

# Orchestration/Main: import sys; import os; import argparse
from collections.abc import Callable
from typing import TYPE_CHECKING, NamedTuple, NewType, TypedDict

import fitz

if TYPE_CHECKING:
    import numpy as np

Text = NewType("Text", str)
Size = NewType("Size", float)
IsBold = NewType("IsBold", bool)
Page = NewType("Page", int)
HeadingLevel = NewType("HeadingLevel", int)

Span = NamedTuple(
    "Span",
    [
        ("page", Page),
        ("size", Size),
        ("text", Text),
        ("is_bold", IsBold),
        ("y_pos", float),
    ],
)
RawData = TypedDict(
    "RawData",
    {
        "embedded_toc": list[tuple[HeadingLevel, Text, Page]],
        "all_font_sizes": list[Size],
        "spans": list[Span],
    },
)

RawStats = TypedDict(
    "RawStats",
    {
        "mean": Size,
        "median": Size,
        "some_threshold": Size,
        "general_heading_threshold": Size,
        "max_size": Size,
        "h1_threshold": Size,
        "frequency": Counter[Size],
        "kde_x": "np.ndarray",
        "kde_y": "np.ndarray",
        "size_percentile_min_threshold": float,
        "freq_max_threshold": int,
    },
)
AnalysisData = TypedDict(
    "AnalysisData",
    {
        "raw_stats": RawStats,
        "merged_stats": dict[str, dict[Size, int]],
        "kde_data": tuple,
    },
)

Strategy = Callable[[RawData, AnalysisData], list[tuple[HeadingLevel, Text, Page]]]


def strategy(func: Strategy) -> Strategy:
    """Mostly a label to help orient around the script. Does type checking as a bonus."""

    @functools.wraps(func)
    def wrapper(
        raw_data: RawData, analysis_data: AnalysisData
    ) -> list[tuple[HeadingLevel, Text, Page]]:
        return func(RawData(raw_data), AnalysisData(analysis_data))

    return wrapper


# Domain: Document Parsing
def parse_pdf_document(pdf_path: str) -> RawData:
    """
    Extracts the document's text spans and font sizes.
    `embedded_toc` is not empty only if the document has an embedded TOC.
    `spans` is a list of all text spans in the document.
    `all_font_sizes` is a list of sizes of all text spans in the document.
    """
    doc = fitz.open(pdf_path)
    embedded_toc: list[tuple[HeadingLevel, Text, Page]] = doc.get_toc()

    all_font_sizes: list[Size] = []
    spans: list[Span] = []

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        dict_text = page.get_text("dict")
        for block in dict_text["blocks"]:
            if block["type"] == 0:  # text block
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        text: Text = span["text"].strip()
                        if text:
                            size: Size = span["size"]
                            all_font_sizes.append(size)
                            is_bold: IsBold = (span["flags"] & 16) != 0
                            # Deterministic y-coordinate (top-down; lower values = higher on page)
                            y_pos = span["origin"][1]
                            spans.append(
                                Span(
                                    page=Page(page_num + 1),
                                    size=Size(size),
                                    text=Text(text),
                                    is_bold=IsBold(is_bold),
                                    y_pos=y_pos,
                                )
                            )

    doc.close()
    return RawData(
        embedded_toc=embedded_toc,
        all_font_sizes=all_font_sizes,
        spans=spans,
    )


# Domain: Statistical Analysis
class FontStatisticalAnalyzer:
    """
    Analyzes font statistics for TOC inference following a pipeline: raw font metrics computation → derived thresholds → applied heading inference → optional visualization.

    Responsibility boundaries:
    - Raw: Computes basic metrics (mean, median, frequencies, sorted sizes) from font sizes.
    - Derived: Calculates dynamic thresholds (e.g., percentiles, frequency caps) from raw metrics.
    - Applied: Filters and infers headings using raw/derived data.
    - Viz: Generates optional visualizations from computed data.
    """

    deltas: dict[str, Size]

    def __init__(self, deltas: dict[str, Size] = None) -> None:
        if not deltas:
            self.deltas = {"very light": 0.01, "light": 0.1, "moderate": 0.5}
        else:
            self.deltas = deltas

    def analyze(self, sizes: list[Size], visualize: bool = False) -> AnalysisData:
        self.raw_metrics = self._compute_raw_metrics(sizes)
        self.thresholds = self._derive_thresholds()
        merged_stats: dict[str, dict[Size, int]] = self._compute_merged_stats(sizes)
        if visualize:
            self.kde_data = self._compute_viz_data(sizes)
        else:
            self.kde_data = ()
        return AnalysisData(
            raw_stats=RawStats(
                {
                    **self.raw_metrics,
                    **self.thresholds,
                    "sorted_sizes": self.raw_metrics["sorted_sizes"],
                    "all_fonts_count": self.raw_metrics["all_fonts_count"],
                }
            ),
            merged_stats=merged_stats,
            kde_data=self.kde_data,
        )

    def _compute_raw_metrics(self, sizes: list[Size]) -> dict:
        if not sizes:
            return {}
        raw_freq: Counter[Size] = Counter(sizes)
        mean_size: Size = statistics.mean(sizes)
        median_size: Size = statistics.median(sizes)
        max_size: Size = max(sizes)
        h1_threshold: Size = max_size * 0.9
        general_heading_threshold: Size = mean_size
        sorted_sizes = sorted(sizes)  # For percentile calcs
        return {
            "mean": mean_size,
            "median": median_size,
            "max_size": max_size,
            "h1_threshold": h1_threshold,
            "general_heading_threshold": general_heading_threshold,
            "frequency": raw_freq,
            "sorted_sizes": sorted_sizes,
            "all_fonts_count": len(sorted_sizes),
        }

    def _derive_thresholds(self) -> dict:
        freq_values = list(self.raw_metrics["frequency"].values())
        size_percentile_min_threshold = 35.0
        sorted_freq_values = sorted(freq_values)
        freq_95th_percentile = (
            sorted_freq_values[int(0.95 * len(sorted_freq_values))]
            if sorted_freq_values
            else 0
        )
        freq_max_threshold = max(1400, freq_95th_percentile)
        return {
            "size_percentile_min_threshold": size_percentile_min_threshold,
            "freq_max_threshold": freq_max_threshold,
        }

    def _compute_viz_data(self, sizes: list[Size]) -> tuple:
        import numpy as np
        from scipy.stats import gaussian_kde

        sizes_array = np.array(sizes)
        kde = gaussian_kde(sizes_array, bw_method=0.1)
        x_kde = np.linspace(min(sizes), max(sizes), 1000)
        y_kde = kde(x_kde)
        return (x_kde, y_kde)

    def _get_percentile(self, size: Size) -> float:
        import bisect

        sorted_sizes = self.raw_metrics["sorted_sizes"]
        all_fonts_count = self.raw_metrics["all_fonts_count"]
        count_smaller = bisect.bisect_left(sorted_sizes, size)
        return (count_smaller / all_fonts_count) * 100 if all_fonts_count > 0 else 0

    def _infer_headings(
        self, spans: list[Span]
    ) -> list[tuple[HeadingLevel, Text, Page]]:
        if not spans:
            return []

        # Light filtering: bold text under 10 words
        potential_headings = [
            span
            for span in spans
            if len(span.text) > 1 and len(span.text.split()) < 10 and span.is_bold
        ]

        if not potential_headings:
            return []

        # Uniqueness counting
        heading_counts: dict[tuple[Text, Size, IsBold], int] = {}
        for heading in potential_headings:
            key: tuple[Text, Size, IsBold] = (
                heading.text,
                heading.size,
                heading.is_bold,
            )
            heading_counts[key] = heading_counts.get(key, 0) + 1

        unique_headings: list[Span] = [
            heading
            for heading in potential_headings
            if heading_counts[(heading.text, heading.size, heading.is_bold)] == 1
        ]

        if not unique_headings:
            return []
        
        # Filter if >2 in same line/group (tune to 3 if too aggressive)
        MAX_HEADINGS_IN_SAME_GROUP = 2
        Y_ROUNDING = 5.0  # Bucket size for y_pos noise (adjust based on PDF scaling)
        groups = defaultdict(list)
        for h in unique_headings:
            rounded_y = round(h.y_pos / Y_ROUNDING) * Y_ROUNDING
            groups[(h.page, rounded_y)].append(h)

        # Access raw metrics and thresholds
        general_heading_threshold = self.raw_metrics["general_heading_threshold"]
        h1_threshold = self.raw_metrics["h1_threshold"]
        size_percentile_min_threshold = self.thresholds["size_percentile_min_threshold"]
        freq_max_threshold = self.thresholds["freq_max_threshold"]
        font_freq = self.raw_metrics["frequency"]

        # Inference: filter and assign levels
        inferred_toc: list[tuple[HeadingLevel, Text, Page]] = []
        for heading in unique_headings:
            size = heading.size
            is_bold = heading.is_bold
            percentile = self._get_percentile(size)

            rounded_y = round(heading.y_pos / Y_ROUNDING) * Y_ROUNDING
            group = groups[(heading.page, rounded_y)]

            if (
                size < general_heading_threshold
                or not is_bold
                or percentile < size_percentile_min_threshold
                or font_freq.get(size, 0) >= freq_max_threshold
                or len(group) > MAX_HEADINGS_IN_SAME_GROUP
            ):
                continue

            page = heading.page
            text = heading.text
            level = (
                1 if size >= h1_threshold else HeadingLevel(2)
            )  # Assuming H2 for non-H1 headings; refine for more levels if needed

            inferred_toc.append((HeadingLevel(level), text, page))

        # Sort by page
        inferred_toc.sort(key=lambda x: x[2])
        return inferred_toc

    def _compute_merged_stats(self, sizes: list[Size]) -> dict[str, dict[Size, int]]:
        """
        Maps labels to size count.
        Only used for visualization.
        """
        merged_stats: dict[str, dict[Size, int]] = {}
        for label, delta in self.deltas.items():
            merged_freq: dict[Size, int] = self._merge_sizes(sizes, delta)
            merged_stats[label] = merged_freq
        return merged_stats

    @staticmethod
    def _merge_sizes(sizes: list[Size], delta: float) -> dict[Size, int]:
        """
        Merges sizes that are close to each other to (hopefully) reduce noise.
        """
        if not sizes:
            return {}
        sorted_unique: list[Size] = sorted(set(sizes))
        merged: dict[Size, int] = {}
        current_group: list[Size] = [sorted_unique[0]]
        for i in range(1, len(sorted_unique)):
            if sorted_unique[i] - current_group[-1] <= delta:
                current_group.append(sorted_unique[i])
            else:
                group_key: Size = statistics.mean(current_group)
                group_count: int = sum(Counter(sizes)[s] for s in current_group)
                merged[group_key] = group_count
                current_group = [sorted_unique[i]]
        group_key: Size = statistics.mean(current_group)
        group_count: int = sum(Counter(sizes)[s] for s in current_group)
        merged[group_key] = group_count
        return merged

    def font_strategy(self, raw_data: RawData) -> list[tuple[HeadingLevel, Text, Page]]:
        spans: list[Span] = raw_data.get("spans", [])
        if not spans or not raw_data.get("all_font_sizes"):
            return []

        return self._infer_headings(spans)

    def generate_visualizations(
        self, all_font_sizes: list[Size], output_dir: str = "."
    ):
        if not all_font_sizes:
            return []

        raw_stats: RawStats = RawStats(self.raw_metrics)

        # Helper: Create and persist raw histogram with KDE
        def _create_and_save_raw_hist() -> str:
            import numpy as np
            import plotly.graph_objects as go

            sizes_array = np.array(all_font_sizes)
            hist, bin_edges = np.histogram(sizes_array, bins=100)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            customdata = list(zip(bin_edges[:-1], bin_edges[1:]))
            bin_width = bin_edges[1] - bin_edges[0] if len(bin_edges) > 1 else 1

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=bin_centers,
                    y=hist,
                    width=bin_width,
                    marker=dict(
                        color="rgba(0, 123, 255, 0.3)",
                        line=dict(color="rgba(0, 123, 255, 0.5)", width=1),
                    ),
                    name="Histogram",
                    customdata=customdata,
                    hovertemplate="Bin: %{customdata[0]:.3f} - %{customdata[1]:.3f}<br>Frequency: %{y}<extra></extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=self.kde_data[0],
                    y=self.kde_data[1] * len(all_font_sizes) * bin_width,
                    mode="lines",
                    line=dict(color="green", width=2),
                    name="KDE",
                    hovertemplate="KDE 0.1: %{y:.1f}<extra></extra>",
                )
            )

            # Add vlines for mean, median, h1_threshold
            fig.add_vline(
                x=raw_stats["mean"],
                line=dict(color="rgba(0,128,0,0.25)", width=2, dash="dash"),
                annotation_text="Mean",
                annotation_position="top left",
            )
            fig.add_vline(
                x=raw_stats["median"],
                line=dict(color="rgba(255,165,0,0.25)", width=2, dash="dash"),
                annotation_text="Median",
                annotation_position="top center",
            )
            fig.add_vline(
                x=raw_stats["h1_threshold"],
                line=dict(color="rgba(128,0,128,0.25)", width=2, dash="dash"),
                annotation_text="Threshold",
                annotation_position="top right",
            )

            # Add annotations for top frequencies
            sorted_freq = sorted(
                raw_stats["frequency"].items(), key=lambda x: x[1], reverse=True
            )[:5]
            for i, (size, count) in enumerate(sorted_freq):
                fig.add_annotation(
                    x=size,
                    y=count,
                    text=f"Top {i + 1}: {size:.2f} ({count})",
                    showarrow=True,
                    arrowhead=1,
                    yshift=10,
                    font=dict(size=8),
                )

            fig.update_layout(
                title="Interactive Raw Font Size Distribution with KDE",
                xaxis_title="Font Size",
                yaxis_title="Frequency",
                barmode="overlay",
                hovermode="x unified",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            )
            filename = os.path.join(output_dir, "raw_font_size_dist.html")
            fig.write_html(filename)
            print("Saved interactive raw distribution to 'raw_font_size_dist.html'")
            return filename

        # Helper: Create and persist sorted bar chart
        def _create_and_save_sorted_bar() -> str:
            import plotly.graph_objects as go

            unique_sizes: list[Size] = sorted(raw_stats["frequency"].keys())
            counts: list[int] = [raw_stats["frequency"][size] for size in unique_sizes]

            fig = go.Figure(
                go.Scatter(
                    x=unique_sizes,
                    y=counts,
                    mode="markers+lines",
                    marker=dict(color=counts, colorscale="viridis", size=10),
                    line=dict(color="gray"),
                )
            )
            fig.update_layout(
                title="Interactive Frequency of Unique Font Sizes (Sorted)",
                xaxis_title="Font Size",
                yaxis_title="Frequency",
                yaxis_type="log",
            )
            filename = os.path.join(output_dir, "unique_font_size_freq.html")
            fig.write_html(filename)
            print(
                "Saved interactive unique font size frequency to 'unique_font_size_freq.html'"
            )
            return filename

        # Helper: Create and persist merged distributions (one per delta)
        def _create_and_save_merged() -> list[str]:
            import plotly.graph_objects as go

            merged_files: list[str] = []
            for (
                label,
                merged_freq,
            ) in raw_stats.items():  # Changed from data["merged_stats"] to raw_stats
                merged_sizes: list[Size] = sorted(merged_freq.keys())
                merged_counts: list[int] = [merged_freq[size] for size in merged_sizes]

                fig = go.Figure(
                    go.Scatter(
                        x=merged_sizes,
                        y=merged_counts,
                        mode="markers+lines",
                        marker=dict(color=merged_counts, colorscale="rdbu", size=12),
                        line=dict(color="lightgray"),
                    )
                )
                fig.update_layout(
                    title=f"Interactive {label.capitalize()} Merged Font Size Distribution",
                    xaxis_title="Merged Font Size",
                    yaxis_title="Frequency",
                    yaxis_type="log" if label == "very light" else "linear",
                )

                filename = os.path.join(
                    output_dir, f"{label.replace(' ', '_')}_merged_font_size_dist.html"
                )
                fig.write_html(filename)
                print(f"Saved interactive {label} merged distribution to '{filename}'")
                merged_files.append(filename)
            return merged_files

        # Main visualization logic
        saved_files = []
        saved_files.append(_create_and_save_raw_hist())
        saved_files.append(_create_and_save_sorted_bar())
        saved_files.extend(_create_and_save_merged())
        return saved_files

    def infer_toc(
        self, raw_data: RawData, use_embedded: bool = True
    ) -> list[tuple[HeadingLevel, Text, Page]]:
        if use_embedded:
            embedded = embedded_strategy(raw_data, {})
            if embedded:
                return embedded
        return self.font_strategy(raw_data)


# Strategy helpers


@strategy
def embedded_strategy(
    raw_data: RawData, _: AnalysisData
) -> list[tuple[HeadingLevel, Text, Page]]:
    """
    The default strategy: use the embedded TOC if it exists.
    """
    return raw_data.get("embedded_toc", [])


# Orchestrator
def get_toc(
    pdf_path: str, *, visualize: bool = False
) -> list[tuple[HeadingLevel, Text, Page]]:
    raw_data: RawData = parse_pdf_document(pdf_path)
    if embedded_toc := raw_data.get("embedded_toc"):
        return embedded_toc

    analyzer = FontStatisticalAnalyzer()
    analyzer.analyze(raw_data["all_font_sizes"], visualize=visualize)

    if visualize:
        analyzer.generate_visualizations(raw_data["all_font_sizes"])

    return analyzer.infer_toc(raw_data, use_embedded=not visualize)


# Main
def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Extract or infer TOC from PDF")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Generate and save font size visualizations",
    )
    args = parser.parse_args()

    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found at {args.pdf_path}")
        return

    toc: list[tuple[HeadingLevel, Text, Page]] = get_toc(
        args.pdf_path, visualize=args.visualize
    )
    pdf_name = os.path.basename(args.pdf_path)

    if not toc:
        print(f"No table of contents found or could be inferred in '{pdf_name}'.")
    else:
        print(f"Table of Contents for '{pdf_name}' (inferred if no embedded TOC):")
        for level, title, page in toc:
            if isinstance(level, int):
                indent = "#" * level + " "
                indent = "\n" + indent if level == 1 else indent
            else:
                indent = "##* "
            print(f"{indent}{title} (Page {page})")


if __name__ == "__main__":
    main_cli()
