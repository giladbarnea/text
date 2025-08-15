# gist id: 840b7964edb648b7313a77d0368c6751
import collections
import importlib
import math
import re
import sys
import typing
from collections import deque
from collections.abc import Generator, Iterator
from difflib import SequenceMatcher
from pathlib import Path
from typing import TypeAlias

import fitz  # PyMuPDF


def similarity(a, b) -> float:
    return SequenceMatcher(None, a, b).ratio()


def normalize_text(text) -> str:
    return re.sub(r"[^\w\s]", ".", text.lower())


ChapterTitle: typing.TypeAlias = str
PageNumber: typing.TypeAlias = int


def extract_chapter(
    pdf_path=None, chapter_name=None, output=None
) -> str | typing.LiteralString:
    # pymupdf4llm.to_markdown("./system-design-interview-vol1.pdf")
    if not pdf_path:
        pdf_path = interactive_user_select(breadth_first_search, Path.home())
    else:
        if Path(pdf_path).is_file():
            pdf_path = Path(pdf_path)
        else:
            pdf_path = interactive_user_select(
                breadth_first_search, Path.home(), item_substring_filter=pdf_path
            )
    doc = fitz.open(pdf_path)

    # toc: [ [level: int , title: str, page: int] , ... ]
    toc: list[list] = doc.get_toc()  # type: ignore
    chapter_names = [f"{toc[i][1]} - {toc[i][2]}" for i in range(len(toc))]
    if not chapter_name:
        chapter_name = interactive_user_select(lambda: iter(chapter_names))

    normalized_chapter_name = normalize_text(chapter_name)

    toc_match: tuple[ChapterTitle, PageNumber] | None = None
    next_chapter_toc_match: tuple[ChapterTitle, PageNumber] | None = None
    for i, (_, title, page) in enumerate(toc):
        normalized_title = normalize_text(title)
        included: bool = normalized_chapter_name in normalized_title
        if not included and normalized_title in normalized_chapter_name:
            normalized_chapter_name = normalized_title
            included = True
        if included:
            toc_match = (normalized_title, page)
            if i < len(toc) - 1:
                next_chapter_toc_match = (normalize_text(toc[i + 1][1]), toc[i + 1][2])
            break
        is_similar: bool = similarity(normalized_chapter_name, normalized_title) > 0.8
        if is_similar:
            toc_match = (normalized_title, page)
            if i < len(toc) - 1:
                next_chapter_toc_match = (normalize_text(toc[i + 1][1]), toc[i + 1][2])
            break

    if not toc_match:
        return (
            f"ERROR: Chapter {chapter_name!r} not found. Available chapters:\n - "
            + "\n - ".join(chapter_names)
        )

    toc_title, toc_page = toc_match
    # Step 4: Find all occurrences of the chapter name
    occurrences: list[tuple[PageNumber, TextLine, Score]] = (
        find_chapter_title_occurrences(
            doc, normalized_chapter_name, toc_title, toc_page
        )
    )

    # Step 5: Identify the most likely start of the chapter
    if not occurrences:
        return (
            f"ERROR: Chapter {chapter_name!r} not found. Available chapters:\n - "
            + "\n - ".join(chapter_names)
        )

    start_occurrence: tuple[PageNumber, TextLine, Score] = max(
        occurrences, key=lambda x: x[2]
    )
    start_page = start_occurrence[0]

    if next_chapter_toc_match:
        next_chapter_title, next_chapter_page = next_chapter_toc_match
        next_chapter_occurrences: list[tuple[PageNumber, TextLine, Score]] = (
            find_chapter_title_occurrences(
                doc, next_chapter_title, next_chapter_title, next_chapter_page
            )
        )
        next_chapter_occurrence: tuple[PageNumber, TextLine, Score] = max(
            next_chapter_occurrences, key=lambda x: x[2]
        )
        next_chapter_start_page = next_chapter_occurrence[0]
    else:
        next_chapter_start_page = None

    # Step 6: Extract chapter content
    chapter_content = []
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        text = page.get_text()  # type: ignore

        reached_next_chapter: bool = (
            next_chapter_start_page is not None and page_num >= next_chapter_start_page
        )
        if reached_next_chapter:
            break

        chapter_content.append(text)

    # If we've reached the end of the document
    formatted_chapter_content = "\n".join(chapter_content)
    if not output:
        return formatted_chapter_content
    write_chapter_to_text_file(toc_title, output, formatted_chapter_content)
    write_chapter_to_markdown_file(
        toc_title, output, doc, pages=range(start_page, page_num), write_images=True
    )


