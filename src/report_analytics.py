"""Plain-language analytics for the single assignment report.

All counts and comparisons come from registry/run records. Labels translate internal enums; they do not certify model claims.
"""
from collections import Counter, defaultdict
from urllib.parse import urlparse

ENUM_LABELS = {
    "self_serve_free": "Self-serve, no paid plan stated",
    "self_serve_trial_or_paid_plan": "Self-serve, with trial or paid plan",
    "approval_or_review_required": "Approval or review required",
    "partner_or_contact_sales": "Partner or sales contact required",
    "no_public_api": "No public API reported",
    "official": "Official AI-assistant connection reported",
    "community": "Community connection reported",
    "none_found": "Not found in the sources reviewed",
    "yes": "Looks feasible in the model output",
    "yes_with_caveats": "Feasible with constraints in the model output",
    "no": "Model reports a blocker",
    "supported_lexical": "Matching quotation found (text check only)",
    "unsupported": "Quotation does not support this claim as submitted",
    "unknown": "Unknown",
    "not_found_in_provided_evidence": "Not found in the evidence supplied",
    "needs_human": "Needs human review",
    "not_run": "Not yet reviewed",
    "complete": "Complete",
    "paused_quota": "Paused at provider quota",
    "failed": "Failed; see attempt log",
    "quarantined": "Quarantined for identity review",
    "held": "Held pending a decision",
    "excluded": "Excluded pending identity resolution",
    "identity_blocked": "Blocked by identity uncertainty",
    "not_started": "Not started",
    "all_quotes_lexically_supported": "All submitted quotes passed the text check",
    "mixed_lexical_results": "Mixed quote-check results",
    "lexical_review_required": "Quote check needs human review",
    "evidence_bundle_used": "Evidence bundle used",
    "partial_retrieval_identity_review": "Partial retrieval; identity review needed",
    "retrieval_gap": "Evidence retrieval gap",
    "retrieval_available_not_extracted": "Evidence available; extraction pending",
    "identity_blocked_before_retrieval": "Held before retrieval for identity review",
    "not_recorded_or_not_started": "Not recorded or not started",
    "original_list_name": "In the supplied assignment list (verified against the export)",
    "reconstructed_candidate_unverified": "In the supplied assignment list (verified against the export)",
    "identity_review_blocked": "Identity unresolved",
    "identity_review_pending": "Identity review pending",
    "held_provisional": "Held as provisional",
    "excluded_unresolved": "Excluded pending identity resolution",
    "quarantined_identity": "Quarantined for identity review",
    "legacy_model_verification_record_present": "First-pass model review exists; not ground truth",
    "original_segment": "Verified against the supplied assignment list",
    "reconstructed_segment": "Reconstructed candidates; membership unverified",
}


def label(value):
    if value is None or value == "":
        return "Not yet established"
    if isinstance(value, list):
        return ", ".join(label(x) for x in value) if value else "Not yet established"
    return ENUM_LABELS.get(str(value), str(value).replace("_", " "))


def _primary(row):
    return next((v for v in row.get("versions", []) if v.get("version") == row.get("primary_version")), None)


def _safe_url(url, source_urls):
    p = urlparse(url or "")
    return p.scheme in ("http", "https") and bool(p.netloc) and url in source_urls


def filter_apps(apps, query="", category="", status="", provenance=""):
    """The matrix's documented filter semantics, exercised by offline tests."""
    q = (query or "").casefold().strip()
    return [a for a in apps if
            (not q or q in " ".join([a["name"], a["category"], a.get("description", ""), a.get("blocker", ""), " ".join(e["quote"] for e in a["evidence"])]).casefold()) and
            (not category or a["category"] == category) and
            (not status or a["status_label"] == status) and
            (not provenance or a["provenance"] == provenance)]


def _evidence_support(row, field):
    return [c for c in row.get("claims", []) if c.get("field") == field and c.get("state") == "supported_lexical"]


def _finding(title, statement, note, ids, measure=None, established=True):
    return {"title": title, "statement": statement, "note": note,
            "support_ids": sorted(set(ids)), "measure": measure,
            "established": bool(established)}


