#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,plotly,scipy python3.13

# Imports grouped by domain
# Parsing: import fitz  # PyMuPDF
import argparse
import os
import statistics

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

Heading = NamedTuple(
    "Heading", [("page", Page), ("size", Size), ("text", Text), ("is_bold", IsBold)]
)
RawData = TypedDict(
    "RawData",
    {
        "embedded_toc": list[tuple[HeadingLevel, Text, Page]],
        "all_font_sizes": list[Size],
        "potential_headings": list[Heading],
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


# Utility function (used in Analysis)
def merge_sizes(sizes: list[Size], delta: float) -> dict[Size, int]:
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


# Domain: Document Parsing
def parse_pdf_document(pdf_path: str) -> RawData:
    doc = fitz.open(pdf_path)
    embedded_toc: list[tuple[HeadingLevel, Text, Page]] = doc.get_toc()

    all_font_sizes: list[Size] = []
    potential_headings: list[Heading] = []

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
                            if len(text) > 1 and len(text.split()) < 10 and is_bold:
                                # 1st (light) filter: bold sentences under 10 words.
                                potential_headings.append(
                                    Heading(
                                        page=Page(page_num + 1),
                                        size=Size(size),
                                        text=Text(text),
                                        is_bold=IsBold(is_bold),
                                    )
                                )

    doc.close()
    return RawData(
        embedded_toc=embedded_toc,
        all_font_sizes=all_font_sizes,
        potential_headings=potential_headings,
    )


# Domain: Statistical Analysis (Font-specific)
class FontSizeAnalyzer:
    deltas: dict[str, Size]

    def __init__(self, deltas: dict[str, Size] = None) -> None:
        if not deltas:
            self.deltas = {"very light": 0.01, "light": 0.1, "moderate": 0.5}
        else:
            self.deltas = deltas

    def compute_raw_stats(self, sizes: list[Size]) -> RawStats:
        """This is where we compute the stats that will be used for filtering.
        "Heavy" computation lifting should be done here.
        """
        import numpy as np
        from scipy.stats import gaussian_kde

        if not sizes:
            return {}
        raw_freq: Counter[Size] = Counter(sizes)
        mean_size: Size = statistics.mean(sizes)
        median_size: Size = statistics.median(sizes)
        max_size: Size = max(sizes)
        h1_threshold: Size = max_size * 0.9
        some_threshold: Size = (
            median_size * 1.1
        )  # I don't remember what this is. Keeping to see if it's useful.
        general_heading_threshold: Size = mean_size

        print(
            f"mean_size={mean_size}\n"
            f"median_size={median_size}\n"
            f"max_size={max_size}\n"
            f"h1_threshold={h1_threshold}\n"
            f"some_threshold={some_threshold}\n"
            f"general_heading_threshold={general_heading_threshold}\n"
            f"raw_freq={raw_freq}"
        )

        # KDE
        sizes_array = np.array(sizes)
        kde = gaussian_kde(sizes_array, bw_method=0.1)
        x_kde = np.linspace(min(sizes), max(sizes), 1000)
        y_kde = kde(x_kde)

        # Dynamic threshold computation
        freq_values = list(raw_freq.values())
        median_freq = statistics.median(freq_values) if freq_values else 0
        
        # Set percentile min to ~35% (even less aggressive than 40% to capture missing H2/H4 headings)
        size_percentile_min_threshold = 35.0
        
        # Set freq max threshold to capture H2/H4 headings that may have high frequency due to similar body text sizes
        # Use 95th percentile of frequencies or minimum of 1400 to allow high-frequency headings
        sorted_freq_values = sorted(freq_values)
        freq_95th_percentile = sorted_freq_values[int(0.95 * len(sorted_freq_values))] if sorted_freq_values else 0
        freq_max_threshold = max(1400, freq_95th_percentile)

        return RawStats(
            {
                "mean": mean_size,
                "median": median_size,
                "h1_threshold": h1_threshold,
                "some_threshold": some_threshold,
                "general_heading_threshold": general_heading_threshold,
                "max_size": max_size,
                "frequency": raw_freq,
                "kde_x": x_kde,
                "kde_y": y_kde,
                "size_percentile_min_threshold": size_percentile_min_threshold,
                "freq_max_threshold": freq_max_threshold,
            }
        )

    def compute_merged_stats(self, sizes: list[Size]) -> dict[str, dict[Size, int]]:
        """
        Maps labels to size count.
        Only used for visualization.
        """
        merged_stats: dict[str, dict[Size, int]] = {}
        for label, delta in self.deltas.items():
            merged_freq: dict[Size, int] = merge_sizes(sizes, delta)
            merged_stats[label] = merged_freq
        return merged_stats

    def analyze(self, sizes: list[Size]) -> AnalysisData:
        raw_stats: RawStats = self.compute_raw_stats(sizes)
        merged_stats: dict[str, dict[Size, int]] = self.compute_merged_stats(sizes)
        return AnalysisData(
            raw_stats=raw_stats,
            merged_stats=merged_stats,
            kde_data=(raw_stats.get("kde_x"), raw_stats.get("kde_y")),  # For viz
        )


# Domain: Visualization Generation
def generate_visualizations(
    analysis_data: AnalysisData, all_font_sizes: list[Size], output_dir: str = "."
):
    if not all_font_sizes:
        return []

    data: AnalysisData = analysis_data
    raw_stats: RawStats = data["raw_stats"]

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
                x=data["kde_data"][0],
                y=data["kde_data"][1] * len(all_font_sizes) * bin_width,
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
        for label, merged_freq in data["merged_stats"].items():
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


# Domain: TOC Inference
def infer_toc(
    raw_data: RawData,
    analysis_data: AnalysisData,
    strategies: list[
        Callable[[RawData, AnalysisData], list[tuple[HeadingLevel, Text, Page]]]
    ] = None,
) -> list[tuple[HeadingLevel, Text, Page]]:
    if not strategies:
        strategies = [embedded_strategy, font_strategy]  # Default chain

    for strategy in strategies:
        toc = strategy(raw_data, analysis_data)
        if toc:  # Non-empty TOC
            return toc
    return []  # No TOC inferred


# Strategy helpers
def embedded_strategy(
    raw_data: RawData, _: AnalysisData
) -> list[tuple[HeadingLevel, Text, Page]]:
    """
    This is the default strategy.
    It's used if no other strategy is provided.
    """
    return raw_data.get("embedded_toc", [])


def font_strategy(
    raw_data: RawData, analysis_data: AnalysisData
) -> list[tuple[HeadingLevel, Text, Page]]:
    """
    Infer TOC from font sizes. Relies on the analysis data from `compute_raw_stats()`.
    """
    potential_headings: list[Heading] = raw_data.get("potential_headings", [])
    if not potential_headings or not raw_data.get(
        "all_font_sizes"
    ):  # Clue: No data available
        return []

    # Add access to required data for Phase 1 filters
    all_font_sizes = sorted(raw_data.get("all_font_sizes", []))
    all_fonts_count = len(all_font_sizes)
    font_freq = analysis_data["raw_stats"].get("frequency", Counter())

    # Two-pass to filter for headings that appear exactly once.
    #  Rationale is true headings don't repeat throughout the document.
    heading_counts: dict[tuple[Text, Size, IsBold], int] = {}
    for heading in potential_headings:
        key: tuple[Text, Size, IsBold] = (heading.text, heading.size, heading.is_bold)
        heading_counts[key] = heading_counts.get(key, 0) + 1

    unique_headings: list[Heading] = []
    for heading in potential_headings:
        key: tuple[Text, Size, IsBold] = (heading.text, heading.size, heading.is_bold)
        if heading_counts[key] == 1:
            unique_headings.append(heading)

    if not unique_headings:
        return []

    analysis_data["raw_stats"].get(
        "some_threshold", 0
    )  # Don't remember what this is for
    h1_threshold: Size = analysis_data["raw_stats"].get("h1_threshold", 0)
    general_heading_threshold: Size = analysis_data["raw_stats"].get(
        "general_heading_threshold", 0
    )

    # --- Define filter thresholds for Phase 1
    # Extract dynamic thresholds from analysis data
    size_percentile_min_threshold = analysis_data["raw_stats"].get("size_percentile_min_threshold", 35.0)
    freq_max_threshold = analysis_data["raw_stats"].get("freq_max_threshold", 1400)

    # Assign levels (font-specific heuristics)
    inferred_toc: list[tuple[HeadingLevel, Text, Page]] = []

    # Dicts for debugging purposes.
    bysize: defaultdict[Size, list[str]] = defaultdict(list)
    bypage: defaultdict[Page, list[str]] = defaultdict(list)

    import bisect

    for heading in unique_headings:
        size = heading.size
        is_bold = heading.is_bold

        # Compute percentile for this heading's font size
        count_smaller = bisect.bisect_left(all_font_sizes, size)
        percentile = (
            (count_smaller / all_fonts_count) * 100 if all_fonts_count > 0 else 0
        )

        # Apply Phase 1 filters: size threshold, bold requirement, percentile filter, and frequency filter
        if (
            size < general_heading_threshold
            or not is_bold
            or percentile < size_percentile_min_threshold
            or font_freq.get(size, 0) >= freq_max_threshold
        ):
            continue

        page = heading.page
        text = heading.text
        if size >= h1_threshold:
            level = 1
        else:  # Need granularity here
            level = "?"
        bysize[size].append(
            f"{text[:20]!r:<23} │ {level=} │ {is_bold=:<1} │ p.{page:>2}"
        )
        bypage[page].append(
            f"{text[:20]!r:<23} │ {level=} │ {is_bold=:<1} │ sz {size:>3.2f}"
        )
        inferred_toc.append((HeadingLevel(level), text, page))

    print("\n\n==== Unique headings by SIZE ====")
    # TODO: move as much percentile logic as possible to `compute_raw_stats()`
    for sz, uniqhd in sorted(bysize.items()):
        count_smaller = bisect.bisect_left(all_font_sizes, sz)
        percentile = (
            (count_smaller / all_fonts_count) * 100 if all_fonts_count > 0 else 0
        )
        print(f"--- size={sz}, percentile={percentile:.2f}%, {len(uniqhd)} items ---")
        for hd in uniqhd:
            print(f" {hd}")

    print("\n\n==== Unique headings by PAGE ====")
    for pg, uniqhd in sorted(bypage.items()):
        print(f"--- page={pg}, {len(uniqhd)} items ---")
        for hd in uniqhd:
            print(f" {hd}")

    # Sort by page
    inferred_toc.sort(key=lambda x: x[2])
    return inferred_toc


# Orchestrator
def get_toc(
    pdf_path: str, visualize: bool = False
) -> list[tuple[HeadingLevel, Text, Page]]:
    raw_data: RawData = parse_pdf_document(pdf_path)

    if raw_data["embedded_toc"] and not visualize:
        return raw_data["embedded_toc"]

    analyzer = FontSizeAnalyzer()
    analysis_data = analyzer.analyze(raw_data["all_font_sizes"])

    if visualize:
        generate_visualizations(analysis_data, raw_data["all_font_sizes"])

    return infer_toc(raw_data, analysis_data)


# Main
def main() -> None:
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
            print(f"{'  ' * (len(level))}{title} (Page {page})")


if __name__ == "__main__":
    main()
