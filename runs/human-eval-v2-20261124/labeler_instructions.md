# Labeler instructions (one page)
1. Open ONLY your label sheet (`label_sheet_blind_*.csv`). Do not open scoring sheets, model outputs, Groq verdicts, plans, tiers or any file under runs/ other than your sheet and these instructions.
2. Work alone. Do not discuss an app with the other labeler until the agreement report exists. Do not ask an LLM what the answer is.
3. For each app first confirm which product it is from the vendor's own site (reconstructed-list apps have no identity authority). If identity is doubtful write it in `notes` and mark the app's rows `undeterminable` only if no public source decides the field.
4. Use official documentation, pricing pages, developer portals and official repositories only. For every non-blank truth cell fill URL, a verbatim quote and the access date (docs change). Save a page copy or hash if you can.
5. Set fields (`auth_methods`, `api_types`): separate values with `;`. Enum fields: pick one allowed value; if none fits choose the closest and set `enum_fit` = forced.
6. `undeterminable_from_public_sources` = Y only when no public source decides the field. `existing_mcp = none_found` needs the search queries listed in `notes`.
7. `blocker` is free text: the main obstacle, or `none`.
8. Calibration set first (3 apps), then meet once with the other labeler to align definitions. Definitions are then FROZEN: changes need a written amendment before any frame is labelled.
