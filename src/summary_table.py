"""
Plain-ASCII summary tables for the terminal (Challenge 4).

main.py's default output prints every reason on its own line, which is thorough but
long. With --table, main.py uses this module instead: one compact table per profile
(one row per song, with the reasons for its score), then an overview table with
every profile's #1 pick.

No third-party library is needed: borders are plain "+", "-", "=" and "|", and long
cells are wrapped with the standard library's textwrap, so the output looks the
same in any terminal and the project needs nothing extra installed.

    render_table()                   draw any table from headers, rows and widths
    short_reason()                   "energy 0.82 vs target 0.8 (+1.47)" -> "energy +1.47"
    format_recommendation_table()    one profile's top k, with a Why column
    format_overview_table()          the #1 pick for every profile
"""

import re
import textwrap
from typing import Dict, List, Sequence, Tuple, Union

# Total width of every table, including borders. 80 columns fits a standard terminal.
TABLE_WIDTH = 80

# A cell is either one string (wrapped to the column width automatically) or a list
# of strings, where each item starts on its own line and is wrapped if too long.
Cell = Union[str, Sequence[str]]

# Column widths (text only, borders not included) for the per-profile table:
#   #  | Song (title, artist, genre / mood) | Score | Why
# render_table() draws "| " + cell + " " per column plus a closing "|", which adds
# 3 characters per column and 1 at the end: 4 * 3 + 1 = 13. So the Why column gets
# whatever is left of TABLE_WIDTH: 80 - 13 - (2 + 22 + 7) = 36.
RECOMMENDATION_WIDTHS = (2, 22, 7, TABLE_WIDTH - 13 - (2 + 22 + 7))

# Overview table: Profile | #1 pick | Score. 3 columns -> 3 * 3 + 1 = 10 for borders,
# so the #1 pick column gets 80 - 10 - (34 + 7) = 29.
OVERVIEW_WIDTHS = (34, TABLE_WIDTH - 10 - (34 + 7), 7)

# How each reason from score_song() / diversify() starts, mapped to a short label for
# the Why column. Checked in order, so longer prefixes that share a start with a
# shorter one come first ("mood tags matched" before "mood match", "non-acoustic fit"
# before "acoustic fit").
SHORT_LABELS = (
    ("genre match", "genre"),
    ("mood tags matched", "tags"),
    ("mood match", "mood"),
    ("language match", "language"),
    ("non-acoustic fit", "acoustic"),
    ("acoustic fit", "acoustic"),
    ("energy", "energy"),
    ("valence", "valence"),
    ("danceability", "dance"),
    ("tempo_bpm", "tempo"),
    ("popularity", "popularity"),
    ("release_decade", "decade"),
    ("instrumentalness", "instrumental"),
)

# Every scoring reason ends with its points in parentheses: "(+1.47)", "(+2.0)",
# or "(-1.50)" for a diversity penalty. This captures the signed number.
POINTS_AT_END = re.compile(r"\(([+-]\d+(?:\.\d+)?)\)$")


def short_reason(reason: str) -> str:
    """Shrink one full reason into a short "label +points" tag for the Why column.

    Examples:
        "genre match: pop (+2.0)"                -> "genre +2.00"
        "energy 0.82 vs target 0.8 (+1.47)"      -> "energy +1.47"
        "non-acoustic fit, acousticness 0.18 (+0.82)" -> "acoustic +0.82"
        "diversity penalty: 1 song by LoRoom already picked (-1.50)"
                                                 -> "same artist -1.50"

    Args:
        reason: One reason string as produced by score_song() or diversify().

    Returns:
        The short tag, with points always shown to 2 decimals and a sign. A reason
        without points at the end (e.g. "no preferences matched") is returned
        unchanged, and one with an unknown start keeps its text before the first
        ":" or "(", so new kinds of reasons still show up rather than vanish.
    """
    match = POINTS_AT_END.search(reason)
    if not match:
        return reason
    points = float(match.group(1))

    # Diversity penalties name the artist with " by "; genre penalties don't.
    if reason.startswith("diversity penalty"):
        label = "same artist" if " by " in reason else "same genre"
    else:
        # next() returns the first matching label, or the fallback if none match.
        fallback = re.split(r"[:(]", reason, maxsplit=1)[0].strip()
        label = next((short for prefix, short in SHORT_LABELS
                      if reason.startswith(prefix)), fallback)

    # :+.2f always shows the sign and 2 decimals: 2.0 -> "+2.00", -1.5 -> "-1.50".
    return f"{label} {points:+.2f}"


