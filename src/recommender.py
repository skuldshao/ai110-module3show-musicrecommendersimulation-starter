"""
Core logic for the Music Recommender Simulation.

Pipeline (see "Data Flow" in README.md):
    load_songs()      read data/songs.csv into a list of song dicts
    score_song()      judge ONE song against the user's preferences -> (score, reasons)
    explain_reasons() join those reasons into the one-line explanation users see
    recommend_songs() judge EVERY song, sort highest first, return the top k

The CLI (src/main.py) uses the functions above. The Recommender class offers the
same scoring as an object-oriented interface over Song / UserProfile dataclasses,
which is what tests/test_recommender.py exercises.

All scoring weights live in the constants below, so experiments only need to edit
this block rather than the functions. The Step 3 "Weight Shift" experiment is one
switch, WEIGHT_SHIFT_EXPERIMENT, rather than hand-edited numbers, so the baseline
and experimental weights can both be rerun (see "Experiments You Tried" in README.md).
"""

import csv
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict

# Numeric columns in songs.csv that load_songs() converts from str to float.
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence",
                "danceability", "acousticness")

# Step 3 data experiment ("Weight Shift"): True doubles energy's weight (1.5 -> 3.0)
# and halves genre's (2.0 -> 1.0), which raises MAX_SCORE from 7.0 to 7.5. It tests how
# much the rankings depend on the genre label vs. how loud a song is.
# Left False so the baseline results in README.md and model_card.md stay reproducible;
# set it to True and rerun `python -m src.main` to see the experimental rankings.
WEIGHT_SHIFT_EXPERIMENT = False

# Scoring weights for score_song(), from the README's Algorithm Recipe (max total 7.0).
# The two `x if WEIGHT_SHIFT_EXPERIMENT else y` lines pick the experimental value x
# when the switch is on and the baseline value y otherwise.
# Genre: the strongest signal at baseline (17 genres across 20 songs, so a match is rare).
GENRE_WEIGHT = 1.0 if WEIGHT_SHIFT_EXPERIMENT else 2.0
# Mood: half of genre at baseline, because moods overlap (chill / relaxed / laid-back).
MOOD_WEIGHT = 1.0
# Energy: the most spread-out feature (0.22-0.98), so it gets the biggest numeric weight.
# Known weakness: the catalog has NO songs between 0.55 and 0.75, so this rule serves
# medium-energy listeners poorly (see "Limitations and Bias" in model_card.md).
ENERGY_WEIGHT = 3.0 if WEIGHT_SHIFT_EXPERIMENT else 1.5
ACOUSTIC_WEIGHT = 1.0  # max points for matching the user's acoustic vs. electronic taste
TEMPO_RANGE_BPM = 100.0  # tempo gap that counts as "completely different"

# Numeric closeness rules: (song field, user_prefs key, max points, distance scale).
# "distance scale" converts the raw gap onto 0-1: the 0-1 features use 1.0 (no change),
# tempo divides its BPM gap by TEMPO_RANGE_BPM. Add a tuple here to score a new feature.
NUMERIC_RULES = (
    # energy: worth ENERGY_WEIGHT (1.5 baseline, 3.0 in the experiment)
    ("energy", "target_energy", ENERGY_WEIGHT, 1.0),
    # fine-tuning: happy vs. dark
    ("valence", "target_valence", 0.5, 1.0),
    ("danceability", "target_danceability", 0.5, 1.0),  # fine-tuning: groove
    ("tempo_bpm", "target_tempo_bpm", 0.5, TEMPO_RANGE_BPM),  # fine-tuning: speed
)

# Highest possible score_song() total (a perfect match on every rule); main.py shows
# scores as "x / MAX_SCORE". Derived from the weights so it stays correct if they change.
# rule[2] is the "max points" slot of each NUMERIC_RULES tuple:
#   baseline:   2 + 1 + 1 + (1.5 + 0.5 * 3) = 7.0
#   experiment: 1 + 1 + 1 + (3.0 + 0.5 * 3) = 7.5
MAX_SCORE = GENRE_WEIGHT + MOOD_WEIGHT + ACOUSTIC_WEIGHT + \
    sum(rule[2] for rule in NUMERIC_RULES)


