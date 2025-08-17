import os
import requests
import argparse
import re
import sys
import json


def get_doc_title(text: str) -> str | bool:
    lines = text.splitlines()
    for line in lines:
        if line.startswith("#"):
            return line.split(" ", 1)[1].strip()
    return False


def split_on_h2(text: str) -> list[str]:
    lines = text.splitlines()
    parts = []
    current_block = []

    for i, line in enumerate(lines):
        if line.startswith("## "):
            # Found h2 header, save previous block if it exists
            if current_block:
                parts.append("\n".join(current_block))
                current_block = []

        current_block.append(line)

    # Handle the last block
    if current_block:
        parts.append("\n".join(current_block))

    return parts


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
            "reasoning_effort": reasoning_effort,
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

    title = get_doc_title(text)
    if not title:
        print("No title found", file=sys.stderr)
        return
    parts: list[str] = split_on_h2(text)
    parts_info = [
        f"{i + 1} | '{part.splitlines()[0]}': {len(part.splitlines())}"
        for i, part in enumerate(parts)
    ]
    section_stats = (
        f"Text title: {title}.\nParts: {len(parts)}.\nLine count for each:\n"
        + "\n".join(parts_info)
    )
    print(
        section_stats,
        file=sys.stderr,
    )
    division_prompt = DIVISION_PROMPT.format(text_name=title, section_stats=section_stats, text=text)
    division_response = gpt5(division_prompt, reasoning_effort="low")
    division_json: dict[str, list[str]] = json.loads(division_response)
    print(division_json, file=sys.stderr)
    tts_prompt: str = requests.get(prompt_cdn_url).text
    tts_prompt = f"The given content is a part of '{title}'.\n\n{tts_prompt}"
    tts_parts = []
    part_essences = []
    # for group_name, group_parts in division_json.items():
    for i, part in enumerate(parts):
        part_name = part.splitlines()[0]
        part_prompt = tts_prompt.replace("${tag}", part_name)
        if part_essences:
            previous_context = "\n".join(part_essences)
            part_prompt += f"\n\nPrevious parts for context: {previous_context}"
        part_prompt = f"{part_prompt}\n\n---\n\n<{part_name}>\n{part}\n</{part_name}>"
        print(f"\n      -------- Part {i}: {part_name} --------", file=sys.stderr)
        llm_response = gpt5(part_prompt, reasoning_effort="high")
        tts_parts.append(llm_response)
        essence = gpt5_mini(
            f"The given content is a part of '{title}'.\n\n{tts_prompt}\n\n---\n\n<{part_name}>\n{part}\n</{part_name}>\n\nOutput what it is about in 10 words or less. Start with the part name, like so: '{part_name} <essence>'",
            reasoning_effort="medium",
        )
        part_essences.append(essence)
    print("\n      -------- Done --------", file=sys.stderr)
    with open(args.output, "w") as f:
        f.write(f"# {title}\n\n")
        for i, part in enumerate(tts_parts):
            f.write(part + "\n\n")


if __name__ == "__main__":
    main()
