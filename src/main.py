"""
Command line runner for the Music Recommender Simulation.

This is the CLI front end: it loads the catalog, runs every taste profile in
PROFILES (everyday listeners), EDGE_CASE_PROFILES (adversarial stress tests) and
ADVANCED_PROFILES (Challenge 1 song features) through recommend_songs(), and
prints a ranked, explained top 5 for each.
The scoring and ranking logic itself lives in recommender.py:
- load_songs       read data/songs.csv
- score_song       judge one song -> (score, reasons)
- recommend_songs  judge every song, sort, keep the top k
- max_score_for    the most points a profile could earn (the "/ max" in the output)
The --table view's formatting lives in summary_table.py.

Run from the project root with:  python -m src.main
Pick a ranking strategy (Challenge 2) with --mode, e.g.:
    python -m src.main --mode mood-first
Modes: balanced (the default), genre-first, mood-first, energy-focused.
Run  python -m src.main --help  to see what each one does.
Add --diverse (Challenge 3) to penalize repeated artists and genres within each
top 5. It works with any mode, e.g.:  python -m src.main --mode mood-first --diverse
Add --table (Challenge 4) to print each top 5 as a compact table, with the reasons
for every score, followed by an overview of each profile's #1 pick.
"""

import argparse

# Support both `python -m src.main` (package import) and `python src/main.py` (script import).
# With -m, Python runs from the project root, so the module is found as src.recommender.
# As a plain script, Python only searches src/ itself, so the module is just `recommender`.
# The weight constants are imported only so main() can announce the Step 3 experiment;
# SCORING_MODES / DEFAULT_MODE are the Challenge 2 strategies that --mode chooses from;
# DEFAULT_DIVERSITY is the Challenge 3 penalty policy that --diverse turns on.
try:
    from src.recommender import (load_songs, recommend_songs, max_score_for, MAX_SCORE,
                                 WEIGHT_SHIFT_EXPERIMENT, GENRE_WEIGHT, ENERGY_WEIGHT,
                                 SCORING_MODES, DEFAULT_MODE, DEFAULT_DIVERSITY)
except ModuleNotFoundError:
    from recommender import (load_songs, recommend_songs, max_score_for, MAX_SCORE,
                             WEIGHT_SHIFT_EXPERIMENT, GENRE_WEIGHT, ENERGY_WEIGHT,
                             SCORING_MODES, DEFAULT_MODE, DEFAULT_DIVERSITY)

# The Challenge 4 table view (--table), imported the same two ways as above.
try:
    from src.summary_table import (format_recommendation_table, format_overview_table,
                                   TABLE_WIDTH)
except ModuleNotFoundError:
    from summary_table import (format_recommendation_table, format_overview_table,
                               TABLE_WIDTH)

# Every diversity-penalty reason starts with this (see diversify() in recommender.py).
# print_recommendations() uses it to print those reasons with "-" instead of "+".
# summary_table.short_reason() checks the same prefix to label them "same artist" /
# "same genre", so a rewording in diversify() must update all three places.
PENALTY_PREFIX = "diversity penalty"

# Width of the "=====" / "-----" rules that frame each section of terminal output.
LINE_WIDTH = 72

# Taste profiles to run, keyed by a display name.
# Categorical prefs (genre, mood) must match the CSV label exactly, ignoring case;
# numeric targets are on the same 0.0-1.0 scale as songs.csv (except tempo, which is
# in BPM). See ADVANCED_PROFILES below for the optional Challenge 1 preferences.
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

# Challenge 1 profiles, run last. Each one sets some of the five optional advanced
# preferences (target_popularity, favorite_decade, preferred_mood_tags,
# target_instrumentalness, preferred_language) to show those rules at work. Their
# scores are shown out of a higher max, because max_score_for() adds the weight of
# every advanced rule the profile uses.
ADVANCED_PROFILES = {
    # Same as "Default pop/happy", plus detailed mood tags. Tags give PARTIAL credit,
    # so Rooftop Lights (tagged upbeat AND sunny) should gain on Gym Hero (only
    # upbeat). Does that close the gap the genre label opened?
    "Advanced: happy pop + mood tags": {
        "favorite_genre": "pop",
        "favorite_mood": "happy",
        "target_energy": 0.80,
        "target_valence": 0.80,
        "target_danceability": 0.80,
        "target_tempo_bpm": 120,
        "likes_acoustic": False,
        "preferred_mood_tags": ["upbeat", "sunny"],
    },
    # The late-night study listener, now asking for lesser-known (popularity 30),
    # vocal-free tracks with a cozy, rainy feel. Uses four of the five new features.
    "Advanced: hidden-gem study listener": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
        "target_valence": 0.60,
        "target_danceability": 0.55,
        "target_tempo_bpm": 80,
        "likes_acoustic": True,
        "target_popularity": 30,
        "target_instrumentalness": 0.95,
        "preferred_mood_tags": ["cozy", "rainy"],
        "preferred_language": "instrumental",
    },
    # No genre or mood at all: only mid-tempo numbers plus a decade, a lyrics language
    # and tags. Tests whether the new features alone can find a coherent "90s,
    # nostalgic, English-language" list.
    "Advanced: 90s throwback, English lyrics": {
        "target_energy": 0.50,
        "target_valence": 0.65,
        "target_danceability": 0.60,
        "target_tempo_bpm": 95,
        "likes_acoustic": True,
        "favorite_decade": 1990,
        "preferred_language": "english",
        "preferred_mood_tags": ["nostalgic", "warm"],
    },
}

