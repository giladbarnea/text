#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,matplotlib,seaborn,plotly,scipy python3
import sys
import fitz  # PyMuPDF
import os
import statistics
import plotly.graph_objects as go
from collections import Counter
from scipy.stats import gaussian_kde
import numpy as np


def get_toc(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()
    if not toc:
        potential_headings = []
        all_sizes = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            dict_text = page.get_text("dict")
            for block in dict_text["blocks"]:
                if block["type"] == 0:  # text block
                    for line in block.get("lines", []):
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                size = span["size"]
                                all_sizes.append(size)
                                is_bold = (span["flags"] & 16) != 0
                                if "a state space" in text:
                                    print(
                                        f"Debug: Found normal text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}"
                                    )
                                if (
                                    "2. Framework" in text
                                    or "A. Model and Training Details" in text
                                ):
                                    print(
                                        f"Debug: Found h1 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}"
                                    )
                                if "Data and tasks." in text:
                                    print(
                                        f"Debug: Found h3 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}"
                                    )
                                if (
                                    len(text.split()) < 10 and len(text) > 1
                                ):  # Short, non-empty, likely heading
                                    potential_headings.append((
                                        page_num + 1,
                                        size,
                                        text,
                                        is_bold,
                                    ))
                                    if (
                                        "Comparing foundation models to world models"
                                        in text
                                        or "B.1. Physics" in text
                                    ):
                                        print(
                                            f"Debug: Found h2 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}"
                                        )

        if all_sizes:
            raw_freq = Counter(all_sizes)

            # Interactive Raw Histogram with KDE using Plotly
            all_sizes_array = np.array(all_sizes)
            kde_01 = gaussian_kde(all_sizes_array,bw_method=0.1)
            x_kde_01 = np.linspace(min(all_sizes), max(all_sizes), 1000)
            y_kde_01 = kde_01(x_kde_01)

            hist, bin_edges = np.histogram(all_sizes_array, bins=100)
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            customdata = list(zip(bin_edges[:-1], bin_edges[1:]))
            bin_width = bin_edges[1] - bin_edges[0] if len(bin_edges) > 1 else 1

            fig_raw = go.Figure()
            fig_raw.add_trace(
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
            fig_raw.add_trace(
                go.Scatter(
                    x=x_kde_01,
                    y=y_kde_01 * len(all_sizes) * bin_width,
                    mode="lines",
                    line=dict(color="green", width=2),
                    name="KDE",
                    hovertemplate="KDE 0.1: %{y:.1f}<extra></extra>",
                )
            )

            mean_size = statistics.mean(all_sizes)
            median_size = statistics.median(all_sizes)
            threshold = median_size * 1.1
            fig_raw.add_vline(
                x=mean_size,
                line=dict(color="rgba(0,128,0,0.25)", width=2, dash="dash"),
                annotation_text="Mean",
                annotation_position="top left",
            )
            fig_raw.add_vline(
                x=median_size,
                line=dict(color="rgba(255,165,0,0.25)", width=2, dash="dash"),
                annotation_text="Median",
                annotation_position="top center",
            )
            fig_raw.add_vline(
                x=threshold,
                line=dict(color="rgba(128,0,128,0.25)", width=2, dash="dash"),
                annotation_text="Threshold",
                annotation_position="top right",
            )

            sorted_freq = sorted(raw_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            for i, (size, count) in enumerate(sorted_freq):
                fig_raw.add_annotation(
                    x=size,
                    y=count,
                    text=f"Top {i + 1}: {size:.2f} ({count})",
                    showarrow=True,
                    arrowhead=1,
                    yshift=10,
                    font=dict(size=8),
                )

            fig_raw.update_layout(
                title="Interactive Raw Font Size Distribution with KDE",
                xaxis_title="Font Size",
                yaxis_title="Frequency",
                barmode="overlay",
                hovermode="x unified",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            )
            fig_raw.write_html("raw_font_size_dist.html")
            print("Saved interactive raw distribution to 'raw_font_size_dist.html'")

            # Interactive Sorted Bar Chart
            unique_sizes = sorted(raw_freq.keys())
            counts = [raw_freq[size] for size in unique_sizes]
            fig_bar = go.Figure(
                go.Scatter(
                    x=unique_sizes,
                    y=counts,
                    mode="markers+lines",
                    marker=dict(color=counts, colorscale="viridis", size=10),
                    line=dict(color="gray"),
                )
            )
            fig_bar.update_layout(
                title="Interactive Frequency of Unique Font Sizes (Sorted)",
                xaxis_title="Font Size",
                yaxis_title="Frequency",
                yaxis_type="log",
            )
            fig_bar.write_html("unique_font_size_freq.html")
            print(
                "Saved interactive unique font size frequency to 'unique_font_size_freq.html'"
            )

            # Function to merge close sizes (unchanged)
            def merge_sizes(sizes, delta):
                if not sizes:
                    return {}
                sorted_unique = sorted(set(sizes))
                merged = {}
                current_group = [sorted_unique[0]]
                for i in range(1, len(sorted_unique)):
                    if sorted_unique[i] - current_group[-1] <= delta:
                        current_group.append(sorted_unique[i])
                    else:
                        group_key = statistics.mean(current_group)
                        group_count = sum(raw_freq[s] for s in current_group)
                        merged[group_key] = group_count
                        current_group = [sorted_unique[i]]
                group_key = statistics.mean(current_group)
                group_count = sum(raw_freq[s] for s in current_group)
                merged[group_key] = group_count
                return merged

            # Interactive Merged Distributions
            deltas = {"very light": 0.01, "light": 0.1, "moderate": 0.5}
            for label, delta in deltas.items():
                merged_freq = merge_sizes(all_sizes, delta)
                merged_sizes = sorted(merged_freq.keys())
                merged_counts = [merged_freq[size] for size in merged_sizes]
                fig_merged = go.Figure(
                    go.Scatter(
                        x=merged_sizes,
                        y=merged_counts,
                        mode="markers+lines",
                        marker=dict(color=merged_counts, colorscale="rdbu", size=12),
                        line=dict(color="lightgray"),
                    )
                )
                fig_merged.update_layout(
                    title=f"Interactive {label.capitalize()} Merged Font Size Distribution",
                    xaxis_title="Merged Font Size",
                    yaxis_title="Frequency",
                    yaxis_type="log" if label == "very light" else "linear",
                )
                fig_merged.write_html(
                    f"{label.replace(' ', '_')}_merged_font_size_dist.html"
                )
                print(
                    f"Saved interactive {label} merged distribution to '{label.replace(' ', '_')}_merged_font_size_dist.html'"
                )

            print(
                f"Debug:\n · Mean size: {mean_size}\n · median size: {median_size}\n · threshold: {threshold}\n · {sorted(all_sizes).index(median_size)=}\n · {len(all_sizes)=}"
            )

            # Deduplicate by text and page
            unique_headings = []
            seen = set()
            for page, size, text, is_bold in potential_headings:
                key = (text, page)
                if key not in seen:
                    seen.add(key)
                    unique_headings.append((page, size, text, is_bold))

            if unique_headings:
                # Find max size
                max_size = max(h[1] for h in unique_headings)

                # Assign levels
                inferred_toc = []
                for page, size, text, is_bold in unique_headings:
                    if size > threshold:
                        if size >= max_size * 0.9:
                            level = 1
                        else:
                            level = 2
                        inferred_toc.append([level, text, page])

                # Sort by page number to maintain document order
                inferred_toc.sort(key=lambda x: x[2])

                doc.close()
                return inferred_toc
            else:
                doc.close()
                return []
        else:
            doc.close()
            return []
    doc.close()
    return toc


def main():
    pdf_path = sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: File not found at {pdf_path}")
    else:
        try:
            toc = get_toc(pdf_path)
            pdf_name = os.path.basename(pdf_path)

            if not toc:
                print(
                    f"No table of contents found or could be inferred in '{pdf_name}'."
                )
            else:
                print(
                    f"Table of Contents for '{pdf_name}' (inferred if no embedded TOC):"
                )
                for level, title, page in toc:
                    print(f"{'  ' * (level - 1)}{title} (Page {page})")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
