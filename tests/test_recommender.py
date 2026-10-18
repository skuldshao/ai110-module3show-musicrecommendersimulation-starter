"""
Tests for the OOP Recommender in src/recommender.py.

Recommender wraps the same score_song() the CLI uses, so these tests also check
the scoring rules: ranking by score (not list order), the k <= 0 guard, and that
explanations list the reasons behind each score. Run from the project root with: pytest
"""

from src.recommender import Song, UserProfile, Recommender

def make_small_recommender() -> Recommender:
    """Build a Recommender over two opposite songs: an upbeat pop track listed
    first, then a calm acoustic lofi track. Tests use the list order to check that
    recommend() ranks by score rather than just returning songs in order.
    """
    songs = [
        Song(
            id=1,
            title="Test Pop Track",
            artist="Test Artist",
            genre="pop",
            mood="happy",
            energy=0.8,
            tempo_bpm=120,
            valence=0.9,
            danceability=0.8,
            acousticness=0.2,
        ),
        Song(
            id=2,
            title="Chill Lofi Loop",
            artist="Test Artist",
            genre="lofi",
            mood="chill",
            energy=0.4,
            tempo_bpm=80,
            valence=0.6,
            danceability=0.5,
            acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def test_recommend_returns_songs_sorted_by_score():
    """A pop/happy, high-energy fan should get the pop track first."""
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)

    assert len(results) == 2
    # Starter expectation: the pop, happy, high energy song should score higher.
    # The pop track is also listed first, so this alone can't tell real ranking from
    # list order; test_recommend_ranks_by_score_not_list_order covers that.
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_recommend_ranks_by_score_not_list_order():
    """A lofi/chill fan should get the lofi track first even though it is listed
    second. An unscored recommend() that returns songs in list order fails this.
    """
    user = UserProfile(
        favorite_genre="lofi",
        favorite_mood="chill",
        target_energy=0.4,
        likes_acoustic=True,
    )
    results = make_small_recommender().recommend(user, k=2)

    assert [song.title for song in results] == ["Chill Lofi Loop", "Test Pop Track"]


def test_recommend_with_non_positive_k_returns_empty_list():
    """k <= 0 asks for nothing. Guards against songs[:-1] ("all but the last")
    leaking through for a negative k.
    """
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()

    assert rec.recommend(user, k=0) == []
    assert rec.recommend(user, k=-1) == []


def test_explain_recommendation_returns_non_empty_string():
    """The explanation should always be a non-empty string."""
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()
    song = rec.songs[0]

    explanation = rec.explain_recommendation(user, song)
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


def test_explain_recommendation_lists_scoring_reasons():
    """The explanation should name the rules that earned points, in the same
    wording as the CLI's "Why:" bullets, rather than a fixed placeholder.
    """
    user = UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        likes_acoustic=False,
    )
    rec = make_small_recommender()

    explanation = rec.explain_recommendation(user, rec.songs[0])

    assert "genre match: pop (+2.0)" in explanation
    assert "mood match: happy (+1.0)" in explanation
    assert "energy 0.8 vs target 0.8 (+1.50)" in explanation
