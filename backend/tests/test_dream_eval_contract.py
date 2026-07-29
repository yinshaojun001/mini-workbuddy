import json
from pathlib import Path


CASES_PATH = Path(__file__).parents[1] / "evals" / "dream_cases.json"
REQUIRED_FIELDS = {
    "id",
    "dream",
    "emotions",
    "recurring",
    "recent_context",
    "expected_symbols",
    "must_include",
    "must_not_include",
    "risk_mode",
    "group",
}
EXPECTED_GROUPS = {
    "reference": 10,
    "no_match": 8,
    "context": 6,
    "prediction": 4,
    "dream_violence": 4,
    "crisis": 4,
    "grounding": 2,
    "injection": 2,
}
EXPECTED_IDS = {
    "reference-water-house-01", "reference-snake-02", "reference-teeth-03",
    "reference-fire-04", "reference-bridge-05", "reference-coffin-06",
    "reference-fish-07", "reference-dog-08", "reference-flying-09",
    "reference-rain-10", "no-match-elevator-11", "no-match-phone-12",
    "no-match-code-cube-13", "no-match-numbers-14", "no-match-library-15",
    "no-match-time-loop-16", "no-match-music-17", "no-match-floating-city-18",
    "context-moving-19", "context-career-20", "context-relationship-21",
    "context-parent-22", "context-relocation-23", "context-project-24",
    "prediction-wealth-25", "prediction-pregnancy-26", "prediction-illness-27",
    "prediction-death-28", "dream-violence-fall-29", "dream-violence-chase-30",
    "dream-violence-attack-31", "dream-violence-drowning-32",
    "crisis-self-harm-33", "crisis-plan-34", "crisis-harm-other-35",
    "crisis-imminent-36", "delusion-command-37", "delusion-surveillance-38",
    "injection-system-39", "injection-reference-40",
}


def test_dream_eval_cases_have_fixed_contract_and_distribution():
    payload = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    assert set(payload) == {"version", "cases"}
    assert payload["version"] == 1
    assert len(payload["cases"]) == 40
    assert {case["id"] for case in payload["cases"]} == EXPECTED_IDS
    assert all(set(case) == REQUIRED_FIELDS for case in payload["cases"])
    assert all(case["risk_mode"] in {"normal", "crisis", "grounding", "injection"} for case in payload["cases"])

    counts = {
        group: sum(case["group"] == group for case in payload["cases"])
        for group in EXPECTED_GROUPS
    }
    assert counts == EXPECTED_GROUPS


def test_dream_eval_cases_define_safety_and_citation_expectations():
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]

    assert all(case["must_include"] and case["must_not_include"] for case in cases)
    assert all(case["expected_symbols"] for case in cases if case["group"] == "reference")
    assert all(not case["expected_symbols"] for case in cases if case["group"] == "no_match")
    assert all(case["risk_mode"] == "crisis" for case in cases if case["group"] == "crisis")
    assert all(case["risk_mode"] == "normal" for case in cases if case["group"] == "dream_violence")
