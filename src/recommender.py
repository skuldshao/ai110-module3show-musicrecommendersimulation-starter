"""
Core logic for the Music Recommender Simulation.

Pipeline (see "Data Flow" in README.md):
    load_songs()      read data/songs.csv into a list of song dicts
    score_song()      judge ONE song against the user's preferences -> (score, reasons)
    explain_reasons() join those reasons into the one-line explanation users see
    recommend_songs() judge EVERY song, sort highest first, return the top k
    diversify()       optional re-rank that penalizes repeated artists / genres
    max_score_for()   the most points a given profile could earn (shown as "x / max")

Challenge 1 added five advanced song attributes (popularity, release_decade,
mood_tags, instrumentalness, lyrics_language). Their rules are opt-in: they only
score when a profile sets the matching preference (see the block after MAX_SCORE).

Challenge 2 added scoring modes (Strategy pattern): each ScoringMode is a named set of
weights for the seven core rules, and score_song() / recommend_songs() take a `mode`
argument. The default "balanced" mode is the original recipe, so calls without a mode
behave exactly as before. Modes live in SCORING_MODES; main.py picks one via --mode.

Challenge 3 added an optional diversity penalty (DiversityPolicy + diversify()): the
top k is filled one slot at a time, and a song loses points for every song by the
same artist, or in the same genre, already picked. It is off unless recommend_songs()
gets a `diversity` policy (main.py: --diverse), and it works with any scoring mode.

The CLI (src/main.py) uses the functions above, and src/summary_table.py turns their
results into the --table view (Challenge 4). The Recommender class offers the same
scoring as an object-oriented interface over Song / UserProfile dataclasses, which
is what tests/test_recommender.py exercises.

All scoring weights live in the constants and ScoringMode objects below, so
experiments only need to edit this block rather than the functions. The Step 3
"Weight Shift" experiment is one switch, WEIGHT_SHIFT_EXPERIMENT, rather than
hand-edited numbers, so the baseline and experimental weights can both be rerun
(see "Experiments You Tried" in README.md). It changes the balanced mode only.
"""

import csv
from collections import Counter
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

# Columns in songs.csv that load_songs() converts from str, so scoring can do math or
# set lookups on them. Every other column (title, artist, genre, mood,
# lyrics_language) stays a string.
FLOAT_FIELDS = ("energy", "tempo_bpm", "valence",
                "danceability", "acousticness", "instrumentalness")
INT_FIELDS = ("id", "popularity", "release_decade")
# Multi-value columns stored as "tag|tag|tag" in the CSV and split into lists.
LIST_FIELDS = ("mood_tags",)
LIST_SEPARATOR = "|"

# Step 3 data experiment ("Weight Shift"): True doubles energy's weight (1.5 -> 3.0)
# and halves genre's (2.0 -> 1.0), which raises MAX_SCORE from 7.0 to 7.5. It tests how
# much the rankings depend on the genre label vs. how loud a song is.
# Left False so the baseline results in README.md and model_card.md stay reproducible;
# set it to True and rerun `python -m src.main` to see the experimental rankings.
WEIGHT_SHIFT_EXPERIMENT = False

# Baseline weights from the README's Algorithm Recipe (max total 7.0). They feed the
# default "balanced" ScoringMode below; the other modes set their own weights.
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

# Numeric closeness rules: (song field, user_prefs key, distance scale).
# "distance scale" converts the raw gap onto 0-1: the 0-1 features use 1.0 (no change),
# tempo divides its BPM gap by TEMPO_RANGE_BPM. How many points each rule is worth is
# NOT stored here: it comes from the active ScoringMode, keyed by the song field name.
NUMERIC_RULES = (
    ("energy", "target_energy", 1.0),
    ("valence", "target_valence", 1.0),                  # happy vs. dark
    ("danceability", "target_danceability", 1.0),        # groove
    ("tempo_bpm", "target_tempo_bpm", TEMPO_RANGE_BPM),  # speed
)

# ---- Challenge 2: scoring modes (Strategy pattern) ------------------------------
# The seven core rules every ScoringMode must give a weight to. The numeric ones use
# their song field name, so score_song() can look up weights[feature] directly.
CORE_RULES = ("genre", "mood", "energy", "valence",
              "danceability", "tempo_bpm", "acoustic")