# Keys of the five optional advanced preferences, in the order the header prints them.
ADVANCED_PREF_KEYS = ("preferred_mood_tags", "target_popularity", "favorite_decade",
                      "target_instrumentalness", "preferred_language")


def print_profile_header(name: str, prefs: dict, width: int = LINE_WIDTH) -> None:
    """Print a boxed header naming the profile and summarizing its preferences.

    A third line lists the advanced (Challenge 1) preferences, but only for profiles
    that set at least one, so the original profiles' headers are unchanged.

    Args:
        name: Display name for the profile (a key of PROFILES, EDGE_CASE_PROFILES or
            ADVANCED_PROFILES).
        prefs: The profile's user_prefs dict. Missing keys print as "-".
        width: Length of the "=====" rules. The default view uses LINE_WIDTH; the
            --table view passes TABLE_WIDTH so the header lines up with its table.
    """
    print("=" * width)
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
    # Line 3 (advanced profiles only): any() is True if at least one advanced pref
    # is set, so profiles without them keep their original two-line header.
    if any(key in prefs for key in ADVANCED_PREF_KEYS):
        # Tags are a list; join them so the header shows "upbeat, sunny", not
        # "['upbeat', 'sunny']". A missing list falls back to "-" like other prefs.
        tags = ", ".join(prefs.get("preferred_mood_tags", [])) or "-"
        print(
            f"  tags={tags}  "
            f"popularity={prefs.get('target_popularity', '-')}  "
            f"decade={prefs.get('favorite_decade', '-')}  "
            f"instrumentalness={prefs.get('target_instrumentalness', '-')}  "
            f"language={prefs.get('preferred_language', '-')}"
        )
    print("=" * width)


