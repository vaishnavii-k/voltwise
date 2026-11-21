"""Run: python -m recommendation.demo (from repository root)."""
import json
from datetime import datetime, timedelta, timezone
from .engine import recommend

ist = timezone(timedelta(hours=5, minutes=30))
base = datetime.now(ist).replace(hour=10, minute=0, second=0, microsecond=0)
if datetime.now(ist) > base:
    base += timedelta(days=1)
def when(minutes):
    return (base + timedelta(minutes=minutes)).isoformat()

STATIONS = [
    {'id': 'A', 'name': 'Station A', 'distance_km': 4, 'travel_minutes': 10, 'capacity_kw': 50, 'tariff_per_kwh': 12},
    {'id': 'B', 'name': 'Station B', 'distance_km': 9, 'travel_minutes': 20, 'capacity_kw': 30, 'tariff_per_kwh': 14},
    {'id': 'C', 'name': 'Station C', 'distance_km': 20, 'travel_minutes': 35, 'capacity_kw': 60, 'tariff_per_kwh': 10},
]
CONNECTORS = [
    {'id': 'A1', 'station_id': 'A', 'type': 'CCS2', 'max_power_kw': 20},
    {'id': 'A2', 'station_id': 'A', 'type': 'CCS2', 'max_power_kw': 20},
    {'id': 'A3', 'station_id': 'A', 'type': 'CCS2', 'max_power_kw': 20},
    {'id': 'B1', 'station_id': 'B', 'type': 'CCS2', 'max_power_kw': 30},
    {'id': 'C1', 'station_id': 'C', 'type': 'CCS2', 'max_power_kw': 60},
]
RESERVATIONS = [
    {'station_id': 'A', 'connector_id': 'A1', 'start_time': when(0), 'end_time': when(60), 'reserved_power_kw': 20, 'status': 'confirmed'},
    {'station_id': 'A', 'connector_id': 'A2', 'start_time': when(0), 'end_time': when(60), 'reserved_power_kw': 20, 'status': 'confirmed'},
    {'station_id': 'B', 'connector_id': 'B1', 'start_time': when(0), 'end_time': when(60), 'reserved_power_kw': 30, 'status': 'confirmed'},
]
REQUEST = {'now': when(0), 'preferred_start': when(0), 'battery_soc': 10, 'battery_kwh': 50,
           'target_soc': 40, 'consumption_kwh_per_km': 0.2, 'connector_type': 'CCS2', 'search_hours': 8}

if __name__ == '__main__':
    print(json.dumps(recommend(REQUEST, STATIONS, CONNECTORS, RESERVATIONS), indent=2))
