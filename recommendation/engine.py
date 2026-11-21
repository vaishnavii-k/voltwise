"""VoltWise recommendation and station-capacity evaluation (standard library only).

Pure, side-effect-free planning functions. The backend MUST recheck and insert the
chosen booking in a single database transaction; these functions DO NOT reserve.
All timestamps must be timezone-aware ISO 8601 strings.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil, isfinite
from typing import Any

SLOT_MINUTES = 30
EMERGENCY_SOC = 15.0
MIN_ARRIVAL_RESERVE_KWH = 1.0


def parse_time(value: str) -> datetime:
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None or d.utcoffset() is None:
        raise ValueError('All times must include a timezone offset (e.g. +05:30)')
    return d.astimezone(timezone.utc)


def overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def ceil_to_slot(ts: datetime, minutes: int = SLOT_MINUTES) -> datetime:
    ts = ts.astimezone(timezone.utc)
    step = minutes * 60
    timestamp = ts.timestamp()
    return datetime.fromtimestamp(ceil(timestamp / step) * step, timezone.utc)


def priority_for_soc(soc: float) -> str:
    if not (isfinite(soc) and 0 <= soc <= 100):
        raise ValueError('SOC must be between 0 and 100')
    if soc <= 15:
        return 'critical'
    if soc <= 30:
        return 'high'
    if soc <= 60:
        return 'normal'
    return 'flexible'


def estimate_charge_minutes(battery_kwh: float, arrival_soc: float,
                            target_soc: float, power_kw: float,
                            efficiency: float = 0.90) -> int:
    """Simplified constant-power charging estimate rounded to 30-min slots."""
    if not (battery_kwh > 0 and power_kw > 0 and 0 < efficiency <= 1 and
            0 <= arrival_soc <= target_soc <= 100):
        raise ValueError('Invalid battery/target/power/efficiency')
    energy_to_battery = battery_kwh * (target_soc - arrival_soc) / 100
    return max(SLOT_MINUTES, ceil((energy_to_battery / efficiency / power_kw) * 60 / SLOT_MINUTES) * SLOT_MINUTES)


def peak_reserved_kw(reservations: list[dict[str, Any]], station_id: str,
                     start: datetime, end: datetime) -> float:
    """Actual peak overlapping power in [start,end), not a naive sum of all overlaps.

    Assumes constant reserved power for each confirmed reservation interval.
    """
    points: list[tuple[datetime, int, float]] = []
    for r in reservations:
        if r['station_id'] != station_id or r['status'] != 'confirmed':
            continue
        rs, re = parse_time(r['start_time']), parse_time(r['end_time'])
        if re <= rs:
            raise ValueError('Reservation end must be after start')
        if not overlaps(start, end, rs, re):
            continue
        kw = float(r['reserved_power_kw'])
        if not isfinite(kw) or kw <= 0:
            raise ValueError('Reservation power must be positive')
        left, right = max(start, rs), min(end, re)
        points.append((left, 1, kw))
        points.append((right, 0, -kw))
    # At equal timestamp, process ends first, then starts: [start,end) semantics.
    points.sort(key=lambda x: (x[0], x[1]))
    active = peak = 0.0
    for _, _, delta in points:
        active += delta
        peak = max(peak, active)
    return peak


def slot_feasibility(station: dict[str, Any], connector: dict[str, Any],
                     reservations: list[dict[str, Any]], start: datetime,
                     end: datetime, requested_kw: float) -> tuple[bool, str]:
    if end <= start or requested_kw <= 0:
        return False, 'invalid_interval_or_power'
    if connector['station_id'] != station['id']:
        return False, 'connector_not_at_station'
    if requested_kw > float(connector['max_power_kw']) + 1e-9:
        return False, 'connector_power_limit'
    for r in reservations:
        if r['connector_id'] == connector['id'] and r['status'] == 'confirmed':
            if overlaps(start, end, parse_time(r['start_time']), parse_time(r['end_time'])):
                return False, 'connector_reserved'
    peak = peak_reserved_kw(reservations, station['id'], start, end)
    if peak + requested_kw > float(station['capacity_kw']) + 1e-9:
        return False, 'station_power_limit'
    return True, 'feasible'


def recommend(request: dict[str, Any], stations: list[dict[str, Any]],
              connectors: list[dict[str, Any]], reservations: list[dict[str, Any]],
              top_n: int = 3) -> dict[str, Any]:
    """Return feasible candidate slots. Does NOT create a reservation.

    Request: now, preferred_start, battery_soc, battery_kwh, target_soc,
    consumption_kwh_per_km, connector_type, optional safety_reserve_kwh,
    search_hours (default 24), efficiency (default 0.9).
    Station: id, name, distance_km, travel_minutes, capacity_kw, tariff_per_kwh.
    Connector: id, station_id, type, max_power_kw.
    Reservation: station_id, connector_id, start_time, end_time,
    reserved_power_kw, status.
    """
    now = parse_time(request['now'])
    preferred = max(now, parse_time(request['preferred_start']))
    soc = float(request['battery_soc'])
    priority = priority_for_soc(soc)
    battery_kwh = float(request['battery_kwh'])
    target_soc = float(request['target_soc'])
    consumption = float(request['consumption_kwh_per_km'])
    reserve_kwh = float(request.get('safety_reserve_kwh', MIN_ARRIVAL_RESERVE_KWH))
    efficiency = float(request.get('efficiency', 0.90))
    search_hours = float(request.get('search_hours', 24))
    if not (battery_kwh > 0 and consumption > 0 and reserve_kwh >= 0 and
            0 < efficiency <= 1 and soc < target_soc <= 100 and 0 < search_hours <= 168 and top_n >= 1):
        raise ValueError('Invalid charging request')
    remaining_kwh = battery_kwh * soc / 100
    candidates: list[dict[str, Any]] = []
    diagnostics = {'unreachable_stations': 0, 'no_compatible_connectors': 0,
                   'conflicting_or_overloaded_slots': 0}
    search_end = now + timedelta(hours=search_hours)
    for station in stations:
        distance = float(station['distance_km'])
        travel_minutes = float(station['travel_minutes'])
        if distance < 0 or travel_minutes < 0 or float(station['capacity_kw']) <= 0 or float(station['tariff_per_kwh']) < 0:
            raise ValueError('Invalid station data')
        arrival_energy = remaining_kwh - distance * consumption
        if arrival_energy < reserve_kwh:
            diagnostics['unreachable_stations'] += 1
            continue
        arrival_soc = arrival_energy / battery_kwh * 100
        arrival = now + timedelta(minutes=travel_minutes)
        compatible = [c for c in connectors if c['station_id'] == station['id']
                      and c['type'] == request['connector_type']]
        if not compatible:
            diagnostics['no_compatible_connectors'] += 1
        for conn in compatible:
            power = min(float(conn['max_power_kw']), float(station['capacity_kw']))
            if power <= 0:
                continue
            duration = estimate_charge_minutes(battery_kwh, arrival_soc, target_soc, power, efficiency)
            first = ceil_to_slot(max(preferred, arrival))
            grid_energy = battery_kwh * (target_soc - arrival_soc) / 100 / efficiency
            t = first
            while t + timedelta(minutes=duration) <= search_end:
                end = t + timedelta(minutes=duration)
                feasible, reason = slot_feasibility(station, conn, reservations, t, end, power)
                if not feasible:
                    diagnostics['conflicting_or_overloaded_slots'] += 1
                    t += timedelta(minutes=SLOT_MINUTES)
                    continue
                delay = max(0, (t - preferred).total_seconds() / 60)
                estimated_cost = grid_energy * float(station['tariff_per_kwh'])
                candidates.append({
                    'station_id': station['id'], 'station_name': station['name'],
                    'connector_id': conn['id'], 'start_time': t.isoformat(),
                    'end_time': end.isoformat(), 'reserved_power_kw': power,
                    'charging_minutes': duration, 'distance_km': distance,
                    'travel_minutes': travel_minutes, 'arrival_soc_percent': round(arrival_soc, 2),
                    'estimated_cost_inr': round(estimated_cost, 2),
                    'waiting_minutes': round(delay, 1),
                    'reason': 'Compatible connector, safe estimated arrival, no overlapping booking, capacity available',
                })
                t += timedelta(minutes=SLOT_MINUTES)

    # Safety/feasibility are hard filters. Priority changes sorting of viable options.
    if priority == 'critical':
        key = lambda c: (c['waiting_minutes'], c['travel_minutes'], c['estimated_cost_inr'])
    elif priority == 'high':
        key = lambda c: (0.8 * c['waiting_minutes']/60 + 0.2 * c['estimated_cost_inr']/500,
                         c['waiting_minutes'])
    elif priority == 'normal':
        key = lambda c: (0.5 * c['waiting_minutes']/60 + 0.5 * c['estimated_cost_inr']/500,
                         c['waiting_minutes'])
    else:
        key = lambda c: (0.2 * c['waiting_minutes']/60 + 0.8 * c['estimated_cost_inr']/500,
                         c['waiting_minutes'])
    candidates.sort(key=key)
    return {'priority': priority, 'recommendations': candidates[:top_n],
            'considered_feasible_slots': len(candidates), 'diagnostics': diagnostics,
            'notice': 'Planning only: FastAPI must revalidate and book atomically in Supabase PostgreSQL.'}
