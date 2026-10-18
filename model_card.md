# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

**TuneJudge 1.0**: a talent-show judge for your playlist. It scores every song on the same scorecard and recommends the winners.

---

## 2. Intended Use  

**Goal / task.** TuneJudge suggests songs. You describe your taste, and it picks the 5 songs from a 20-song catalog that fit it best. It does not predict ratings, and it does not learn from what you play. It just scores each song against the taste you describe, then shows its reasons.

**What it assumes about you.** You can name one favorite genre and one favorite mood. You can describe the energy, happiness, danceability and tempo you want as numbers. You can answer yes or no to "do you like acoustic sound?" If you want, you can also give a few mood tags, a favorite decade, how popular you like your songs, how instrumental, and a lyrics language.

**Intended use.** Classroom exploration. It is built to show how a simple recommender turns data into a ranked list, and how the choice of weights changes the results. It is good for trying out listener profiles and seeing why each song was picked.

**Not intended for:**

- **Real listeners or a real music app.** The catalog has only 20 made-up songs with hand-picked numbers, and it was never tested with real people.
- **Deciding which artists get promoted or paid.** Some songs get recommended much more often than others, for reasons that have nothing to do with quality (see sections 6 and 7).
- **Listeners whose taste spans several genres or moods.** It only accepts one of each.
- **Taking settings straight from a form or file without checking them.** It does not validate input. For example, the word "False" counts as a "yes" (see section 6).

---

## 3. How the Model Works  

Think of the recommender as a judge at a talent show. Every song in the catalog gets the same scorecard, the judge adds up the points, and the songs with the most points are recommended.

**What the judge knows about each song.** Each song has two labels, a genre (pop, lofi, rock…) and a mood (happy, chill, intense…). It also has five measurements: energy (how intense it feels), valence (how happy or dark it sounds), danceability, tempo (how fast it is), and acousticness (how much it sounds like real instruments rather than electronics).

**What the judge knows about you.** You tell it your favorite genre, your favorite mood, the energy, happiness, danceability and tempo you want, and whether you like acoustic sound.

**How the points are given (out of 7):**

- **Same genre as your favorite: 2 points.** This is the biggest prize because it is the strongest clue. Most genres appear only once in the catalog, so a match means a lot.
- **Same mood as your favorite: 1 point.** Mood matters, but mood words overlap a lot ("chill", "relaxed" and "laid-back" are close), so missing a mood match hurts less than missing a genre match.
- **Closeness on energy: up to 1.5 points.** A song with exactly the energy you asked for gets all 1.5 points. The further away it is, the fewer points it gets. Energy is worth the most of the measurements because it best separates a calm song from an intense one.
- **Closeness on happiness, danceability and tempo: up to 0.5 points each.** These work the same way but count for less. They mostly decide the order among songs that are already good fits.
- **Acoustic fit: up to 1 point.** If you like acoustic music, the more acoustic a song is, the more points it gets. If you don't, electronic-sounding songs get the points instead.

**Optional extras (added for Challenge 1), up to 3 more points.** These only count if you ask for them:

- **Mood tags: up to 1 point.** Each song has three detailed tags, like "rainy, cozy, dreamy". You get partial credit: if you ask for two tags and a song has one, it earns half a point.
- **Popularity, decade and instrumentalness: up to 0.5 points each.** These use closeness, like energy does.
- **Lyrics language: 0.5 points** if it matches.

If you don't ask for an extra, it is skipped, and your score stays out of 7.

**Scoring modes (added for Challenge 2).** The points above are the default "balanced" mode. You can switch the judge to a different mode. The rules stay the same, but each mode changes how much they count:

- **Genre-first:** genre is worth 5 points, more than every other rule combined, so songs in your genre always come first.
- **Mood-first:** the same idea, but for mood.
- **Energy-focused:** energy and tempo decide, and genre and mood barely count.

No mode is best for everyone. Mood-first finally gives the "sad" listener the sad song, but genre-first makes the *Gym Hero* problem worse.

**Diversity option (added for Challenge 3).** If you turn it on, the judge fills your top 5 one spot at a time. A song loses 1.5 points for every song by the same artist already on your list, and 0.75 points for every song in the same genre. That stops one artist or genre from taking over your list, and every lost point is shown as a "−" line. Your #1 song never changes.

