# Provenance-by-status cross-tab (100 apps)

Status derived INDEPENDENTLY from primary artifacts, then reconciled against the master coverage matrix and the execution ledger (all checks below passed).

| Provenance | Completed baseline | Completed, quarantined | Planned (frozen v1f) | Held: Neo4j | Held: identity | Excluded: identity | Unplanned | **Row total** |
|---|---|---|---|---|---|---|---|---|
| ORIGINAL_NOTION_LIST_1_50 | 23 | 0 | 16 | 0 | 0 | 1 | 10 | **50** |
| RECONSTRUCTED_LIST_51_100 | 2 | 1 | 12 | 1 | 2 | 1 | 31 | **50** |
| **Column total** | **25** | **1** | **28** | **1** | **2** | **2** | **41** | **100** |
| Master coverage count | 25 | 1 | 28 | 1 | 2 | 2 | 41 | 100 |

## Exact IDs per cell

| Provenance | Status | IDs |
|---|---|---|
| ORIGINAL_NOTION_LIST_1_50 | Completed baseline | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 21, 22, 23, 28, 49 |
| ORIGINAL_NOTION_LIST_1_50 | Completed, quarantined | - |
| ORIGINAL_NOTION_LIST_1_50 | Planned (frozen v1f) | 20, 25, 26, 27, 29, 32, 33, 34, 36, 38, 39, 41, 43, 44, 46, 47 |
| ORIGINAL_NOTION_LIST_1_50 | Held: Neo4j | - |
| ORIGINAL_NOTION_LIST_1_50 | Held: identity | - |
| ORIGINAL_NOTION_LIST_1_50 | Excluded: identity | 50 |
| ORIGINAL_NOTION_LIST_1_50 | Unplanned | 15, 24, 30, 31, 35, 37, 40, 42, 45, 48 |
| RECONSTRUCTED_LIST_51_100 | Completed baseline | 51, 84 |
| RECONSTRUCTED_LIST_51_100 | Completed, quarantined | 58 |
| RECONSTRUCTED_LIST_51_100 | Planned (frozen v1f) | 52, 53, 56, 61, 62, 63, 65, 70, 71, 72, 75, 76 |
| RECONSTRUCTED_LIST_51_100 | Held: Neo4j | 66 |
| RECONSTRUCTED_LIST_51_100 | Held: identity | 73, 78 |
| RECONSTRUCTED_LIST_51_100 | Excluded: identity | 80 |
| RECONSTRUCTED_LIST_51_100 | Unplanned | 54, 55, 57, 59, 60, 64, 67, 68, 69, 74, 77, 79, 81, 82, 83, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100 |

## Sub-splits that reconcile to the columns

Planned (frozen v1f) by phase: original 7+9 = 16, reconstructed 8+4 = 12; total 28.

| Unplanned: expansion wave | Original | Reconstructed | Total |
|---|---|---|---|
| 3A_core_ready_access_topup | 7 | 7 | 14 |
| 3B_partial_targeted_reretrieval | 3 | 3 | 6 |
| 3H_provisional_identity_hold | 0 | 2 | 2 |
| 4_no_retrieval_full_discovery | 0 | 19 | 19 |

## Reconciliation checks

- PASS: original IDs 1-50 sum to 50 [50]
- PASS: reconstructed IDs 51-100 sum to 50 [50]
- PASS: grand total 100
- PASS: independent status == master coverage status for EVERY app [0 mismatches]
- PASS: every status column total == master coverage count
- PASS: provenance == master coverage provenance for every app
- PASS: ledger provenance_group agrees for every app
- PASS: status == ledger master_status for every app
- PASS: v1f phase split sums to the PLANNED column (15 + 13 = 28)
- PASS: expansion waves sum to the UNPLANNED column (41) and to the expansion plan
- PASS: a reconstructed app is never flagged as notion-verified (master + ledger)
- PASS: baseline records: 25 + 1 quarantined = 26 = files in baseline/p1_v1/pass1
