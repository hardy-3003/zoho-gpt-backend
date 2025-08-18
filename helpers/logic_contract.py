from __future__ import annotations
from functools import wraps
from typing import Any, Callable, Dict

from helpers import telemetry  # added in step 1

# Optional imports: everything here is best-effort to avoid breaking existing code.
try:
    from helpers import learning_hooks
except Exception:  # pragma: no cover
    learning_hooks = None

try:
    from helpers import history_store
except Exception:  # pragma: no cover
    history_store = None

try:
    from analyzers import delta_compare, anomaly_engine
except Exception:  # pragma: no cover
    delta_compare = None
    anomaly_engine = None

try:
    from helpers import rules_engine
except Exception:  # pragma: no cover
    rules_engine = None


def _ensure_envelope(resp: Any) -> Dict[str, Any]:
    """
    Normalize legacy/plain results into the standard envelope:
    {result, provenance, confidence, alerts, meta}
    """
    if isinstance(resp, dict) and {"result", "confidence", "provenance"} <= set(
        resp.keys()
    ):
        # Already compliant-ish; make sure required keys exist
        resp.setdefault("alerts", [])
        resp.setdefault("meta", {})
        return resp

    # Treat as raw result payload
    return {
        "result": resp if isinstance(resp, dict) else {"data": resp},
        "provenance": {"source": "internal", "path": None},
        "confidence": 0.6,
        "alerts": [],
        "meta": {},
    }


def _safe_confidence(result: Dict[str, Any], alerts: Any) -> float:
    base = 0.6
    # heuristic nudge if trivial/empty
    try:
        if not result or all(v in (0, None, [], {}, "") for v in result.values()):
            base -= 0.10
    except Exception:
        pass
    try:
        if alerts and len(alerts) > 0:
            base -= 0.15
    except Exception:
        pass
    # learning hook wins if present
    if learning_hooks and hasattr(learning_hooks, "score_confidence"):
        try:
            base = learning_hooks.score_confidence(
                result=result, alerts=alerts, base=base
            )
        except Exception:
            pass
    return max(0.1, min(0.95, float(base)))


def l4_compliant(validate: bool = True, logic_id: str | None = None) -> Callable:
    """
    Decorator to enforce L4 envelope + optional validation/history/deltas/anomalies.

    Usage:
        @l4_compliant(validate=True, logic_id="L-001")
        def handle_impl(payload): ...
    """

    def _decorator(func: Callable) -> Callable:
        @wraps(func)
        def _wrapped(payload: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
            tags = {"logic": logic_id or getattr(func, "__name__", "unknown")}
            with telemetry.timing("logic.runtime_ms", tags=tags):
                try:
                    raw = func(payload, *args, **kwargs)
                except Exception as e:
                    telemetry.incr("logic.error", tags=tags)
                    # Standard error envelope
                    return {
                        "result": None,
                        "provenance": {"source": "internal", "path": None},
                        "confidence": 0.2,
                        "alerts": [{"level": "error", "message": str(e)}],
                        "meta": {"exception": e.__class__.__name__},
                    }

            env = _ensure_envelope(raw)

            # Optional validations
            if (
                validate
                and rules_engine
                and hasattr(rules_engine, "validate_accounting")
            ):
                try:
                    v_alerts = rules_engine.validate_accounting(
                        env["result"], payload=payload
                    )
                    if v_alerts:
                        env["alerts"].extend(v_alerts)
                except Exception:
                    pass

            # History, deltas, anomalies (best-effort)
            prev = None
            if history_store and hasattr(history_store, "load_latest") and logic_id:
                try:
                    tenant = (
                        (payload or {}).get("tenant")
                        or (payload or {}).get("org")
                        or "default"
                    )
                    prev = history_store.load_latest(logic_id=logic_id, tenant=tenant)
                except Exception:
                    prev = None

            if prev:
                if delta_compare and hasattr(delta_compare, "compute"):
                    try:
                        env["meta"].setdefault(
                            "deltas",
                            delta_compare.compute(prev.get("result"), env["result"]),
                        )
                    except Exception:
                        pass
                if anomaly_engine and hasattr(anomaly_engine, "score"):
                    try:
                        env["meta"].setdefault(
                            "anomalies", anomaly_engine.score(env["result"])
                        )
                    except Exception:
                        pass

            # Confidence (shared heuristic + learning hook)
            try:
                env["confidence"] = _safe_confidence(
                    env.get("result", {}), env.get("alerts", [])
                )
            except Exception:
                pass

            # Learning: record feedback/event
            if learning_hooks:
                try:
                    # append_event is optional; ignore failures
                    if hasattr(learning_hooks, "append_event") and logic_id:
                        learning_hooks.append_event(
                            logic_id=logic_id,
                            payload=payload,
                            result=env.get("result"),
                            alerts=env.get("alerts", []),
                            notes=["l4-v0-run", "schema:stable"],
                        )
                except Exception:
                    pass

            # Write history (best-effort)
            if history_store and hasattr(history_store, "append_event") and logic_id:
                try:
                    tenant = (
                        (payload or {}).get("tenant")
                        or (payload or {}).get("org")
                        or "default"
                    )
                    history_store.append_event(
                        logic_id=logic_id,
                        tenant=tenant,
                        payload=payload,
                        result=env.get("result"),
                        alerts=env.get("alerts", []),
                        meta=env.get("meta", {}),
                    )
                except Exception:
                    pass

            telemetry.incr("logic.success", tags=tags)
            return env

        return _wrapped

    return _decorator
