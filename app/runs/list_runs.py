from __future__ import annotations

from typing import Any

from psycopg import AsyncConnection

from app.runs.finished_stages import ordered_finished_stages


async def read_run_list(connection: AsyncConnection) -> dict[str, Any]:
    """Every run the application knows about, for the run list on the screen.

    All runs, newest first, with no cap: the screen has no paging affordance,
    so a limit here would make the list quietly incomplete while looking
    complete. Ordered by `COALESCE(started_at, created_at)` rather than
    `started_at` alone, because a `waiting` run has no `started_at` yet and
    would otherwise sort wrongly or drop out of a strict ordering.
    """
    result = await connection.execute(
        "SELECT runs.id, runs.status, runs.started_at, runs.finished_stages, "
        "projects.name AS project_name, "
        "(SELECT count(*) FROM decisions WHERE decisions.run_id = runs.id "
        "AND decisions.outcome IS NULL) AS waiting_decisions "
        "FROM runs JOIN projects ON projects.id = runs.project_id "
        "ORDER BY COALESCE(runs.started_at, runs.created_at) DESC"
    )
    runs = await result.fetchall()
    return {
        "runs": [
            {
                "run_id": str(run["id"]),
                "project_name": run["project_name"],
                "status": run["status"],
                # Sent unchanged rather than substituted with created_at: a
                # run that has not started must say so, not report a moment
                # it started as a fact.
                "started_at": (
                    run["started_at"].isoformat()
                    if run["started_at"] is not None
                    else None
                ),
                "waiting_decisions": run["waiting_decisions"],
                "finished_stages": ordered_finished_stages(run["finished_stages"]),
            }
            for run in runs
        ]
    }
