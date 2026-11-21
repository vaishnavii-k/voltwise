import unittest
from datetime import datetime, timezone
from recommendation.engine import (priority_for_soc, estimate_charge_minutes,
                                   peak_reserved_kw, slot_feasibility, recommend)

T = lambda s: datetime.fromisoformat(s.replace('Z', '+00:00'))

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.station = {'id': 'S', 'name':'Hub','capacity_kw': 50, 'tariff_per_kwh': 12,
                        'distance_km': 4, 'travel_minutes': 10}
        self.connector = {'id': 'C3', 'station_id': 'S', 'type': 'CCS2', 'max_power_kw': 20}
        self.bookings = [
            {'station_id':'S','connector_id':'C1','start_time':'2026-11-16T10:00:00+05:30', 'end_time':'2026-11-16T11:00:00+05:30','reserved_power_kw':20,'status':'confirmed'},
            {'station_id':'S','connector_id':'C2','start_time':'2026-11-16T10:30:00+05:30', 'end_time':'2026-11-16T11:30:00+05:30','reserved_power_kw':20,'status':'confirmed'},
        ]
    def test_priority(self):
        self.assertEqual(priority_for_soc(10), 'critical')
        self.assertEqual(priority_for_soc(25), 'high')
        self.assertEqual(priority_for_soc(50), 'normal')
        self.assertEqual(priority_for_soc(80), 'flexible')
    def test_duration(self):
        self.assertEqual(estimate_charge_minutes(50, 20, 80, 20), 120)
    def test_peak_not_sum_of_nonoverlapping(self):
        self.assertEqual(peak_reserved_kw(self.bookings,'S',T('2026-11-16T10:00:00+05:30'),T('2026-11-16T11:30:00+05:30')), 40)
    def test_overload_even_when_connector_free(self):
        ok, reason = slot_feasibility(self.station,self.connector,self.bookings,T('2026-11-16T10:30:00+05:30'),T('2026-11-16T11:00:00+05:30'),20)
        self.assertFalse(ok)
        self.assertEqual(reason,'station_power_limit')
    def test_back_to_back_allowed(self):
        ok, _ = slot_feasibility(self.station,{'id':'C1','station_id':'S','max_power_kw':20},self.bookings,T('2026-11-16T11:30:00+05:30'),T('2026-11-16T12:00:00+05:30'),20)
        self.assertTrue(ok)
    def test_same_connector_conflict(self):
        ok, reason = slot_feasibility(self.station,{'id':'C1','station_id':'S','max_power_kw':20},self.bookings,T('2026-11-16T10:15:00+05:30'),T('2026-11-16T10:45:00+05:30'),20)
        self.assertEqual(reason,'connector_reserved')
    def test_low_soc_unreachable_station_filtered(self):
        request={'now':'2026-11-16T10:00:00+05:30','preferred_start':'2026-11-16T10:00:00+05:30','battery_soc':10,'battery_kwh':50,'target_soc':40,'consumption_kwh_per_km':0.2,'connector_type':'CCS2','search_hours':5}
        stations=[self.station,{'id':'F','name':'Far','capacity_kw':100,'tariff_per_kwh':5,'distance_km':25,'travel_minutes':30}]
        conns=[self.connector,{'id':'F1','station_id':'F','type':'CCS2','max_power_kw':50}]
        result=recommend(request,stations,conns,self.bookings)
        self.assertEqual(result['priority'],'critical')
        self.assertTrue(result['recommendations'])
        self.assertTrue(all(x['station_id']=='S' for x in result['recommendations']))
        self.assertEqual(result['diagnostics']['unreachable_stations'],1)
    def test_bad_timezone(self):
        from recommendation.engine import parse_time
        with self.assertRaises(ValueError):
            parse_time('2026-11-16T10:00:00')

if __name__=='__main__':
    unittest.main()
