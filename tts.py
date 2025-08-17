import os
import requests
import argparse
import re
import sys
import json
from pathlib import Path
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", (Path.home() / ".openai-api-key").read_text().strip())

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
            "reasoning_effort": "low"
        },
    )
    return response.json()["choices"][0]["message"]["content"]


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
            "reasoning_effort": "low"
        },
    )
    return response.json()["choices"][0]["message"]["content"]


DIVISION_PROMPT = """The following {text_name} is a long text that I plan to pass through an LLM to make it text-to-speech-friendly (text optimized for TTS). My strategy is to give it one part at a time so as not to overwhelm its context window.
My current naive implementation splits the text by Markdown headers. However, this has an inherent problem: the length and semantic weight of sections vary widely. Put differently, the document is best taken in as a few sequences of subsequent sections that should be treated as one piece. Individually, they don't have enough semantic weight or meaningful length to justify processing them solo. Once in a while, you'll find a single section that is a significant semantic group on its own, justifying processing it independently; but that's the exception to the rule.
Group the sections so it makes sense to pass whole groups to the text-to-speech LLM.
Output a JSON object where the keys are "group_1", "group_2", etc., and the values are string arrays of section names, as you see fit.
The output should be a valid JSON object, and only the JSON object, nothing else.

---

{section_stats}

---

<{text_name}>
{text}
</{text_name}>
"""


def main():
    parser = argparse.ArgumentParser(description="Text-to-speech conversion tool")
    parser.add_argument("input", help="Input Markdown file path")
    parser.add_argument("output", help="Output Markdown file path")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        text = f.read()
    prompt_cdn_url = "https://raw.githubusercontent.com/giladbarnea/llm-templates/refs/heads/main/text/readable.md"

    doc_title = get_doc_title(text)
    if not doc_title:
        print("No title found", file=sys.stderr)
        return
    sections: dict[str, str] = split_on_h2(text)
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
    division_response = gpt5(division_prompt, reasoning_effort="low")
    division_json: dict[str, list[str]] = json.loads(division_response)
    print(division_json, file=sys.stderr)
    tts_prompt: str = requests.get(prompt_cdn_url).text
    tts_prompt = f"The given content is a part of '{doc_title}'.\n\n{tts_prompt}"
    tts_parts = []
    section_essences: dict[str, str] = {}
    for i, section_group_headings in enumerate(division_json.values()):
        joined_group = ""
        for section_heading in section_group_headings:
            section_body = sections[section_heading]
            joined_group += f"\n{section_heading}\n{section_body}"

        group_title = f"Part of '{doc_title}' encompassing sections " + ", ".join(
            [f"'{h.removeprefix('##').lstrip()}'" for h in section_group_headings]
        )
        group_prompt = tts_prompt.replace("${tag}", group_title)
        if section_essences:
            previous_context = "\n".join(
                [
                    f"{i + 1}. {k}: {v}"
                    for i, (k, v) in enumerate(section_essences.items())
                ]
            )
            group_prompt += f"\n\nPreceding sections for context (do not process these, only use them for context):\n{previous_context}"
        group_prompt = (
            f"{group_prompt}\n\n---\n\n<{group_title}\n{joined_group}\n</{group_title}>"
        )
        print(f"\n      -------- Group {i}: {group_title} --------", file=sys.stderr)
        llm_response = gpt5(group_prompt, reasoning_effort="high")
        tts_parts.append(llm_response)
        if i < len(division_json) - 1:
            for section_heading in section_group_headings:
                section_body = sections[section_heading]
                joined_group += f"\n{section_heading}\n{section_body}"
                essence = gpt5_mini(
                    f"The given section is a part of '{doc_title}'.\n\n---\n\n<{section_heading}>\n{section_body}\n</{section_heading}>\n\nOutput what it is about in 10 words or less. No need to start with the section name or any intro, no explanations, just output the essence of it.",
                    reasoning_effort="medium",
                )
                section_essences[section_heading] = essence

    print("\n      -------- Done --------", file=sys.stderr)
    with open(args.output, "w") as f:
        f.write(f"# {doc_title}\n\n")
        for i, section in enumerate(tts_parts):
            f.write(section + "\n\n")


if __name__ == "__main__":
    main()
