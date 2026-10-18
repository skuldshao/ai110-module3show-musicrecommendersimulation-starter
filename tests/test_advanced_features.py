"""
Tests for the Challenge 1 advanced song features in src/recommender.py.

Covers loading the five new songs.csv columns, the opt-in design (profiles without
advanced preferences score exactly as before), partial credit for mood tags, the
decade / language rules, and max_score_for(). Run from the project root with: pytest
"""

from pathlib import Path

from src.recommender import load_songs, score_song, max_score_for, MAX_SCORE

# Build the CSV path from this file's location, so the test works from any directory.
SONGS_CSV = Path(__file__).resolve().parent.parent / "data" / "songs.csv"

# A core-only profile (the README's default pop/happy listener): no advanced prefs.
CORE_PREFS = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.80,
    "target_valence": 0.80,
    "target_danceability": 0.80,
    "target_tempo_bpm": 120,
    "likes_acoustic": False,
}

# One hand-made song with every column, so expected points are easy to work out.
SONG = {
    "genre": "pop", "mood": "happy", "energy": 0.8, "valence": 0.8,
    "danceability": 0.8, "tempo_bpm": 120.0, "acousticness": 0.0,
    "popularity": 70, "release_decade": 2000, "mood_tags": ["upbeat", "pumped"],
    "instrumentalness": 0.1, "lyrics_language": "english",
}


def test_load_songs_parses_advanced_columns():
    """The five new columns load with usable types: ints, a float, a tag list, text."""
    songs = load_songs(str(SONGS_CSV))
    library_rain = next(song for song in songs if song["title"] == "Library Rain")

    assert len(songs) == 20
    assert library_rain["popularity"] == 55
    assert library_rain["release_decade"] == 2020
    assert library_rain["mood_tags"] == ["rainy", "cozy", "dreamy"]
    assert library_rain["instrumentalness"] == 0.95
    assert library_rain["lyrics_language"] == "instrumental"


def test_advanced_rules_are_opt_in():
    """Without advanced prefs, a song scores exactly as the 7-point core recipe says
    (a perfect core match = 7.0), no advanced reasons appear, and the max stays 7.0.
    """
    score, reasons = score_song(CORE_PREFS, SONG)

    assert score == 7.0
    assert len(reasons) == 7  # genre, mood, 4 numeric rules, acoustic fit
    assert max_score_for(CORE_PREFS) == MAX_SCORE


def test_mood_tags_give_partial_credit():
    """Matching 1 of 2 wanted tags earns half of the 1.0 tag weight, case-insensitively."""
    score, reasons = score_song({"preferred_mood_tags": ["Upbeat", "sunny"]}, SONG)

    assert score == 0.5
    assert reasons == ["mood tags matched: Upbeat (1 of 2) (+0.50)"]


def test_decade_and_language_rules():
    """A song 10 years off the favorite decade earns 0.5 * (1 - 10/30) = 0.33, and a
    matching lyrics language adds 0.5.
    """
    prefs = {"favorite_decade": 2010, "preferred_language": "English"}
    score, reasons = score_song(prefs, SONG)

    assert score == 0.83
    assert reasons == [
        "release_decade 2000 vs target 2010 (+0.33)",
        "language match: english (+0.5)",
    ]


def test_max_score_for_adds_only_the_advanced_rules_used():
    """Each advanced pref raises the ceiling by its weight; all five add 3.0 in total."""
    two_rules = {**CORE_PREFS, "target_popularity": 50, "preferred_mood_tags": ["cozy"]}
    all_rules = {**two_rules, "favorite_decade": 1990, "target_instrumentalness": 0.5,
                 "preferred_language": "english"}

    assert max_score_for(two_rules) == MAX_SCORE + 0.5 + 1.0
    assert max_score_for(all_rules) == MAX_SCORE + 3.0