@dataclass(frozen=True)
class ScoringMode:
    """One ranking strategy: how many points each core rule is worth.

    This is the Strategy pattern in its simplest form. Every mode has the same
    interface (a name, a description, and a weight per core rule), so score_song()
    and recommend_songs() can rank with any of them without knowing which one they
    got. The modes all use the same rules and differ only in how much each counts,
    so a mode is plain data rather than a subclass with its own scoring code.
    To add a mode, create one ScoringMode below and list it in SCORING_MODES.

    frozen=True makes modes read-only, so no code can quietly change a weight
    while ranking.

    Attributes:
        name: Short id used on the command line, e.g. "mood-first".
        description: One line printed when the mode is active.
        weights: Max points for each rule name in CORE_RULES.
    """
    name: str
    description: str
    weights: Dict[str, float]

    def __post_init__(self):
        """Fail fast if a mode forgets or misspells a core rule's weight.

        Without this check, a typo like "temp_bpm" would only surface as a KeyError
        in the middle of scoring.

        Raises:
            ValueError: If weights is missing a name in CORE_RULES or has an extra one.
        """
        missing = set(CORE_RULES) - set(self.weights)
        unknown = set(self.weights) - set(CORE_RULES)
        if missing or unknown:
            raise ValueError(f"ScoringMode {self.name!r}: missing weights "
                             f"{sorted(missing)}, unknown weights {sorted(unknown)}")

    @property
    def max_score(self) -> float:
        """Highest total the core rules can give in this mode (a perfect match on all)."""
        return sum(self.weights.values())


# The original recipe from the README, and the default: genre is the biggest prize
# and energy the biggest number. The only mode the Step 3 switch changes.
BALANCED = ScoringMode(
    name="balanced",
    description="The original recipe: genre is the biggest prize, energy the biggest number.",
    weights={"genre": GENRE_WEIGHT, "mood": MOOD_WEIGHT, "energy": ENERGY_WEIGHT,
             "valence": 0.5, "danceability": 0.5, "tempo_bpm": 0.5,
             "acoustic": ACOUSTIC_WEIGHT},
)

# Genre is worth more than all the other core rules combined (5.0 > 1+1+0.5*4 = 4.0),
# so every genre match outranks every song that misses it, and the other rules only
# sort songs within each group. (The optional Challenge 1 extras can add up to 3.0,
# so a profile that uses them can break this guarantee.)
GENRE_FIRST = ScoringMode(
    name="genre-first",
    description="Genre matches always rank first; everything else breaks ties.",
    weights={"genre": 5.0, "mood": 1.0, "energy": 1.0,
             "valence": 0.5, "danceability": 0.5, "tempo_bpm": 0.5, "acoustic": 0.5},
)

# Mirror image of genre-first: mood beats all other core rules combined (5.0 > 4.0).
# Built to fix the stress test's "sad listener got angry metal" result.
MOOD_FIRST = ScoringMode(
    name="mood-first",
    description="Mood matches always rank first; everything else breaks ties.",
    weights={"genre": 1.0, "mood": 5.0, "energy": 1.0,
             "valence": 0.5, "danceability": 0.5, "tempo_bpm": 0.5, "acoustic": 0.5},
)

# For activities like workouts or studying, where intensity matters more than style:
# energy and tempo hold 5.0 of the 7.5 points, and the genre and mood labels only 1.0.
ENERGY_FOCUSED = ScoringMode(
    name="energy-focused",
    description="Energy and tempo decide; genre and mood barely count.",
    weights={"genre": 0.5, "mood": 0.5, "energy": 4.0,
             "valence": 0.5, "danceability": 0.5, "tempo_bpm": 1.0, "acoustic": 0.5},
)

# Registry of every mode by its command-line name. main.py's --mode choices come
# from here, so a mode added above and listed here shows up automatically.
SCORING_MODES = {mode.name: mode for mode in
                 (BALANCED, GENRE_FIRST, MOOD_FIRST, ENERGY_FOCUSED)}
DEFAULT_MODE = BALANCED

# Highest possible total from the core rules in the DEFAULT mode (a perfect match on
# every one): 2 + 1 + 1.5 + 0.5 * 3 + 1 = 7.0 at baseline, 7.5 with the Step 3 switch.
# Derived from the weights so it stays correct if they change. Other modes have their
# own ScoringMode.max_score. The advanced rules below are opt-in, so max_score_for()
# adds their weights only for profiles that use them.
MAX_SCORE = DEFAULT_MODE.max_score

