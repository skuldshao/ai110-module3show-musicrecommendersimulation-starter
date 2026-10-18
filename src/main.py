"""
Command line runner for the Music Recommender Simulation.

This is the CLI front end: it loads the catalog, runs every taste profile in
PROFILES (everyday listeners) and then EDGE_CASE_PROFILES (adversarial stress
tests) through recommend_songs(), and prints a ranked, explained top 5 for each.
The scoring and ranking logic itself lives in recommender.py:
- load_songs       read data/songs.csv
- score_song       judge one song -> (score, reasons)
- recommend_songs  judge every song, sort, keep the top k

Run from the project root with:  python -m src.main
"""

# Support both `python -m src.main` (package import) and `python src/main.py` (script import).
# With -m, Python runs from the project root, so the module is found as src.recommender.
# As a plain script, Python only searches src/ itself, so the module is just `recommender`.
# The weight constants are imported only so main() can announce the Step 3 experiment.
try:
    from src.recommender import (load_songs, recommend_songs, MAX_SCORE,
                                 WEIGHT_SHIFT_EXPERIMENT, GENRE_WEIGHT, ENERGY_WEIGHT)
except ModuleNotFoundError:
    from recommender import (load_songs, recommend_songs, MAX_SCORE,
                             WEIGHT_SHIFT_EXPERIMENT, GENRE_WEIGHT, ENERGY_WEIGHT)

# Width of the "=====" / "-----" rules that frame each section of terminal output.
LINE_WIDTH = 72

# Taste profiles to run, keyed by a display name.
# Categorical prefs are matched exactly; numeric targets are on the same 0.0-1.0
# scale as songs.csv (except tempo, which is in BPM).
PROFILES = {
    # The starter's default profile: an upbeat, danceable, mostly electronic pop fan.
    "Default pop/happy": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.80,
        "target_valence": 0.80,
        "target_danceability": 0.80,
        "target_tempo_bpm": 120,
        "likes_acoustic": False,
    },
    # A late-night study listener who wants calm, warm, acoustic tracks.
    "Late-night study (lofi/chill)": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
        "target_valence": 0.60,
        "target_danceability": 0.55,
        "target_tempo_bpm": 80,
        "likes_acoustic": True,
    },
    # A loud, fast, darker-sounding guitar listener (workout / headbanging).
    # The catalog has only ONE rock song, so this shows what fills slots #2-#5
    # once the genre bonus runs out.
    "Deep intense rock": {
        "favorite_genre": "rock",
        "favorite_mood": "intense",
        "target_energy": 0.90,
        "target_valence": 0.40,
        "target_danceability": 0.60,
        "target_tempo_bpm": 150,
        "likes_acoustic": False,
    },
}

# Adversarial "stress test" profiles, run after PROFILES. Each one is built to
# poke a specific weak spot in score_song() rather than to describe a real
# listener, so the comment above each says what it tests and what to look for.
EDGE_CASE_PROFILES = {
    # Conflicting prefs: the mood label says "sad", but the numbers ask for loud,
    # fast, electronic music. The only sad song (Pinewood Letters) is quiet acoustic
    # folk, so the label and the numbers point at different songs. Which side wins?
    "Edge: high energy + sad mood": {
        "favorite_mood": "sad",
        "target_energy": 0.90,
        "target_valence": 0.20,
        "target_danceability": 0.50,
        "target_tempo_bpm": 150,
        "likes_acoustic": False,
    },
    # Genre vs. everything else: asks for metal, but every numeric target describes
    # calm, happy, acoustic music. Can the genre bonus alone (+2.0 at baseline) drag the
    # one metal song (Iron Cathedral) into the top 5? "peaceful" matches no song's mood.
    "Edge: metal genre, calm acoustic numbers": {
        "favorite_genre": "metal",
        "favorite_mood": "peaceful",
        "target_energy": 0.20,
        "target_valence": 0.80,
        "target_danceability": 0.40,
        "target_tempo_bpm": 70,
        "likes_acoustic": True,
    },
    # Near-miss label: the catalog spells it "hip-hop". score_song() lowercases both
    # sides, so "Confident" still matches "confident", but a space instead of a
    # hyphen is a different string, so the whole genre bonus (+2.0 at baseline)
    # should silently vanish.
    "Edge: genre typo 'Hip Hop'": {
        "favorite_genre": "Hip Hop",
        "favorite_mood": "Confident",
        "target_energy": 0.80,
        "target_valence": 0.60,
        "target_danceability": 0.85,
        "target_tempo_bpm": 95,
        "likes_acoustic": False,
    },
    # Wrong type: an EDM fan whose likes_acoustic arrived as the STRING "False"
    # (e.g. from a web form or CSV). Any non-empty string is truthy in Python, so
    # score_song() should treat this user as an acoustic fan, the opposite of intended.
    "Edge: likes_acoustic as string": {
        "favorite_genre": "edm",
        "favorite_mood": "euphoric",
        "target_energy": 0.95,
        "target_valence": 0.85,
        "target_danceability": 0.90,
        "target_tempo_bpm": 128,
        "likes_acoustic": "False",
    },
    # Invalid numbers: targets outside the 0-1 feature scale and a 300 BPM tempo.
    # Nothing validates prefs, so look for a crash, negative points, or odd rankings.
    "Edge: out-of-range targets": {
        "target_energy": 1.5,
        "target_valence": -0.5,
        "target_danceability": 2.0,
        "target_tempo_bpm": 300,
    },
    # Cold start: a brand-new user with no preferences at all. Every rule is skipped,
    # so every song scores 0.00 and the tie-break (CSV order) decides the top 5.
    "Edge: empty profile (cold start)": {},
}


