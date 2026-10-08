import random
import statistics


def interval(values, repetitions=1000):
    if not values:
        return None
    rng = random.Random(42)
    means = sorted(statistics.mean(rng.choices(values, k=len(values))) for _ in range(repetitions))
    return [round(means[int(repetitions * .025)], 4), round(means[int(repetitions * .975)], 4)]


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (position - low), 4)


def summarize(rows, dataset, settings, mode, answer_source, traces):
    cases = {c.id: c for c in dataset.cases}
    judges = sorted({r["judge"] for r in rows})
    leaderboard, calibration = [], []
    for judge in judges:
        selected = [r for r in rows if r["judge"] == judge]
        for answer in ("A", "B"):
            values = [statistics.mean(r["points"][answer]["scores"].values()) for r in selected]
            wins = sum(r["preference"] == answer and r["order_consistent"] for r in selected)
            leaderboard.append({"judge": judge, "system": answer, "mean_score": round(statistics.mean(values), 3),
                                "score_interval": interval(values), "wins": wins,
                                "ties": sum(r["preference"] == "tie" for r in selected), "cases": len(values)})
        deltas = [statistics.mean(r["points"]["B"]["scores"].values()) - statistics.mean(r["points"]["A"]["scores"].values()) for r in selected]
        gold = [(r, cases[r["case_id"]].labels) for r in selected
                if cases[r["case_id"]].labels.status == "human_reviewed" and answer_source == "fixtures"]
        correct = total = bad = false_accept = good = false_reject = pair_correct = pair_total = 0
        for r, labels in gold:
            for answer, verdict in labels.verdicts.items():
                prediction = r["points"][answer]["verdict"]
                total += 1
                correct += prediction == verdict
                bad += verdict == "reject"
                good += verdict == "accept"
                false_accept += verdict == "reject" and prediction == "accept"
                false_reject += verdict == "accept" and prediction == "reject"
            if labels.preference is not None:
                pair_total += 1
                pair_correct += r["order_consistent"] and r["preference"] == labels.preference
        calibration.append({"judge": judge, "human_labels": total, "agreement": correct / total if total else None,
                            "false_acceptance": false_accept / bad if bad else None,
                            "false_rejection": false_reject / good if good else None,
                            "unacceptable_labels": bad, "acceptable_labels": good,
                            "pair_agreement": pair_correct / pair_total if pair_total else None,
                            "order_consistency": sum(r["order_consistent"] for r in selected) / len(selected),
                            "paired_delta_B_minus_A": round(statistics.mean(deltas), 4),
                            "paired_delta_interval": interval(deltas)})
    provisional = []
    for judge in judges:
        pairs = [(r, cases[r["case_id"]].labels) for r in rows if r["judge"] == judge
                 and cases[r["case_id"]].labels.status == "ai_authored" and answer_source == "fixtures"]
        comparisons = [(r["points"][a]["verdict"], v) for r, labels in pairs for a, v in labels.verdicts.items()]
        provisional.append({"judge": judge, "reference_labels": len(comparisons),
                            "agreement": sum(p == v for p, v in comparisons) / len(comparisons) if comparisons else None,
                            "provenance": "AI-authored provisional references, not human calibration"})
    disagreements = []
    for case_id in cases:
        group = [r for r in rows if r["case_id"] == case_id]
        if len({r["preference"] for r in group}) > 1 or any(not r["order_consistent"] for r in group):
            disagreements.append(case_id)
    reasons = []
    if mode == "demo":
        reasons.append("Demo simulators cannot approve real releases")
    for c in calibration:
        if c["human_labels"] < settings.minimum_human_labels:
            reasons.append(f'{c["judge"]}: insufficient human-reviewed labels')
        if c["agreement"] is None or c["agreement"] < settings.minimum_agreement:
            reasons.append(f'{c["judge"]}: human agreement is absent or below threshold')
        if c["false_acceptance"] is None or c["false_acceptance"] > settings.maximum_false_acceptance:
            reasons.append(f'{c["judge"]}: false acceptance is absent or above threshold')
        bounds = c["paired_delta_interval"]
        if bounds is None or bounds[0] < 0:
            reasons.append(f'{c["judge"]}: candidate B has not established non-regression against A')
        if c["order_consistency"] < 1:
            reasons.append(f'{c["judge"]}: inconsistent swapped preferences')
    latencies = [t["latency_seconds"] for t in traces if not t.get("cache_hit")]
    costs = [t["cost_usd"] for t in traces]
    return {"leaderboard": leaderboard, "calibration": calibration, "provisional_reference": provisional, "disagreements": disagreements,
            "gate": {"passed": not reasons and bool(calibration), "reasons": reasons},
            "metrics": {"calls": len(traces), "cache_hits": sum(t.get("cache_hit", False) for t in traces),
                        "latency_p50": percentile(latencies, .5), "latency_p99": percentile(latencies, .99),
                        "cost_usd": sum(costs) if all(c is not None for c in costs) else None,
                        "tokens": sum(t.get("tokens", 0) for t in traces)},
            "category_counts": {tag: sum(tag in c.tags for c in cases.values()) for tag in sorted({t for c in cases.values() for t in c.tags})}}