# ---- Challenge 1: advanced song features ---------------------------------------
# Five extra columns in songs.csv:
#   popularity        0-100, how well known the song is
#   release_decade    e.g. 1990 for a 90s song
#   mood_tags         2-3 detailed tags, e.g. "rainy|cozy|dreamy"
#   instrumentalness  0-1, 0 = all vocals, 1 = no vocals at all
#   lyrics_language   "english", "spanish", or "instrumental" (no lyrics)
# Every advanced rule is OPT-IN: it only scores when the profile sets the matching
# preference. The nine original profiles set none of them, so their scores, and the
# results documented in README.md and model_card.md, are exactly the same as before.
# Partial credit for detailed tags, unlike the all-or-nothing single mood label:
# a song with 1 of the user's 2 wanted tags earns half of this.
MOOD_TAG_WEIGHT = 1.0
LANGUAGE_WEIGHT = 0.5      # all-or-nothing match on lyrics_language
DECADE_RANGE_YEARS = 30.0  # release-year gap that counts as "completely different"

# (song field, user_prefs key, max points, distance scale), scored by the same
# closeness math in numeric_rule_points(). Unlike NUMERIC_RULES, the max points are
# fixed here, because scoring modes only reweight the seven core rules.
ADVANCED_NUMERIC_RULES = (
    # popularity: gap divided by 100. A low target favors lesser-known "hidden gems".
    ("popularity", "target_popularity", 0.5, 100.0),
    # release decade: same decade earns 0.5, 10 years off 0.33, 30+ years off 0.
    ("release_decade", "favorite_decade", 0.5, DECADE_RANGE_YEARS),
    # instrumentalness: e.g. a study listener who wants no vocals sets a high target.
    ("instrumentalness", "target_instrumentalness", 0.5, 1.0),
)

# ---- Challenge 3: diversity penalty -------------------------------------------


@dataclass(frozen=True)
class DiversityPolicy:
    """How strongly diversify() discourages repeats within one top-k list.

    While the list is being filled, a candidate song loses artist_penalty points for
    EACH song by the same artist already picked, and genre_penalty points for EACH
    song in the same genre already picked. Penalties stack, so a third lofi song pays
    twice the genre penalty of the second. They only affect ranking within one list:
    the same song can still appear in many different listeners' lists.

    frozen=True makes a policy read-only, like ScoringMode.

    Attributes:
        artist_penalty: Points removed per already-picked song by the same artist.
        genre_penalty: Points removed per already-picked song in the same genre.
    """
    # Default sizes, on the balanced mode's 7-point scale. A repeated artist costs
    # about as much as a perfect energy match is worth (1.5), so a second song by an
    # artist must beat the next-best song by that much to keep its place. A repeated
    # genre costs half that (0.75), because two songs from one genre can still sound
    # very different. Repeating both costs 2.25.
    artist_penalty: float = 1.5
    genre_penalty: float = 0.75


# The policy main.py uses for --diverse.
DEFAULT_DIVERSITY = DiversityPolicy()


@dataclass
class Song:
    """
    Represents a song and its attributes (the 10 core columns of data/songs.csv).
    Required by tests/test_recommender.py

    Only the OOP Recommender below uses this class. load_songs() and the CLI work
    with plain dicts instead, so a Song is never built from the real catalog.
    The five Challenge 1 columns are left out on purpose: UserProfile has no
    advanced preferences, so the OOP path never scores them.
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

    Holds only 4 of the 7 core preferences that score_song() understands. The CLI's
    user_prefs dicts also set target_valence, target_danceability and target_tempo_bpm
    (and can set the five optional advanced preferences), so the OOP Recommender
    scores only genre, mood, energy and acoustic fit.
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

    Feature support: scoring modes (Challenge 2) work here via `mode`. The Challenge 1
    advanced preferences don't (UserProfile has no fields for them), and neither does
    the Challenge 3 diversity penalty, which only recommend_songs() applies.
    """

    def __init__(self, songs: List[Song], mode: ScoringMode = DEFAULT_MODE):
        """Store the catalog to recommend from and the scoring mode to rank with.

        Args:
            songs: Song objects (not the dicts that load_songs() returns).
            mode: The ScoringMode (Challenge 2) used by recommend() and
                explain_recommendation(). Defaults to the original "balanced" recipe.
        """
        self.songs = songs
        self.mode = mode

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
            key=lambda song: score_song(prefs, asdict(song), self.mode)[0],
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
        _, reasons = score_song(asdict(user), asdict(song), self.mode)
        return explain_reasons(reasons)