def print_profile_header(name: str, prefs: dict) -> None:
    """Print a boxed header naming the profile and summarizing its preferences.

    Args:
        name: Display name for the profile (a key of PROFILES or EDGE_CASE_PROFILES).
        prefs: The profile's user_prefs dict. Missing keys print as "-".
    """
    print("=" * LINE_WIDTH)
    print(f"Profile: {name}")
    # likes_acoustic is printed with repr() so its TYPE is visible: the boolean False
    # prints as False, but the string "False" prints as 'False' (quoted). Without this,
    # the "likes_acoustic as string" edge case would look identical to a valid profile.
    likes_acoustic = prefs.get("likes_acoustic")
    acoustic_text = "-" if likes_acoustic is None else repr(likes_acoustic)
    # Line 1: the categorical prefs that earn the big genre/mood bonuses.
    print(
        f"  genre={prefs.get('favorite_genre', '-')}  "
        f"mood={prefs.get('favorite_mood', '-')}  "
        f"likes_acoustic={acoustic_text}"
    )
    # Line 2: the numeric targets that earn closeness points.
    print(
        f"  energy={prefs.get('target_energy', '-')}  "
        f"valence={prefs.get('target_valence', '-')}  "
        f"danceability={prefs.get('target_danceability', '-')}  "
        f"tempo={prefs.get('target_tempo_bpm', '-')} BPM"
    )
    print("=" * LINE_WIDTH)


def print_recommendations(recommendations: list) -> None:
    """Print a ranked list of recommendations, one block per song.

    Each block shows the rank, title, artist, genre/mood, the score out of
    MAX_SCORE, and every reason score_song() gave, one per line.

    Args:
        recommendations: (song_dict, score, explanation) tuples from
            recommend_songs(), already sorted highest score first.
    """
    # Empty list (e.g. k=0 or an empty catalog): say so instead of printing nothing.
    if not recommendations:
        print("  (no recommendations)")
        return

    # enumerate(..., start=1) numbers the songs #1, #2, ... and the inner parentheses
    # unpack each (song, score, explanation) tuple into three named variables.
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        # Title line: rank, title, artist, and the labels that drive genre/mood points.
        print(f"#{rank}  {song['title']} - {song['artist']}  [{song['genre']} / {song['mood']}]")
        # Show the score against the maximum possible so "6.76" has context.
        print(f"    Score: {score:.2f} / {MAX_SCORE:.2f}")
        print("    Why:")
        # recommend_songs() joins the reasons with "; " into one string; split it
        # back apart so each reason gets its own bulleted line.
        for reason in explanation.split("; "):
            print(f"      + {reason}")
        # Thin divider between songs, but not after the last one.
        if rank < len(recommendations):
            print("    " + "-" * (LINE_WIDTH - 4))
    print()


def main() -> None:
    """Run the CLI simulation: load songs, then print a top 5 for every profile.

    For each taste profile in PROFILES, then each in EDGE_CASE_PROFILES, prints a
    header followed by the top 5 recommendations with scores and reasons. If the
    weight-shift experiment is switched on in recommender.py, a notice with the
    experimental weights is printed first.

    Run from the project root so the relative path data/songs.csv resolves.
    """
    # Load once and reuse for every profile; recommend_songs() never modifies the list.
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    # Label experimental runs so their output can't be mistaken for the baseline.
    # Nothing is printed when the switch is off, so baseline output is unchanged.
    if WEIGHT_SHIFT_EXPERIMENT:
        print(f"*** WEIGHT SHIFT EXPERIMENT: genre +{GENRE_WEIGHT}, "
              f"energy x{ENERGY_WEIGHT}, max score {MAX_SCORE:.2f} ***\n")

    # Everyday listeners first, then the adversarial edge cases. {**a, **b} merges the
    # two dicts into a new one and keeps insertion order, so the edge cases print last.
    all_profiles = {**PROFILES, **EDGE_CASE_PROFILES}

    # Run the same catalog through every profile so their rankings can be compared.
    for name, user_prefs in all_profiles.items():
        # Input -> Process -> Output: score all songs, keep the 5 best, then print them.
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_profile_header(name, user_prefs)
        print_recommendations(recommendations)


if __name__ == "__main__":
    main()
