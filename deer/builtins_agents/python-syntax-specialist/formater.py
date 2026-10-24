import ast
import re
import textwrap


def escape_python(text: str) -> str:
    """Detects valid Python code blocks, even when they start inline with text,

    wraps them in Markdown ```python, and safely preserves existing escaped code.
    """
    dedented_text = textwrap.dedent(text)
    lines = dedented_text.splitlines()
    processed_lines = []

    # Helper to split lines where code starts mid-sentence (e.g., text: class X:)
    inline_code_pattern = re.compile(r"^(.*?)(?<!\w)(class\s+\w+|def\s+\w+.*?:.*)$")

    for line in lines:
        # If a line contains regular text followed by inline code, split it into two lines
        match = inline_code_pattern.match(line)
        if match and not line.strip().startswith("```"):
            prefix, code_part = match.groups()
            if prefix.strip():
                processed_lines.append(prefix.strip())
            processed_lines.append(code_part)
        else:
            processed_lines.append(line)

    lines = processed_lines
    result = []
    buffer = []
    in_existing_code_block = False

    def flush_buffer():
        if not buffer:
            return
        block = "\n".join(buffer)
        try:
            ast.parse(block)
            result.append(f"```python\n{block}\n```")
        except SyntaxError:
            result.extend(buffer)
        buffer.clear()

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_buffer()
            in_existing_code_block = not in_existing_code_block
            result.append(line)
            continue

        if in_existing_code_block:
            result.append(line)
            continue

        is_code_line = stripped and (
            line.startswith("    ")
            or line.startswith("\t")
            or any(
                stripped.startswith(kw)
                for kw in [
                    "def ",
                    "class ",
                    "import ",
                    "from ",
                    "return ",
                    "if ",
                    "for ",
                    "while ",
                    "try:",
                    "except ",
                    "with ",
                ]
            )
        )

        if is_code_line or (buffer and stripped == ""):
            buffer.append(line)
        else:
            flush_buffer()
            result.append(line)

    flush_buffer()
    return "\n".join(result)