def pack_tags(tags: List[str], width: int, separator: str = ", ") -> List[str]:
    """Pack short tags into lines no wider than `width`, never splitting a tag.

    textwrap would happily break "energy +1.47" into "energy" and "+1.47" on two
    lines. This keeps each tag whole, so a label always stays next to its points.

    Args:
        tags: Short tags, e.g. ["genre +2.00", "mood +1.00", "energy +1.47"].
        width: The column width to fit.
        separator: Text placed between tags on the same line.

    Returns:
        The lines of the cell. A tag longer than the whole width gets a line of
        its own (render_table() then wraps that one line).
    """
    # A line that continues on the next one ends with the separator minus its
    # trailing space (","), so the reader can tell the list goes on.
    trailer = separator.rstrip()
    lines = []
    current = ""
    for tag in tags:
        # Try adding this tag to the current line; start a new line if it won't fit.
        candidate = f"{current}{separator}{tag}" if current else tag
        # Leave room for the trailing "," in case this line turns out not to be the
        # last. Otherwise a line packed to exactly `width` would overflow by one
        # once the comma is added, and render_table() would split a tag to fit it.
        if current and len(candidate) + len(trailer) > width:
            lines.append(current + trailer)
            current = tag
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_table(headers: Sequence[str], rows: Sequence[Sequence[Cell]],
                 widths: Sequence[int], right_align: Sequence[int] = ()) -> str:
    """Draw a plain-ASCII table whose cells can span several lines.

    Example with one row:

        +----+--------+
        | #  | Song   |
        +====+========+
        | 1  | Title  |
        |    | Artist |
        +----+--------+

    Args:
        headers: One header per column.
        rows: Each row is one Cell per column (a string, or a list of strings
            for separate lines). Long lines are wrapped to the column width.
        widths: Text width of each column, borders not included.
        right_align: Indexes of columns to right-align (e.g. numbers).

    Returns:
        The whole table as one string, ready to print.
    """
    # "+" corners with "-" runs; each run is the column width plus the two padding
    # spaces around the text. The line under the header uses "=" to stand out.
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    header_border = border.replace("-", "=")

    def cell_lines(cell: Cell, width: int) -> List[str]:
        """Turn one cell into wrapped lines that each fit the column width."""
        items = [cell] if isinstance(cell, str) else list(cell)
        lines = []
        for item in items:
            # wrap() returns [] for "", so keep an empty line in that case.
            lines.extend(textwrap.wrap(item, width) or [""])
        return lines

    def row_lines(row: Sequence[Cell]) -> List[str]:
        """Render one table row, padding short cells so all columns line up."""
        columns = [cell_lines(cell, width) for cell, width in zip(row, widths)]
        height = max(len(column) for column in columns)
        output = []
        for line_index in range(height):
            parts = []
            for column_index, (column, width) in enumerate(zip(columns, widths)):
                # A cell with fewer lines than the tallest one shows blanks below.
                text = column[line_index] if line_index < len(column) else ""
                aligned = (text.rjust(width) if column_index in right_align
                           else text.ljust(width))
                parts.append(f" {aligned} ")
            output.append("|" + "|".join(parts) + "|")
        return output

    lines = [border, *row_lines(headers), header_border]
    for row in rows:
        lines.extend(row_lines(row))
        lines.append(border)
    return "\n".join(lines)


def format_recommendation_table(recommendations: List[Tuple[Dict, float, str]],
                                max_score: float) -> str:
    """Build one profile's table: a row per song, with the reasons for its score.

    Args:
        recommendations: (song_dict, score, explanation) tuples from
            recommend_songs(); the explanation is the reasons joined with "; ".
        max_score: The most this profile could earn, from max_score_for(),
            shown under each score as "of 7.00".

    Returns:
        The table as a string. Each row shows the rank; the title, artist and
        genre / mood; the score; and a Why column with one short tag per reason,
        e.g. "genre +2.00, mood +1.00, energy +1.47, ...".
    """
    if not recommendations:
        return "  (no recommendations)"

    why_width = RECOMMENDATION_WIDTHS[3]
    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        # The explanation is one "; "-joined string; split it back into reasons.
        tags = [short_reason(reason) for reason in explanation.split("; ")]
        rows.append([
            str(rank),
            [song["title"], song["artist"], f"{song['genre']} / {song['mood']}"],
            [f"{score:.2f}", f"of {max_score:.2f}"],
            pack_tags(tags, why_width),
        ])
    return render_table(["#", "Song", "Score", "Why (points per rule)"], rows,
                        RECOMMENDATION_WIDTHS, right_align=(2,))


def format_overview_table(top_picks: List[Tuple[str, Dict, float, float]]) -> str:
    """Build the closing overview: every profile's #1 pick on one screen.

    Args:
        top_picks: (profile name, #1 song dict, its score, the profile's max score)
            tuples, in the order the profiles were run.

    Returns:
        The table as a string, with one row per profile.
    """
    rows = [[name, [song["title"], song["artist"]], [f"{score:.2f}", f"of {max_score:.2f}"]]
            for name, song, score, max_score in top_picks]
    return render_table(["Profile", "#1 pick", "Score"], rows, OVERVIEW_WIDTHS,
                        right_align=(2,))
