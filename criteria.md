# Acceptance criteria — FitFindr

Five criteria that say what "working" means for this agent, written in unit 3
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"The agent handles errors"* is an opinion.
*"When search returns nothing, the agent stops before calling the second tool,
in 5 of 5 tries"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter one. A reason that says something about your tools, your loop, or the
data earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

**Two are written for you. You write three.**

---

## 1. A matching query completes all three tools

Given a query that matches at least one listing, the agent completes all three
tool calls and returns a fit card — in at least 4 of 5 tries.

**Why this target:**
My search depends on matching words in the listing data, so some reasonable phrasings may not find a match. That is why I chose 4 of 5 instead of 5 of 5.
---

## 2. An impossible query stops before the second tool

Given a query that matches no listings, the agent stops before calling
`suggest_outfit` and returns a message naming what to change — 5 of 5 tries.

**Why this target:**
This path is controlled by a simple rule in the agent. When the search returns an empty list, it should always stop before calling suggest_outfit, so 5 of 5 is expected.

---

## 3. Something about state

After a successful search, the id of the item given to suggest_outfit matches the id of session["selected_item"] in 5 of 5 tries.


**Why this target:**
The selected item is saved in the session before suggest_outfit runs, so the same item should be passed to the next tool every time. A mismatch would mean the agent changed the item between steps.


---

## 4. The fit card uses the real listing facts

For 5 different listings, including at least 2 where `brand` is `None`, each
fit card is 2–4 sentences, states that listing's exact price and platform, and
never shows the word "None" or names a brand the listing doesn't have — in at
least 4 of 5 cards.

**Why this target:**
The caption comes from the model, so it can sometimes drop the price or make up a brand, and 32 of the 40 listings have no brand at all. I allowed one miss out of 5 because the wording changes every run, but more than one would mean my prompt isn't giving the model the right facts.

---

## 5. An empty wardrobe still gets a full run

Given a matching query and `get_empty_wardrobe()`, the agent finishes with a
non-empty outfit suggestion and a fit card, and the suggestion doesn't name any
item from the example wardrobe (like "Chunky white sneakers") — 5 of 5 tries.

**Why this target:**
An empty wardrobe is a normal case for a new user, and `suggest_outfit` is supposed to fall back to general styling advice instead of returning nothing. Naming a piece the user doesn't own would mean the tool is making things up, so I expect this every time.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 4 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 4. Something about the fit card

         The fit card is different every time.

         **Why this target:** ...

         > **Revised in unit 4:** For 5 different items, the 5 fit cards share
         > no opening sentence.
         >
         > **Why revised:** "different" wasn't checkable — two cards that
         > differed by one word still counted. The new version is something I
         > can actually score.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said the empty search stops it 5 of 5 times, but I got 3 of 5,
            so 3 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
