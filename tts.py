import os
import requests
import argparse
import sys
import json
from functools import partial
from pathlib import Path
from typing import Mapping, TypeVar
from contextlib import suppress
from concurrent.futures import ThreadPoolExecutor, as_completed
from pprint import pprint

os.environ["OPENAI_API_KEY"] = os.getenv(
    "OPENAI_API_KEY", (Path.home() / ".openai-api-key").read_text().strip()
)

T = TypeVar("T")


def dictget(mapping: Mapping[str, T], key: str) -> T:
    with suppress(KeyError):
        return mapping[key]
    truncated = key
    last_tried = key
    while len(truncated) >= 7:
        truncated = truncated[:-1]
        last_tried = truncated
        with suppress(KeyError):
            return mapping[truncated]
    raise KeyError(f"{key} (last tried: {last_tried})")


def get_doc_title(text: str) -> str | bool:
    lines = text.splitlines()
    for line in lines:
        if line.startswith("#"):
            return line.split(" ", 1)[1].strip()
    return False


def split_on_h2(text: str) -> dict[str, str]:
    """Returns a { "## <heading>": "<heading content>" }"""
    lines = text.splitlines()
    result = {}
    current_heading = None
    current_content = []

    for line in lines:
        if line.startswith("## "):
            # Save previous section if it exists
            if current_heading is not None:
                result[current_heading] = "\n".join(current_content)

            # Start new section
            current_heading = line
            current_content = []
        else:
            # Add line to current section content
            current_content.append(line)

    # Handle the last section
    if current_heading is not None:
        result[current_heading] = "\n".join(current_content)

    return result


