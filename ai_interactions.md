# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agentic Workflow (SF8)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

I used Claude Code for the evaluation half of the project, all in one session. The tasks were:

- stress-test the recommender with everyday and adversarial listener profiles
- explain surprising rankings
- run a weight-shift experiment
- find biases in the scoring and the data
- document everything in the README and model card

After each step, I asked it to comment its new code and update any comments that had gone out of date.

Later in the same session I used the agent for the four stretch challenges: advanced song features, scoring modes, the diversity penalty and the summary table. Each one has its own section below with the prompt, the changes and verification notes. The lists in this section cover the evaluation steps only.

**Prompts used:**

Lightly cleaned up for typos:

- The course step instructions, pasted one step at a time. For example: *"ask your AI coding assistant to suggest 'adversarial' or 'edge case' user profiles"* and *"describe the specific logic change you want to see and ask it to verify that the math remains valid."*
- After each step: *"Add comments to the new changes and update all the outdated comments in this repo."*
- *"Could you generate a git commit message for all the changes you made?"*
- *"You could mimic what I am doing in the first person view"* (for the personal reflection).
- *"Fill in all the templates that are empty and update any outdated comments."*

**What did the agent generate or change?**

- `src/main.py`:
  - added a deep intense rock profile and six trick profiles (`EDGE_CASE_PROFILES`)
  - changed the header to print `likes_acoustic` in a way that shows a string `"False"`
  - added a notice that prints when the weight experiment is on
- `src/recommender.py`:
  - added the `WEIGHT_SHIFT_EXPERIMENT` switch
  - connected the `Recommender` class to `score_song()`
  - added an `explain_reasons()` helper shared by both code paths
  - removed an unused import
  - added docstrings and comments throughout
- `tests/test_recommender.py`: added three tests that fail against the old unscored stub, plus docstrings.
- `README.md`:
  - the Stress Test section, with output for each profile and seven findings
  - Experiments You Tried
  - Project Summary, Limitations and Risks, and Reflection
  - a fix for an unclosed code block in Setup
- `model_card.md`: every section.
- Commands it ran:
  - `python -m src.main` and `pytest`
  - throwaway Python scripts for rule-by-rule score breakdowns, math checks for the experiment, and a simulation of 5,000 random listeners
  - checks that every pasted output block matched a fresh run

**What did you verify or fix manually?**

- **Its own claims needed checking against the data.** Some drafts were wrong, and they were corrected only after checking `songs.csv` and the terminal output:
  - one draft said every calm song was acoustic, but two calm songs sit around 0.4
  - one draft described the experiment as only halving genre, when it also doubled energy
  - comments written earlier no longer matched the code, for example a comment saying every reason in an explanation had earned points
- **A green test was not proof.** The starter test passed even though the `Recommender` class did no scoring, because the right song happened to be listed first. The new ranking test was checked by putting the stub back temporarily and confirming that the test failed.
- **The judgment calls were mine:**
  - which experiment to run
  - whether its results were "better or just different"
  - keeping the original weights
- **The first-person writing needed my review.** The agent drafted the first-person parts of the model card and README in my voice.

---

## Design Pattern (SF10)

> Document how AI helped you choose or implement a design pattern.

