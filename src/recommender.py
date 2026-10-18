"""
Core logic for the Music Recommender Simulation.

Pipeline (see "Data Flow" in README.md):
    load_songs()      read data/songs.csv into a list of song dicts
    score_song()      judge ONE song against the user's preferences -> (score, reasons)
    recommend_songs() judge EVERY song, sort highest first, return the top k

All scoring weights live in the constants below, so experiments only need to edit
this block rather than the functions.
"""

import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Numeric columns in songs.csv that load_songs() converts from str to float.
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence",
                "danceability", "acousticness")

# Scoring weights for score_song(), from the README's Algorithm Recipe (max total 7.0).
GENRE_WEIGHT = 2.0     # strongest signal: 17 genres across 20 songs, so a match is rare
MOOD_WEIGHT = 1.0      # half of genre: moods overlap (chill / relaxed / laid-back)
ACOUSTIC_WEIGHT = 1.0  # max points for matching the user's acoustic vs. electronic taste
TEMPO_RANGE_BPM = 100.0  # tempo gap that counts as "completely different"

# Numeric closeness rules: (song field, user_prefs key, max points, distance scale).
# "distance scale" converts the raw gap onto 0-1: the 0-1 features use 1.0 (no change),
# tempo divides its BPM gap by TEMPO_RANGE_BPM. Add a tuple here to score a new feature.
NUMERIC_RULES = (
    ("energy", "target_energy", 1.5, 1.0),           # most spread-out feature, weighted highest
    ("valence", "target_valence", 0.5, 1.0),         # fine-tuning: happy vs. dark
    ("danceability", "target_danceability", 0.5, 1.0),  # fine-tuning: groove
    ("tempo_bpm", "target_tempo_bpm", 0.5, TEMPO_RANGE_BPM),  # fine-tuning: speed
)

# Highest possible score_song() total (a perfect match on every rule); main.py shows
# scores as "x / MAX_SCORE". Derived from the weights so it stays correct if they change.
# rule[2] is the "max points" slot of each NUMERIC_RULES tuple: 2 + 1 + 1 + (1.5 + 0.5 * 3) = 7.0
MAX_SCORE = GENRE_WEIGHT + MOOD_WEIGHT + ACOUSTIC_WEIGHT + sum(rule[2] for rule in NUMERIC_RULES)


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"


