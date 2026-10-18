# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

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

The judge scores every song this way, sorts them from highest to lowest, and shows you the top 5. Each recommendation lists exactly which rules gave it points, so you can see why it was picked. For example: "genre match: pop (+2.0), energy 0.82 vs target 0.8 (+1.47)…"

**What changed from the starter.** The starter code just returned the first few songs in the file, in file order, with a placeholder explanation. I replaced that with the point system above. The starter's example listener only described genre, mood and energy. The new scoring uses all seven song features, it scores and ranks every song, and it gives a reason for every point awarded. I also doubled the catalog from 10 to 20 songs, adding genres such as metal, classical, folk, reggae and blues, so different kinds of listeners would have something to find.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