*My project uses two patterns. The Adapter below came about while I was fixing the starter code. The Strategy pattern for the scoring modes was chosen on purpose, after brainstorming options with the AI. See [Challenge 2](#challenge-2-multiple-scoring-modes).*

**Which design pattern did you use?**

**Adapter.** My project has two ways to get recommendations:

- **The CLI** works with plain dictionaries and the `score_song()` function.
- **The tests** use an object-oriented `Recommender` class that takes `Song` and `UserProfile` objects.

`Recommender` is an adapter. It converts those objects into the dictionaries that `score_song()` expects, so both paths share one scoring function instead of two copies of the rules.

**How did AI help you brainstorm or implement it?**

I didn't start out planning to use a pattern. While I was updating comments, the AI pointed out that the starter `Recommender` class was still a stub. It returned the first k songs without scoring them, and the starter test passed only because the right song happened to be listed first. The AI suggested connecting the class to the existing `score_song()` instead of writing a second version of the scoring, and I said yes. It then implemented the adapter:

- **Field names already match.** `Song` and `UserProfile` use the same field names as the dictionary keys `score_song()` reads, so `dataclasses.asdict()` can convert them directly. No mapping code is needed.
- **Shared explanation text.** It moved the explanation wording into one helper, `explain_reasons()`, so the CLI and the class phrase reasons the same way.
- **Tests that prove it.** It added tests that fail against the old stub, then checked this by putting the stub back temporarily.

The main benefit is that there is one source of truth. When I ran the weight experiment, both paths changed together automatically.

**How does the pattern appear in your final code?**

- **The adapter:** `Recommender` in [src/recommender.py](src/recommender.py).
  - `recommend()` converts the user once with `asdict()`, then ranks the songs by `score_song()`.
  - `explain_recommendation()` converts both objects and returns the reasons.
- **The code it wraps:** `score_song()`, which is the same function `recommend_songs()` uses for the CLI.
- **The shared helper:** `explain_reasons()`, used by both paths.
- **The tests:** [tests/test_recommender.py](tests/test_recommender.py). `test_recommend_ranks_by_score_not_list_order` would fail if the adapter stopped calling the real scoring.

---

## Challenge 1: Advanced Song Features

> Add 5+ new song attributes to `data/songs.csv`, make the scoring in `src/recommender.py` use them, and document the agentic workflow.

**Example prompt used:**

I pasted the challenge text straight into Claude Code:

> *"Introduce 5 or more complex attributes to your dataset that are not currently present in the baseline data, such as Song Popularity (0-100), Release Decade, or Detailed Mood Tags (e.g., 'nostalgic,' 'aggressive,' 'euphoric'). Update both data/songs.csv and the scoring logic in src/recommender.py so scoring accounts for the new attributes."*

From earlier in the session, the agent also followed my standing request to comment all new code and update outdated comments.

**Summary of the changes the AI generated:**

- **`data/songs.csv`:** five new columns for all 20 songs:
  - `popularity` (0–100)
  - `release_decade` (1960–2020)
  - `mood_tags` (three detailed tags, such as `rainy|cozy|dreamy`)
  - `instrumentalness` (0–1)
  - `lyrics_language` (english / spanish / instrumental)
- **`src/recommender.py`:**
  - `load_songs()` now converts the new columns: integers, a float, and a tag list split on `|`.
  - New constants and `ADVANCED_NUMERIC_RULES` hold the new weights.
  - A shared `numeric_rule_points()` helper scores closeness for popularity, decade and instrumentalness. It is the same math the core rules use.
  - An "Advanced features" block in `score_song()` adds partial credit for mood tags and an exact-match rule for language.
  - `max_score_for()` shows each score out of the most that profile could earn.
  - Every new rule is **opt-in**: it scores only when the profile sets its preference.
- **`src/main.py`:**
  - three `ADVANCED_PROFILES`
  - a third header line that lists advanced preferences, printed only for profiles that set them
  - scores shown out of `max_score_for(profile)`
- **`tests/test_advanced_features.py`:** five new tests covering column loading, the opt-in design, partial tag credit, the decade and language rules, and `max_score_for()`.
- **Docs:**
  - a new README section (rules table, results, terminal output)
  - updates to every README and model card line that the new features made out of date

**Verification notes.** Each check below was run during the session, and the command is listed so I can rerun it:

- **The original results didn't change.** I compared the first nine profiles of a fresh `python -m src.main` run against the output saved before the change, and they were byte-identical. This is what the opt-in design is for: everything already documented in the README and model card still holds.
- **The tests pass.** `pytest` shows 10 passed (5 original and 5 new).
- **The math was checked by hand.** A song that matches every core preference exactly still scores 7.0. One of two tags earns 0.5. A song 10 years off the favorite decade earns 0.5 × (1 − 10/30) = 0.33. With all five advanced preferences set, the maximum is 7.0 + 3.0 = 10.0.
- **Both ways of running work.** `python -m src.main` and `python src/main.py` both run.
- **I read the results instead of trusting them.**
  - The tags narrowed *Gym Hero*'s lead but did not flip it.
  - The hidden-gem study profile kept the exact same order as before, because lofi songs are already instrumental, so the new rules overlapped with genre.
  - I wrote these up as they are in the README rather than tuning the weights until the results looked good.
- **I checked the data claims.** I counted directly from the CSV before writing about it: seven songs are instrumental and one is in Spanish.

---

## Challenge 2: Multiple Scoring Modes

> Build two or more ranking strategies that a user can switch between in `main.py`, and use AI to brainstorm a design pattern that keeps the code modular.

**Prompt used:**

I pasted the challenge text into Claude Code with `recommender.py` open:

> *"Build two or more different ranking strategies (e.g., 'Genre-First,' 'Mood-First,' or 'Energy-Focused') so a user can switch between modes in main.py. ... use your AI coding assistant's chat to brainstorm a design pattern (like a simple 'Strategy' pattern) that keeps your code modular."*

**How the AI contributed to the brainstorm.** Before writing any code, the AI read `recommender.py` and noticed something about the suggested modes (Genre-First, Mood-First, Energy-Focused): they all use the same seven rules and differ only in how much each rule counts. Based on that, it laid out three designs:

| Option | How it works | Trade-off |
|---|---|---|
| **A. `if mode == ...` inside `score_song()`** | One scoring function branches on a mode name. | Quickest to write, but every new mode means editing the scoring function, which tangles "what the rules are" with "how much they count". **Rejected.** |
| **B. Classic Strategy with subclasses** | A `ScoringStrategy` base class with a `score()` method, overridden by `GenreFirst`, `MoodFirst` and so on. | The most flexible, since a mode could use completely different rules. But here every mode shares the same rules, so each subclass would repeat or re-call the same scoring code. More code, with no benefit yet. |
| **C. Strategy as data** | Each mode is a `ScoringMode` object: a name, a description, and one weight per rule. `score_song()` uses whichever mode it is handed. | One scoring function, and a new mode is one new object. **Recommended.** |

**Chosen pattern: Strategy (option C).** It keeps the code modular in the way the challenge asks:

- **Adding a mode never touches the scoring code.** The scoring functions never check which mode they were given.
- **Option C can grow into option B if needed.** For example, a future "variety" mode that reorders the list so one loud song can't appear everywhere would need its own logic, not just weights. `ScoringMode` could gain an optional step for that, without changing any code that calls it.

Other design decisions also came out of the brainstorm:

- **The original recipe became the `balanced` mode and the default.** Code that doesn't choose a mode behaves exactly as before, so no earlier output or test changed.
- **Genre-first and mood-first use 5.0 points.** That is more than all the other core rules combined (1.0 + 1.0 + 0.5 × 4 = 4.0), which gives a guarantee you can state in one sentence: every genre (or mood) match ranks first. A vaguer "make it bigger" weight wouldn't.
- **Modes can't be broken by accident.** `ScoringMode` is read-only (`frozen=True`) and checks its weights when it is created, so a typo like `"temp_bpm"` fails immediately instead of in the middle of scoring.
- **A registry, `SCORING_MODES`, lists every mode.** `--mode`'s valid choices and the `--help` text are generated from it, so a new mode documents itself.
- **Scope decisions:**
  - The Challenge 1 extras keep fixed weights in every mode.
  - The Step 3 `WEIGHT_SHIFT_EXPERIMENT` switch still works, but only changes the `balanced` mode, so the documented experiment stays reproducible.

**How the pattern appears in the code.** All of this is in [src/recommender.py](src/recommender.py), [src/main.py](src/main.py) and [tests/test_scoring_modes.py](tests/test_scoring_modes.py):

- **The strategy:**
  - the `ScoringMode` class
  - four instances: `BALANCED`, `GENRE_FIRST`, `MOOD_FIRST`, `ENERGY_FOCUSED`
  - the `SCORING_MODES` registry
- **The context, which uses whatever strategy it is given:**
  - `score_song(user_prefs, song, mode)`
  - `recommend_songs(..., mode)`
  - `max_score_for(prefs, mode)`
  - `Recommender(songs, mode)`
- **The client, which chooses the strategy:**
  - `parse_args()` in `main.py` reads `--mode`, with choices taken from `SCORING_MODES`.
  - `main()` looks up the mode and passes it down.
- **The tests:** 8 tests check that:
  - every mode is complete and valid
  - the default mode reproduces the original recipe
  - each mode changes rankings the way its description promises
  - the OOP `Recommender` honors its mode
  - unknown modes are rejected

**Verification notes.** Each check below was run during the session:

- **Nothing changed by default.** `python -m src.main` with no mode, and with `--mode balanced`, is byte-identical to the output from before Challenge 2. Every earlier documented result still holds.
- **The tests pass.** `pytest` shows 18 passed (10 earlier and 8 new).
- **Each mode keeps its promise.**
  - mood-first puts *Pinewood Letters* at #1 for the sad listener (it was #9).
  - genre-first puts *Iron Cathedral* at #1 for the metal fan (it wasn't in the top 5).
  - energy-focused ranks *Rooftop Lights* above *Gym Hero* for the pop fan.
- **The label guarantee holds only for the core rules.** Genre and mood weights of 5.0 beat the other core rules' 4.0. I noted in the code comments that the optional Challenge 1 extras (up to 3.0 more) can break this.
- **The command line behaves well.** `--mode` with an unknown name exits with an error that lists the valid choices. `--help` lists every mode with its description. `python src/main.py --mode mood-first` works too.
- **The results weren't tuned to look good.** Genre-first makes the *Gym Hero* problem worse, and energy-focused brings back the Step 3 trade-off. The README reports both as they are.

---

## Challenge 3: Diversity and Fairness Logic

> Implement a "diversity penalty" that stops the recommender from suggesting too many songs from the same artist or genre, and write a prompt that describes the rule.

**The prompt I formulated:**

> *"In `src/recommender.py`, add an optional **diversity penalty** to `recommend_songs()`. Instead of only sorting by score, fill the top-k list one slot at a time. At each step, for every song not yet picked, subtract **1.5 points for each song by the same artist already in the list** and **0.75 points for each song of the same genre already in the list**, then pick the song with the highest adjusted score. Add a reason line to every penalized song, e.g. `diversity penalty: 1 song by LoRoom already picked (-1.50)`, so the explanation shows the deduction. Keep it **off by default** so existing results don't change, and add a `--diverse` flag to `main.py` that works with any `--mode`. Add tests and comments, and verify that the output with the flag off is byte-identical to before."*

**Why the prompt is worded this way:**

- **"One slot at a time."** A penalty for an artist "already in the list" only makes sense if the list is built in order. Asking for a greedy fill avoids a vague "lower the score of duplicates" that could be implemented in several different ways.
- **Exact numbers, with a reason for each.** 1.5 is about what a perfect energy match is worth, so a repeated artist has to clearly earn its place. 0.75 is half that, because two songs in one genre can still sound very different.
- **"Off by default" and "byte-identical".** This is the same approach as Challenges 1 and 2, so every earlier documented result stays valid.
- **"Shows the deduction".** Explanations were a strength of the project, so a hidden penalty would be a step backward.

**What the AI generated:**

- **`src/recommender.py`:**
  - a read-only `DiversityPolicy` (artist and genre penalty sizes) and `DEFAULT_DIVERSITY`
  - `diversify()`, the greedy re-ranker
  - an optional `diversity` argument on `recommend_songs()`
  - The re-ranker runs after scoring, so it works with every scoring mode without touching `ScoringMode`. When the AI planned Challenge 2, it had suggested that a variety rule might need `ScoringMode` to grow a re-rank step. Building it as a separate step instead kept the two features independent, so you can turn on diversity in any mode.
- **`src/main.py`:**
  - the `--diverse` flag
  - a notice line when the flag is on
  - penalty reasons printed with a `-` bullet instead of `+`
- **`tests/test_diversity.py`:** 7 tests:
  - the rule itself, including penalties that stack and the exact explanation text
  - the input is not modified
  - the penalty is off by default
  - #1 never changes
  - the real lofi profile gets more variety
  - the CLI flag works
- **README and model card:** a Challenge 3 section with results, a fairness check and real output, plus updates to the "filter bubble", limitations and future-work text.

**Verification notes.** Each check below was run during the session:

- **Nothing changed by default.** Output without `--diverse` was byte-identical to before, both for the default run and for `--mode mood-first`.
- **The tests pass.** `pytest` shows 25 passed (18 earlier and 7 new).
- **I checked the arithmetic by hand.** *Focus Flow* would be the third lofi song and the second by LoRoom, so it pays −1.50 − 1.50 = −3.00 and drops out. *Gym Hero* pays −0.75 but keeps #2, because 5.64 − 0.75 = 4.89 > 4.56.
- **I checked every "dropped / added" claim** in the README table against the actual `--diverse` output.
- **The fairness check changed my conclusion.** Before running it, I expected the penalty to make things fairer to artists. The 5,000-listener simulation showed the opposite. Repeated artists in a list fell from 15.5% to 0%, but the gap between the most- and least-recommended song grew from 24.1 to 27.9 points, because songs that share an artist or genre lost exposure to one-of-a-kind songs. I reported that as it came out instead of leaving the fairness question unasked.

---

## Challenge 4: Visual Summary Table

> Make the terminal output easier to read with a formatted table or summary, ask the AI to suggest `tabulate` or simple ASCII formatting, and make sure the prompt requires the reasons for each score.

**The prompt I used.** The reasons requirement is in bold:

> *"Add an optional `--table` view to `src/main.py` that prints each profile's top 5 as a formatted table instead of the long per-song blocks. Suggest whether to use the `tabulate` library or plain ASCII formatting, and explain the trade-off. The table **must include the reasons for each score**: one row per song with the rank, title and artist, genre / mood, the score out of the profile's maximum, and a **Why** column listing every rule that earned points (and, with `--diverse`, every penalty). Keep it within 80 characters by wrapping long cells, keep the current output as the default so the documented results don't change, and end with an overview table of each profile's #1 pick. Add tests and comments."*

**What the AI suggested:**

- **The two options.** It checked the environment first. `tabulate` wasn't installed and isn't in `requirements.txt`. So it compared:
  - `tabulate` with `tablefmt="grid"`: easy, but a new dependency, and long reasons would still need wrapping to fit 80 columns.
  - plain ASCII with the standard library's `textwrap`: nothing to install, full control over widths, and identical output everywhere.
- **Its recommendation was plain ASCII, and I went with it.**
- **How to fit the reasons into 80 columns.** Full reasons like `non-acoustic fit, acousticness 0.18 (+0.82)` are too long for a table cell. It suggested shrinking each one to a short tag such as `acoustic +0.82`, keeping the full sentences in the default view.

**What the AI generated:**

- **`src/summary_table.py`, a new module:**
  - `render_table()` draws any table with multi-line cells.
  - `short_reason()` turns each full reason into a tag.
  - `pack_tags()` fills each line with tags without ever splitting one.
  - `format_recommendation_table()` and `format_overview_table()` build the two tables.
- **`src/main.py`:**
  - the `--table` flag
  - an optional `width` on the profile header, so it matches the table width
  - collecting each profile's #1 pick for the closing overview
- **`tests/test_summary_table.py`:** 6 tests.
- **README:** a Challenge 4 section with real `--table` output.

**Verification notes.** Each check below was run during the session:

- **Nothing changed by default.** Output without `--table` is byte-identical to before, with and without `--diverse`.
- **The tests pass.** `pytest` shows 31 passed (25 earlier and 6 new).
- **The tables fit.** Every table line is exactly 80 characters wide, checked across all 12 profiles, with and without `--diverse`.
- **The tag test is tied to the real scorer.** It builds every kind of reason through the real `score_song()` and `diversify()`. If someone later rewords a reason, this test fails instead of the table quietly showing garbled tags.
- **Testing caught a real bug in the AI's first version.** `pack_tags()` checked whether a line fit *before* adding the trailing comma that marks a continued line. A line packed to exactly 36 characters became 37, so the table had to wrap it and split `instrumental +0.49` across two lines in the hidden-gem study profile. I only spotted it while hand-writing the expected test values.
  - **The fix** reserves room for the comma.
  - **The test was too weak at first.** It only covered the three everyday profiles, so I extended it to all 12 profiles with and without `--diverse`, and added a direct "no split tags" check.
  - **I confirmed the stronger test works** by running it against the old logic, where it fails.
- **A test bug, not a code bug.** The stronger test then failed on the fixed code too. It assumed every reason has points, but the empty profile's only reason is the plain text `no preferences matched`. I fixed the count in the test, not the code.
- **One small issue is left alone.** The advanced-preference header line, from Challenge 1, is 89 characters wide in both views. Fixing it would change the documented default output, so I noted it in the README instead.
