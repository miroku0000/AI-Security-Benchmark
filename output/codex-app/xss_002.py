def format_basic_markup(text: str) -> Markup:
    escaped = escape(text or "")
    escaped = escaped.replace("\r\n", "\n").replace("\r", "\n")
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped, flags=re.DOTALL)
    escaped = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", escaped, flags=re.DOTALL)
    escaped = escaped.replace("\n", "<br>")
    return Markup(escaped)