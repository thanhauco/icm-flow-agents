"""CLI / module entry point for the ICM Flow Agents system.

Run with ``python -m src.main`` to process a built-in demo incident through the
full pipeline. Without Azure credentials the system uses deterministic offline
stubs so it runs anywhere.
"""

from __future__ import annotations

import asyncio
import json
import logging

from .config import get_settings
from .observability import HealthCheck
from .output import format_result, to_summary_dict
from .pipeline import IncidentPipeline

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )


_DEMO_INCIDENTS = [
    {
        "source": "email",
        "content": (
            "Production database is down. Users unable to log in. "
            "ConnectionTimeout errors across api-gateway and user-service. "
            "Reported by john.doe@example.com, call 555-123-4567."
        ),
    },
    {
        "source": "chat",
        "content": "TEST alert: flapping health check on staging, please ignore.",
    },
]


async def _run_demo() -> None:
    health = HealthCheck().check()
    logger.info("Health: %s", json.dumps(health.components))

    pipeline = IncidentPipeline()
    for payload in _DEMO_INCIDENTS:
        result, report = await pipeline.run(payload)
        print("\n" + format_result(result))
        print(f"  Evaluation: passed={report.passed} score={report.score}")
        if report.issues:
            print(f"  Issues: {report.issues}")

    print("\nSummary JSON:")
    summaries = [
        to_summary_dict((await pipeline.run(p))[0]) for p in _DEMO_INCIDENTS[:1]
    ]
    print(json.dumps(summaries, indent=2))
    print(f"\nTotal spend: ${pipeline.cost_tracker.total_usd:.4f}")


def main() -> None:
    _configure_logging()
    asyncio.run(_run_demo())


if __name__ == "__main__":
    main()