The judge scores every song this way, sorts them from highest to lowest, and shows you the top 5. Each recommendation lists exactly which rules gave it points, so you can see why it was picked. For example: "genre match: pop (+2.0), energy 0.82 vs target 0.8 (+1.47)…"

**What changed from the starter.** The starter code just returned the first few songs in the file, in file order, with a placeholder explanation. I replaced that with the point system above. The starter's example listener only described genre, mood and energy. The new scoring uses all seven song features, it scores and ranks every song, and it gives a reason for every point awarded. I also doubled the catalog from 10 to 20 songs, adding genres such as metal, classical, folk, reggae and blues, so different kinds of listeners would have something to find.

---

## 4. Data  

**Size.** 20 songs in `data/songs.csv`. Ten came with the starter project. I added ten more (ids 11–20) to cover hip-hop, classical, country, EDM, metal, reggae, R&B, folk, Latin and blues.

**Features.** Each song has a title, an artist, and two labels:

- **Genre:** 17 different genres.
- **Mood:** 16 different moods.

It also has five measurements:

- **Energy, happiness (valence), danceability and acousticness:** each on a 0 to 1 scale.
- **Tempo:** in beats per minute, from 60 to 168.

For Challenge 1, I added five more columns:

- **Popularity:** 0 to 100.
- **Release decade:** the 1960s to the 2020s.
- **Mood tags:** three detailed tags per song, such as "rainy, cozy, dreamy".
- **Instrumentalness:** 0 to 1, where 1 means no vocals.
- **Lyrics language:** English, Spanish, or instrumental.

**Limits.**

- **It is tiny and made up.** The songs are fictional, and I picked the numbers by hand.
- **Most labels appear only once.** 15 of the 17 genres have just one song. Lofi has three and pop has two. Moods are the same: chill has three songs, happy and intense have two, and every other mood has one.
- **There is a hole in the middle.** No song has energy between 0.55 and 0.75.
- **Loudness and acoustic sound always go together.** Every loud song is electronic, and almost every calm song is acoustic. There is no loud acoustic song and no quiet electronic song.
- **Some combinations are missing.** The only sad song is quiet folk, so there is no loud sad song.
- **The Challenge 1 columns are made up too.** I invented the popularity numbers, decades and tags. Only one song is in Spanish. Seven of the twenty songs are instrumental: the three lofi songs plus the ambient, jazz, synthwave and classical ones. So for those genres, the language and instrumental labels mostly repeat what the genre already says.
- **Some parts of taste are not there at all:** the lyrics themselves, artist info, and anything about what a person actually listened to.

---

## 5. Strengths  

- **It works well when your labels and numbers agree, and the catalog has your genre.** The pop/happy fan gets *Sunrise City* (6.76 out of 7). The rock fan gets *Storm Runner* (6.80). The lofi study listener gets three lofi songs at the top.
- **Different listeners get different lists.** The pop fan and the study listener share no songs at all, because they asked for opposite things.
- **Every pick comes with its reasons.** Each recommendation lists the points it earned, so you can always see why a song ranked where it did. Since Challenge 4, you can also see them as a compact table with one row per song.
- **It handles missing or odd input without crashing.** A profile with no preferences, or with impossible numbers, still produces a list.
- **The diversity option shares each list among more artists.** With it on (Challenge 3), a song loses 1.5 points for every song by the same artist already on your list, and 0.75 points for every song in the same genre. That makes each list fairer: an artist with several similar songs can't fill your top 5 just by sounding alike, so other artists get a turn. In a simulation of 5,000 random listeners, lists with the same artist twice fell from 15.5% to 0%. It also loosens the filter bubble a little. The study listener gets a blues song instead of a third lofi song, and a brand-new user gets five different genres instead of the first five rows of the file. It does not even out how often each artist is recommended across all listeners, though (see section 6).
- **It is simple and predictable.** The same profile always gets the same list. All the weights sit in one place, so experiments are easy.
- **New features never change old results.** The advanced song features, the scoring modes, the diversity penalty and the table view are all optional. With none of them turned on, every result in this card comes out exactly the same.

---

## 6. Limitations and Bias 