TextLine: typing.TypeAlias = str
Score: typing.TypeAlias = float


def find_chapter_title_occurrences(
    doc, normalized_chapter_name, toc_title, toc_page
) -> list[tuple[PageNumber, TextLine, Score]]:
    occurrences: list[tuple[PageNumber, TextLine, Score]] = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text: str = page.get_text()  # type: ignore
        lines: list[str] = text.split("\n")
        for i, line in enumerate(lines):
            normalized_line = normalize_text(line)
            if not normalized_line.strip():
                continue
            if (
                normalized_chapter_name in normalized_line
                or normalized_chapter_name.startswith(
                    normalized_line
                )  # Handle cases where the chapter title is split across lines
            ):
                score = 0
                # Check if surrounding lines are empty
                has_empty_prev_line: bool = i == 0 or lines[i - 1].strip() == ""
                has_empty_next_line: bool = (
                    i == len(lines) - 1 or lines[i + 1].strip() == ""
                )
                if has_empty_prev_line:
                    score += 0.5
                if has_empty_next_line:
                    score += 0.5
                # Check proximity to TOC page number if available
                toc_page_difference: int = abs(page_num - toc_page) + 1
                proximity_score: float = 1 / math.sqrt(toc_page_difference)
                score += proximity_score
                # Check similarity with TOC title if available
                score += similarity(normalized_line, toc_title)
                occurrences.append((page_num, line, score))
    return occurrences


def breadth_first_search(
    root: Path, item_substring_filter=""
) -> Generator[Path, None, None]:
    queue = deque([root])
    pdfs: list[Path] = []
    while queue:
        try:
            current: Path = queue.popleft()
            if current.is_dir():
                queue.extend(current.iterdir())
            elif current.is_file():
                suffix = current.suffix
                if suffix != ".pdf":
                    continue
                if item_substring_filter not in str(current):
                    continue
                pdfs.append(current)
                yield current
        except PermissionError:
            pass


IteratorFunction: TypeAlias = collections.abc.Callable[..., Iterator[Path | str]]


def interactive_user_select(
    iterator: IteratorFunction, *generator_args, **generator_kwargs
) -> str:
    stderr("Searching for PDF files...")
    lst = []
    try:
        for i, item in enumerate(iterator(*generator_args, **generator_kwargs)):
            stderr(f"{i + 1}. {item}")
            lst.append(item)
    except KeyboardInterrupt:
        if not lst:
            stderr("ERROR: No PDF files found so far.")
            sys.exit(1)
        pass
    while True:
        try:
            choice = int(input("Enter the number: ")) - 1
            return lst[choice]
        except (ValueError, IndexError, TypeError):
            stderr("Invalid choice. Please try again.")


def is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except AttributeError:
        return False


