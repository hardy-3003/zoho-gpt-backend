import json

from logics.common.l4_base import L4Base
from logics.common.l4_default import L4_DEFAULT


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def test_l4_base_noop_determinism():
    base = L4Base()
    ctx = {"org_id": "X", "period": "2025-01"}

    out_hist_r = base.history_read(ctx)
    out_hist_w = base.history_write(ctx, {"k": "v"})
    out_learn = base.learn(ctx, [{"a": 1}, {"b": 2}])
    out_anom = base.detect_anomalies(ctx, [{"x": 1}])
    out_opt = base.self_optimize(ctx, {"state": 1})
    out_expl = base.explain(ctx, {"result": {}})
    out_conf = base.confidence(ctx, {"result": {}})

    # Stable canonical forms
    assert canonical(out_hist_r) == canonical({"snapshot": {}, "status": "empty"})
    assert canonical(out_hist_w) == canonical({"ack": True, "written": False})
    assert canonical(out_learn) == canonical({"accepted": 0, "rejected": 2})
    assert canonical(out_anom) == canonical({"anomalies": [], "count": 0})
    assert canonical(out_opt) == canonical({"actions": [], "state": {}})
    assert canonical(out_expl) == canonical({"explanation": "no-op"})
    assert canonical(out_conf) == canonical({"score": 1.0})

    # Types
    assert isinstance(out_hist_r, dict)
    assert isinstance(out_hist_w, dict)
    assert isinstance(out_learn, dict)
    assert isinstance(out_anom, dict)
    assert isinstance(out_opt, dict)
    assert isinstance(out_expl, dict)
    assert isinstance(out_conf, dict)


def test_l4_default_singleton_behavior_matches_base():
    base = L4Base()
    ctx = {}

    assert canonical(L4_DEFAULT.history_read(ctx)) == canonical(base.history_read(ctx))
    assert canonical(L4_DEFAULT.history_write(ctx, {})) == canonical(
        base.history_write(ctx, {})
    )
    assert canonical(L4_DEFAULT.learn(ctx, [])) == canonical(base.learn(ctx, []))
    assert canonical(L4_DEFAULT.detect_anomalies(ctx, [])) == canonical(
        base.detect_anomalies(ctx, [])
    )
    assert canonical(L4_DEFAULT.self_optimize(ctx, {})) == canonical(
        base.self_optimize(ctx, {})
    )
    assert canonical(L4_DEFAULT.explain(ctx, {})) == canonical(base.explain(ctx, {}))
    assert canonical(L4_DEFAULT.confidence(ctx, {})) == canonical(
        base.confidence(ctx, {})
    )