**Listeners who want medium energy get pushed to one extreme.** The catalog has no songs with energy between 0.55 and 0.75, and its calm songs are mostly acoustic while its loud songs are electronic. For someone who wants 0.65 energy, every song earns about the same energy points (0.85 to 1.35 out of 1.5), so the yes/no acoustic setting ends up deciding the list. When I tested a medium-energy listener who doesn't like acoustic sound, all five picks were loud, including *Gym Hero* (0.93), while *Dusty Highway Home* (0.55), which is much closer in energy, came 9th. Switching the same listener to "likes acoustic" gave five calm songs instead, so an in-between listener never gets in-between music.

**Other limitations I found:**

- **Labels must match word for word.** "Indie pop" earns nothing for "pop", and "Hip Hop" earns nothing for "hip-hop". The mood tags from Challenge 1 give partial credit, but only for profiles that use them. Genre and mood still need an exact match.
- **The genre label can outweigh how a song feels.** *Gym Hero* (pop, intense) beats the happier *Rooftop Lights* (indie pop) for a happy-pop fan (see section 7).
- **Labels quietly lose when the numbers disagree.** A "sad" listener who wants loud music gets angry metal, and the only sad song comes 9th. The system never says that it ignored the word.
- **Small genres get thin lists.** A rock fan gets one rock song, then songs that only sound similar.
- **There are no input checks.** The word "False" counts as "yes", and impossible numbers are accepted without a warning.
- **New users get the first five songs in the file**, because every song ties at zero. With the diversity option on, they get five different genres instead, but that is still decided by file order, not by anything about them.
- **The diversity option is fair to lists, not to artists.** In a simulation of 5,000 random listeners, it stopped any list from repeating an artist. But songs that share an artist or genre lost up to 6 points of exposure, and the gap between the most- and least-recommended song grew from 24 to 28 points.
- **The weights are my picks, not the listener's.** Since Challenge 2, a listener can choose one of four scoring modes, such as "mood-first". But I picked all four weight sets by hand, and nobody can set their own.

---

## 7. Evaluation  

**Profiles I tested.** I ran nine listeners through the same 20 songs. Three are everyday listeners: a pop/happy fan, a late-night lofi study listener, and a deep intense rock fan. Six are "trick" profiles, built to catch the scoring off guard: conflicting preferences, a genre typo, a setting given as the wrong data type, impossible numbers, and a brand-new user with no preferences at all. The full terminal output for every profile is in the README's [Stress Test](README.md#stress-test-diverse-and-adversarial-profiles) section. While looking for bias I also tried one extra listener who wants medium energy (section 6). I also ran one experiment that doubled the weight on energy and halved the weight on genre (README, [Experiments You Tried](README.md#experiments-you-tried)). It fixed the *Gym Hero* problem for pop fans, but it let a happy pop song into the rock and sad lists. The results were different, not better, so I kept the original weights. Later, for Challenge 1, I added three profiles that use the new song features (README, [Challenge 1](README.md#challenge-1-advanced-song-features)). The nine profiles below still score exactly as before, because the new rules only count when a profile asks for them. For Challenge 2, I ranked all twelve profiles under four scoring modes (README, [Challenge 2](README.md#challenge-2-multiple-scoring-modes)). For Challenge 3, I compared every profile with and without the diversity penalty, and re-ran the 5,000-listener simulation to check fairness (README, [Challenge 3](README.md#challenge-3-diversity-and-fairness-logic)). Everything below uses the default "balanced" mode with no diversity penalty.

**What I looked for.** For each list I asked four questions. Does the #1 song match my own sense of what this listener wants? Can I explain the #1 song using only the scoring rules? Does the same song keep showing up for very different listeners? When two listeners differ on one setting, does the list change the way I'd expect?

**Results that matched my intuition.**

- **Pop/happy:** *Sunrise City* is the only song that is both pop and happy, and it wins by more than a full point.
- **Late-night study:** *Library Rain* and *Midnight Coding* take #1 and #2. Both are calm, acoustic lofi tracks, and either would be a good pick for studying.
- **Deep intense rock:** *Storm Runner*, the only rock song, wins with 6.80 out of 7.

