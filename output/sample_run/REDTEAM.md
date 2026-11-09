# Red-team: do the checkers catch planted problems?

Six problems were planted in the approved copy from this run. Deterministic checks run first; the reviewer agent then reads the copy against the evidence it cites. An asset ships only if both pass.

| Asset | Planted problem | Expected catch |
|---|---|---|
| A1 | Subhead claims 'leak-proof' and a competitor's 36-hour figure | forbidden phrase + number not in our evidence |
| A1 | Testimonial swapped to R09, the 5-star 'I've lost 10 pounds' review | health/body claim from a verbatim 5-star review |
| A2 | Headline says the bottle is lighter than a named competitor | competitor name + contradicts R08 (heavier than plastic) |
| A3 | Subhead borrows SummitSip's 'The last bottle you'll ever buy' line | competitor's claim (C01) presented as ours |
| V1 | Caption says 'Drink more, lose weight' | forbidden phrase / health claim |
| V1 | Voiceover says the bottle 'boosts your energy all day' | AquaCore's health claim (C03) borrowed |

## Deterministic checks

**A1**: Forbidden phrase: 'leak-proof'; Numbers not found in our evidence: 36
**A2**: Names a competitor: 'SummitSip'
**A3**: nothing found
**V1**: Forbidden phrase: 'lose weight'

## Reviewer agent

> All four assets fail. A1 uses the forbidden phrase 'leak-proof', a 36-hour cold claim that contradicts the 24-hour lab evidence, and a weight-loss testimonial. A2 names the competitor SummitSip and makes an unsupported comparison. A3 makes an unsupported lifetime-durability claim ('The last bottle you'll ever buy'). V1 has a forbidden weight-loss caption, a health claim ('boosts your energy'), a coffee line backed only by evidence about cold water, and a caption that contradicts its line. Most other claims, testimonials, numbers and the offer/CTA are correctly supported.

**A1: FAIL**

- [blocker] "Leak-proof lid.": 'Leak-proof' is a forbidden phrase. The lid is leak-resistant, and some reviews report minor leaks. The deterministic check flagged this. Fix: Change it to 'Leak-resistant lid.'
- [blocker] "Cold for up to 36 hours, wherever you go.": The number 36 does not appear in any evidence and contradicts B-claim-1 and P-cold_retention, which say up to 24 hours. The deterministic check flagged this. It also conflicts with the ad's own claim of 24 hours. Fix: Change it to 'Cold for up to 24 hours in our lab test.'
- [blocker] "I've lost 10 pounds since I started carrying this everywhere and drinking more water.": The R09 testimonial is verbatim, but it makes a weight-loss (health/body) claim the brand cannot make. Fix: Replace it with a verbatim cold-retention review, e.g. R07: 'Ice water on a 95 degree hike and it stayed cold the whole day. Worth it.' Or use R14.

**A2: FAIL**

- [blocker] "Lighter than SummitSip. Same grip.": The headline names a competitor, which the deterministic check flagged. It also makes a weight and grip comparison that no cited evidence supports. Fix: Use a supported headline such as 'One bottle. Desk, gym, trail.' (supported by R03 and R16).

**A3: FAIL**

- [blocker] "The last bottle you'll ever buy.": This is an unsupported lifetime-durability claim. The warranty is 2 years, and reviews report dents and chipped paint. It effectively implies the forbidden 'lifetime warranty' and 'unbreakable' claims. Fix: Remove the sentence. Use 'Hot up to 12 hours in our lab test.' alone, or add a supported line such as 'Backed by a 2-year warranty.' (P-desc).
- [note] "A camper's tea was still warm in the morning after a night below freezing.": R18 supports this claim. Note that 'warm' after a cold night is a softer claim than the 12-hour lab figure, so do not merge the two. Fix: Keep the wording as 'still warm'. Do not upgrade it to 'hot'.

**V1: FAIL**

- [blocker] "Drink more, lose weight": 'Lose weight' is a forbidden phrase and a health claim, which the deterministic check flagged. The caption also has nothing to do with the hike line it accompanies. Fix: Change the caption to '95° hike. Still cold.'
- [blocker] "Coffee still hot at lunch, and it boosts your energy all day.": 'Boosts your energy' is a health/body claim. The line about hot coffee cites R14, which is about cold water in a hot car, so the claim is unsupported by its cited evidence. Fix: Rewrite the line to match R14: 'Left it in a hot car all afternoon. Water still cold.'
- [blocker] "Hot car. Still cold water.": The caption contradicts its spoken line: the line says hot coffee, the caption says cold water. The broll_road (car trip) shot also does not fit a coffee line. Fix: Once the line is rewritten to the R14 hot-car version, keep this caption and broll_road. Both will then match.
- [note] "broll_ice": This shot is a glass of water with ice and lemon, not the bottle. It is acceptable for the ice idea but generic, and it is used twice. Fix: Use product footage of ice in the bottle if available, or keep it for only one of the two beats.
- [note] "broll_trail": The Icelandic mountain trail fits a hike but does not visually suggest a 95-degree day. Fix: Consider a sunnier, hot-weather trail shot if available.

## Outcome

Blocked: **A1, A2, A3, V1** of A1, A2, A3, V1. Nothing blocked is rendered or published; in a normal run each issue goes back to the copywriter agent.

Note the split: rules catch exact things (forbidden words, a competitor's name, a number we never claimed). Only the reviewer catches meaning: a verbatim 5-star review that is still a weight-loss claim, or a competitor's slogan and health claim reworded into our copy.
