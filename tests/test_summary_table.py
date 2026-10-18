"""
Tests for the Challenge 4 table view: src/summary_table.py and main.py's --table.

Covers: every kind of reason the scorer can produce gets the right short tag (built
from real score_song() / diversify() output, so a wording change in the scorer
breaks this test instead of silently garbling the table), tags are never split
across lines, every table line is exactly TABLE_WIDTH wide, and --table runs end
to end. Run from the project root with: pytest
"""

import re
from pathlib import Path

from src.main import ADVANCED_PROFILES, EDGE_CASE_PROFILES, PROFILES, main, parse_args
from src.recommender import DiversityPolicy, diversify, load_songs, recommend_songs, score_song
from src.summary_table import (
    POINTS_AT_END, TABLE_WIDTH, format_recommendation_table, pack_tags, render_table,
    short_reason,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS = load_songs(str(PROJECT_ROOT / "data" / "songs.csv"))

# A table line whose last cell (the Why column) starts with signed points, e.g.
# "|    |   ...   |         | +0.49,    |". That only happens if a tag was split.
SPLIT_TAG = re.compile(r"\| [+-]\d+\.\d{2}\S*\s*\|$")


def test_short_reason_covers_every_reason_the_scorer_makes():
    """A profile that sets all 12 preferences yields every kind of scoring reason;
    each one must shrink to its expected label with signed, 2-decimal points.
    """
    prefs = {**PROFILES["Default pop/happy"], "target_popularity": 80,
             "favorite_decade": 2020, "preferred_mood_tags": ["upbeat"],
             "target_instrumentalness": 0.1, "preferred_language": "english"}
    sunrise_city = SONGS[0]  # pop / happy / english / 2020 / tagged "upbeat"
    _, reasons = score_song(prefs, sunrise_city)
    labels = [short_reason(reason).rsplit(" ", 1)[0] for reason in reasons]

    assert labels == ["genre", "mood", "energy", "valence", "dance", "tempo",
                      "acoustic", "popularity", "decade", "instrumental", "tags",
                      "language"]
    assert short_reason(reasons[0]) == "genre +2.00"  # "+2.0" is shown as "+2.00"


def test_short_reason_for_penalties_and_plain_text():
    """Diversity penalties become "same artist" / "same genre" tags with a minus
    sign, and a reason without points passes through unchanged.
    """
    ranked = [({"artist": "A", "genre": "pop"}, 3.0, []),
              ({"artist": "A", "genre": "pop"}, 2.0, [])]
    penalties = diversify(ranked, k=2, policy=DiversityPolicy())[1][2]

    assert [short_reason(p) for p in penalties] == ["same artist -1.50", "same genre -0.75"]
    assert short_reason("no preferences matched") == "no preferences matched"


def test_pack_tags_never_splits_a_tag():
    """Tags fill each line up to the width, a label always stays with its points,
    and a continued line's trailing comma still fits within the width.
    """
    tags = ["genre +2.00", "mood +1.00", "energy +1.47", "valence +0.48"]
    # "energy +1.47, valence +0.48" is 27 characters, too wide for 26, so it splits
    # between the two tags, never inside one.
    assert pack_tags(tags, width=26) == [
        "genre +2.00, mood +1.00,",
        "energy +1.47,",
        "valence +0.48",
    ]
    # "genre +2.00, mood +1.00" is exactly 23 characters. At width 23 it can't stay
    # on one line, because the line would need a trailing comma (24 > 23).
    assert pack_tags(tags[:3], width=23) == ["genre +2.00,", "mood +1.00,", "energy +1.47"]
    for width in range(13, 40):
        assert all(len(line) <= width for line in pack_tags(tags, width))


def test_render_table_pads_multiline_cells():
    """Shorter cells are padded so every line of a row is the same width."""
    table = render_table(["#", "Song"], [["1", ["Title", "Artist"]]], widths=[2, 8])

    assert table.splitlines() == [
        "+----+----------+",
        "| #  | Song     |",
        "+====+==========+",
        "| 1  | Title    |",
        "|    | Artist   |",
        "+----+----------+",
    ]


def test_recommendation_table_fits_and_keeps_every_reason():
    """For all 12 profiles, with and without the diversity penalty: each table line
    is exactly TABLE_WIDTH wide, no tag is split across lines, and the Why column
    has one tag per reason (none dropped while packing).

    This caught a real bug: in the hidden-gem study profile, "instrumental +0.49"
    used to split across two lines when a packed line plus its trailing comma was
    one character too wide.
    """
    all_profiles = {**PROFILES, **EDGE_CASE_PROFILES, **ADVANCED_PROFILES}
    for diversity in (None, DiversityPolicy()):
        for prefs in all_profiles.values():
            recommendations = recommend_songs(prefs, SONGS, 5, diversity=diversity)
            table = format_recommendation_table(recommendations, 7.0)
            lines = table.splitlines()

            assert all(len(line) == TABLE_WIDTH for line in lines)
            # A split tag would leave its points at the start of the Why cell.
            assert not any(SPLIT_TAG.search(line) for line in lines)
            # Count reasons that carry points; "no preferences matched" (the empty
            # profile) has none and is shown as plain text, not as a tag.
            reason_count = sum(1 for _, _, explanation in recommendations
                               for reason in explanation.split("; ")
                               if POINTS_AT_END.search(reason))
            # Each tag ends in signed points ("+1.47" / "-0.75"); count them.
            tag_count = table.count(" +") + table.count(" -")
            assert tag_count == reason_count


def test_table_flag_runs_end_to_end(capsys, monkeypatch):
    """--table is off by default; with it, main() prints tables and the overview."""
    assert parse_args([]).table is False
    assert parse_args(["--table"]).table is True

    monkeypatch.chdir(PROJECT_ROOT)  # main() reads the relative path data/songs.csv
    main(["--table"])
    output = capsys.readouterr().out

    assert "| #  | Song" in output
    assert "Why (points per rule)" in output
    assert "Overview: the #1 pick for every profile" in output