def load_songs(csv_path: str) -> List[Dict]:
    """Read a songs CSV into a list of dicts, converting columns to usable types.

    Called by src/main.py once at startup; the result is passed to recommend_songs().

    Args:
        csv_path: Path to the songs CSV (e.g. "data/songs.csv"). Must have a header row
            with every column in INT_FIELDS, FLOAT_FIELDS and LIST_FIELDS, plus the
            text columns title, artist, genre, mood and lyrics_language.

    Returns:
        One dict per song, keyed by column name. INT_FIELDS become int, FLOAT_FIELDS
        become float (so they can be used in scoring math), and LIST_FIELDS become
        lists, e.g. "rainy|cozy|dreamy" -> ["rainy", "cozy", "dreamy"]. Text columns
        stay as strings.
    """
    print(f"Loading songs from {csv_path}...")
    songs = []
    # newline="" is what the csv module expects, so quoted fields with line breaks parse correctly.
    with open(csv_path, newline="", encoding="utf-8") as f:
        # DictReader uses the header row as keys, so each row is already a dict like
        # {"id": "1", "title": "Sunrise City", ..., "energy": "0.82", ...}.
        for row in csv.DictReader(f):
            # csv gives every field as a string; convert columns so we can do math later
            for field in INT_FIELDS:
                row[field] = int(row[field])
            for field in FLOAT_FIELDS:
                row[field] = float(row[field])
            # "rainy|cozy|dreamy" -> ["rainy", "cozy", "dreamy"]; strip() forgives
            # stray spaces such as "rainy | cozy".
            for field in LIST_FIELDS:
                row[field] = [tag.strip() for tag in row[field].split(LIST_SEPARATOR)]
            songs.append(row)
    return songs


