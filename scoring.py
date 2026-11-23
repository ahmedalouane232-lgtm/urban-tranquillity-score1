"""Pure scoring, scenario and cost functions, independently testable from the UI."""
from copy import deepcopy
import math

from catalogue import CRITERIA, ISSUES, ACTION_BY_ID, STATUSES, SEVERITIES


def new_assessment():
    return {key: {"status": "Not assessed", "rating": 0, "evidence": "", "observation": "",
                  "na_reason": "", "severity": "Routine review"} for key in ISSUES}


def default_weights():
    return {c["id"]: c["weight"] for c in CRITERIA}


def evaluate(assessment, weights):
    """Keep missing items in the denominator; report bounds rather than invent scores."""
    rows = []
    for criterion in CRITERIA:
        items = [assessment[s["id"]] for s in criterion["issues"]
                 if assessment[s["id"]]["status"] != "Not applicable"]
        weight = weights[criterion["id"]]
        known = [s for s in items if s["status"] == "Assessed"]
        rows.append({"id": criterion["id"], "name": criterion["name"], "weight": weight,
                     "applicable": len(items), "assessed": len(known),
                     "rating": sum(s["rating"] for s in known) / len(known) if known else None,
                     "coverage": len(known) / len(items) if items else 0,
                     "lower_fraction": sum(s["rating"] for s in known) / (4 * len(items)) if items else 0})
    total = sum(r["weight"] for r in rows if r["applicable"])
    lower = coverage = 0.0
    for row in rows:
        row["normalised_weight"] = row["weight"] / total * 100 if total and row["applicable"] else 0
        lower += row["lower_fraction"] * row["normalised_weight"]
        coverage += row["coverage"] * row["normalised_weight"]
    applicable = sum(r["applicable"] for r in rows)
    assessed = sum(r["assessed"] for r in rows)
    complete = total > 0 and math.isclose(coverage, 100, abs_tol=1e-8)
    return {"rows": rows, "total_weight": total, "lower": lower,
            "upper": min(100.0, lower + 100 - coverage) if total else None,
            "coverage": coverage, "complete": complete,
            "score": lower if complete else None,
            "assessed_score": lower / coverage * 100 if coverage else None,
            "applicable": applicable, "assessed": assessed}


def default_action(action):
    return {"selected": False, "quantity": 1.0, "low": float(action["low"]),
            "high": float(action["high"]), "annual": float(action["annual"]),
            "target": 3, "owner": "", "timing": "To agree"}


def project_scenario(assessment, plan, adjustments=None):
    """Forecasts stay separate; multiple actions on one item never add their gains."""
    projected = deepcopy(assessment)
    for key, config in plan.items():
        if not config["selected"] or config["quantity"] <= 0:
            continue
        target = projected[ACTION_BY_ID[key]["issue"]]
        if target["status"] == "Assessed":
            target["rating"] = max(target["rating"], config["target"])
    # Explicit cross-theme assumptions can override a gain or model an adverse effect.
    if any(c["selected"] and c["quantity"] > 0 for c in plan.values()):
        for key, rating in (adjustments or {}).items():
            if projected[key]["status"] == "Assessed":
                projected[key]["rating"] = rating
    return projected


def cost_totals(plan, years):
    low = high = annual = 0.0
    for config in plan.values():
        if config["selected"]:
            low += config["quantity"] * config["low"]
            high += config["quantity"] * config["high"]
            annual += config["quantity"] * config["annual"]
    return {"low": low, "high": high, "annual": annual,
            "lifecycle_low": low + years * annual, "lifecycle_high": high + years * annual}


def _number(value, low, high):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and low <= value <= high


def validate_snapshot(data):
    """Accept only our bounded data schema; no code, external resources or implicit migration."""
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported file format. Upload a version 1 assessment JSON.")
    project, assessment, weights, plan = (data.get(k) for k in ("project", "assessment", "weights", "plan"))
    if not all(isinstance(v, dict) for v in (project, assessment, weights, plan)):
        raise ValueError("Project, assessment, weights and plan must be objects.")
    if set(assessment) != set(ISSUES) or set(weights) != {c["id"] for c in CRITERIA}:
        raise ValueError("The assessment criteria do not match this version of the app.")
    if set(plan) - set(ACTION_BY_ID):
        raise ValueError("The file contains unknown actions.")
    adjustments = data.get("adjustments", {})
    if not isinstance(adjustments, dict) or set(adjustments) - set(ISSUES):
        raise ValueError("Unknown scenario adjustments.")
    if any(type(v) is not int or not 0 <= v <= 4 for v in adjustments.values()):
        raise ValueError("Scenario adjustments must be ratings from 0 to 4.")
    for key, item in assessment.items():
        if not isinstance(item, dict) or item.get("status") not in STATUSES or item.get("severity") not in SEVERITIES:
            raise ValueError(f"Invalid assessment status for {key}.")
        if type(item.get("rating")) is not int or not 0 <= item["rating"] <= 4:
            raise ValueError(f"Invalid rating for {key}.")
        if any(not isinstance(item.get(k), str) or len(item[k]) > 10000 for k in ("evidence", "observation")):
            raise ValueError("Observation and evidence must be text of at most 10,000 characters.")
        if not isinstance(item.get("na_reason", ""), str) or len(item.get("na_reason", "")) > 10000:
            raise ValueError("Exclusion reasons must be text of at most 10,000 characters.")
    if any(not _number(v, 0, 100) for v in weights.values()):
        raise ValueError("Weights must be finite numbers between 0 and 100.")
    if project.get("stage") not in ("Planning", "Construction", "Completed / in operation"):
        raise ValueError("Unknown project stage.")
    if not isinstance(project.get("name"), str) or len(project["name"]) > 200:
        raise ValueError("Project name must be text of at most 200 characters.")
    for key, low, high in [("area", 0, 1e9), ("budget", 0, 1e12), ("years", 1, 30)]:
        if not _number(project.get(key), low, high):
            raise ValueError(f"Invalid project {key}.")
    if type(project["years"]) is not int:
        raise ValueError("The operating horizon must be a whole number of years.")
    for key, config in plan.items():
        if not isinstance(config, dict) or type(config.get("selected")) is not bool:
            raise ValueError(f"Invalid selection for {key}.")
        for field in ("quantity", "low", "high", "annual"):
            if not _number(config.get(field), 0, 1e9):
                raise ValueError(f"Invalid {field} for {key}.")
        if config["low"] > config["high"]:
            raise ValueError("A low unit cost exceeds its high unit cost.")
        if type(config.get("target")) is not int or not 0 <= config["target"] <= 4:
            raise ValueError("Expected ratings must be integers from 0 to 4.")
        if any(not isinstance(config.get(k), str) or len(config[k]) > 1000 for k in ("owner", "timing")):
            raise ValueError("Action owners and timing must be text of at most 1,000 characters.")
    return data
