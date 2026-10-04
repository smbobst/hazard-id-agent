"""Deterministic sorting of CTX hazard data into cancer and non-cancer evidence bundles.

No AI is used here. Every record keeps a short reference ID (e.g. TV-718311) so each
statement in the written summary can be traced back to the EPA record it came from.
"""
from collections import defaultdict

# --- Source tiers -----------------------------------------------------------
# Tier 1: EPA peer-reviewed human health assessments.
# Tier 2: other EPA program values and other government/authoritative bodies.
# Tier 3: everything else in ToxValDB (study-level data, industry dossiers, QSAR, etc.).
TIER1_KEYS = ("IRIS", "PPRTV")
TIER2_KEYS = (
    "EPA", "HEAST", "RSL", "OPP", "OPPT", "ATSDR", "OEHHA", "CAL", "HEALTH CANADA",
    "WHO", "IARC", "NTP", "EFSA", "JECFA", "JMPR", "RIVM", "NIOSH", "OSHA", "ACGIH",
    "EU ", "ECHA", "DOD", "DOE", "USGS", "FDA", "NIH",
)
TIER_LABEL = {
    1: "EPA peer-reviewed assessment (IRIS/PPRTV)",
    2: "Other EPA program or government/authoritative body",
    3: "Study-level or screening data (not an EPA assessment)",
}


def source_tier(source: str | None) -> int:
    s = (source or "").upper()
    if any(k in s for k in TIER1_KEYS):
        return 1
    if any(k in s for k in TIER2_KEYS):
        return 2
    return 3


def _trim(v, n=220):
    if v is None:
        return None
    v = str(v).strip()
    return v if len(v) <= n else v[: n - 1] + "…"


CANCER_TYPE_KEYS = ("SLOPE FACTOR", "UNIT RISK", "CSF", "IUR", "CANCER", "RISK SPECIFIC", "TUMOR")
TOXICITY_VALUE_KEYS = ("RFD", "RFC", "MRL", "ADI", "TDI", "REL", "REFERENCE", "CRITERION", "GUIDELINE")
POD_SUPERCATS = ("POINT OF DEPARTURE", "DOSE RESPONSE SUMMARY VALUE", "EFFECT LEVEL")


def _is_cancer_record(r: dict) -> bool:
    t = " ".join(str(r.get(k) or "") for k in ("toxvalType", "toxvalSubtype", "riskAssessmentClass")).upper()
    return any(k in t for k in CANCER_TYPE_KEYS)


def _tv_row(r: dict) -> dict:
    return {
        "ref": f"TV-{r.get('id')}",
        "tier": source_tier(r.get("source")),
        "source": r.get("source"),
        "subsource": r.get("subsource"),
        "type": r.get("toxvalType"),
        "subtype": r.get("toxvalSubtype"),
        "qualifier": r.get("qualifier"),
        "value": r.get("toxvalNumeric"),
        "units": r.get("toxvalUnits"),
        "riskClass": r.get("riskAssessmentClass"),
        "studyType": r.get("studyType"),
        "duration": " ".join(str(x) for x in (r.get("studyDurationValue"), r.get("studyDurationUnits")) if x not in (None, "", "-")) or r.get("studyDurationClass"),
        "species": r.get("speciesCommon"),
        "sex": r.get("sex"),
        "lifestage": r.get("lifestage"),
        "route": r.get("exposureRoute"),
        "method": r.get("exposureMethod"),
        "effect": _trim(r.get("toxicologicalEffect")),
        "year": r.get("year"),
        "reference": _trim(r.get("longRef") or r.get("title"), 180),
        "url": r.get("sourceUrl") or r.get("subsourceUrl"),
    }


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("inf")