**Comparing profiles side by side.** Each comment below compares two profiles' top 5 lists: what changed, and whether that change makes sense. I compared the three everyday listeners with each other, then compared each trick profile with the normal profile closest to it.

*Everyday listeners*

- **Pop/happy vs. late-night study:** The two lists share no songs. The pop fan gets loud, danceable, electronic songs (average energy 0.85), and the study listener gets quiet, mostly acoustic ones (average energy 0.36). This makes sense, because the two profiles ask for opposite things on almost every setting, including whether they like acoustic sound.
- **Pop/happy vs. deep intense rock:** Both lists are loud and electronic, so they share two songs, *Gym Hero* and *Laser Bloom*. The difference is happiness. The pop list is full of bright, happy songs. The rock list brings in darker ones like *Iron Cathedral* (angry metal) and *Night Drive Loop* (moody synthwave). This makes sense: the rock fan asked for the same loudness but much less happiness (0.4 instead of 0.8). *Gym Hero* gets into both lists for different reasons: its pop label for the pop fan, and its "intense" mood for the rock fan.
- **Late-night study vs. deep intense rock:** No shared songs, as expected for opposite listeners. The more telling difference is how fast the scores drop. The study listener's top three are all lofi and within one point of each other (6.73 to 5.75), because the catalog has three lofi songs. The rock fan's #1 scores 6.80, but #2 drops to 4.49, because there is only one rock song. After that, the system can only fill the list with songs that sound similar. That is a gap in the catalog, not a mistake in the scoring.

*Trick profiles vs. the closest normal profile*

- **High energy + sad vs. deep intense rock:** The same five songs, just in a different order. Asking for "sad" instead of "rock/intense" barely mattered, because no loud song in the catalog is sad, so the mood word had nothing to match. The one real change, *Iron Cathedral* moving up to #1, comes from the lower happiness target (0.2 instead of 0.4): it is the darkest song in the catalog. The numbers add up, but it shows that the system can quietly ignore what a listener asks for in words (see Surprise 1 below).
- **Metal genre with calm numbers vs. late-night study:** Three of the five songs are the same (*Spacewalk Thoughts*, *Library Rain* and *Coffee Shop Stories*), and no metal song appears at all. Asking for metal changed almost nothing, because every other setting describes quiet, acoustic music, and the only metal song is the loudest one in the catalog. On the scorecard this makes sense: the 2-point genre prize can't make up for losing on every measurement. But a real person who typed "metal" would be confused by this list.
- **"Hip Hop" typo vs. "hip-hop" spelled correctly:** The same five songs in the same order, and *Concrete Crown* stays #1. The only difference is its score: 4.83 instead of 6.83. To the computer, a space instead of a hyphen is a different genre, so the 2-point genre prize disappears. The ranking held only because *Concrete Crown* fits so well on everything else. In a closer race, the typo could have pushed the right song down.
- **Acoustic setting given as the word "False" vs. a real "no":** *Laser Bloom* stays #1, but its score drops from 6.92 to 5.99. *Storm Runner* falls out of the top 5, and *Rooftop Lights*, the most acoustic of the upbeat songs, jumps to #2. The program reads any word typed into that setting, even "False", as a yes, so this EDM fan gets treated like someone who loves acoustic sound. The damage is small here only because the catalog has no loud acoustic songs to promote.
- **Impossible numbers vs. deep intense rock:** Four of the five songs are the same, but the impossible-numbers list is simply sorted from loudest to quietest (energy 0.98 down to 0.82), and every score is under 1 out of 7. Impossible danceability and tempo targets give every song zero points for those settings, so energy is the only setting left to tell songs apart. That is the correct math, but the system should have warned that the input made no sense.
- **Empty profile vs. pop/happy:** Both lists start with *Sunrise City*, for completely different reasons. The pop fan gets it because it is the best match (6.76 out of 7). The empty profile gets it because it is the first song in the file (0.00). With no preferences, every song ties, and ties keep their file order, so these "recommendations" are just the first five songs in the file.

**Why does *Gym Hero* keep showing up for people who just want happy pop?** Think of the scorecard from section 3. *Gym Hero* is labeled "pop", so it collects the biggest single prize: 2 points for matching your favorite genre. Its mood is "intense", not "happy", so it misses the mood prize, but that prize is only worth 1 point. Compare *Rooftop Lights*, which most people would call a better fit. It is a happy song, but it is labeled "indie pop", and the judge only gives the genre prize when the label matches word for word. So *Rooftop Lights* gets the 1-point mood prize and nothing for genre.

