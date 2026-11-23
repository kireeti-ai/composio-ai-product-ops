# Publication redactions

GitHub push protection flagged one string in two saved copies of Discord's developer documentation (app #26): the documentation's own example bot token. It is not a credential of this project. To publish, the string was replaced by `[REDACTED_DISCORD_DOC_EXAMPLE_TOKEN]` in the published copy only; the local originals are unchanged. Because of this, `baseline/SHA256SUMS.txt` and the run manifests will not match these two files in this repository.

| File | SHA-256 before redaction | SHA-256 as published | Occurrences |
|---|---|---|---|
| `baseline/p1_v1/raw/26.json` | `d409e07153800f66667501661cd97139d832ec6a7f3bac0a01d80134eb594c0c` | `816869d0814aae6abfc9d6817d5ddb547734890d525d83df1d17f0621e00bfdb` | 1 |
| `runs/p1-batchA-groq-20261123_193428/bundles_full/26.json` | `c556f83963c2698781b5e8065c428effa5efdf99e724ba4151005dda8bb7e15d` | `8455f4b53f048a556e9f8fcb67d2e2cbc7eb80f3f922c446d758684313d682a2` | 1 |
