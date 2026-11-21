"""Phase 4 tests: python -m unittest discover -s recommendation/tests -v"""
import unittest
from copy import deepcopy
from datetime import datetime

from recommendation.engine import slot_feasibility
from recommendation.load_balancing import schedule_batch

NOW = '2026-11-23T10:00:00+05:30'
STATIONS = [
    {'id': 'S', 'name': 'Main Hub', 'distance_km': 2, 'travel_minutes': 5,
     'capacity_kw': 30, 'tariff_per_kwh': 12},
]
CONNECTORS = [
    {'id': 'A', 'station_id': 'S', 'type': 'CCS2', 'max_power_kw': 20},
    {'id': 'B', 'station_id': 'S', 'type': 'CCS2', 'max_power_kw': 20},
]


def request(identifier, soc=30, submitted_at=NOW, search_hours=4, connector_type='CCS2'):
    return {'request_id': identifier, 'now': NOW, 'submitted_at': submitted_at,
            'preferred_start': NOW, 'battery_soc': soc, 'battery_kwh': 20,
            'target_soc': 60 if soc < 60 else 90, 'consumption_kwh_per_km': 0.2,
            'connector_type': connector_type, 'search_hours': search_hours}


class Phase4Scenarios(unittest.TestCase):
    def test_priority_order_critical_before_normal(self):
        result = schedule_batch([request('normal', 50), request('critical', 10)], STATIONS, CONNECTORS, [])
        self.assertEqual(result['results'][0]['request_id'], 'critical')
        self.assertEqual(result['results'][0]['priority'], 'critical')

    def test_equal_priority_fifo(self):
        early = request('early', 25, '2026-11-23T09:55:00+05:30')
        later = request('later', 25, '2026-11-23T09:56:00+05:30')
        result = schedule_batch([later, early], STATIONS, CONNECTORS, [])
        self.assertEqual([r['request_id'] for r in result['results']], ['early', 'later'])

    def test_no_overlapping_connector_or_capacity_violation(self):
        result = schedule_batch([request(f'R{i}', 10) for i in range(4)], STATIONS, CONNECTORS, [])
        accepted = [r['slot'] for r in result['results'] if r['status'] == 'proposed']
        booked = []
        for item in accepted:
            station = STATIONS[0]
            connector = next(c for c in CONNECTORS if c['id'] == item['connector_id'])
            yes, reason = slot_feasibility(
                station, connector, booked,
                datetime.fromisoformat(item['start_time']),
                datetime.fromisoformat(item['end_time']),
                item['reserved_power_kw'],
            )
            self.assertTrue(yes, reason)
            booked.append({'station_id':'S','connector_id':item['connector_id'],
                           'start_time':item['start_time'],'end_time':item['end_time'],
                           'reserved_power_kw':item['reserved_power_kw'],'status':'confirmed'})

    def test_confirmed_booking_is_never_displaced(self):
        existing = [{'station_id':'S','connector_id':'A','start_time':NOW,
                     'end_time':'2026-11-23T13:00:00+05:30',
                     'reserved_power_kw':20,'status':'confirmed'}]
        before = deepcopy(existing)
        result = schedule_batch([request('critical', 10)], STATIONS, CONNECTORS, existing)
        self.assertEqual(existing, before)
        self.assertEqual(result['results'][0]['status'], 'proposed')
        self.assertGreaterEqual(datetime.fromisoformat(result['results'][0]['slot']['start_time']),
                                datetime.fromisoformat('2026-11-23T13:00:00+05:30'))

    def test_incompatible_connector_results_unassigned(self):
        result = schedule_batch([request('X', 10, connector_type='CHAdeMO')], STATIONS, CONNECTORS, [])
        self.assertEqual(result['unassigned_count'], 1)
        self.assertEqual(result['results'][0]['status'], 'unassigned')

    def test_empty_batch(self):
        result = schedule_batch([], STATIONS, CONNECTORS, [])
        self.assertEqual(result['results'], [])
        self.assertEqual(result['proposed_count'], 0)

    def test_duplicate_request_id_rejected(self):
        with self.assertRaises(ValueError):
            schedule_batch([request('same'), request('same')], STATIONS, CONNECTORS, [])


if __name__ == '__main__':
    unittest.main()
