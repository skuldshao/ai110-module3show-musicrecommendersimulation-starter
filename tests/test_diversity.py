"""
Tests for the Challenge 3 diversity penalty in src/recommender.py and the
--diverse flag in src/main.py.

Covers: the rule itself (a repeated artist or genre loses points, and penalties
stack), the explanation lines, the guarantees (off by default, #1 never changes,
the caller's data is not modified), and its effect on a real profile. Run from the
project root with: pytest
"""

from pathlib import Path

from src.main import ADVANCED_PROFILES, EDGE_CASE_PROFILES, PROFILES, parse_args
from src.recommender import (
    DEFAULT_DIVERSITY, DiversityPolicy, diversify, load_songs, recommend_songs,
)

# Build the CSV path from this file's location, so the test works from any directory.
SONGS = load_songs(str(Path(__file__).resolve().parent.parent / "data" / "songs.csv"))
ALL_PROFILES = {**PROFILES, **EDGE_CASE_PROFILES, **ADVANCED_PROFILES}


def song(title: str, artist: str, genre: str) -> dict:
    """A minimal song dict with only the fields diversify() reads (plus a title)."""
    return {"title": title, "artist": artist, "genre": genre}


def test_repeated_artist_is_penalized_and_explained():
    """A second song by the same artist loses 1.5 points, so a slightly weaker song
    by someone else takes its place, and the penalty shows up as a reason.
    """
    ranked = [
        (song("Hit", "Same Artist", "pop"), 5.0, ["genre match: pop (+2.0)"]),
        (song("B-side", "Same Artist", "rock"), 4.8, []),
        (song("Other", "Someone Else", "jazz"), 4.0, []),
    ]
    picked = diversify(ranked, k=3, policy=DiversityPolicy())

    assert [s["title"] for s, _, _ in picked] == ["Hit", "Other", "B-side"]
    b_side_score, b_side_reasons = picked[2][1], picked[2][2]
    assert b_side_score == 3.3  # 4.8 - 1.5
    assert b_side_reasons == [
        "diversity penalty: 1 song by Same Artist already picked (-1.50)"]


def test_penalties_stack_for_each_repeat():
    """The third song in a genre pays twice the genre penalty of the second."""
    ranked = [(song(f"Lofi {n}", f"Artist {n}", "lofi"), 5.0, []) for n in range(3)]
    picked = diversify(ranked, k=3, policy=DiversityPolicy())

    assert [score for _, score, _ in picked] == [5.0, 4.25, 3.5]
    assert picked[2][2] == ["diversity penalty: 2 lofi songs already picked (-1.50)"]


def test_diversify_does_not_modify_its_input():
    """The caller's list and each song's reasons list are left untouched."""
    reasons = []
    ranked = [(song("A", "X", "pop"), 2.0, []), (song("B", "X", "pop"), 1.0, reasons)]
    diversify(ranked, k=2, policy=DiversityPolicy())

    assert len(ranked) == 2
    assert reasons == []


def test_off_by_default():
    """Without a policy, recommend_songs() gives the plain ranking from before
    Challenge 3, for every profile.
    """
    for prefs in ALL_PROFILES.values():
        assert recommend_songs(prefs, SONGS, 5) == recommend_songs(prefs, SONGS, 5, diversity=None)


def test_first_pick_never_changes():
    """The #1 song is never penalized, because nothing has been picked before it."""
    for prefs in ALL_PROFILES.values():
        plain = recommend_songs(prefs, SONGS, 5)
        diverse = recommend_songs(prefs, SONGS, 5, diversity=DEFAULT_DIVERSITY)
        assert diverse[0][0] is plain[0][0]
        assert diverse[0][1] == plain[0][1]


def test_lofi_listener_gets_more_variety():
    """The study listener's plain top 5 has three lofi songs, two by LoRoom. With
    the penalty, the third lofi song (Focus Flow, also by LoRoom) makes room for
    another genre, and no artist appears twice.
    """
    prefs = PROFILES["Late-night study (lofi/chill)"]
    plain = recommend_songs(prefs, SONGS, 5)
    diverse = recommend_songs(prefs, SONGS, 5, diversity=DEFAULT_DIVERSITY)

    assert sum(s["genre"] == "lofi" for s, _, _ in plain) == 3
    assert sum(s["genre"] == "lofi" for s, _, _ in diverse) == 2
    assert "Focus Flow" not in [s["title"] for s, _, _ in diverse]
    artists = [s["artist"] for s, _, _ in diverse]
    assert len(artists) == len(set(artists))


def test_cli_diverse_flag():
    """--diverse is off unless given, and combines with any --mode."""
    assert parse_args([]).diverse is False
    assert parse_args(["--diverse"]).diverse is True
    both = parse_args(["--mode", "mood-first", "--diverse"])
    assert (both.mode, both.diverse) == ("mood-first", True)
