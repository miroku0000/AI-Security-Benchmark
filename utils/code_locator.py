"""
Utility functions for locating code patterns and extracting line numbers.
"""
import re
from typing import List, Dict, Optional


def find_pattern_locations(code: str, pattern: str, context_lines: int = 0) -> List[Dict]:
    """
    Find all occurrences of a regex pattern in code and return location info.

    Args:
        code: The source code to search
        pattern: Regex pattern to search for
        context_lines: Number of lines of context to include before/after match

    Returns:
        List of dicts with keys: line_number, line_content, match, context
    """
    locations = []
    lines = code.split('\n')

    for line_num, line in enumerate(lines, 1):
        matches = list(re.finditer(pattern, line, re.IGNORECASE))
        for match in matches:
            # Get context lines
            start_line = max(0, line_num - context_lines - 1)
            end_line = min(len(lines), line_num + context_lines)
            context = '\n'.join(lines[start_line:end_line])

            locations.append({
                'line_number': line_num,
                'line_content': line.strip(),
                'match': match.group(0),
                'context': context,
                'column_start': match.start(),
                'column_end': match.end()
            })

    return locations


def format_code_location(location: Dict, show_context: bool = False) -> str:
    """
    Format a code location for display.

    Args:
        location: Location dict from find_pattern_locations
        show_context: Whether to include code context

    Returns:
        Formatted string showing line number and code
    """
    line_num = location['line_number']
    line_content = location['line_content']
    match = location['match']

    # Highlight the matched portion
    highlighted = line_content.replace(match, f'>>>{match}<<<')

    result = f"Line {line_num}: {highlighted}"

    if show_context and location.get('context'):
        result += f"\n\nContext:\n{location['context']}"

    return result


def is_comment_line(line: str, language: str = "python") -> bool:
    """
    Check if a line is a comment.

    Args:
        line: The line to check
        language: Programming language (python or javascript)

    Returns:
        True if the line is a comment, False otherwise
    """
    stripped = line.strip()

    if language == "python":
        # Python: line starts with #
        return stripped.startswith('#')
    elif language == "javascript":
        # JavaScript: line starts with // or is within /* */
        return stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*')

    return False


def find_pattern_locations_skip_comments(code: str, pattern: str, language: str = "python", context_lines: int = 0) -> List[Dict]:
    """
    Find all occurrences of a regex pattern in code, SKIPPING COMMENT LINES.

    This is useful for detecting hardcoded secrets - we don't want to flag
    examples or prompts in comments as actual vulnerabilities.

    Args:
        code: The source code to search
        pattern: Regex pattern to search for
        language: Programming language (python or javascript)
        context_lines: Number of lines of context to include before/after match

    Returns:
        List of dicts with keys: line_number, line_content, match, context
    """
    locations = []
    lines = code.split('\n')

    for line_num, line in enumerate(lines, 1):
        # Skip comment lines
        if is_comment_line(line, language):
            continue

        matches = list(re.finditer(pattern, line, re.IGNORECASE))
        for match in matches:
            # Get context lines
            start_line = max(0, line_num - context_lines - 1)
            end_line = min(len(lines), line_num + context_lines)
            context = '\n'.join(lines[start_line:end_line])

            locations.append({
                'line_number': line_num,
                'line_content': line.strip(),
                'match': match.group(0),
                'context': context,
                'column_start': match.start(),
                'column_end': match.end()
            })

    return locations


def find_multiline_pattern(code: str, pattern: str) -> List[Dict]:
    """
    Find multiline pattern matches and return their locations.

    Args:
        code: The source code to search
        pattern: Regex pattern (can match across lines)

    Returns:
        List of dicts with start_line, end_line, and matched_text
    """
    locations = []
    matches = re.finditer(pattern, code, re.MULTILINE | re.DOTALL)

    for match in matches:
        # Find which lines this match spans
        start_pos = match.start()
        end_pos = match.end()

        # Count newlines before start to get line number
        start_line = code[:start_pos].count('\n') + 1
        end_line = code[:end_pos].count('\n') + 1

        matched_text = match.group(0)

        locations.append({
            'start_line': start_line,
            'end_line': end_line,
            'matched_text': matched_text,
            'match_object': match
        })

    return locations


def extract_function_at_line(code: str, line_number: int, language: str = "python") -> Optional[Dict]:
    """
    Extract the complete function containing the specified line number.

    Args:
        code: The source code
        line_number: Line number within a function
        language: Programming language (python or javascript)

    Returns:
        Dict with function_name, start_line, end_line, function_body or None
    """
    lines = code.split('\n')

    if language == "python":
        # Find function definition by walking backwards
        func_start = None
        for i in range(line_number - 1, -1, -1):
            if re.match(r'\s*def\s+\w+', lines[i]):
                func_start = i + 1  # 1-indexed
                break

        if func_start is None:
            return None

        # Find function end (next def or class, or end of file)
        func_end = len(lines)
        base_indent = len(lines[func_start - 1]) - len(lines[func_start - 1].lstrip())

        for i in range(func_start, len(lines)):
            line = lines[i]
            if line.strip() and not line.strip().startswith('#'):
                current_indent = len(line) - len(line.lstrip())
                if current_indent <= base_indent and i > func_start:
                    func_end = i
                    break

        func_match = re.match(r'\s*def\s+(\w+)', lines[func_start - 1])
        func_name = func_match.group(1) if func_match else "unknown"

        return {
            'function_name': func_name,
            'start_line': func_start,
            'end_line': func_end,
            'function_body': '\n'.join(lines[func_start - 1:func_end])
        }

    elif language == "javascript":
        # Similar logic for JavaScript functions
        func_start = None
        for i in range(line_number - 1, -1, -1):
            if re.search(r'function\s+\w+|const\s+\w+\s*=.*function|=>\s*\{', lines[i]):
                func_start = i + 1
                break

        if func_start is None:
            return None

        # Count braces to find function end
        brace_count = 0
        func_end = len(lines)

        for i in range(func_start - 1, len(lines)):
            brace_count += lines[i].count('{') - lines[i].count('}')
            if brace_count == 0 and i > func_start - 1:
                func_end = i + 1
                break

        func_match = re.search(r'function\s+(\w+)|const\s+(\w+)', lines[func_start - 1])
        func_name = func_match.group(1) or func_match.group(2) if func_match else "unknown"

        return {
            'function_name': func_name,
            'start_line': func_start,
            'end_line': func_end,
            'function_body': '\n'.join(lines[func_start - 1:func_end])
        }

    return None