def build_report_data(rows, registry, comparison, legacy_verification, human_labels,
                      retrieval, source_check, source_meta=None):
    registry_ids = [int(a[0]) for a in registry["apps"]]
    row_ids = [int(r["registry_id"]) for r in rows]
    if len(registry_ids) != len(set(registry_ids)) or sorted(registry_ids) != list(range(1, len(registry_ids) + 1)):
        raise ValueError("registry IDs must be unique and contiguous")
    if row_ids != registry_ids:
        raise ValueError("dataset rows must match the registry one-for-one and in order")
    source_meta = source_meta or {}
    apps = []
    for r in rows:
        p = _primary(r); f = p.get("fields", {}) if p else {}
        page_urls = {s.get("url") for s in (p or {}).get("sources", [])}
        ev = []
        for e in (p or {}).get("evidence", []):
            ev.append({"field": e.get("field", ""), "url": e.get("url", ""), "quote": e.get("quote", ""),
                       "valid": bool(e.get("valid")), "issues": e.get("issues", []),
                       "state": next((c.get("state") for c in p.get("claims", []) if c.get("field") == e.get("field")), "unknown"),
                       "source_confirmed": _safe_url(e.get("url"), page_urls),
                       "retrieved_at": source_meta.get(e.get("url"))})
        prov = r.get("provenance_class", "unknown")
        provenance = "original_segment" if prov in ("original_notion", "verified_original_assignment_export") else "reconstructed_segment"
        all_versions = _comparison_versions(r)
        version_history = [{"version": name, "provider": v.get("provider", ""), "model": v.get("model", ""),
                            "model_identity_verified": v.get("model_identity_verified"), "extracted_at": v.get("extracted_at", ""),
                            "tokens": v.get("tokens"), "latency_s": v.get("latency_s"), "source_ref": v.get("source_ref", "")}
                           for name, v in all_versions.items()]
        sources = [{"url": s.get("url", ""), "sha256": s.get("sha256", ""), "chars": s.get("chars"),
                    "retrieved_at": source_meta.get(s.get("url"))} for s in (p or {}).get("sources", [])]
        apps.append({"id": int(r["registry_id"]), "name": r["name"], "category": r["category"],
                     "provenance": provenance, "provenance_label": label(provenance),
                     "status": r.get("status", ""), "status_label": ("Newly researched (source-quoted)" if r.get("manual_research") and not p else label(r.get("extraction_status"))),
                     "identity_label": ("Resolved to the registry hint; see identity note" if r.get("manual_research") and not p and r.get("identity_status") in ("identity_review_blocked", "identity_review_pending") else label(r.get("identity_status"))), "retrieval_label": label(r.get("retrieval_status")),
                     "extraction_label": label(r.get("extraction_status")), "evidence_label": label(r.get("evidence_validation_status")),
                     "verification_label": label(r.get("verification_status")), "human_label": label(r.get("human_review_status")),
                     "primary_version": r.get("primary_version"), "provider_model": (p or {}).get("provider", "") + (" · " if p and p.get("provider") and p.get("model") else "") + (p or {}).get("model", ""),
                     "description": f.get("one_liner", ""), "auth": f.get("auth_methods", []), "access": f.get("access"),
                     "access_label": label(f.get("access")), "access_note": f.get("access_note", ""),
                     "api_types": f.get("api_types", []), "api_types_label": label(f.get("api_types", [])),
                     "api_breadth": f.get("api_breadth"), "mcp": f.get("existing_mcp"), "mcp_label": label(f.get("existing_mcp")),
                     "buildability": f.get("buildability"), "buildability_label": label(f.get("buildability")),
                     "blocker": f.get("blocker", ""),
                     "claims": [{"field": c.get("field", ""), "item": c.get("item", ""), "state": c.get("state", "unknown"), "state_label": label(c.get("state"))} for c in (p or {}).get("claims", [])],
                     "evidence": ev, "claim_state_counts": (p or {}).get("claim_state_counts", {}),
                     "versions": version_history, "_versions": all_versions, "extracted_at": (p or {}).get("extracted_at", ""),
                     "sources": sources, "version_count": len(r.get("versions", [])),
                     "source_count": len((p or {}).get("sources", [])),
                     "recorded_model": (p or {}).get("model", ""),
                     "manual": r.get("manual_research"), "claim_review": r.get("claim_review")})

    extracted = [a for a in apps if a["primary_version"]]
    states = Counter(c["state"] for a in extracted for c in a["claims"])
    quotes = [e for a in extracted for e in a["evidence"]]
    quote_valid = sum(e["valid"] and e["source_confirmed"] for e in quotes)
    BAD = ("unsupported", "conflicting")   # review verdicts that remove a first-pass claim from the findings
    profiled = []
    for a in apps:
        if a["primary_version"]:
            drop = {(c["field"], str(c["claim"])) for c in (a.get("claim_review") or []) if c["verdict"] in BAD}
            one = lambda f, v: None if (f, str(v)) in drop else v
            pr = {"access": one("access", a["access"]), "mcp": one("existing_mcp", a["mcp"]), "buildability": one("buildability", a["buildability"]),
                  "auth": [x for x in a["auth"] if ("auth_methods", x) not in drop], "api_types": [x for x in a["api_types"] if ("api_types", x) not in drop],
                  "blocker": (a["blocker"] or "none"), "sup_access": bool(_evidence_support(a, "access")), "sup_build": bool(_evidence_support(a, "access")) and bool(_evidence_support(a, "auth_methods")), "tier": "first_pass"}   # buildability is a judgement: require quote-supported access and auth
        elif (a.get("manual") or {}).get("profile"):
            m = a["manual"]["profile"]
            pr = {"access": m["access"], "mcp": m["mcp"], "buildability": m["buildability"], "auth": m["auth"], "api_types": m["api_types"], "blocker": m["blocker"] or "none",
                  "sup_access": m["quoted"]["access"], "sup_build": m["quoted"]["access"] and m["quoted"]["auth"], "tier": "source_quoted"}
        else:
            continue
        a["profile"] = pr
        profiled.append({"id": a["id"], "name": a["name"], "category": a["category"], "access_label": a["access_label"] if a["primary_version"] else label(pr["access"]), **pr})
    UNK = (None, "unknown", "undeterminable")
    access_apps = [a for a in profiled if a["access"] not in UNK]
    access_counts = Counter(a["access"] for a in access_apps)
    mcp_apps = [a for a in profiled if a["mcp"] not in UNK]
    mcp_counts = Counter(a["mcp"] for a in mcp_apps)
    gate_values = {"approval_or_review_required", "partner_or_contact_sales"}
    category_access = defaultdict(list)
    for a in access_apps:
        category_access[a["category"]].append(a)
    cat_stats = []
    for cat, group in sorted(category_access.items()):
        gated = [a for a in group if a["access"] in gate_values]
        cat_stats.append({"category": cat, "observed": len(group), "gated": len(gated),
                          "rate": len(gated) / len(group) if group else None,
                          "ids": [a["id"] for a in gated]})

    easy = [a for a in profiled if a["buildability"] == "yes" and a["access"] == "self_serve_free" and a["sup_access"] and a["sup_build"]]
    outreach = [a for a in profiled if a["access"] in gate_values and a["sup_access"]]
    auth_apps = [a for a in profiled if a["auth"]]
    auth_counts = Counter(x for a in auth_apps for x in set(a["auth"]))
    build_apps = [a for a in profiled if a["buildability"] not in UNK]
    build_counts = Counter(a["buildability"] for a in build_apps)
    blockers = Counter(a["blocker"] for a in profiled if a["blocker"] and a["blocker"] != "none")
    original_n = sum(a["provenance"] == "original_segment" for a in apps)
    reconstructed_n = sum(a["provenance"] == "reconstructed_segment" for a in apps)

    findings = []
    n, total = len(extracted), len(apps)
    n1, n2 = len(extracted), len([a for a in apps if not a["primary_version"] and (a.get("manual") or {}).get("profile")])
    findings.append(_finding("Coverage", f"{n1 + n2} of {total} registry positions have research behind them: {n1} first-pass extractions and {n2} source-quoted records.",
                             "All 100 positions are in the supplied assignment list. The two groups were checked differently; see Verification.",
                             [a["id"] for a in profiled], f"{n1 + n2}/{total}"))
    if auth_apps:
        top = auth_counts.most_common(3)
        findings.append(_finding("Authentication", "Most common methods across apps with a known method: " + "; ".join(f"{label(k)} {v} of {len(auth_apps)}" for k, v in top) + ".",
                                 f"Apps often support several methods, so shares add to more than 100%. {total - len(auth_apps)} positions have no usable authentication finding.",
                                 [a["id"] for a in auth_apps], f"{top[0][1]}/{len(auth_apps)}"))
    if states:
        supported = states.get("supported_lexical", 0); claims_n = sum(states.values())
        nm = [a for a in apps if not a["primary_version"] and (a.get("manual") or {}).get("claims")]
        nc = [c for a in nm for c in a["manual"]["claims"]]; ns = sum(c["verdict"] == "supported_by_official_quote" for c in nc)
        findings.append(_finding("Evidence checks", f"First-pass positions: {supported} of {claims_n} claim items have a matching quotation and source. Source-quoted positions: {ns} of {len(nc)} claims are directly supported by an official quotation.",
                                 "Two different checks with their own denominators: a text and source check is not proof that a claim is factually correct, and neither is human verification.",
                                 [a["id"] for a in extracted if any(c["state"] == "supported_lexical" for c in a["claims"])] + [a["id"] for a in nm],
                                 f"{supported}/{claims_n} · {ns}/{len(nc)}"))
    else:
        findings.append(_finding("Evidence checks", "Not yet established", "No claim items are available to measure.", [], None, False))
    if access_counts:
        k, v = access_counts.most_common(1)[0]
        findings.append(_finding("How access is described", f"The most common access label is “{label(k)}” ({v} of {len(access_apps)} classified apps; {total - len(access_apps)} of {total} positions could not be classified).",
                                 "First-pass labels that review found unsupported or conflicting are excluded. Treat this as a research lead until a person checks the source and actual developer-access requirements.",
                                 [a["id"] for a in access_apps if a["access"] == k], f"{v}/{len(access_apps)}"))
    else:
        findings.append(_finding("How access is described", "Not yet established", "No usable access classifications are present.", [], None, False))
    comparable = [c for c in cat_stats if c["observed"] >= 2]
    if len(comparable) >= 2:
        hi = max(comparable, key=lambda c: (c["rate"], c["gated"], c["category"]))
        lo = min(comparable, key=lambda c: (c["rate"], c["gated"], c["category"]))
        if hi["rate"] == lo["rate"]:
            statement = f"The classified categories with enough observations have the same approval/partner share: {hi['gated']}/{hi['observed']} at both ends."
        else:
            statement = f"The largest reported approval/partner share is in {hi['category']}: {hi['gated']} of {hi['observed']} classified apps."
        findings.append(_finding("Category differences", statement,
                                 f"The smallest is {lo['category']}: {lo['gated']} of {lo['observed']}. These are model-coded and not human-confirmed.",
                                 [a["id"] for c in (hi, lo) for a in category_access[c["category"]]],
                                 f"{hi['gated']}/{hi['observed']} vs {lo['gated']}/{lo['observed']}"))
    else:
        findings.append(_finding("Category differences", "Not yet established", "Fewer than two categories have at least two classified apps.", [], None, False))
    if mcp_apps:
        o = mcp_counts.get("official", 0)
        findings.append(_finding("AI-assistant (MCP) connection", f"An official MCP server was found for {o} of {len(mcp_apps)} apps with an MCP finding ({mcp_counts.get('community', 0)} community, {mcp_counts.get('none_found', 0)} none found in reviewed sources).",
                                 f"{total - len(mcp_apps)} of {total} positions have no MCP finding. None found means not found in the reviewed sources, not that none exists.",
                                 [a["id"] for a in mcp_apps if a["mcp"] == "official"], f"{o}/{len(mcp_apps)}"))
    if build_apps:
        y = build_counts.get("yes", 0); c = build_counts.get("yes_with_caveats", 0)
        tb = blockers.most_common(1)
        findings.append(_finding("Buildability and blockers", f"{y} of {len(build_apps)} apps with a verdict look buildable today and {c} more with caveats.",
                                 "Verdicts are model judgements from the evidence. Blockers are mostly app-specific: approval or review, plan limits, per-tenant credentials, enterprise licences.",
                                 [a["id"] for a in build_apps if a["buildability"] == "yes"], f"{y}/{len(build_apps)}"))
    human_n = int(human_labels.get("labelled_claims", 0))
    if human_n:
        findings.append(_finding("Independent review", f"{human_n} sampled claims have a human label; the rest of the findings are model-reviewed.",
                                 "Too few labels for an accuracy rate; see Verification for hits and misses.", [], str(human_n)))
    else:
        findings.append(_finding("Independent review", "No human-labelled claims are present yet.",
                                 "No accuracy, precision or recall estimate is reported.", [], "0 labelled claims"))

    manual = [a for a in apps if a.get("manual") and not a["primary_version"]]
    mclaims = [c for a in manual for c in a["manual"].get("claims", [])]
    mv = Counter(c["verdict"] for c in mclaims)
    mquoted = [c for c in mclaims if c.get("quote")]
    reviewed = [(a["id"], c) for a in apps for c in (a.get("claim_review") or [])]
    rvc = Counter(c["verdict"] for _, c in reviewed)
    if manual:
        sup = mv.get("supported_by_official_quote", 0)
        findings.append(_finding("Newly researched positions (source-quoted)",
                                 f"{len(manual)} positions without a first-pass extraction now have quoted evidence: {sup} of {len(mclaims)} claims are directly supported by an official-source quotation; {mv.get('partially_supported', 0)} are partly supported.",
                                 "Quotations were re-fetched and read against each claim by model reviewers. This is not human verification and is kept separate from the 54 first-pass records.",
                                 [a["id"] for a in manual], f"{sup}/{len(mclaims)}"))
    if reviewed:
        findings.append(_finding("Model review of flagged first-pass claims",
                                 f"Of {len(reviewed)} flagged claims in the first-pass records, a model review judged {rvc.get('supported', 0)} supported, {rvc.get('partially_supported', 0)} partly supported, {rvc.get('unsupported', 0)} unsupported, {rvc.get('conflicting', 0)} conflicting and {rvc.get('unverifiable', 0)} unverifiable.",
                                 "Model-reviewed against stored pages, not human-verified; unsupported means the stored evidence does not establish it, not that it is false.",
                                 sorted({i for i, _ in reviewed}), f"{rvc.get('supported', 0)}/{len(reviewed)}"))
    changes = _correction_summary(apps)
    for app in apps:
        app.pop("_versions", None)
    versioned = Counter(a["primary_version"] for a in extracted)
    list_cross = defaultdict(Counter)
    for a in apps:
        list_cross[a["provenance"]][a["status"]] += 1
    model_verdicts = legacy_verification.get("verdicts", {})
    metrics = {
        "positions": total, "extracted": n, "not_extracted": total - n,
        "claims": sum(states.values()), "claim_states": dict(states),
        "evidence": len(quotes), "evidence_valid": quote_valid,
        "evidence_not_source_confirmed": sum(not e["source_confirmed"] for e in quotes),
        "positions_researched": len(profiled), "access": dict(access_counts), "access_observed": len(access_apps), "auth": dict(auth_counts), "auth_observed": len(auth_apps), "build_counts": dict(build_counts),
        "mcp": dict(mcp_counts), "mcp_observed": len(mcp_apps),
        "buildability": dict(build_counts),
        "category_access": cat_stats, "easy_wins": [a["id"] for a in easy],
        "outreach": [a["id"] for a in outreach], "category_counts": dict(Counter(a["category"] for a in apps)),
        "provenance_counts": {"original_segment": original_n, "reconstructed_segment": reconstructed_n},
        "provenance_status": {k: dict(v) for k, v in list_cross.items()},
        "run_versions": dict(versioned), "legacy_verification_app_records": int(legacy_verification.get("app_records", 0)),
        "legacy_verdict_count": sum(model_verdicts.values()), "legacy_verdicts": model_verdicts,
        "human_labelled_claims": human_n, "retrieval": retrieval,
        "source_reconciliation": source_check.get("reconciliation_status", "not_recorded"),
        "source_reconciliation_checked_at": source_check.get("checked_at", "not recorded"),
        "source_reconciliation_message": source_check.get("access_result", "not recorded"),
        "source_reconciliation_registry_changed": source_check.get("registry_changed", True),
        "dataset_created": "", "data_as_of": "",
        "findings": findings, "category_rows": cat_stats,
        "easy_wins_data": [{"id": a["id"], "name": a["name"], "category": a["category"]} for a in easy],
        "outreach_data": [{"id": a["id"], "name": a["name"], "category": a["category"], "access": a["access_label"]} for a in outreach],
        "manual_research": {"positions": len(manual), "claims": len(mclaims), "claims_with_quote": len(mquoted), "verdicts": dict(mv), "mcp": dict(Counter(a["manual"]["summary"].get("mcp_status", "unknown") for a in manual))},
        "claim_review": {"claims": len(reviewed), "verdicts": dict(rvc), "basis": "model_reviewed_not_human_verified"},
        "correction": changes,
        "correction_apps": len(changes),
    }
    return {"apps": apps, "metrics": metrics}


