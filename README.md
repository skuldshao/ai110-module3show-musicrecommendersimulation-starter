# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

**Song features used:** genre, mood, energy, valence, danceability, tempo_bpm, acousticness.

**UserProfile stores:** favorite genre, favorite mood, target energy / valence / danceability / tempo, and whether they like acoustic sound.

### Algorithm Recipe

Each song is scored independently against the user profile (max **7.0** points):

| Rule | Points | Why this weight |
|---|---|---|
| Genre matches `favorite_genre` | **+2.0** | Strongest identity signal. 17 genres across 20 songs, so a match is rare and meaningful. |
| Mood matches `favorite_mood` | **+1.0** | Captures the "vibe," but moods overlap (chill / relaxed / laid-back), so a miss is less damning than a genre miss. |
| Energy closeness | **+1.5 × (1 − \|song − target\|)** | Most spread-out numeric feature (0.22–0.98); separates calm from intense best. |
| Valence closeness | **+0.5 × (1 − \|song − target\|)** | Fine-tuning: happy vs. dark. |
| Danceability closeness | **+0.5 × (1 − \|song − target\|)** | Fine-tuning: groove. |
| Tempo closeness | **+0.5 × (1 − min(\|song − target\| / 100, 1))** | BPM normalized by ~100 (catalog spans 60–168). |
| Acoustic fit | **+1.0 × acousticness** if `likes_acoustic`, else **+1.0 × (1 − acousticness)** | Rewards the texture the user prefers. |

Categorical matches are worth 3.0 of 7.0 points (~43%), and numeric similarity is worth 4.0. A song that matches both genre and mood almost always ranks first. The similarity scores then sort songs that only partly match.

**Choosing songs:** score every song, sort by score from highest to lowest, return the top `k` (default 5), and attach the reasons that added points as the explanation.

### Expected Biases

- **Over-prioritizes genre.** A +2.0 genre match can outweigh a song that fits the user's mood and energy better. For a pop/happy user, *Gym Hero* (pop/intense) outranks *Rooftop Lights* (indie pop/happy). Raising the mood weight to 1.5 does not change that order.
- **Exact string matching is brittle.** "indie pop" gets no credit for "pop", and "relaxed" or "laid-back" gets no credit for "chill". Labels that are close in meaning count as complete misses.
- **Catalog imbalance helps some users more than others.** Lofi has 3 songs, while most genres have only 1. A lofi fan gets a top 3 that all match their genre. A metal or blues fan gets one genre match, and the rest of their list is chosen by numeric similarity alone.
- **Filter bubble.** Because the top results tend to share the user's genre and mood, the system rarely surfaces something different the user might enjoy. It has no diversity or discovery bonus.
- **Fixed, hand-picked weights.** The weights reflect my judgment, not real listening data, and every user gets the same weights. Someone who cares more about mood than genre cannot express that.
- **Acoustic preference is all-or-nothing.** `likes_acoustic` is a true/false setting, so users in the middle are pushed toward one extreme.

### Data Flow

```mermaid
flowchart LR
    subgraph Input
        U["User Prefs<br/>genre, mood,<br/>target energy / valence /<br/>danceability / tempo,<br/>likes_acoustic"]
        C[("data/songs.csv")]
    end

    subgraph Process["Process: the loop"]
        L["load_songs()<br/>CSV → list of song dicts"]
        F{"for each song"}
        S["score_song(user_prefs, song)<br/>+2.0 genre · +1.0 mood<br/>+ energy / valence / dance / tempo closeness<br/>+ acoustic fit"]
        R["collect (song, score, reasons)"]
    end

    subgraph Output["Output: the ranking"]
        O["sort by score, highest first"]
        K["take top k (default 5)"]
        P["print rank, title, score / 7.00,<br/>and a 'Why:' bullet per reason"]
    end

    C --> L --> F
    U --> S
    F --> S --> R --> F
    F -- "all 20 scored" --> O --> K --> P
```

1. **Input:** `main.py` builds the `user_prefs` dict, and `load_songs()` reads `songs.csv` into a list of dicts. Numeric fields are converted to `float`.
2. **Process:** `recommend_songs()` runs `score_song()` on every song. Each call returns a `(score, reasons)` pair, where `reasons` lists what earned points, for example `"genre match: pop (+2.0)"`. The songs are scored independently, so each score depends only on that song and the user.
3. **Output:** the scored songs are sorted from highest to lowest score, the first `k` are kept, and each is returned as `(song, score, explanation)` for `main.py` to print.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Output of `python -m src.main` for the default pop/happy profile and the late-night study (lofi/chill) profile:

```
$ python -m src.main
Loading songs from data/songs.csv...
Loaded songs: 20

========================================================================
Profile: Default pop/happy
  genre=pop  mood=happy  likes_acoustic=False
  energy=0.8  valence=0.8  danceability=0.8  tempo=120 BPM
========================================================================
#1  Sunrise City - Neon Echo  [pop / happy]
    Score: 6.76 / 7.00
    Why:
      + genre match: pop (+2.0)
      + mood match: happy (+1.0)
      + energy 0.82 vs target 0.8 (+1.47)
      + valence 0.84 vs target 0.8 (+0.48)
      + danceability 0.79 vs target 0.8 (+0.49)
      + tempo_bpm 118 vs target 120 (+0.49)
      + non-acoustic fit, acousticness 0.18 (+0.82)
    --------------------------------------------------------------------
#2  Gym Hero - Max Pulse  [pop / intense]
    Score: 5.64 / 7.00
    Why:
      + genre match: pop (+2.0)
      + energy 0.93 vs target 0.8 (+1.30)
      + valence 0.77 vs target 0.8 (+0.48)
      + danceability 0.88 vs target 0.8 (+0.46)
      + tempo_bpm 132 vs target 120 (+0.44)
      + non-acoustic fit, acousticness 0.05 (+0.95)
    --------------------------------------------------------------------
#3  Rooftop Lights - Indigo Parade  [indie pop / happy]
    Score: 4.56 / 7.00
    Why:
      + mood match: happy (+1.0)
      + energy 0.76 vs target 0.8 (+1.44)
      + valence 0.81 vs target 0.8 (+0.49)
      + danceability 0.82 vs target 0.8 (+0.49)
      + tempo_bpm 124 vs target 120 (+0.48)
      + non-acoustic fit, acousticness 0.35 (+0.65)
    --------------------------------------------------------------------
#4  Concrete Crown - Blocktide  [hip-hop / confident]
    Score: 3.60 / 7.00
    Why:
      + energy 0.78 vs target 0.8 (+1.47)
      + valence 0.62 vs target 0.8 (+0.41)
      + danceability 0.86 vs target 0.8 (+0.47)
      + tempo_bpm 94 vs target 120 (+0.37)
      + non-acoustic fit, acousticness 0.12 (+0.88)
    --------------------------------------------------------------------
#5  Laser Bloom - Pulsewave  [edm / euphoric]
    Score: 3.58 / 7.00
    Why:
      + energy 0.96 vs target 0.8 (+1.26)
      + valence 0.88 vs target 0.8 (+0.46)
      + danceability 0.93 vs target 0.8 (+0.43)
      + tempo_bpm 128 vs target 120 (+0.46)
      + non-acoustic fit, acousticness 0.03 (+0.97)

========================================================================
Profile: Late-night study (lofi/chill)
  genre=lofi  mood=chill  likes_acoustic=True
  energy=0.4  valence=0.6  danceability=0.55  tempo=80 BPM
========================================================================
#1  Library Rain - Paper Lanterns  [lofi / chill]
    Score: 6.73 / 7.00
    Why:
      + genre match: lofi (+2.0)
      + mood match: chill (+1.0)
      + energy 0.35 vs target 0.4 (+1.42)
      + valence 0.6 vs target 0.6 (+0.50)
      + danceability 0.58 vs target 0.55 (+0.49)
      + tempo_bpm 72 vs target 80 (+0.46)
      + acoustic fit, acousticness 0.86 (+0.86)
    --------------------------------------------------------------------
#2  Midnight Coding - LoRoom  [lofi / chill]
    Score: 6.62 / 7.00
    Why:
      + genre match: lofi (+2.0)
      + mood match: chill (+1.0)
      + energy 0.42 vs target 0.4 (+1.47)
      + valence 0.56 vs target 0.6 (+0.48)
      + danceability 0.62 vs target 0.55 (+0.47)
      + tempo_bpm 78 vs target 80 (+0.49)
      + acoustic fit, acousticness 0.71 (+0.71)
    --------------------------------------------------------------------
#3  Focus Flow - LoRoom  [lofi / focused]
    Score: 5.75 / 7.00
    Why:
      + genre match: lofi (+2.0)
      + energy 0.4 vs target 0.4 (+1.50)
      + valence 0.59 vs target 0.6 (+0.49)
      + danceability 0.6 vs target 0.55 (+0.48)
      + tempo_bpm 80 vs target 80 (+0.50)
      + acoustic fit, acousticness 0.78 (+0.78)
    --------------------------------------------------------------------
#4  Spacewalk Thoughts - Orbit Bloom  [ambient / chill]
    Score: 4.55 / 7.00
    Why:
      + mood match: chill (+1.0)
      + energy 0.28 vs target 0.4 (+1.32)
      + valence 0.65 vs target 0.6 (+0.47)
      + danceability 0.41 vs target 0.55 (+0.43)
      + tempo_bpm 60 vs target 80 (+0.40)
      + acoustic fit, acousticness 0.92 (+0.92)
    --------------------------------------------------------------------
#5  Coffee Shop Stories - Slow Stereo  [jazz / relaxed]
    Score: 3.74 / 7.00
    Why:
      + energy 0.37 vs target 0.4 (+1.46)
      + valence 0.71 vs target 0.6 (+0.45)
      + danceability 0.54 vs target 0.55 (+0.49)
      + tempo_bpm 90 vs target 80 (+0.45)
      + acoustic fit, acousticness 0.89 (+0.89)
```

**Does pop/happy match expectations?** Mostly. *Sunrise City* is the only song that is both pop and happy, and it ranks #1 by more than a full point. Places #4 and #5 go to songs with no label match, *Concrete Crown* and *Laser Bloom*, which make sense as upbeat, danceable, non-acoustic tracks. The surprise is #2: *Gym Hero* (pop / intense) beats *Rooftop Lights* (indie pop / happy), even though Rooftop Lights is closer on mood, energy, valence and tempo. This is the genre over-weighting predicted in [Expected Biases](#expected-biases). The exact genre match earns +2.0, while "indie pop" earns nothing for genre.

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