def build_bundles(chem: dict, raw: dict, max_pods_per_group: int = 8) -> dict:
    """Return {'chemical', 'cancer', 'noncancer', 'coverage', 'sources'}."""
    toxval = [r for r in raw.get("toxval", []) if isinstance(r, dict)]
    human = [r for r in toxval if "ECO" not in str(r.get("humanEco") or "").upper()]

    # ---------------- Cancer bundle ----------------
    cancer_tv = [_tv_row(r) for r in human if _is_cancer_record(r)]
    cancer_tv.sort(key=lambda x: (x["tier"], str(x["route"]), _num(x["value"])))

    cancer_calls = [
        {
            "ref": f"CS-{c.get('id')}",
            "tier": source_tier(c.get("source")),
            "source": c.get("source"),
            "route": c.get("exposureRoute"),
            "classification": c.get("cancerCall"),
            "url": c.get("url"),
        }
        for c in raw.get("cancer_summary", []) if isinstance(c, dict)
    ]
    cancer_calls.sort(key=lambda x: x["tier"])

    gs = [g for g in raw.get("genetox_summary", []) if isinstance(g, dict)]
    genetox_summary = [
        {
            "ref": f"GS-{g.get('id') or g.get('genetoxSummaryId')}",
            "overall_call": g.get("genetoxCall"),
            "ames": g.get("ames"),
            "micronucleus": g.get("micronucleus"),
            "reports_positive": g.get("reportsPositive"),
            "reports_negative": g.get("reportsNegative"),
            "reports_other": g.get("reportsOther"),
        }
        for g in gs
    ]

    gd = [g for g in raw.get("genetox_details", []) if isinstance(g, dict)]
    tally = defaultdict(lambda: defaultdict(int))
    for g in gd:
        cat = g.get("assayCategory") or g.get("assayTypeStandard") or "unspecified"
        tally[cat][(g.get("assayResult") or "unspecified").lower()] += 1
    genetox_tally = {cat: dict(v) for cat, v in tally.items()}
    # Keep a representative, positive-first sample of individual assays.
    gd_sorted = sorted(gd, key=lambda g: (0 if "pos" in str(g.get("assayResult")).lower() else 1, -(g.get("year") or 0)))
    genetox_examples = [
        {
            "ref": f"GD-{g.get('id') or g.get('genetoxDetailsId')}",
            "category": g.get("assayCategory"),
            "assay": g.get("assayTypeStandard") or g.get("assayType"),
            "species": g.get("species"),
            "strain": g.get("strain"),
            "metabolic_activation": g.get("metabolicActivation"),
            "result": g.get("assayResult"),
            "source": g.get("source"),
            "year": g.get("year"),
        }
        for g in gd_sorted[:30]
    ]

    iris = []
    for i in raw.get("iris", []):
        if not isinstance(i, dict):
            continue
        iris.append({
            "ref": "IRIS",
            "tier": 1,
            "last_revision": str(i.get("lastSignificantRevision") or ""),
            "critical_effect_systems": i.get("criticalEffectsSystems"),
            "rfd_chronic": i.get("rfdChronic"),
            "rfd_subchronic": i.get("rfdSubchronic"),
            "rfc_chronic": i.get("rfcChronic"),
            "rfc_subchronic": i.get("rfcSubchronic"),
            "tumor_site": i.get("tumorSite"),
            "literature_screening": i.get("literatureScreeningReview"),
            "url": i.get("irisUrl"),
        })

    pprtv = []
    for p in raw.get("pprtv", []):
        if not isinstance(p, dict):
            continue
        pprtv.append({
            "ref": f"PPRTV-{p.get('id') or p.get('pprtvSubstanceId')}",
            "tier": 1,
            "last_revision": p.get("lastRevision"),
            "rfd": p.get("rfdValue"),
            "rfc": p.get("rfcValue"),
            "weight_of_evidence": p.get("woe"),
            "assessment_url": p.get("pprtvAssessment"),
            "iris_link": p.get("irisLink"),
        })

    cancer = {
        "iris_tumor_sites": [{"ref": "IRIS", "tumor_site": i["tumor_site"], "url": i["url"]} for i in iris if i.get("tumor_site")],
        "pprtv_weight_of_evidence": [{"ref": p["ref"], "woe": p["weight_of_evidence"]} for p in pprtv if p.get("weight_of_evidence")],
        "classifications": cancer_calls,
        "quantitative_cancer_values": cancer_tv[:40],
        "genotoxicity_summary": genetox_summary,
        "genotoxicity_assay_tally": genetox_tally,
        "genotoxicity_examples": genetox_examples,
    }

    # ---------------- Non-cancer bundle ----------------
    nc = [r for r in human if not _is_cancer_record(r)]
    tox_values, pods = [], defaultdict(list)
    for r in nc:
        row = _tv_row(r)
        sup = str(r.get("toxvalTypeSuperCategory") or "").upper()
        typ = str(r.get("toxvalType") or "").upper()
        if "TOXICITY VALUE" in sup or any(k in typ for k in TOXICITY_VALUE_KEYS):
            tox_values.append(row)
        elif any(k in sup for k in POD_SUPERCATS) or any(k in typ for k in ("NOAEL", "LOAEL", "NOEL", "LOEL", "BMD", "BMDL")):
            key = (str(r.get("riskAssessmentClass") or "unspecified").lower(), str(r.get("exposureRoute") or "unspecified").lower())
            pods[key].append(row)

    tox_values.sort(key=lambda x: (x["tier"], str(x["route"]), _num(x["value"])))
    pod_groups = []
    for (rclass, route), rows in sorted(pods.items()):
        # Prefer mg/kg-day oral or mg/m3 inhalation units; show lowest values first, higher tiers first.
        rows.sort(key=lambda x: (x["tier"], _num(x["value"])))
        pod_groups.append({
            "risk_assessment_class": rclass,
            "route": route,
            "n_records": len(rows),
            "lowest_values": rows[:max_pods_per_group],
        })
    # Keep the prompt a manageable size for data-rich chemicals: the 20 best-populated groups.
    if len(pod_groups) > 20:
        pod_groups = sorted(pod_groups, key=lambda g: -g["n_records"])[:20]
        pod_groups.sort(key=lambda g: (g["risk_assessment_class"], g["route"]))

    # Flag endpoint-specific guideline triggers
    def _has(words):
        text = " ".join(
            " ".join(str(x.get(k) or "") for k in ("riskClass", "studyType", "effect", "lifestage"))
            for g in pod_groups for x in g["lowest_values"]
        ).upper()
        return any(w in text for w in words)

    endpoint_flags = {
        "developmental": _has(("DEVELOPMENT", "FETAL", "TERATO", "PRENATAL", "EMBRYO")),
        "reproductive": _has(("REPRODUCT", "FERTILITY", "SPERM", "ESTROUS", "MULTIGENERATION")),
        "neurotoxicity": _has(("NEURO", "BEHAVIOR", "CHOLINESTERASE", "BRAIN")),
    }

    noncancer = {
        "iris": iris,
        "pprtv": pprtv,
        "toxicity_values": tox_values[:40],
        "points_of_departure_by_class_and_route": pod_groups,
        "endpoint_guideline_triggers": endpoint_flags,
    }

    coverage = {
        "toxval_records_total": len(toxval),
        "toxval_human_health_records": len(human),
        "cancer_classification_records": len(cancer_calls),
        "cancer_quantitative_records": len(cancer_tv),
        "genetox_detail_records": len(gd),
        "noncancer_toxicity_values": len(tox_values),
        "noncancer_pod_records": sum(len(v) for v in pods.values()),
        "has_iris": bool(iris),
        "has_pprtv": bool(pprtv),
        "api_errors": raw.get("_errors", {}),
    }

    # Flat list for the "Data used" table in the web page
    sources = []
    for row in cancer_tv[:40] + tox_values[:40] + [x for g in pod_groups for x in g["lowest_values"]]:
        sources.append({k: row.get(k) for k in ("ref", "tier", "source", "type", "qualifier", "value", "units", "riskClass", "route", "species", "studyType", "effect", "url")})
    for c in cancer_calls:
        sources.append({"ref": c["ref"], "tier": c["tier"], "source": c["source"], "type": "Cancer classification", "value": c["classification"], "route": c["route"], "url": c["url"]})
    for i in iris:
        sources.append({"ref": "IRIS", "tier": 1, "source": "IRIS", "type": "IRIS assessment", "value": f"RfD {i['rfd_chronic'] or '—'}; RfC {i['rfc_chronic'] or '—'}", "url": i["url"]})
    for p in pprtv:
        sources.append({"ref": p["ref"], "tier": 1, "source": "PPRTV", "type": "PPRTV assessment", "value": f"RfD {p['rfd'] or '—'}; RfC {p['rfc'] or '—'}; WOE {p['weight_of_evidence'] or '—'}", "url": p["assessment_url"]})

    return {
        "chemical": chem,
        "tier_definitions": TIER_LABEL,
        "cancer": cancer,
        "noncancer": noncancer,
        "coverage": coverage,
        "sources": sources,
    }
