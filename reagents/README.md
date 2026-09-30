# Name-reaction reagent list

Generated from `rxno.obo` by `build_reagents.py` (run from repo root).

- `name_reaction_reagents.md` / `.tsv` / `.json` – reagent list per name reaction
- `reagent_index.md` – reverse index, reagent -> reactions
- `unresolved.tsv` – name reactions with no reagent data yet
- `curated_reagents.tsv` – hand-curated input (edit this, then re-run the script)

RXNO itself only records reagents through `has_catalyst` (27 terms) and free text in definitions,
so most reagents are curated from standard literature. The `source` column says which:
`curated` or `curated+ontology`. Reactions without curated reagents, including catalyst-only ontology records, are in `unresolved.tsv`, with the parent class's reagents shown for context only. Curated entries have not been
checked against primary references, so review them before using them for synthesis planning.
