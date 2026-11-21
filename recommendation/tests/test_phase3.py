"""Phase 3: explainable, feasible, diversified recommendations."""
import unittest
from recommendation.engine import recommend

NOW = '2026-11-22T10:00:00+05:30'
BASE = dict(now=NOW, preferred_start=NOW, battery_soc=10, battery_kwh=50,
            target_soc=40, consumption_kwh_per_km=0.2,
            connector_type='CCS2', search_hours=5)
STATIONS = [
    dict(id='A', name='Station A', distance_km=4, travel_minutes=10, capacity_kw=50, tariff_per_kwh=12),
    dict(id='B', name='Station B', distance_km=9, travel_minutes=20, capacity_kw=30, tariff_per_kwh=14),
    dict(id='C', name='Station C', distance_km=21, travel_minutes=30, capacity_kw=60, tariff_per_kwh=10),
]
CONNECTORS = [
    dict(id='A1', station_id='A', type='CCS2', max_power_kw=20),
    dict(id='A2', station_id='A', type='CCS2', max_power_kw=20),
    dict(id='B1', station_id='B', type='CCS2', max_power_kw=30),
    dict(id='C1', station_id='C', type='CCS2', max_power_kw=60),
]
RESERVED_B = [dict(station_id='B', connector_id='B1', start_time=NOW,
                   end_time='2026-11-22T11:00:00+05:30',
                   reserved_power_kw=30, status='confirmed')]

class Phase3Scenarios(unittest.TestCase):
    def test_scores_explain_every_recommendation(self):
        result = recommend(BASE, STATIONS, CONNECTORS, RESERVED_B)
        for item in result['recommendations']:
            self.assertIsInstance(item['score'], float)
            self.assertIn('estimated_cost_inr', item['score_factors'])
            self.assertIn('station power capacity', item['reason'])
            self.assertTrue(item['reason'])

    def test_top_three_are_diverse_when_possible(self):
        result = recommend({**BASE, 'battery_soc': 50, 'target_soc': 80}, STATIONS, CONNECTORS, [])
        picks = result['recommendations']
        self.assertEqual(len(picks), 3)
        self.assertEqual(len({p['station_id'] for p in picks}), 3)
        self.assertEqual([p['rank'] for p in picks], [1, 2, 3])

    def test_critical_excludes_unreachable_station(self):
        result = recommend(BASE, STATIONS, CONNECTORS, RESERVED_B)
        self.assertNotIn('C', [i['station_id'] for i in result['recommendations']])

    def test_full_booking_conflict_excluded_even_when_diversifying(self):
        result = recommend(BASE, STATIONS, CONNECTORS, RESERVED_B)
        for item in result['recommendations']:
            if item['station_id'] == 'B':
                self.assertGreaterEqual(item['start_time'], '2026-11-22T05:30:00+00:00')

    def test_flexible_cost_weight_exceeds_wait_weight(self):
        r = recommend({**BASE, 'battery_soc': 80, 'target_soc': 90}, STATIONS, CONNECTORS, [])
        f = r['recommendations'][0]['score_factors']
        self.assertGreater(f['cost_weight'], f['waiting_weight'])

    def test_zero_feasible_returns_empty(self):
        r = recommend(BASE, [STATIONS[2]], [CONNECTORS[3]], [])
        self.assertEqual(r['recommendations'], [])

if __name__ == '__main__':
    unittest.main()