def _comparison_versions(row):
    return {v.get("version"): v for v in row.get("versions", [])}


def _correction_summary(apps):
    out = []
    for a in apps:
        old, new = a["_versions"].get("bench5v1"), a["_versions"].get("corrected5")
        if not old or not new:
            continue
        old_fields, new_fields = old.get("fields", {}), new.get("fields", {})
        changed = []
        for key in sorted(set(old_fields) | set(new_fields)):
            if old_fields.get(key) != new_fields.get(key):
                changed.append({"field": key, "before": old_fields.get(key), "after": new_fields.get(key)})
        old_valid = sum(bool(e.get("valid")) for e in old.get("evidence", []))
        new_valid = sum(bool(e.get("valid")) for e in new.get("evidence", []))
        out.append({"id": a["id"], "name": a["name"], "category": a["category"], "changes": changed,
                    "before_quotes": [old_valid, len(old.get("evidence", []))],
                    "after_quotes": [new_valid, len(new.get("evidence", []))],
                    "after_unsupported": new.get("claim_state_counts", {}).get("unsupported", 0),
                    "after_unknown": new.get("claim_state_counts", {}).get("unknown", 0),
                    "after_not_found": new.get("claim_state_counts", {}).get("not_found_in_provided_evidence", 0)})
    return out
