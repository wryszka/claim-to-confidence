# Executive briefing — From Claim to Confidence

**In one sentence:** a live, believable demonstration showing how a single correction to one
insurance claim flows — automatically, safely, and with a full paper trail — through
everything that decision touches: the money the insurer sets aside, its reinsurance, its
accounts, and its capital.

### Why now
A recent demonstration showed how a frontier AI model — Claude — can fix spreadsheet formulas
and draft a regulatory letter. It's genuinely powerful, and it answers an important question:
*can a model help an actuary do the task?* This demo **extends that story**: *when a claim
changes, can you trust the number that comes out the other end — after reinsurance, after the
accounting, after the capital impact — and can you prove how you got there, months later?* A
model excels at the task; a governed platform operationalises the whole decision. **Together,
they're what the business needs** — and in this demo they're together: Claude runs (via
Databricks' Foundation Model API) as a first-class agent *inside* the governed decision loop,
not as a standalone tool. That's where the two strengths meet.

### What a "reserve" is (the one piece of jargon)
An insurer's best estimate of money it still expects to pay for claims that have already
happened but aren't fully settled. If a claim grows, that estimate rises — and the change
ripples outward. This demo makes that ripple visible, correct and trustworthy.

### The story in one picture
| Step | What happens | The number |
|---|---|---|
| A claim is corrected | One claim's estimate rises | **€2.0m** |
| The reserve is re-decided | Total money set aside rises (gross) | **+€2.2m** |
| Reinsurance is applied | After the reinsurer's 20% share, the insurer's own extra cost | **+€1.76m** |
| The accounts are protected | €2.0m already booked, so only the remainder is posted | **+€0.2m** |

The last step is the quiet hero: a disconnected spreadsheet would double-count because it
doesn't know what finance already did. The connected platform does — and stops the error.

### What we want the audience to remember
1. A powerful model can speed up a *task*. A governed platform connects the whole *decision*.
2. Bricksurance turns a change in a claim into a traceable reserve decision, with the
   reinsurance, finance and capital consequences all visible.
3. It stays pleasant for the specialists while the system enforces quality, authority and
   reproducibility underneath.

### What is real, and what we won't claim
Everything on screen runs for real on Databricks against synthetic data for a fictional
insurer. We will not claim regulatory certification, will not invent savings figures, and in
anything public we credit others' progress and simply show what more becomes possible when the
whole decision is connected. This is a cooperative story.