On everything the judge can measure, the two songs are almost tied (3.64 points to 3.56). *Rooftop Lights* is closer to the energy, happiness, danceability and tempo the listener asked for. *Gym Hero* earns a little more for sounding fully electronic. So the whole one-point gap between them comes from the labels: a "pop" label is worth twice as much as a "happy" label, and "indie pop" doesn't count as pop. In plain terms, the system trusts the name on the box more than how the song actually feels.

*Gym Hero* also shows up well beyond pop: it is in the top 5 for 7 of my 9 profiles, even though it gets the genre prize only once. It is the catalog's all-purpose loud song. It is very energetic (0.93), very danceable (0.88) and almost entirely electronic, so anyone who asks for loud, non-acoustic music finds it close to what they asked for, whatever genre they named. Five of my nine profiles want loud music, which inflates that count. In two of the seven lists, it appears for reasons that have nothing to do with taste: its position in the song file (the empty profile) and its raw loudness (the impossible-numbers profile).

**Surprise 1: a metal song is the top pick for a "sad" listener.** One trick profile asks for a sad mood, but also for loud, fast, non-acoustic music. The #1 pick was *Iron Cathedral*, an angry metal song. The only sad song in the catalog, *Pinewood Letters*, came 9th. Here is how the points added up:

| Rule | #1 *Iron Cathedral* | #2 *Storm Runner* | #9 *Pinewood Letters* |
|---|---|---|---|
| Mood is "sad" (+1.0) | 0 | 0 | +1.00 |
| Energy (target 0.9) | +1.38 | +1.48 | +0.60 |
| Happiness/valence (target 0.2) | +0.49 | +0.36 | +0.47 |
| Danceability (target 0.5) | +0.47 | +0.42 | +0.45 |
| Tempo (target 150 BPM) | +0.41 | +0.49 | +0.19 |
| Not acoustic | +0.96 | +0.90 | +0.09 |
| **Total** | **3.72** | **3.65** | **2.80** |

No loud song in the catalog is tagged "sad", so the mood point was out of reach for every song that fit the energy. The race came down to the numbers. *Iron Cathedral* won because it is the darkest song in the catalog: its happiness score (valence) of 0.22 almost exactly matches the 0.2 target. It beat *Storm Runner* by only 0.07 points, which is basically a coin flip. *Pinewood Letters* earned the mood point, but it is quiet and acoustic. Energy and acoustic fit together are worth 2.5 of the 7 points, so it fell far behind.

This feels only partly right. The low happiness target is the number version of "sad", and the system did respect it by picking the darkest loud song. But angry metal is not sad music. Someone who wants energetic sad songs is probably thinking of something like emo, and the catalog has nothing like that. The system just hands over the closest match by the numbers and never says that nothing really fit. The best score was only 3.72 out of 7.

**Surprise 2: acoustic fit decides close calls.** For the study listener, *Library Rain* (6.73) beat *Midnight Coding* (6.62), even though *Midnight Coding* is closer on energy and tempo. *Library Rain* won on acoustic fit alone (+0.86 vs. +0.71). Acoustic fit is the only rule where "more is better" instead of "closer is better", so for anyone who likes acoustic music, the most acoustic song always gets a boost.

**Surprise 3: no single song wins everywhere.** The nine profiles produced seven different #1 songs, so the genre prize is not strong enough to push one song to the top of every list. The repetition happens further down the list instead, as the *Gym Hero* explanation above shows.

---

## 8. Future Work  

1. **Give partial credit for related labels.** "Indie pop" should earn some of the "pop" prize, and "relaxed" some of the "chill" prize. That would fix the *Gym Hero* problem directly. My weight experiment showed that simply shrinking the genre prize for everyone causes new problems. The mood tags I added for Challenge 1 are a first step: they cut *Gym Hero*'s lead over *Rooftop Lights* from 1.08 to 0.58 points, but didn't flip it. Genre needs the same kind of partial credit.
2. **Fix the medium-energy problem.** Let listeners set an acoustic target from 0 to 1, like the other numbers, instead of answering yes or no. Also add songs with energy between 0.55 and 0.75, plus loud acoustic and quiet electronic songs.
3. **Check input and be honest about weak matches.** Reject settings like the word "False" or an energy of 1.5. When nothing fits well, or when a genre or mood the listener asked for was overruled, say so instead of quietly handing over the closest songs.

