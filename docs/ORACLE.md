# The financial oracle (verified)

All figures **EUR millions, accident year 2023 only, gross, undiscounted indemnity.** These
are acceptance oracles: the engine must reproduce them from real inputs, never return them
canned. Verified internally consistent to the cent, and reproduced by `tools/smoke_test.py`
(43/43 checks) and live from the Unity Catalog tables.

## Inputs and method indications

| Item | Initial (cutoff 3 Jul) | Corrected (cutoff 6 Jul) |
|---|---:|---:|
| Paid to date | 58.0 | 58.0 |
| Case outstanding | 23.0 | 25.0 |
| Reported incurred = paid + case | 81.0 | 83.0 |
| Selected incurred cumulative development factor | 1.20 | 1.20 |
| Selected paid cumulative development factor | 1.70 | 1.70 |
| Earned premium | 120.0 | 120.0 |
| Expected loss ratio | 80% | 80% |
| Expected ultimate (= premium × loss ratio) | 96.0 | 96.0 |
| Incurred chain-ladder ultimate (= incurred × 1.20) | 97.2 | 99.6 |
| Paid chain-ladder ultimate (= paid × 1.70) | 98.6 | 98.6 |
| Incurred Bornhuetter-Ferguson ultimate | 97.0 | 99.0 |

**Formulas.** Reported incurred = paid + case. Incurred CL = incurred × incurred CDF.
Paid CL = paid × paid CDF. Expected ultimate = premium × loss ratio.
Incurred BF = incurred + expected ultimate × (1 − 1/incurred CDF) = 81.0 + 96.0 × 0.16667 = 97.0.
Outstanding = ultimate − paid. IBNR = ultimate − paid − case.

The 1.20 and 1.70 are **prescribed, governed actuarial selections**, not fitted. Empirical
factors from the triangle (~1.19 incurred) are shown separately as a diagnostic.

## Selection and reinsurance

Demo selection policy for this cohort (synthetic, not a recommendation): **50% incurred
chain-ladder + 50% incurred Bornhuetter-Ferguson.**

| Item | Initial | Corrected | Change |
|---|---:|---:|---:|
| Selected ultimate | 97.1 | 99.3 | +2.2 |
| Selected gross outstanding | 39.1 | 41.3 | +2.2 |
| Selected gross IBNR | 16.1 | 16.3 | +0.2 |
| Ceded outstanding (20% quota share) | 7.82 | 8.26 | +0.44 |
| Net outstanding | 31.28 | 33.04 | +1.76 |

## Finance — prevent double counting

The claims ledger has **already posted** the €2m case correction. Ledger gross outstanding =
case 25.0 + existing IBNR 16.1 = **41.1**. Revised selected gross outstanding = 41.3. So only
**€0.2m** of additional IBNR remains to book.

| Movement | Gross | Ceded | Net |
|---|---:|---:|---:|
| Case correction (already posted) | 2.00 | 0.40 | 1.60 |
| Additional IBNR (to book) | 0.20 | 0.04 | 0.16 |
| **Total revision vs original** | **2.20** | **0.44** | **1.76** |

Residual journal (balanced): debit gross claims expense 0.20 / credit IBNR liability 0.20;
debit reinsurance recoverable 0.04 / credit reinsurance recovery income 0.04.

## Four numbers, kept distinct

- **+2.4** — incurred chain-ladder *method indication* movement (97.2 → 99.6).
- **+2.2** — *selected gross* movement (the 50/50 blend; BF moves only +2.0). The hero gross.
- **+1.76** — *net* movement after the 20% quota share. Labelled "net undiscounted indemnity
  movement" — not an IFRS 17 charge, not a capital number.
- **+0.2** — *residual finance journal* only (€2.0m already booked).
