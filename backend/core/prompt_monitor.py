import os

try:
    from .prompt_loader import get_prompt_release
    from ..storage.database import get_prompt_metrics
except ImportError:
    from core.prompt_loader import get_prompt_release
    from storage.database import get_prompt_metrics


def _threshold(name, default):
    return float(os.getenv(name, str(default)))


def get_prompt_status():
    release = get_prompt_release()
    window_seconds = int(_threshold("PROMPT_ALERT_WINDOW_SECONDS", 3600))
    min_feedback = int(_threshold("PROMPT_ALERT_MIN_FEEDBACK", 20))
    min_calls = int(_threshold("PROMPT_ALERT_MIN_CALLS", 20))
    thresholds = {
        "accuracy_drop_pp": _threshold("PROMPT_ALERT_ACCURACY_DROP_PP", 5),
        "failure_rate_percent": _threshold("PROMPT_ALERT_FAILURE_RATE_PERCENT", 1),
        "p95_regression_percent": _threshold("PROMPT_ALERT_P95_REGRESSION_PERCENT", 20),
    }
    versions = {
        release["stable_version"],
        release["previous_version"],
        release["canary_version"],
    }
    metrics = {
        version: get_prompt_metrics(version, window_seconds)
        for version in versions if version
    }
    canary_active = bool(release["canary_version"] and (
        release["canary_percent"] > 0 or release["canary_users"]
    ))
    observed_version = release["canary_version"] if canary_active else release["stable_version"]
    baseline_version = release["stable_version"] if canary_active else release["previous_version"]
    current = metrics[observed_version]
    baseline = metrics.get(baseline_version)
    alerts = []

    if (
        baseline
        and current["feedback_total"] >= min_feedback
        and baseline["feedback_total"] >= min_feedback
        and current["feedback_accuracy"] < baseline["feedback_accuracy"] - thresholds["accuracy_drop_pp"]
    ):
        alerts.append({
            "type": "accuracy",
            "message": "用户反馈通过率低于上一版本阈值",
            "current": current["feedback_accuracy"],
            "baseline": baseline["feedback_accuracy"],
        })
    if current["llm_calls"] >= min_calls and current["failure_rate"] > thresholds["failure_rate_percent"]:
        alerts.append({
            "type": "failure_rate",
            "message": "LLM 调用失败率超过阈值",
            "current": current["failure_rate"],
            "baseline": thresholds["failure_rate_percent"],
        })
    if (
        baseline
        and current["llm_calls"] >= min_calls
        and baseline["llm_calls"] >= min_calls
        and baseline["p95_latency_ms"] > 0
        and current["p95_latency_ms"] > baseline["p95_latency_ms"] * (1 + thresholds["p95_regression_percent"] / 100)
    ):
        alerts.append({
            "type": "latency",
            "message": "LLM P95 延迟超过上一版本阈值",
            "current": current["p95_latency_ms"],
            "baseline": baseline["p95_latency_ms"],
        })

    return {
        "release": release,
        "metrics": metrics,
        "observed_version": observed_version,
        "baseline_version": baseline_version,
        "accuracy_source": "user_feedback",
        "alerts": alerts,
        "alert": bool(alerts),
        "can_rollback": bool(canary_active or (
            release["previous_version"]
            and release["previous_version"] != release["stable_version"]
        )),
        "auto_rollback": False,
        "window_seconds": window_seconds,
        "minimum_samples": {"feedback": min_feedback, "llm_calls": min_calls},
        "thresholds": thresholds,
    }