def paranoid_response_json(response: requests.Response) -> dict:
    response_data = response.json()
    if not response_data:
        print("No response data", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    choices = response_data["choices"]
    if not choices:
        print("No choices in response", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    first_choice = choices[0]
    if not first_choice:
        print("No first choice in response", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    message = first_choice["message"]
    if not message:
        print("No message in first choice", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    content = message["content"]
    if not content:
        print("No content in message", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    return content


def gpt5(message: str, *, reasoning_effort: str) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-5",
            "messages": [{"role": "user", "content": message}],
            "reasoning_effort": reasoning_effort,
        },
    )
    if not response.ok:
        print("Response not ok", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    return paranoid_response_json(response)


def gpt5_mini(message: str, *, reasoning_effort: str) -> str:
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            "Content-Type": "application/json",
        },
        json={
            "model": "gpt-5-mini",
            "messages": [{"role": "user", "content": message}],
            "reasoning_effort": reasoning_effort,
        },
    )
    if not response.ok:
        print("Response not ok", file=sys.stderr)
        from pdbr import set_trace

        set_trace()
    return paranoid_response_json(response)


DIVISION_PROMPT = """The following {text_name} is a long text that I plan to pass through an LLM to make it text-to-speech-friendly (text optimized for TTS). My strategy is to give it one part at a time so as not to overwhelm its context window.
My current naive implementation splits the text by Markdown headers. However, this has an inherent problem: the length and semantic weight of sections vary widely. Put differently, the document is best taken in as a few sequences of subsequent sections that should be treated as one piece. Individually, they don't have enough semantic weight or meaningful length to justify processing them solo. Once in a while, you'll find a single section that is a significant semantic group on its own, justifying processing it independently; but that's the exception to the rule.
Group the sections so it makes sense to pass whole groups to the text-to-speech LLM.
Output a JSON object where the keys are "group_1", "group_2", etc., and the values are string arrays of section names, as you see fit. Use the section names exactly as they appear in the <section_stats> section.
The output should be a valid JSON object, and only the JSON object, nothing else.

---
<section_stats>
{section_stats}
</section_stats>

---

<{text_name}>
{text}
</{text_name}>
"""


def main():
    try:
        parser = argparse.ArgumentParser(description="Text-to-speech conversion tool")
        parser.add_argument("input", help="Input Markdown file path")
        parser.add_argument("output", help="Output Markdown file path")
        args = parser.parse_args()

        with open(args.input, "r") as f:
            text = f.read()
        prompt_cdn_url = "https://raw.githubusercontent.com/giladbarnea/llm-templates/refs/heads/main/text/readable.md"

        # ---[ Doc Title ]---
        doc_title = get_doc_title(text)
        if not doc_title:
            print("No title found", file=sys.stderr)
            return

        sections: dict[str, str] = split_on_h2(text)

        # ---[ Group Sections ]---
        sections_info = [
            f"{i + 1: >2}. '{part_heading}': {len(part_body.splitlines())} lines, {len(part_body.split(' '))} words"
            for i, (part_heading, part_body) in enumerate(sections.items())
        ]
        section_stats = (
            f"Text title: {doc_title}.\nParts: {len(sections)}.\nLine count for each:\n"
            + "\n".join(sections_info)
        )
        print(
            section_stats,
            file=sys.stderr,
        )
        division_prompt = DIVISION_PROMPT.format(
            text_name=doc_title, section_stats=section_stats, text=text
        )
        print("\n      -------- Grouping sections --------", file=sys.stderr)
        division_response = gpt5(division_prompt, reasoning_effort="medium")
        section_groups: dict[str, list[str]] = json.loads(division_response)
        pprint(section_groups, indent=2, stream=sys.stderr, width=120, sort_dicts=False)

        # Validate LLM-produced section_groups resolve against parsed sections
        for group_headings in section_groups.values():
            for section_heading in group_headings:
                dictget(sections, section_heading)

        # ---[ Essences pre compute ]---
        print(
            "\n      -------- Precomputing section essences --------", file=sys.stderr
        )
        # Precompute essences for all referenced sections in parallel (max 4 workers)
        all_section_essences: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(4, len(section_groups))) as executor:
            future_to_heading = {}
            for group_headings in section_groups.values():
                for h in group_headings:
                    section_body = dictget(sections, h)
                    prompt = (
                        f"The given section is a part of '{doc_title}'.\n\n---\n\n<{h}>\n{section_body}\n</{h}>\n\n"
                        "Output what it is about in 10 words or less. No need to start with the section name or any intro, no explanations, just output the essence of it."
                    )
                    future = executor.submit(
                        partial(gpt5_mini, reasoning_effort="low"), prompt
                    )
                    future_to_heading[future] = h
            for future in as_completed(future_to_heading):
                h = future_to_heading[future]
                all_section_essences[h] = future.result()

        # ---[ TTS prompt ]---
        print("\n      -------- Starting group processing --------", file=sys.stderr)
        tts_prompt: str = requests.get(prompt_cdn_url).text
        tts_prompt = f"The given content is a part of '{doc_title}'.\n\n{tts_prompt}"
        # --[ Collect prompts for each group ]--
        tts_prompts = []
        for i, section_group_headings in enumerate(section_groups.values()):
            # --[ Str join section contents ]--
            joined_group_content = ""
            for section_heading in section_group_headings:
                section_body = dictget(sections, section_heading)
                joined_group_content += f"\n{section_heading}\n{section_body}"

            group_title = f"Part of '{doc_title}' encompassing sections " + ", ".join(
                [f"'{h.removeprefix('##').lstrip()}'" for h in section_group_headings]
            )
            group_prompt = tts_prompt.replace("${tag}", group_title)

            # --[ Append formatted previous essences to prompt ]
            if all_section_essences:
                previous_context = "\n".join(
                    [
                        f"{i + 1}. {k}: {v}"
                        for i, (k, v) in enumerate(all_section_essences.items())
                    ]
                )
                group_prompt += f"\n\nPreceding sections for context (do not process these, only use them for context):\n{previous_context}"
            group_prompt = f"{group_prompt}\n\n---\n\n<{group_title}\n{joined_group_content}\n</{group_title}>"

            # --[ Convert group to TTS friendly ]--
            tts_prompts.append((group_prompt, i, group_title))

        # --[ Process groups in parallel ]--
        tts_parts = [None] * len(tts_prompts)
        with ThreadPoolExecutor(max_workers=min(4, len(tts_prompts))) as executor:
            future_to_prompt = {}
            for prompt, i, group_title in tts_prompts:
                print(
                    f"\n      -------- Started processing group {i}: {group_title} --------",
                    file=sys.stderr,
                )
                future = executor.submit(partial(gpt5, reasoning_effort="high"), prompt)
                future_to_prompt[future] = (prompt, i, group_title)

            for future in as_completed(future_to_prompt):
                print(
                    f"\n      -------- Finished processing group {i}: {group_title} --------",
                    file=sys.stderr,
                )
                prompt, i, group_title = future_to_prompt[future]
                tts_parts[i] = future.result()
        print("\n      -------- Done converting --------", file=sys.stderr)

        # --[ Write output ]--
        with open(args.output, "w") as f:
            f.write(f"# {doc_title}\n\n")
            for i, section in enumerate(tts_parts):
                f.write(section + "\n\n")
    except Exception as e:
        print(f"Error: {e!r}", file=sys.stderr)

        from pdbr import post_mortem

        post_mortem()


if __name__ == "__main__":
    main()