def print_recommendations(recommendations: list, max_score: float) -> None:
    """Print a ranked list of recommendations, one block per song.

    Each block shows the rank, title, artist, genre/mood, the score out of
    max_score, and every reason score_song() gave, one per line.

    Args:
        recommendations: (song_dict, score, explanation) tuples from
            recommend_songs(), already sorted highest score first.
        max_score: The most this profile could earn, from max_score_for(): 7.00
            for the original profiles, more for profiles using advanced features.
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
        # Show the score against this profile's maximum so "6.76" has context.
        print(f"    Score: {score:.2f} / {max_score:.2f}")
        print("    Why:")
        # recommend_songs() joins the reasons with "; " into one string; split it
        # back apart so each reason gets its own bulleted line. Points earned get a
        # "+" bullet; diversity penalties (Challenge 3) take points away, so they get
        # a "-" bullet. No other reason starts with PENALTY_PREFIX, so output without
        # --diverse is unchanged.
        for reason in explanation.split("; "):
            bullet = "-" if reason.startswith(PENALTY_PREFIX) else "+"
            print(f"      {bullet} {reason}")
        # Thin divider between songs, but not after the last one.
        if rank < len(recommendations):
            print("    " + "-" * (LINE_WIDTH - 4))
    print()


def parse_args(argv: list = None) -> argparse.Namespace:
    """Read the command-line options: --mode (Challenge 2), --diverse (Challenge 3)
    and --table (Challenge 4).

    Args:
        argv: Arguments to parse, e.g. ["--mode", "mood-first", "--diverse"]. None
            (the default) reads the real command line, which is what
            `python -m src.main` does; passing a list lets tests call main()
            without a terminal.

    Returns:
        The parsed options. .mode is always a key of SCORING_MODES, because argparse
        rejects anything else with an error that lists the valid choices.
        .diverse and .table are True only if their flag was given.
    """
    # The --help footer lists every mode with its one-line description, built from
    # SCORING_MODES so a newly added mode documents itself.
    mode_help = "\n".join(f"  {mode.name:<16}{mode.description}"
                          for mode in SCORING_MODES.values())
    parser = argparse.ArgumentParser(
        description="Rank the song catalog for every taste profile.",
        epilog=f"scoring modes:\n{mode_help}",
        # Keep the epilog's line breaks instead of rewrapping it into one paragraph.
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=list(SCORING_MODES),
        default=DEFAULT_MODE.name,
        help="ranking strategy to use (default: %(default)s)",
    )
    # store_true: the flag takes no value; present -> True, absent -> False (off).
    parser.add_argument(
        "--diverse",
        action="store_true",
        help=(f"penalize repeats in each top 5: -{DEFAULT_DIVERSITY.artist_penalty:g} "
              f"per song by an artist already picked, "
              f"-{DEFAULT_DIVERSITY.genre_penalty:g} per song in a genre already picked"),
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help=("show each top 5 as a compact table (with the reasons for every score), "
              "then an overview of each profile's #1 pick"),
    )
    return parser.parse_args(argv)


def main(argv: list = None) -> None:
    """Run the CLI simulation: load songs, then print a top 5 for every profile.

    For each taste profile in PROFILES, then EDGE_CASE_PROFILES, then
    ADVANCED_PROFILES, prints a header followed by the top 5 recommendations with
    scores and reasons, ranked with the scoring mode chosen by --mode, and with the
    diversity penalty if --diverse is given. A notice is printed first for a
    non-default mode, for --diverse, or if the weight-shift experiment is switched
    on in recommender.py. With --table, each top 5 is printed as a compact table
    instead, and an overview table of every profile's #1 pick is printed at the end.

    Run from the project root so the relative path data/songs.csv resolves.

    Args:
        argv: Command-line arguments for parse_args(); None reads the real ones.
    """
    args = parse_args(argv)
    # Look up the chosen strategy object by name, e.g. "mood-first" -> MOOD_FIRST.
    mode = SCORING_MODES[args.mode]
    # None means "no diversity penalty", which recommend_songs() treats as the
    # plain ranking from before Challenge 3.
    diversity = DEFAULT_DIVERSITY if args.diverse else None

    # Load once and reuse for every profile; recommend_songs() never modifies the list.
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    # Label non-default modes so their output can't be mistaken for the baseline.
    # Nothing is printed in the default mode, so baseline output is unchanged.
    if mode is not DEFAULT_MODE:
        print(f"*** SCORING MODE: {mode.name} - {mode.description} "
              f"(core max {mode.max_score:.2f}) ***\n")

    # Label experimental runs the same way. The Step 3 switch only changes the
    # balanced (default) mode's weights, so it is only announced in that mode.
    if WEIGHT_SHIFT_EXPERIMENT and mode is DEFAULT_MODE:
        print(f"*** WEIGHT SHIFT EXPERIMENT: genre +{GENRE_WEIGHT}, "
              f"energy x{ENERGY_WEIGHT}, max score {MAX_SCORE:.2f} ***\n")

    # Label diversity runs too, since their scores include penalties.
    if diversity is not None:
        print(f"*** DIVERSITY PENALTY: -{diversity.artist_penalty:.2f} per song by an "
              f"artist already picked, -{diversity.genre_penalty:.2f} per song in a "
              f"genre already picked ***\n")

    # Everyday listeners first, then the adversarial edge cases, then the Challenge 1
    # profiles. {**a, **b, **c} merges the dicts into a new one and keeps insertion
    # order, so the original nine profiles print first, exactly as before.
    all_profiles = {**PROFILES, **EDGE_CASE_PROFILES, **ADVANCED_PROFILES}

    # (profile name, #1 song, score, max score) for the --table overview at the end.
    top_picks = []

    # Run the same catalog through every profile so their rankings can be compared.
    for name, user_prefs in all_profiles.items():
        # Input -> Process -> Output: score all songs with the chosen strategy, keep
        # the 5 best (with repeat penalties if --diverse), then print them.
        recommendations = recommend_songs(user_prefs, songs, k=5, mode=mode,
                                          diversity=diversity)
        # Scores are shown out of the most THIS profile could earn in THIS mode.
        max_score = max_score_for(user_prefs, mode)
        if args.table:
            # Compact view: same header (as wide as the table), then one table row
            # per song with a short tag for each reason.
            print_profile_header(name, user_prefs, width=TABLE_WIDTH)
            print(format_recommendation_table(recommendations, max_score))
            print()
            if recommendations:
                top_song, top_score, _ = recommendations[0]
                top_picks.append((name, top_song, top_score, max_score))
        else:
            # Default view, unchanged: every reason on its own line.
            print_profile_header(name, user_prefs)
            print_recommendations(recommendations, max_score)

    # Table view only: finish with every profile's #1 pick on one screen.
    if args.table:
        print("=" * TABLE_WIDTH)
        print("Overview: the #1 pick for every profile")
        print("=" * TABLE_WIDTH)
        print(format_overview_table(top_picks))


if __name__ == "__main__":
    main()
