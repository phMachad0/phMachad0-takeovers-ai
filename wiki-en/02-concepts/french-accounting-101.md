---
type: concept
tags: [domain, accounting, france]
status: draft
updated: 2026-09-14
---

# French accounting in 15 minutes

Entry page for the domain. If you've never opened a French financial statement, start here
and follow the links.

## What a French company files with the State every year

Every French company closes an **exercice** (fiscal year, normally 12 months, not always
matching the calendar year) and produces the **comptes annuels** — the annual financial
statements. That package has three pieces, defined by the *Code de commerce*:

| French piece | rough equivalent | what it is |
|---|---|---|
| **Bilan** | Balance Sheet | snapshot of net worth at closing date |
| **Compte de résultat** | Income Statement | record of what happened during the fiscal year |
| **Annexe** | Notes to the financial statements | text and tables explaining the two above |

Watch out for a false friend that trips everyone up at first: **"bilan" does NOT mean
"annual accounts" in the broad sense — it specifically means the balance sheet.** But
Takeovers uses "bilan" in the folder name (`data/<siren>/bilans/`) to refer to the *entire
filing* — bilan + compte de résultat + annexe + reports. Both senses coexist in the
challenge. See [[french-glossary]].

## Where this gets filed

The annual accounts are **filed** with the *greffe du tribunal de commerce* (the commercial
court registry) and enter the **RNE** — *Registre National des Entreprises*, the French
national business register, operated by **INPI**. That's where all the PDFs in `data/` come
from. See [[corpus-and-scope]].

Two different dates, and confusing them is a common mistake:

- **date de clôture** — the fiscal year's closing date (e.g. 30/04/2023). This is the date
  the schema asks for in `fiscal_year_end`.
- **date de dépôt** — the date the document was filed with the registry. This is the date
  that's **in the filename** (`bilan_2023-11-20_<id>.pdf`).

The gap between the two is months, sometimes over a year. The brief warns: *"Not the
deposit date in the filename."*

## SIREN, SIRET, RCS

- **SIREN** — 9 digits, identifies the **company**. It's the folder name in `data/`.
  Roughly equivalent to the root of a Brazilian CNPJ (its first 8 digits).
- **SIRET** — 14 digits = SIREN + 5 digits identifying an **establishment**. Equivalent to a
  full CNPJ with branch code.
- **RCS** — *Registre du Commerce et des Sociétés*, the commercial register. Appears as
  `RCS AVIGNON 401 009 741` — registry's city + SIREN.

## The corporate forms that appear in the corpus

| acronym | name | analogue |
|---|---|---|
| **SARL** | Société à Responsabilité Limitée | Ltda (limited liability company) |
| **EURL** | single-member SARL | single-member Ltda |
| **SAS** | Société par Actions Simplifiée | simplified joint-stock company, flexible bylaws |
| **SA** | Société Anonyme | classic corporation, mandatory board |

This matters for two reasons: it changes the vocabulary (*parts sociales* in an SARL vs
*actions* in an SAS/SA) and it changes which tax form the company uses.

## The Plan Comptable Général

France has a **mandatory national chart of accounts**, the PCG, with numbered classes
(class 6 = expenses, class 7 = revenue, etc.). That's why French financial statements are so
much more standardized than Brazilian or American ones — and it's the underlying reason
[[idea-01-code-anchoring]] works.

Important practical consequence: the **French compte de résultat is organized by the
NATURE of the expense**, not by function. There's no line "Cost of Goods Sold". There are
"purchases of goods", "purchases of raw materials", "salaries", "external services". Anyone
who wants COGS has to build it. See [[cogs-a-la-francaise]].

## Next reading

- [[liasse-fiscale]] — the standardized tax form
- [[plaquette-vs-liasse]] — **the finding that defines the pipeline's architecture**
- [[the-12-fields]] — exactly what needs to be extracted