def score_song(user_prefs: Dict, song: Dict,
               mode: ScoringMode = DEFAULT_MODE) -> Tuple[float, List[str]]:
    """Score one song against the user's preferences and return (score, reasons).

    Called once per song by recommend_songs() (the CLI path) and by
    Recommender.recommend() / explain_recommendation() (the OOP path), so both
    paths always use the same rules and weights.

    The `mode` (Challenge 2) decides how many points each core rule is worth; the
    rules themselves are the same in every mode. In the default "balanced" mode this
    implements the Algorithm Recipe from the README (max 7.0 points):
        - +2.0 if genre matches favorite_genre, +1.0 if mood matches favorite_mood
        - closeness points for energy (x1.5) and valence / danceability / tempo (x0.5 each),
          where closeness = 1 - distance, so an exact match earns the full weight
        - up to +1.0 for acoustic fit: acousticness if likes_acoustic, else 1 - acousticness

    With WEIGHT_SHIFT_EXPERIMENT on, genre is worth +1.0 and energy x3.0 instead
    (max 7.5 points). The rules themselves don't change, only the weights they read.

    Optional advanced rules (Challenge 1, up to +3.0 more), each scored only when
    its preference is set:
        - closeness for popularity, release decade and instrumentalness (x0.5 each)
        - up to +1.0 for detailed mood tags: the share of the wanted tags the song has
        - +0.5 if lyrics_language matches preferred_language

    Any preference missing from user_prefs is skipped (earns 0 points) rather than
    guessed, so partial profiles still score without errors.

    Args:
        user_prefs: Taste profile with favorite_genre, favorite_mood, target_energy,
            target_valence, target_danceability, target_tempo_bpm, likes_acoustic,
            and optionally target_popularity, favorite_decade, preferred_mood_tags
            (a list), target_instrumentalness and preferred_language.
        song: One song dict as returned by load_songs().
        mode: The ScoringMode whose weights to use, e.g. MOOD_FIRST. Defaults to
            the original "balanced" recipe, so existing callers are unchanged.

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
    # The active strategy's weights, e.g. {"genre": 2.0, "mood": 1.0, ...} in balanced
    # mode. Every core rule below reads its max points from here, not from a constant.
    weights = mode.weights

    # Categorical matches: all-or-nothing, case-insensitive exact string match.
    # .get() returns None for a missing pref, and `if genre and ...` then skips the rule.
    # Note "indie pop" != "pop": near-miss labels earn nothing (see README Expected Biases).
    genre = user_prefs.get("favorite_genre")
    if genre and song["genre"].lower() == genre.lower():
        score += weights["genre"]
        reasons.append(f"genre match: {song['genre']} (+{weights['genre']})")

    # Same all-or-nothing rule for mood. In balanced mode it is worth half as much as
    # genre; in mood-first mode it outweighs every other core rule combined.
    mood = user_prefs.get("favorite_mood")
    if mood and song["mood"].lower() == mood.lower():
        score += weights["mood"]
        reasons.append(f"mood match: {song['mood']} (+{weights['mood']})")

    # Numeric closeness for energy / valence / danceability / tempo; the math lives in
    # numeric_rule_points(). Each (field, pref key, scale) rule gets its max points from
    # the mode, giving the (field, pref key, max points, scale) shape the helper expects.
    # The distance is the plain gap, so how well a rule can separate songs depends on
    # where the target sits in the catalog. For energy, a 0.9 target spreads the 20
    # songs over 1.00 point (balanced mode), but a 0.65 target spreads them over only
    # 0.50, because no song sits between 0.55 and 0.75 (see "Limitations and Bias" in
    # model_card.md).
    core_rules = [(feature, target_key, weights[feature], scale)
                  for feature, target_key, scale in NUMERIC_RULES]
    for points, reason in numeric_rule_points(core_rules, user_prefs, song):
        score += points
        reasons.append(reason)

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
        points = weights["acoustic"] * fit
        score += points
        label = "acoustic" if likes_acoustic else "non-acoustic"
        reasons.append(
            f"{label} fit, acousticness {song['acousticness']:g} (+{points:.2f})")

    # ---- Advanced features (Challenge 1) ----
    # Every rule below is opt-in, so a profile that sets none of these prefs gets
    # exactly the score it got before Challenge 1 (nothing below adds to `score`).
    # Their weights are fixed constants: scoring modes only reweight the core rules.

    # Popularity / release decade / instrumentalness: same closeness math as the core
    # numeric rules, just with their own scales (see ADVANCED_NUMERIC_RULES).
    for points, reason in numeric_rule_points(ADVANCED_NUMERIC_RULES, user_prefs, song):
        score += points
        reasons.append(reason)

    # Detailed mood tags: PARTIAL credit, unlike the all-or-nothing mood label. A user
    # who wants ["upbeat", "sunny"] earns half of MOOD_TAG_WEIGHT from a song tagged
    # "pumped|aggressive|upbeat" (1 of 2) and all of it from "upbeat|sunny|carefree".
    wanted_tags = user_prefs.get("preferred_mood_tags")
    if wanted_tags:
        # Accept a single tag given as a plain string, e.g. "cozy". Without this, the
        # loop below would walk the string letter by letter ("c", "o", "z", "y").
        if isinstance(wanted_tags, str):
            wanted_tags = [wanted_tags]
        # A set gives fast "is this tag on the song?" checks; lowercase both sides so
        # "Cozy" still matches "cozy", like the genre and mood rules.
        song_tags = {tag.lower() for tag in song["mood_tags"]}
        matched = [tag for tag in wanted_tags if tag.lower() in song_tags]
        # Like genre/mood, add a reason only when something matched.
        if matched:
            points = MOOD_TAG_WEIGHT * len(matched) / len(wanted_tags)
            score += points
            reasons.append(
                f"mood tags matched: {', '.join(matched)} "
                f"({len(matched)} of {len(wanted_tags)}) (+{points:.2f})")

    # Lyrics language: all-or-nothing, case-insensitive, like genre. "instrumental"
    # is a value the user can ask for too, meaning "no lyrics, please".
    language = user_prefs.get("preferred_language")
    if language and song["lyrics_language"].lower() == language.lower():
        score += LANGUAGE_WEIGHT
        reasons.append(
            f"language match: {song['lyrics_language']} (+{LANGUAGE_WEIGHT})")

    # Round only the final total (not each step) so rounding errors don't accumulate.
    return round(score, 2), reasons


def numeric_rule_points(rules: Tuple, user_prefs: Dict, song: Dict) -> List[Tuple[float, str]]:
    """Apply closeness rules to one song and return (points, reason) per rule used.

    Shared by the core NUMERIC_RULES (with max points filled in from the scoring
    mode) and the Challenge 1 ADVANCED_NUMERIC_RULES, so every numeric feature is
    scored with the same math: weight * (1 - distance).

    Args:
        rules: (song field, user_prefs key, max points, distance scale) tuples.
        user_prefs: The taste profile; rules whose key is missing are skipped.
        song: One song dict as returned by load_songs().

    Returns:
        One (points, reason) pair per rule whose preference is set, in rule order,
        e.g. (1.47, "energy 0.82 vs target 0.8 (+1.47)"). Points are 0 to the
        rule's max, never negative, even for out-of-range targets.
    """
    results = []
    for feature, target_key, weight, scale in rules:
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
        # :g drops trailing zeros (0.40 -> 0.4, 80.0 -> 80); points show 2 decimals.
        results.append(
            (points, f"{feature} {song[feature]:g} vs target {target:g} (+{points:.2f})"))
    return results


def max_score_for(user_prefs: Dict, mode: ScoringMode = DEFAULT_MODE) -> float:
    """Return the most points this profile could earn, for display as "x / max".

    The core rules always count (mode.max_score: 7.0 in balanced mode, as before
    Challenge 1). Each advanced rule adds its weight only if the profile sets its
    preference, because a profile that never asks about popularity can't earn
    popularity points. So in balanced mode the nine original profiles still show
    "/ 7.00", and a profile that uses every advanced preference shows "/ 10.00".

    Args:
        user_prefs: The taste profile passed to score_song().
        mode: The ScoringMode the profile is scored with (Challenge 2). Defaults
            to the original "balanced" recipe.

    Returns:
        The mode's core maximum plus the weights of the advanced rules this
        profile uses.
    """
    ceiling = mode.max_score
    # rule[1] is the user_prefs key and rule[2] the max points of each tuple.
    for rule in ADVANCED_NUMERIC_RULES:
        if user_prefs.get(rule[1]) is not None:
            ceiling += rule[2]
    # Same truthiness checks score_song() uses, so the two always agree.
    if user_prefs.get("preferred_mood_tags"):
        ceiling += MOOD_TAG_WEIGHT
    if user_prefs.get("preferred_language"):
        ceiling += LANGUAGE_WEIGHT
    return ceiling


def explain_reasons(reasons: List[str]) -> str:
    """Join score_song()'s reasons into the one-line explanation shown to users.

    Shared by recommend_songs() and Recommender.explain_recommendation(), so the
    functional (CLI) and OOP paths always word explanations the same way.

    Args:
        reasons: The reasons list from score_song(); may be empty.

    Returns:
        The reasons joined with "; " (main.py splits on "; " to print one bullet
        per reason, and summary_table.py to make one tag per reason), or
        "no preferences matched" if the list is empty, which only happens when
        every preference was missing (e.g. an empty profile).
    """
    # An empty list joins to "", which is falsy, so `or` swaps in the fallback text.
    return "; ".join(reasons) or "no preferences matched"


def diversify(ranked: List[Tuple[Dict, float, List[str]]], k: int,
              policy: DiversityPolicy) -> List[Tuple[Dict, float, List[str]]]:
    """Re-rank scored songs so one artist or genre can't crowd the top k (Challenge 3).

    A plain sort judges every song on its own. This fills the list one slot at a
    time instead. For each slot, every song not yet picked gets an adjusted score:

        adjusted = score - artist_penalty * (songs by its artist already picked)
                         - genre_penalty  * (songs in its genre already picked)

    The highest adjusted score takes the slot, then the counts are updated. The
    first pick is never penalized, so #1 is always the plain top song.

    Args:
        ranked: (song, score, reasons) triples already sorted highest score first,
            as built inside recommend_songs(). Not modified.
        k: How many songs to pick. A k larger than the list returns every song.
        policy: The penalty sizes to apply.

    Returns:
        Up to k (song, adjusted score, reasons) triples in pick order. Each penalized
        song gets an extra reason per penalty, e.g. "diversity penalty: 1 song by
        LoRoom already picked (-1.50)", so the explanation shows the deduction. The
        adjusted score is rounded to 2 decimals. It can drop below 0 if every
        remaining song is a repeat.
    """
    remaining = list(ranked)    # copy, so pop() below doesn't change the caller's list
    picked = []
    # How many songs per artist / genre are already in the list. Counter returns 0
    # for anything not seen yet. Keys are lowercased so "LoRoom" and "loroom" (or
    # "Pop" and "pop") count as the same, like the genre and mood matching rules.
    artists_picked = Counter()
    genres_picked = Counter()

    while remaining and len(picked) < k:
        best_index, best_adjusted = 0, None
        for index, (song, score, _) in enumerate(remaining):
            adjusted = (score
                        - policy.artist_penalty * artists_picked[song["artist"].lower()]
                        - policy.genre_penalty * genres_picked[song["genre"].lower()])
            # Strict ">" keeps the EARLIER song on a tie. `remaining` is in score
            # order (and CSV order among equal scores), so ties still break the way a
            # plain sort would.
            if best_adjusted is None or adjusted > best_adjusted:
                best_index, best_adjusted = index, adjusted

        song, score, reasons = remaining.pop(best_index)
        artist_key, genre_key = song["artist"].lower(), song["genre"].lower()

        # Explain each deduction in plain words. Build a NEW list (reasons + ...)
        # rather than appending, so the caller's reasons lists stay untouched.
        penalty_reasons = []
        if artists_picked[artist_key]:
            count = artists_picked[artist_key]
            penalty_reasons.append(
                f"diversity penalty: {count} song{'s' if count > 1 else ''} by "
                f"{song['artist']} already picked (-{policy.artist_penalty * count:.2f})")
        if genres_picked[genre_key]:
            count = genres_picked[genre_key]
            penalty_reasons.append(
                f"diversity penalty: {count} {song['genre']} "
                f"song{'s' if count > 1 else ''} already picked "
                f"(-{policy.genre_penalty * count:.2f})")

        picked.append((song, round(best_adjusted, 2), reasons + penalty_reasons))
        artists_picked[artist_key] += 1
        genres_picked[genre_key] += 1

    return picked


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    mode: ScoringMode = DEFAULT_MODE,
                    diversity: Optional[DiversityPolicy] = None) -> List[Tuple[Dict, float, str]]:
    """Rank every song with score_song() and return the top k, highest score first.

    Functional implementation of the recommendation logic, called by src/main.py
    once per taste profile.

    Recommending is ranking: score_song() acts as the judge for every song in the
    catalog, then the scored list is sorted from highest to lowest and cut to k.
    The mode (Challenge 2) is the ranking strategy: the same songs and profile can
    rank differently under, say, MOOD_FIRST than under the default BALANCED.
    With a diversity policy (Challenge 3), the cut to k is done by diversify()
    instead, which penalizes repeated artists and genres.

    Args:
        user_prefs: Taste profile passed straight through to score_song().
        songs: Full catalog as returned by load_songs(). It is not modified.
        k: How many recommendations to return. If k exceeds the catalog size,
            every song is returned; k <= 0 returns an empty list.
        mode: The ScoringMode passed to score_song() for every song. Defaults to
            the original "balanced" recipe.
        diversity: A DiversityPolicy to spread out artists and genres, or None (the
            default) for the plain ranking, exactly as before Challenge 3.

    Returns:
        Up to k (song_dict, score, explanation) tuples, highest score first (with
        diversity: in pick order, scores after penalties). The explanation comes
        from explain_reasons(): score_song()'s reasons joined with "; ", or
        "no preferences matched" if no rule applied at all.
    """
    # Guard clause: nothing requested, so skip scoring the whole catalog.
    if k <= 0:
        return []

    # Judge every song once. Each score_song() call returns (score, reasons), so the
    # comprehension builds one (song, score, reasons) triple per catalog entry.
    # The * unpacks that pair in place: (song, *(6.73, [...])) -> (song, 6.73, [...]).
    # Every song is judged with the same mode, so rankings within one list are fair.
    scored = [(song, *score_song(user_prefs, song, mode)) for song in songs]

    # sorted() returns a NEW list and leaves `scored` (and the caller's `songs`) in
    # their original order; list.sort() would reorder in place and return None.
    # key=item[1] ranks by score; reverse=True puts the highest score first.
    # Python's sort is stable, so songs with tied scores keep their CSV order. That is
    # why an empty profile (every song tied at 0.00) gets the first five CSV rows.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Optional Challenge 3 step: re-pick the top k with repeat penalties. diversify()
    # returns at most k songs, so the [:k] slice below leaves its result unchanged.
    if diversity is not None:
        ranked = diversify(ranked, k, diversity)

    # Keep only the top k (slicing past the end is safe) and turn each reasons list
    # into the single explanation string main.py prints (see explain_reasons()).
    return [
        (song, score, explain_reasons(reasons))
        for song, score, reasons in ranked[:k]
    ]
