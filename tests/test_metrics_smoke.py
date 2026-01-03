# tests/test_metrics_smoke.py
from __future__ import annotations


def compute_equity_curve_points(executions):
    ordered = sorted(executions, key=lambda e: e.ts_utc)
    points = []
    cumulative = 0.0
    for e in ordered:
        signed_qty = e.quantity if e.side == "BUY" else -e.quantity
        cumulative += (-signed_qty * e.price) + e.commission
        points.append((e.ts_utc, cumulative))
    return points


def test_equity_curve_non_empty(parsed_executions):
    curve = compute_equity_curve_points(parsed_executions)
    assert len(curve) > 0
