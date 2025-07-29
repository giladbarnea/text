#!/usr/bin/env /opt/homebrew/bin/uvx --with=PyMuPDF,matplotlib,seaborn python3
import sys
import fitz  # PyMuPDF
import os
import statistics
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter

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
                                    print(f"Debug: Found normal text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}")
                                if "2. Framework" in text or "A. Model and Training Details" in text:
                                    print(f"Debug: Found h1 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}")
                                if "Data and tasks." in text:
                                    print(f"Debug: Found h3 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}")
                                
                                all_sizes.append(size)
                                if len(text.split()) < 10 and len(text) > 1:  # Short, non-empty, likely heading
                                    potential_headings.append((page_num + 1, size, text, is_bold))
                                    if "Comparing foundation models to world models" in text or "B.1. Physics" in text:
                                        print(f"Debug: Found h2 text on page {page_num + 1}, size {size}, text: '{text}', bold: {is_bold}")
                                    
        if all_sizes:
            # Set seaborn theme for better aesthetics
            sns.set_theme(style="whitegrid")
            
            # Raw frequency distribution
            raw_freq = Counter(all_sizes)
            
            # Enhanced raw histogram with KDE
            plt.figure(figsize=(12, 7))
            sns.histplot(all_sizes, bins=50, kde=True, color='blue', alpha=0.7)
            plt.title("Raw Font Size Distribution with KDE")
            plt.xlabel("Font Size")
            plt.ylabel("Frequency")
            plt.grid(True)
            
            # Add vertical lines for stats
            mean_size = statistics.mean(all_sizes)
            median_size = statistics.median(all_sizes)
            threshold = median_size * 1.1
            plt.axvline(mean_size, color='green', linestyle='--', label=f'Mean: {mean_size:.2f}')
            plt.axvline(median_size, color='red', linestyle='--', label=f'Median: {median_size:.2f}')
            plt.axvline(threshold, color='purple', linestyle='--', label=f'Threshold: {threshold:.2f}')
            plt.legend()
            
            # Annotate major peaks
            sorted_freq = sorted(raw_freq.items(), key=lambda x: x[1], reverse=True)[:5]  # Top 5 peaks
            for size, count in sorted_freq:
                plt.annotate(f'Size: {size:.2f}\nCount: {count}', xy=(size, count), xytext=(size + 0.5, count + 50),
                             arrowprops=dict(facecolor='black', shrink=0.05), fontsize=10)
            
            plt.savefig("raw_font_size_dist.png", dpi=300)
            plt.close()
            print("Saved enhanced raw distribution to 'raw_font_size_dist.png'")
            
            # Sorted bar chart of unique sizes
            plt.figure(figsize=(14, 7))
            unique_sizes = sorted(raw_freq.keys())
            counts = [raw_freq[size] for size in unique_sizes]
            sns.barplot(x=unique_sizes, y=counts, palette='viridis')
            plt.title("Frequency of Unique Font Sizes (Sorted)")
            plt.xlabel("Font Size")
            plt.ylabel("Frequency")
            plt.xticks(rotation=90, fontsize=8)
            plt.tight_layout()
            plt.savefig("unique_font_size_freq.png", dpi=300)
            plt.close()
            print("Saved unique font size frequency bar chart to 'unique_font_size_freq.png'")
            
            # Function to merge close sizes
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
                # Last group
                group_key = statistics.mean(current_group)
                group_count = sum(raw_freq[s] for s in current_group)
                merged[group_key] = group_count
                return merged
            
            # Merged distributions with plots
            deltas = {
                "very light": 0.01,
                "light": 0.1,
                "moderate": 0.5
            }
            for label, delta in deltas.items():
                merged_freq = merge_sizes(all_sizes, delta)
                
                # Plot merged histogram
                merged_sizes = list(merged_freq.keys())
                merged_counts = list(merged_freq.values())
                plt.figure(figsize=(12, 7))
                sns.barplot(x=merged_sizes, y=merged_counts, palette='coolwarm')
                plt.title(f"{label.capitalize()} Merged Font Size Distribution")
                plt.xlabel("Merged Font Size")
                plt.ylabel("Frequency")
                plt.xticks(rotation=45)
                plt.tight_layout()
                plt.savefig(f"{label}_merged_font_size_dist.png", dpi=300)
                plt.close()
                print(f"Saved {label} merged distribution to '{label}_merged_font_size_dist.png'")
            
            print(f"Debug:\n · Mean size: {mean_size}\n · median size: {median_size}\n · threshold: {threshold}\n · {sorted(all_sizes).index(median_size)=}\n · {len(all_sizes)=}")
            
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
                print(f"No table of contents found or could be inferred in '{pdf_name}'.")
            else:
                print(f"Table of Contents for '{pdf_name}' (inferred if no embedded TOC):")
                for level, title, page in toc:
                    print(f"{'  ' * (level - 1)}{title} (Page {page})")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()