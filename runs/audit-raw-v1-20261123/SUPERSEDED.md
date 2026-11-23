# SUPERSEDED by audit-raw-v2-20261123 (kept as history, do not use for decisions)
Rubric v1 was too lenient: 74/81 READY, duplicate pages counted twice, wrong-product domains counted as "official" (e.g. Sherlock), and every app showed 8-10
"MCP hits" because the MCP search query always returns MCP-related results regardless of the app. Found by hand-checking ambiguous-name apps (Close, Front, Plain,
Twenty, Linear, Coda, Sherlock, Clay). audit_raw_v1_script.py is the exact script that produced these files.
