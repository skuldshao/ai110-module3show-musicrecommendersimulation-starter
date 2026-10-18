"""
Command line runner for the Music Recommender Simulation.

This is the CLI front end: it loads the catalog, runs every taste profile in
PROFILES through recommend_songs(), and prints a ranked, explained top 5 for each.
The scoring and ranking logic itself lives in recommender.py:
- load_songs       read data/songs.csv
- score_song       judge one song -> (score, reasons)
- recommend_songs  judge every song, sort, keep the top k

Run from the project root with:  python -m src.main
"""

# Support both `python -m src.main` (package import) and `python src/main.py` (script import).
# With -m, Python runs from the project root, so the module is found as src.recommender.
# As a plain script, Python only searches src/ itself, so the module is just `recommender`.
try:
    from src.recommender import load_songs, recommend_songs, MAX_SCORE
except ModuleNotFoundError:
    from recommender import load_songs, recommend_songs, MAX_SCORE

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
}


def print_profile_header(name: str, prefs: dict) -> None:
    """Print a boxed header naming the profile and summarizing its preferences.

    Args:
        name: Display name for the profile (a key of PROFILES).
        prefs: The profile's user_prefs dict. Missing keys print as "-".
    """
    print("=" * LINE_WIDTH)
    print(f"Profile: {name}")
    # Line 1: the categorical prefs that earn the big genre/mood bonuses.
    print(
        f"  genre={prefs.get('favorite_genre', '-')}  "
        f"mood={prefs.get('favorite_mood', '-')}  "
        f"likes_acoustic={prefs.get('likes_acoustic', '-')}"
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

    For each taste profile in PROFILES, prints a header followed by the top 5
    recommendations with scores and reasons.

    Run from the project root so the relative path data/songs.csv resolves.
    """
    # Load once and reuse for every profile; recommend_songs() never modifies the list.
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    # Run the same catalog through every profile so their rankings can be compared.
    for name, user_prefs in PROFILES.items():
        # Input -> Process -> Output: score all songs, keep the 5 best, then print them.
        recommendations = recommend_songs(user_prefs, songs, k=5)
        print_profile_header(name, user_prefs)
        print_recommendations(recommendations)


if __name__ == "__main__":
    main()
