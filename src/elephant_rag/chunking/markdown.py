"""Find Markdown blocks without changing source characters."""

import re
from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["heading", "paragraph", "table", "code", "blank"]
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+\S")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class MarkdownBlock:
    start: int
    end: int
    kind: BlockKind


def _table_separator(line: str) -> bool:
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return bool(cells) and all(re.fullmatch(r"\s*:?-{3,}:?\s*", cell) for cell in cells)


def markdown_blocks(text: str) -> tuple[MarkdownBlock, ...]:
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def table_at(index: int) -> bool:
        return index + 1 < len(lines) and "|" in lines[index] and _table_separator(lines[index + 1])

    result: list[MarkdownBlock] = []
    index = 0
    while index < len(lines):
        start = index
        fence = FENCE.match(lines[index])
        if fence:
            marker = fence.group(1)
            index += 1
            while index < len(lines):
                closing = re.fullmatch(
                    r"\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*",
                    lines[index],
                )
                index += 1
                if closing:
                    break
            kind: BlockKind = "code"
        elif table_at(index):
            index += 2
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                index += 1
            kind = "table"
        elif HEADING.match(lines[index]):
            index += 1
            kind = "heading"
        elif not lines[index].strip():
            index += 1
            while index < len(lines) and not lines[index].strip():
                index += 1
            kind = "blank"
        else:
            index += 1
            while index < len(lines):
                if (
                    not lines[index].strip()
                    or HEADING.match(lines[index])
                    or FENCE.match(lines[index])
                    or table_at(index)
                ):
                    break
                index += 1
            kind = "paragraph"
        result.append(MarkdownBlock(offsets[start], offsets[index], kind))
    return tuple(result)