---

## 9. Personal Reflection  

**My biggest learning moment.** It was the weight experiment. I expected that doubling the energy weight and halving the genre weight would simply make the results better. It did fix the problem I was aiming at: *Rooftop Lights* finally beat *Gym Hero* for the happy-pop fan. But it also put *Sunrise City*, a bright happy pop song, into the lists for the dark rock fan and the sad listener. That is when I understood that weights are trade-offs, not fixes. Every number I pick helps some listeners and hurts others. It also changed how I test. After any change, I now rerun every profile, not just the one I was trying to fix. The other big lesson was that the worst problems came from the data, not the code. The missing medium-energy songs meant a yes/no acoustic setting decided whether someone got calm or loud music.

**How AI tools helped, and when I had to double-check them.** The AI assistant helped in three ways:

- **It sped up the busy work.** It wired up the scoring, formatted the output, and pasted real terminal output into my docs.
- **It explained specific results.** It was most useful when I asked about one result, like "why did *Iron Cathedral* rank first for the sad listener?", because it broke the score down rule by rule.
- **It found edge cases.** It suggested trick profiles I wouldn't have thought of, like the "Hip Hop" typo and the word "False".

I still had to check its work:

- **Its comments drifted from the truth.** Early comments said every reason in an explanation had earned points. The out-of-range test showed reasons worth "+0.00", so the comments were wrong.
- **Its summaries needed checking against the data.** One draft said every calm song was acoustic, but two calm songs sit around 0.4 acousticness. Another draft described the experiment as only halving genre, when it also doubled energy.
- **A passing test proved nothing.** The starter test passed even though the recommender class did no scoring at all. It passed only because the right song happened to be listed first, so I needed a test that fails when the ranking is wrong.
- **Its first version of the table code had a bug.** For Challenge 4, a line of tags exactly as wide as the column overflowed once its comma was added, which split "instrumental +0.49" across two lines. A test I wrote caught it. That test only checked three profiles at first, so I widened it to all of them.
- **My own expectation was wrong too.** I assumed the Challenge 3 diversity penalty would make things fairer to artists. Running the 5,000-listener simulation showed it made exposure slightly *less* even.

My rule now is: check every number against `songs.csv` or the terminal output, and test the claim, not just the code.

**How a simple algorithm can still "feel" like a recommendation.** My system only adds up points and sorts 20 songs. But the lofi study list looks like a playlist I would actually use, and the pop fan's #1 is exactly right. I think the "Why:" lines do a lot of the work. Seeing "genre match: pop (+2.0)" makes a pick feel thought through, even though it is just arithmetic. The flip side surprised me more. The system sounds just as confident when it is guessing. It gave the sad listener angry metal with neat reasons and never said that nothing really fit. A simple algorithm can feel smart until you hit a case it can't handle, and it won't tell you when that happens.

**What I'd try next.** Beyond the fixes in section 8 (partial credit for related labels, an acoustic setting from 0 to 1, more songs in the middle range, and input checks):

- **A variety rule across listeners,** so the same all-purpose loud song can't fill a slot in almost every list. The diversity penalty I added for Challenge 3 only works inside one list, so it doesn't solve this.
- **A thumbs up / thumbs down button** that adjusts the weights for each listener, instead of me hand-picking every weight set, including the four scoring modes.
- **A "no good match" message,** shown when the best score is low, so the system admits when it is guessing.

**How this changed how I think about music apps.** When an app keeps recommending the same few songs, I no longer assume that's my taste. It might be gaps in the catalog, labels that don't fit, or weights someone picked. Seeing reasons like "genre match: pop (+2.0)" made the bias obvious, and most real apps never show that. I also think more about fairness for artists. In my tiny catalog, some songs got recommended far less often just because of how they sound or which genre they share. Real apps have millions of songs and real listening history, but I expect the same trade-offs exist there, just harder to see.
