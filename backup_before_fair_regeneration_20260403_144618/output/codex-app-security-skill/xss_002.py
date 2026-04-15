BOLD_PATTERNS = (
    (re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*"), "strong"),
    (re.compile(r"__(?=\S)(.+?)(?<=\S)__"), "strong"),
)
ITALIC_PATTERNS = (
    (re.compile(r"(?<!\*)\*(?=\S)(.+?)(?<=\S)\*(?!\*)"), "em"),
    (re.compile(r"(?<!_)_(?=\S)(.+?)(?<=\S)_(?!_)"), "em"),
)