def load_songs(csv_path: str) -> List[Dict]:
    """Read a songs CSV into a list of dicts, converting numeric columns to int/float.

    Called by src/main.py once at startup; the result is passed to recommend_songs().

    Args:
        csv_path: Path to the songs CSV (e.g. "data/songs.csv"). Must have a header row
            with id, title, artist, genre, mood, and the numeric FLOAT_FIELDS columns.

    Returns:
        One dict per song, keyed by column name. "id" is converted to int and every
        column in FLOAT_FIELDS to float so they can be used in scoring math; text
        columns (title, artist, genre, mood) stay as strings.
    """
    print(f"Loading songs from {csv_path}...")
    songs = []
    # newline="" is what the csv module expects, so quoted fields with line breaks parse correctly.
    with open(csv_path, newline="", encoding="utf-8") as f:
        # DictReader uses the header row as keys, so each row is already a dict like
        # {"id": "1", "title": "Sunrise City", ..., "energy": "0.82", ...}.
        for row in csv.DictReader(f):
            # csv gives every field as a string; convert numeric columns so we can do math later
            row["id"] = int(row["id"])
            for field in FLOAT_FIELDS:
                row[field] = float(row[field])
            songs.append(row)
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against the user's preferences and return (score, reasons).

    Called by recommend_songs() once per song in the catalog.

    Implements the Algorithm Recipe from the README (max 7.0 points):
        - +2.0 if genre matches favorite_genre, +1.0 if mood matches favorite_mood
        - closeness points for energy (x1.5) and valence / danceability / tempo (x0.5 each),
          where closeness = 1 - distance, so an exact match earns the full weight
        - up to +1.0 for acoustic fit: acousticness if likes_acoustic, else 1 - acousticness

    Any preference missing from user_prefs is skipped (earns 0 points) rather than
    guessed, so partial profiles still score without errors.

    Args:
        user_prefs: Taste profile with favorite_genre, favorite_mood, target_energy,
            target_valence, target_danceability, target_tempo_bpm, likes_acoustic.
        song: One song dict as returned by load_songs().

    Returns:
        (score, reasons): the total score rounded to 2 decimals, and one
        human-readable reason per rule that awarded points, e.g. "genre match: pop (+2.0)"
        or "energy 0.82 vs target 0.8 (+1.47)". Rules that were skipped add no reason.
    """
    score = 0.0    # running total; each rule below adds its points here
    reasons = []   # one string per rule that awarded points, shown to the user as "Why"

    # Categorical matches: all-or-nothing, case-insensitive exact string match.
    # .get() returns None for a missing pref, and `if genre and ...` then skips the rule.
    # Note "indie pop" != "pop": near-miss labels earn nothing (see README Expected Biases).
    genre = user_prefs.get("favorite_genre")
    if genre and song["genre"].lower() == genre.lower():
        score += GENRE_WEIGHT
        reasons.append(f"genre match: {song['genre']} (+{GENRE_WEIGHT})")

    # Same all-or-nothing rule for mood, worth half as much as genre.
    mood = user_prefs.get("favorite_mood")
    if mood and song["mood"].lower() == mood.lower():
        score += MOOD_WEIGHT
        reasons.append(f"mood match: {song['mood']} (+{MOOD_WEIGHT})")

    # Numeric closeness: weight * (1 - distance). Features are on a 0-1 scale except
    # tempo, which is divided by TEMPO_RANGE_BPM and capped so distance stays in 0-1.
    for feature, target_key, weight, scale in NUMERIC_RULES:
        target = user_prefs.get(target_key)
        # Compare against None (not falsiness) so a real target of 0.0 is still scored.
        if target is None:
            continue
        # e.g. energy 0.35 vs target 0.40 -> distance 0.05; tempo 72 vs 80 -> 8/100 = 0.08.
        # min(..., 1.0) stops huge tempo gaps (e.g. 168 vs 60 BPM) from going negative.
        distance = min(abs(song[feature] - target) / scale, 1.0)
        # Flip distance into closeness: exact match earns the full weight, max gap earns 0.
        points = weight * (1.0 - distance)
        score += points
        # :g drops trailing zeros (0.40 -> 0.4, 80.0 -> 80); points show 2 decimals.
        reasons.append(
            f"{feature} {song[feature]:g} vs target {target:g} (+{points:.2f})"
        )

    # Acoustic fit: reward acoustic songs for acoustic fans, electronic songs otherwise.
    # `is not None` matters here: likes_acoustic=False is a real preference, not "missing".
    likes_acoustic = user_prefs.get("likes_acoustic")
    if likes_acoustic is not None:
        fit = song["acousticness"] if likes_acoustic else 1.0 - \
            song["acousticness"]
        points = ACOUSTIC_WEIGHT * fit
        score += points
        label = "acoustic" if likes_acoustic else "non-acoustic"
        reasons.append(
            f"{label} fit, acousticness {song['acousticness']:g} (+{points:.2f})")

    # Round only the final total (not each step) so rounding errors don't accumulate.
    return round(score, 2), reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Rank every song with score_song() and return the top k, highest score first.

    Functional implementation of the recommendation logic, called by src/main.py
    once per taste profile.

    Recommending is ranking: score_song() acts as the judge for every song in the
    catalog, then the scored list is sorted from highest to lowest and cut to k.

    Args:
        user_prefs: Taste profile passed straight through to score_song().
        songs: Full catalog as returned by load_songs(). It is not modified.
        k: How many recommendations to return. If k exceeds the catalog size,
            every song is returned; k <= 0 returns an empty list.

    Returns:
        Up to k (song_dict, score, explanation) tuples, highest score first.
        The explanation joins score_song()'s reasons with "; ", or says no
        preferences matched if the song earned no points at all.
    """
    # Guard clause: nothing requested, so skip scoring the whole catalog.
    if k <= 0:
        return []

    # Judge every song once. Each score_song() call returns (score, reasons), so the
    # comprehension builds one (song, score, reasons) triple per catalog entry.
    # The * unpacks that pair in place: (song, *(6.73, [...])) -> (song, 6.73, [...]).
    scored = [(song, *score_song(user_prefs, song)) for song in songs]

    # sorted() returns a NEW list and leaves `scored` (and the caller's `songs`) in
    # their original order; list.sort() would reorder in place and return None.
    # key=item[1] ranks by score; reverse=True puts the highest score first.
    # Python's sort is stable, so songs with tied scores keep their CSV order.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Keep only the top k (slicing past the end is safe) and turn each reasons list
    # into a single "; "-separated string. main.py splits it back on "; " to print one
    # bullet per reason. An empty list joins to "", which is falsy, so `or` swaps in a
    # fallback message for songs that earned no points.
    return [
        (song, score, "; ".join(reasons) or "no preferences matched")
        for song, score, reasons in ranked[:k]
    ]
