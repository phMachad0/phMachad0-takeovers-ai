---
type: finding
id: F002
tags: [units, trap, critical]
status: draft
updated: 2026-09-14
---

# F002 — Bernachon's "K€" governs the annexe, not the balance sheet

**Impact: high. Partially contradicts a claim in the brief.**

## Claim

The brief says `328024377` *"reports in thousands of euros, said in passing on a handful
of lines"*. In the three documents in scope for this company, **the balance sheet and the
compte de résultat are in euros**. Every mention of `K€` or `Kilo-euros` belongs to **a
single table in the annexe** — the *Liste des filiales et participations*.

## Evidence

Occurrences of `K€` / `en milliers` / `Kilo-euros` across the 15 in-scope documents, with
context:

| doc | pg. | context |
|---|---|---|
| `63e8ebbb…7c` | 10 | `...ions (détenues entre 10 et 50%) Les montants sont indiques en K€ Amortissements des immobilisations...` |
| `63e8ebbb…7d` | 11 | `Liste des filiales et participations` / `Tableau réalisé en Kilo-euros` |
| `63e8ebbb…7d` | 11 | `- Autres participations étrangères` / `Les montants sont indiqués en K€.` |
| `63e8ebbb…7d` | 33 | same (the document repeats the annexe) |
| `63e8ebbb…7e` | 12 | `Liste des filiales et participations` / `Tableau réalisé en Kilo-euros` |
| `63e8ebbb…7e` | 12, 33 | `Les montants sont indiqués en K€.` |
| **all other 12 documents** | — | **no occurrence** |

In every case the marker sits **immediately before or after the subsidiaries table**, and
that table's header reads `Tableau réalisé en Kilo-euros`, explicitly scoping it.

Page 12 of `63e8ebbb54febda17c19ee7e`, in reading order:
```
[200, 452] Immobilisations financières
[196, 576] Liste des filiales et participations
[195, 687] Tableau réalisé en Kilo-euros
[210,1487] EURL BERNACHON PASSION   [888,1485] 8   [1028,1487] -2  [1090,1485] 100,00
[210,1540] SARL BERNACHON PARIS     [873,1535] 10  [1021,1539] 34  [1088,1537] 100,00
[183,2289] Les montants sont indiqués en K€.
```

The values in this table — `8`, `10`, `-2`, `34` — are indeed small, consistent with
thousands of euros. They are the subsidiaries' capital and capitaux propres.

Same filing, page 3, liasse 2051:
```
[1953, 473] DA   [2161, 471] 152 500        ← capital social
[1960,1251] DL   [2125,1252] 3 036 481      ← total capitaux propres
```

## Independent confirmation via internal anchoring

The share capital appears three times in the document, in different records:

- page 3 (liasse 2051, `DA`): `152 500`
- page 20 (legal cover page): `BERNACHON S.A. ... au capital de 152 500 euros`
- page 24 (auditor's report): `SA au capital de 152 500 €`

Exact match, with the unit spelled out in both textual mentions. **The balance sheet is in
euros, proven by the document itself.**

## Consequence

A `grep -i "K€"` over the whole document classifies Bernachon as kEUR and misreads the
balance sheet by 1000× — exactly the error the brief describes, arrived at by a different
path than the one the brief suggests. See [[idea-06-unit-with-scope]].

## Declared uncertainty

I don't know whether I'm reading the brief's intent correctly. Three readings:

1. the brief refers to these annexe lines and the wording is ambiguous;
2. there's a kEUR document outside the 15 listed;
3. it's a deliberate trap and this is the expected conclusion.

What **is** verifiable, and I state with confidence: across the 15 in-scope documents, the
bilan and compte de résultat values are in euros, and I found no counterexample.

**Pending:** also sweep the 5 out-of-scope companies to see whether any kEUR bilan exists
in the corpus. If one does, reading 2 gains ground.

## Links

- [[units-eur-vs-keur]] · [[idea-06-unit-with-scope]]
