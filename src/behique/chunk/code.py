"""Split source code at top-level definitions using tree-sitter.

Code between definitions (imports, constants) becomes its own section. Definitions
too big for one chunk are opened up one level (e.g. a class into its methods) so
symbols stay precise; the packer windows anything still too large.
"""

from __future__ import annotations

from behique.chunk import Section

_DEF_HINTS = ("definition", "declaration", "function", "class", "method", "impl", "struct")
# Byte budget above which a definition is opened into its children.
_OPEN_BYTES = 1600


def _is_def(node) -> bool:
    return node.is_named and any(h in node.type for h in _DEF_HINTS)


def _name(node) -> str | None:
    target = node
    if node.type == "decorated_definition":
        target = node.child_by_field_name("definition") or node
    for field in ("name", "declarator"):
        n = target.child_by_field_name(field)
        while n is not None and n.child_by_field_name("declarator") is not None:
            n = n.child_by_field_name("declarator")
        if n is not None and n.text:
            return n.text.decode("utf-8", "replace").split("(")[0].strip()
    return None


def _body_children(node) -> list:
    body = node
    if node.type == "decorated_definition":
        body = node.child_by_field_name("definition") or node
    body = body.child_by_field_name("body") or body
    return [c for c in body.children if _is_def(c)]


def split(text: str, language: str) -> list[Section]:
    if not text.strip():
        return []
    try:
        from tree_sitter_language_pack import get_parser

        parser = get_parser(language)
    except Exception:
        return [Section(0, len(text))]

    data = text.encode("utf-8")
    # byte offset -> char offset (tree-sitter reports bytes)
    b2c = [0] * (len(data) + 1)
    bi = 0
    for ci, ch in enumerate(text):
        n = len(ch.encode("utf-8"))
        for k in range(n):
            b2c[bi + k] = ci
        bi += n
    b2c[len(data)] = len(text)

    root = parser.parse(data).root_node
    spans: list[tuple[int, int, str | None]] = []  # byte spans

    def visit(nodes, prefix: str | None, lo: int, hi: int) -> None:
        cursor = lo
        for node in nodes:
            if not _is_def(node):
                continue
            if node.start_byte > cursor:
                spans.append((cursor, node.start_byte, prefix))
            name = _name(node)
            qual = f"{prefix}.{name}" if prefix and name else (name or prefix)
            children = _body_children(node)
            if node.end_byte - node.start_byte > _OPEN_BYTES and children:
                visit(children, qual, node.start_byte, node.end_byte)
            else:
                spans.append((node.start_byte, node.end_byte, qual))
            cursor = node.end_byte
        if hi > cursor:
            spans.append((cursor, hi, prefix))

    visit(root.children, None, 0, len(data))

    sections = []
    for b0, b1, sym in spans:
        s, e = b2c[b0], b2c[b1]
        if text[s:e].strip():
            sections.append(Section(s, e, symbol=sym))
    return sections or [Section(0, len(text))]
