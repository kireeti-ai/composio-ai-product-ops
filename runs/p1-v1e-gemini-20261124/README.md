# p1-v1e (prepared, NOT approved) - same 27 apps as p1-v1d, plus provenance and separated retrieval/relevance summaries
- 12 apps numbered 51-100 are CANDIDATE research targets from a reconstructed secondary list: original Notion membership is NOT verified (see PLAN.json provenance).
- Held/excluded: Linear, Coda (identity pending); Sherlock, Harvest, fanbasis (excluded); Neo4j (one record, two surfaces; held); Gladly (pending-approval candidate #28).
- retrieval_usability and evidence_relevance are separate fields (page_evidence_table). Relevance is heuristic, not ground truth.
- The frozen extraction prompt and schema are unchanged. No APPROVED.json exists. Runner: src/run_p1.py --run p1-v1e-gemini-20261124 [--dry-run]
