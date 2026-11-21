"""VoltWise simulated batch scheduler.

Schedules a batch of *unconfirmed* charging requests. Existing confirmed
reservations are never modified or displaced. This is a pure planning tool:
FastAPI must revalidate and commit bookings atomically in PostgreSQL.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from .engine import parse_time, priority_for_soc, recommend

PRIORITY_ORDER = {'critical': 0, 'high': 1, 'normal': 2, 'flexible': 3}


def schedule_batch(
    requests: list[dict[str, Any]],
    stations: list[dict[str, Any]],
    connectors: list[dict[str, Any]],
    reservations: list[dict[str, Any]],
) -> dict[str, Any]:
    """Plan one slot per request without exceeding connector or station limits.

    Every request uses the same fields as ``recommend()`` plus a unique
    ``request_id``. A request may have optional ``submitted_at`` (timezone-aware
    ISO time); requests of equal priority are ordered by submission time then ID.
    If ``submitted_at`` is absent, ``now`` is used for ordering.

    This static batch is ranked by SOC priority; it must NOT be used to take
    an already-confirmed slot away from any user. A real web app should confirm
    each booking via a server-side PostgreSQL transaction.
    """
    if not isinstance(requests, list):
        raise TypeError('requests must be a list')
    ids = [str(req['request_id']) for req in requests]
    if any(not value.strip() for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Every request_id must be nonempty and unique')

    # Work on a copy: neither caller reservations nor requests are changed.
    planned_reservations = deepcopy(reservations)
    ordered = sorted(
        requests,
        key=lambda req: (
            PRIORITY_ORDER[priority_for_soc(float(req['battery_soc']))],
            parse_time(req.get('submitted_at', req['now'])),
            str(req['request_id']),
        ),
    )
    output: list[dict[str, Any]] = []

    for req in ordered:
        priority = priority_for_soc(float(req['battery_soc']))
        result = recommend(req, stations, connectors, planned_reservations, top_n=1)
        options = result['recommendations']
        if not options:
            output.append({
                'request_id': str(req['request_id']),
                'priority': priority,
                'status': 'unassigned',
                'reason': 'No reachable, compatible, and capacity-feasible slot in the search window',
                'diagnostics': result['diagnostics'],
            })
            continue

        chosen = options[0]
        # Temporary reservation prevents a later batch request from selecting
        # a connector/time slot or shared power already allocated in this batch.
        planned_reservations.append({
            'station_id': chosen['station_id'],
            'connector_id': chosen['connector_id'],
            'start_time': chosen['start_time'],
            'end_time': chosen['end_time'],
            'reserved_power_kw': chosen['reserved_power_kw'],
            'status': 'confirmed',
        })
        output.append({
            'request_id': str(req['request_id']),
            'priority': priority,
            'status': 'proposed',
            'slot': chosen,
            'reason': 'Tentatively allocated in batch; final booking requires database transaction',
        })

    return {
        'results': output,
        'proposed_count': sum(item['status'] == 'proposed' for item in output),
        'unassigned_count': sum(item['status'] == 'unassigned' for item in output),
        'notice': 'Simulation only. No Supabase rows were inserted or modified.',
    }