def stderr(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


#  - System Design Interview: An Insider’s Guide - 2
#  - FORWARD - 4
#  - CHAPTER 1: SCALE FROM ZERO TO MILLIONS OF USERS - 5
#  - CHAPTER 2: BACK-OF-THE-ENVELOPE ESTIMATION - 34
#  - CHAPTER 3: A FRAMEWORK FOR SYSTEM DESIGN INTERVIEWS - 42
#  - CHAPTER 4: DESIGN A RATE LIMITER - 51
#  - CHAPTER 5: DESIGN CONSISTENT HASHING - 71
#  - CHAPTER 6: DESIGN A KEY-VALUE STORE - 87
#  - CHAPTER 7: DESIGN A UNIQUE ID GENERATOR IN DISTRIBUTED SYSTEMS - 110
#  - CHAPTER 8: DESIGN A URL SHORTENER - 119
#  - CHAPTER 9: DESIGN A WEB CRAWLER - 132
#  - CHAPTER 10: DESIGN A NOTIFICATION SYSTEM - 151
#  - CHAPTER 11: DESIGN A NEWS FEED SYSTEM - 166
#  - CHAPTER 12: DESIGN A CHAT SYSTEM - 178
#  - CHAPTER 13: DESIGN A SEARCH AUTOCOMPLETE SYSTEM - 200
#  - CHAPTER 14: DESIGN YOUTUBE - 220
#  - CHAPTER 15: DESIGN GOOGLE DRIVE - 244
#  - CHAPTER 16: THE LEARNING CONTINUES - 264
#  - AFTERWORD - 269

DirPath: TypeAlias = Path
FilePath: TypeAlias = Path


def write_chapter_to_text_file(
    chapter_name: str, output_path: DirPath | FilePath | None, content: str
) -> None:
    if not output_path:
        return
    output_path: Path = Path(output_path)
    if output_path.is_dir():
        path_appropriate_chapter_name = make_path_appropriate(chapter_name)
        output_path = output_path / f"{path_appropriate_chapter_name}.txt"
    else:
        assert output_path.parent.is_dir(), (
            f"Parent directory of '{output_path}' does not exist."
        )
    output_path.write_text(content)
    stderr(
        "\n"
        + "-------------"
        + "\n"
        + f"Wrote {len(content.splitlines())} text lines to '{output_path}'"
    )


def write_chapter_to_markdown_file(
    chapter_name: str,
    output_path: DirPath | FilePath | None,
    doc,
    pages: Iterator,
    write_images=True,
) -> None:
    if not output_path:
        return
    output_path: Path = Path(output_path)
    path_appropriate_chapter_name = make_path_appropriate(chapter_name)
    if output_path.is_dir():
        output_path = output_path / f"{path_appropriate_chapter_name}.md"
    else:
        assert output_path.parent.is_dir(), (
            f"Parent directory of '{output_path}' does not exist."
        )
    patch_pymupdf()
    output_dir = output_path.parent
    image_path = output_dir.joinpath(f"img/{path_appropriate_chapter_name}")
    import pymupdf4llm as pymupdf4llm_

    chapter_markdown = pymupdf4llm_.to_markdown(
        doc,
        pages=list(pages),
        write_images=write_images,
        image_path=str(image_path),
        page_width=50000,
        margins=(0, 0, 0, 0),
        page_height=50000,
    )
    output_path.write_text(chapter_markdown)
    stderr(
        "\n"
        + "-------------"
        + "\n"
        + f"Wrote {len(chapter_markdown.splitlines())} markdown lines to '{output_path}'"
    )


def make_path_appropriate(s: str) -> str:
    from string import punctuation

    for c in punctuation + " ":
        s = s.replace(c, "-")
    return re.sub(r"-{2,}", "-", s)


def patch_pymupdf() -> bool:
    search = r"""
            if not code:
                out_string += "\n"
        out_string += "\n"
        if code:
            out_string += "```\n"  # switch of code mode
            code = False

        return (
            out_string.replace(" \n", "\n").replace("  ", " ").replace("\n\n\n", "\n\n")
        )"""
    replace = r"""
            # if not code:
                # out_string += "\n"
        out_string += "\n"
        if code:
            out_string += "```\n"  # switch of code mode
            code = False

        clean_string = (
            out_string.replace(" \n", "\n").replace("  ", " ").replace("\n\n\n", "\n\n")
        )
        import re
        return re.sub(r"(\n?)(\*\*[^\*]+\*\*) ", r"\1\2\n", clean_string, re.MULTILINE)
	"""
    pymupdf4llm = importlib.import_module("pymupdf4llm")
    fn_file_path = Path(pymupdf4llm.to_markdown.__code__.co_filename)
    file_text = fn_file_path.read_text()
    if search not in file_text:
        if replace not in file_text:
            stderr(
                "ERROR: Patching pymupdf4llm.to_markdown failed; search string not found."
            )
            return False
        stderr("pyMuPDF patch already applied.")
        return True
    file_text = file_text.replace(search, replace)
    fn_file_path.write_text(file_text)
    import sys

    [sys.modules.pop(m) for m in list(sys.modules) if "pymu" in m.lower()]
    stderr("Patched pymupdf4llm.to_markdown.")
    return True


if __name__ == "__main__":
    from argparse import ArgumentParser

    # -p,--pdf <path> -c,--chapter <name>
    # pdf_path = "/Users/gilad/Documents/system-design-interview-vol1.pdf"
    parser = ArgumentParser()
    parser.add_argument(
        "-p",
        "--pdf",
        help="Path to the PDF file, or a substring of the file name",
        required=False,
    )
    parser.add_argument("-c", "--chapter", help="Chapter name", required=False)
    parser.add_argument(
        "-o", "--output", help="Output file or directory", required=False
    )
    args = parser.parse_args()
    pdf_path = args.pdf
    if not is_interactive() and not pdf_path:
        stderr(
            "ERROR: When running in non-interactive mode, you must provide the PDF path."
        )
        sys.exit(1)
    chapter_content = extract_chapter(pdf_path, args.chapter, args.output)
    print(chapter_content) if chapter_content else None
