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

- **The adapter:** `Recommender` in [src/recommender.py](src/recommender.py#L107).
  - `recommend()` ([line 126](src/recommender.py#L126)) converts the user once with `asdict()`, then ranks the songs by `score_song()`.
  - `explain_recommendation()` ([line 157](src/recommender.py#L157)) converts both objects and returns the reasons.
- **The code it wraps:** `score_song()` ([line 203](src/recommender.py#L203)), which is the same function `recommend_songs()` uses for the CLI.
- **The shared helper:** `explain_reasons()` ([line 299](src/recommender.py#L299)), used by both paths.
- **The tests:** [tests/test_recommender.py](tests/test_recommender.py). `test_recommend_ranks_by_score_not_list_order` would fail if the adapter stopped calling the real scoring.
