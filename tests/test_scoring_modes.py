"""
Tests for the Challenge 2 scoring modes (Strategy pattern) in src/recommender.py
and the --mode switch in src/main.py.

Covers: every mode is complete and valid, the default mode reproduces the original
recipe, each alternative mode changes rankings the way it promises, the OOP
Recommender honors a mode, and the CLI rejects unknown modes. Run from the project
root with: pytest
"""

from pathlib import Path

import pytest

from src.main import EDGE_CASE_PROFILES, PROFILES, parse_args
from src.recommender import (
    BALANCED, CORE_RULES, DEFAULT_MODE, ENERGY_FOCUSED, GENRE_FIRST, MAX_SCORE,
    MOOD_FIRST, SCORING_MODES, Recommender, ScoringMode, Song, UserProfile,
    load_songs, recommend_songs, score_song,
)

# Build the CSV path from this file's location, so the test works from any directory.
SONGS = load_songs(str(Path(__file__).resolve().parent.parent / "data" / "songs.csv"))


def top_titles(prefs: dict, mode: ScoringMode, k: int = 5) -> list:
    """Return the titles of the top k songs for a profile under one scoring mode."""
    return [song["title"] for song, _, _ in recommend_songs(prefs, SONGS, k, mode=mode)]


def test_every_mode_weights_all_core_rules():
    """Each registered mode weights exactly the seven core rules, and its max score
    is the sum of those weights.
    """
    assert set(SCORING_MODES) == {"balanced", "genre-first", "mood-first", "energy-focused"}
    for mode in SCORING_MODES.values():
        assert set(mode.weights) == set(CORE_RULES)
        assert mode.max_score == sum(mode.weights.values())


def test_default_mode_is_the_original_recipe():
    """Leaving out the mode gives the same scores as passing BALANCED explicitly,
    so every result documented before Challenge 2 still holds.
    """
    prefs = PROFILES["Default pop/happy"]
    assert DEFAULT_MODE is BALANCED
    assert BALANCED.max_score == MAX_SCORE
    for song in SONGS:
        assert score_song(prefs, song) == score_song(prefs, song, BALANCED)


def test_mood_first_puts_the_only_sad_song_first():
    """The stress test's "sad listener got angry metal" result is fixed by
    mood-first: the one sad song jumps from outside the top 5 to #1.
    """
    sad = EDGE_CASE_PROFILES["Edge: high energy + sad mood"]
    assert "Pinewood Letters" not in top_titles(sad, BALANCED)
    assert top_titles(sad, MOOD_FIRST)[0] == "Pinewood Letters"


def test_genre_first_ranks_genre_matches_above_everything_else():
    """The metal fan with calm numbers finally gets the metal song, at #1, because
    in genre-first the genre prize outweighs all other core rules combined.
    """
    metal = EDGE_CASE_PROFILES["Edge: metal genre, calm acoustic numbers"]
    assert "Iron Cathedral" not in top_titles(metal, BALANCED)
    assert top_titles(metal, GENRE_FIRST)[0] == "Iron Cathedral"


def test_energy_focused_prefers_the_closer_energy_over_the_genre_label():
    """For the pop/happy fan, energy-focused ranks Rooftop Lights (energy 0.76,
    0.04 from the target) above Gym Hero (0.93, 0.13 away), even though only
    Gym Hero is labeled pop.
    """
    pop = PROFILES["Default pop/happy"]
    ranked = top_titles(pop, ENERGY_FOCUSED)
    assert ranked.index("Rooftop Lights") < ranked.index("Gym Hero")


def test_incomplete_mode_is_rejected():
    """A mode that misspells or leaves out a core rule fails when it is created,
    not later in the middle of scoring.
    """
    with pytest.raises(ValueError):
        ScoringMode(name="broken", description="typo in a rule name",
                    weights={**BALANCED.weights, "temp_bpm": 0.5})


def test_recommender_class_uses_its_mode():
    """The OOP Recommender ranks with the mode it was given: a genre match wins in
    balanced mode, and a mood match wins in mood-first.
    """
    common = dict(artist="Test", energy=0.5, tempo_bpm=100, valence=0.5,
                  danceability=0.5, acousticness=0.5)
    songs = [Song(id=1, title="Genre Match", genre="pop", mood="intense", **common),
             Song(id=2, title="Mood Match", genre="rock", mood="happy", **common)]
    user = UserProfile(favorite_genre="pop", favorite_mood="happy",
                       target_energy=0.5, likes_acoustic=False)

    assert Recommender(songs).recommend(user, k=1)[0].title == "Genre Match"
    assert Recommender(songs, mode=MOOD_FIRST).recommend(user, k=1)[0].title == "Mood Match"


def test_cli_mode_switch():
    """--mode defaults to balanced, accepts every registered mode, and rejects
    unknown names (argparse exits with an error listing the valid choices).
    """
    assert parse_args([]).mode == "balanced"
    for name in SCORING_MODES:
        assert parse_args(["--mode", name]).mode == name
    with pytest.raises(SystemExit):
        parse_args(["--mode", "loudest"])
