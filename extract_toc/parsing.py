from __future__ import annotations

from .types import HeadingLevel, Page, RawData, Size, Span, Text, IsBold
import fitz


def parse_pdf_document(pdf_path: str, *, debug: bool = False) -> RawData:
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
        # Detect if current page appears to be a TOC page when debug is enabled
        debug_this_page = False
        if debug:
            try:
                # Lightweight scan for common TOC markers
                for block in dict_text.get("blocks", []):
                    if block.get("type") == 0:
                        for line in block.get("lines", []):
                            for sp in line.get("spans", []):
                                t = (sp.get("text") or "").strip().casefold()
                                if t and ("table of contents" in t or t == "contents"):
                                    debug_this_page = True
                                    raise StopIteration
            except StopIteration:
                pass
            if debug_this_page:
                print(f"\n[DEBUG] Candidate TOC page detected: page {page_num + 1}")
                # Dump link annotations on this page
                try:
                    links = page.get_links()  # type: ignore[attr-defined]
                except Exception:
                    links = []
                if links:
                    print(f"[DEBUG] Found {len(links)} link annotations on page {page_num + 1}")
                    for i, link in enumerate(links, 1):
                        dest_page = link.get("page")
                        uri = link.get("uri")
                        rect = link.get("from")
                        print(f"  - link[{i}]: rect={rect}, dest_page={dest_page}, uri={uri}")
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
                            if debug_this_page:
                                bbox = span.get("bbox")
                                origin = span.get("origin")
                                print(
                                    f"[DEBUG] span: text={text!r}, size={size:.2f}, bold={bool(is_bold)}, origin={origin}, bbox={bbox}"
                                )
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