@dataclass
class Song:
    """
    Represents a song and its attributes (the same columns as data/songs.csv).
    Required by tests/test_recommender.py

    Only the OOP Recommender below uses this class. load_songs() and the CLI work
    with plain dicts instead, so a Song is never built from the real catalog.
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

    Holds only 4 of the 7 preferences that score_song() understands. The CLI's
    user_prefs dicts also set target_valence, target_danceability and target_tempo_bpm,
    so the OOP Recommender scores only genre, mood, energy and acoustic fit.
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """
    OOP interface for the recommendation logic.
    Required by tests/test_recommender.py

    A thin wrapper around the same score_song() the CLI uses, so both paths judge
    songs with identical rules and weights. The field names of Song and UserProfile
    match the dict keys score_song() reads, so dataclasses.asdict() converts them
    directly. The CLI (src/main.py) uses the functional recommend_songs() instead.
    """

    def __init__(self, songs: List[Song]):
        """Store the catalog to recommend from.

        Args:
            songs: Song objects (not the dicts that load_songs() returns).
        """
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the k songs that best match the user, highest score first.

        Args:
            user: The listener's preferences.
            k: How many songs to return. k <= 0 returns an empty list; a k larger
                than the catalog returns every song.

        Returns:
            Up to k Song objects ranked by score_song(). Songs with tied scores keep
            their list order, the same tie-break recommend_songs() uses.
        """
        # Same guard as recommend_songs(). Without it a negative k would slice from
        # the end (songs[:-1] is "all but the last") instead of returning nothing.
        if k <= 0:
            return []

        # asdict() turns the dataclass into {"favorite_genre": "pop", ...}, the same
        # user_prefs shape score_song() expects. Convert the user once, not per song.
        prefs = asdict(user)

        # Rank by score alone: score_song() returns (score, reasons), so [0] keeps
        # the score. sorted() is stable (even with reverse=True) and leaves
        # self.songs in its original order.
        ranked = sorted(
            self.songs,
            key=lambda song: score_song(prefs, asdict(song))[0],
            reverse=True,
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Explain a song's score for this user, one reason per rule that applied.

        Args:
            user: The listener's preferences.
            song: The song to explain.

        Returns:
            score_song()'s reasons joined with "; ", e.g.
            "genre match: pop (+2.0); mood match: happy (+1.0); energy 0.8 vs ...",
            worded exactly like the CLI's "Why:" bullets (see explain_reasons()).
        """
        # Only the reasons are needed here; the score itself is discarded with _.
        _, reasons = score_song(asdict(user), asdict(song))
        return explain_reasons(reasons)


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

    Called once per song by recommend_songs() (the CLI path) and by
    Recommender.recommend() / explain_recommendation() (the OOP path), so both
    paths always use the same rules and weights.

    Implements the Algorithm Recipe from the README (max 7.0 points):
        - +2.0 if genre matches favorite_genre, +1.0 if mood matches favorite_mood
        - closeness points for energy (x1.5) and valence / danceability / tempo (x0.5 each),
          where closeness = 1 - distance, so an exact match earns the full weight
        - up to +1.0 for acoustic fit: acousticness if likes_acoustic, else 1 - acousticness

    With WEIGHT_SHIFT_EXPERIMENT on, genre is worth +1.0 and energy x3.0 instead
    (max 7.5 points). The rules themselves don't change, only the weights they read.

    Any preference missing from user_prefs is skipped (earns 0 points) rather than
    guessed, so partial profiles still score without errors.

    Args:
        user_prefs: Taste profile with favorite_genre, favorite_mood, target_energy,
            target_valence, target_danceability, target_tempo_bpm, likes_acoustic.
        song: One song dict as returned by load_songs().

    Returns:
        (score, reasons): the total score rounded to 2 decimals, and one
        human-readable reason per rule that was applied, e.g. "genre match: pop (+2.0)"
        or "energy 0.82 vs target 0.8 (+1.47)". Genre/mood add a reason only on a
        match, but the numeric and acoustic rules always add one when their pref is
        set, even if they earn +0.00 (see the out-of-range stress test in README.md).
        Rules skipped because the pref is missing add no reason.
    """
    score = 0.0    # running total; each rule below adds its points here
    reasons = []   # one string per rule that was applied, shown to the user as "Why"

    # Categorical matches: all-or-nothing, case-insensitive exact string match.
    # .get() returns None for a missing pref, and `if genre and ...` then skips the rule.
    # Note "indie pop" != "pop": near-miss labels earn nothing (see README Expected Biases).
    genre = user_prefs.get("favorite_genre")
    if genre and song["genre"].lower() == genre.lower():
        score += GENRE_WEIGHT
        reasons.append(f"genre match: {song['genre']} (+{GENRE_WEIGHT})")

    # Same all-or-nothing rule for mood: half as much as genre at baseline, and equal
    # to genre under the weight-shift experiment.
    mood = user_prefs.get("favorite_mood")
    if mood and song["mood"].lower() == mood.lower():
        score += MOOD_WEIGHT
        reasons.append(f"mood match: {song['mood']} (+{MOOD_WEIGHT})")

    # Numeric closeness: weight * (1 - distance). Features are on a 0-1 scale except
    # tempo, which is divided by TEMPO_RANGE_BPM and capped so distance stays in 0-1.
    # The distance is the plain gap, so how well a rule can separate songs depends on
    # where the target sits in the catalog. For energy, a 0.9 target spreads the 20
    # songs over 1.00 point, but a 0.65 target spreads them over only 0.50, because no
    # song sits between 0.55 and 0.75 (see "Limitations and Bias" in model_card.md).
    for feature, target_key, weight, scale in NUMERIC_RULES:
        target = user_prefs.get(target_key)
        # Compare against None (not falsiness) so a real target of 0.0 is still scored.
        if target is None:
            continue
        # e.g. energy 0.35 vs target 0.40 -> distance 0.05; tempo 72 vs 80 -> 8/100 = 0.08.
        # min(..., 1.0) stops huge gaps from going negative: big tempo gaps (e.g. 168 vs
        # 60 BPM) and out-of-range targets (e.g. danceability 2.0) both earn 0, not < 0.
        distance = min(abs(song[feature] - target) / scale, 1.0)
        # Flip distance into closeness: exact match earns the full weight, max gap earns 0.
        points = weight * (1.0 - distance)
        score += points
        # :g drops trailing zeros (0.40 -> 0.4, 80.0 -> 80); points show 2 decimals.
        reasons.append(
            f"{feature} {song[feature]:g} vs target {target:g} (+{points:.2f})"
        )

    # Acoustic fit: reward acoustic songs for acoustic fans, electronic songs otherwise.
    # Unlike the numeric rules, this is "more is better", not closeness: the most
    # acoustic (or most electronic) song always gets the most points, and there is no
    # way to ask for "somewhat acoustic". In this catalog calm songs are acoustic and
    # loud songs are electronic, so this rule can outweigh the energy target for a
    # medium-energy listener (see "Limitations and Bias" in model_card.md).
    # `is not None` matters here: likes_acoustic=False is a real preference, not "missing".
    # Any truthy value counts as "likes acoustic", including the STRING "False"
    # (see the "likes_acoustic as string" stress test in README.md).
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


def explain_reasons(reasons: List[str]) -> str:
    """Join score_song()'s reasons into the one-line explanation shown to users.

    Shared by recommend_songs() and Recommender.explain_recommendation(), so the
    functional (CLI) and OOP paths always word explanations the same way.

    Args:
        reasons: The reasons list from score_song(); may be empty.

    Returns:
        The reasons joined with "; " (main.py splits on "; " to print one bullet
        per reason), or "no preferences matched" if the list is empty, which only
        happens when every preference was missing (e.g. an empty profile).
    """
    # An empty list joins to "", which is falsy, so `or` swaps in the fallback text.
    return "; ".join(reasons) or "no preferences matched"


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
        The explanation comes from explain_reasons(): score_song()'s reasons joined
        with "; ", or "no preferences matched" if no rule applied at all.
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
    # Python's sort is stable, so songs with tied scores keep their CSV order. That is
    # why an empty profile (every song tied at 0.00) gets the first five CSV rows.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Keep only the top k (slicing past the end is safe) and turn each reasons list
    # into the single explanation string main.py prints (see explain_reasons()).
    return [
        (song, score, explain_reasons(reasons))
        for song, score, reasons in ranked[:k]
    ]
