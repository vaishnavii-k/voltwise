"""Phase 2 tests for VoltWise emergency recommendations and existing reservations.
Run from repository root: py -m unittest discover -s recommendation/tests -v
"""
import unittest
from datetime import datetime
from recommendation.engine import recommend, slot_feasibility

NOW = '2026-11-22T10:00:00+05:30'
PREFERRED_LATER = '2026-11-22T12:00:00+05:30'


def request(soc=10, preferred=NOW):
    return {
        'now': NOW, 'preferred_start': preferred, 'battery_soc': soc,
        'battery_kwh': 50, 'target_soc': 40 if soc < 40 else 80,
        'consumption_kwh_per_km': 0.2, 'connector_type': 'CCS2',
        'search_hours': 8,
    }


STATIONS = [
    {'id': 'A', 'name': 'Station A', 'distance_km': 4, 'travel_minutes': 10,
     'capacity_kw': 50, 'tariff_per_kwh': 12},
    {'id': 'B', 'name': 'Station B', 'distance_km': 9, 'travel_minutes': 20,
     'capacity_kw': 30, 'tariff_per_kwh': 14},
    {'id': 'C', 'name': 'Station C', 'distance_km': 21, 'travel_minutes': 35,
     'capacity_kw': 60, 'tariff_per_kwh': 10},
]
CONNECTORS = [
    {'id': 'A1', 'station_id': 'A', 'type': 'CCS2', 'max_power_kw': 20},
    {'id': 'B1', 'station_id': 'B', 'type': 'CCS2', 'max_power_kw': 30},
    {'id': 'C1', 'station_id': 'C', 'type': 'CCS2', 'max_power_kw': 60},
]
RESERVED_B = [{
    'station_id': 'B', 'connector_id': 'B1',
    'start_time': NOW, 'end_time': '2026-11-22T11:00:00+05:30',
    'reserved_power_kw': 30, 'status': 'confirmed',
}]


class Phase2Scenarios(unittest.TestCase):
    def test_critical_user_gets_earliest_feasible_slot_even_if_preferred_is_later(self):
        result = recommend(request(10, PREFERRED_LATER), STATIONS, CONNECTORS, RESERVED_B)
        self.assertEqual(result['priority'], 'critical')
        self.assertTrue(result['recommendations'])
        first_start = datetime.fromisoformat(result['recommendations'][0]['start_time'])
        self.assertLess(first_start, datetime.fromisoformat(PREFERRED_LATER))

    def test_already_reserved_station_b_is_not_offered_in_conflicting_interval(self):
        result = recommend(request(10), STATIONS, CONNECTORS, RESERVED_B, top_n=30)
        for item in result['recommendations']:
            if item['station_id'] == 'B':
                self.assertGreaterEqual(
                    datetime.fromisoformat(item['start_time']),
                    datetime.fromisoformat('2026-11-22T11:00:00+05:30'))

    def test_unreachable_station_c_is_filtered_at_ten_percent(self):
        result = recommend(request(10), STATIONS, CONNECTORS, RESERVED_B, top_n=30)
        self.assertNotIn('C', [x['station_id'] for x in result['recommendations']])
        self.assertEqual(result['diagnostics']['unreachable_stations'], 1)

    def test_normal_priority_respects_preferred_start(self):
        result = recommend(request(50, PREFERRED_LATER), STATIONS, CONNECTORS, RESERVED_B)
        self.assertEqual(result['priority'], 'normal')
        self.assertTrue(result['recommendations'])
        for item in result['recommendations']:
            self.assertGreaterEqual(datetime.fromisoformat(item['start_time']),
                                    datetime.fromisoformat(PREFERRED_LATER))

    def test_station_power_limit_still_blocks_free_connector(self):
        station = STATIONS[0]
        free_connector = {'id': 'A3', 'station_id': 'A', 'max_power_kw': 20}
        bookings = [
            {'station_id': 'A', 'connector_id': f'A{i}',
             'start_time': NOW, 'end_time': '2026-11-22T11:00:00+05:30',
             'reserved_power_kw': 20, 'status': 'confirmed'}
            for i in (1, 2)
        ]
        ok, reason = slot_feasibility(
            station, free_connector, bookings,
            datetime.fromisoformat(NOW),
            datetime.fromisoformat('2026-11-22T10:30:00+05:30'), 20)
        self.assertFalse(ok)
        self.assertEqual(reason, 'station_power_limit')


if __name__ == '__main__':
    unittest.main()
