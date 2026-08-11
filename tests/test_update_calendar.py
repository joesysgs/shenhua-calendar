import importlib.util, json, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("updater",ROOT/"scripts/update_calendar.py")
updater=importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)

class Tests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/"config.json").read_text())
        self.event={"id":"x","competition":"中超","round":"第1轮","start":"2026-03-07T17:00:00+08:00","home":"上海申花","away":"大连英博","venue":"上海体育场","status":"scheduled","source":"test"}
    def test_parse_official(self):
        raw={"match_id":18,"match_time":"2026-08-18 19:35","home_team_name":"上海申花","away_team_name":"北京国安","match_type_name":"中超","round_name":"第18轮","stadium_name":"上海体育场"}
        event=updater.parse_official(raw,self.config)
        self.assertEqual(event["start"],"2026-08-18T19:35:00+08:00")
    def test_uid_stable_after_time_change(self):
        changed=dict(self.event,start="2026-03-08T19:35:00+08:00")
        self.assertEqual(updater.uid(self.event),updater.uid(changed))
    def test_postponed_label(self):
        text=updater.make_ics([dict(self.event,status="postponed")],self.config,"2026-08-11T00:00:00+00:00")
        self.assertIn("[延期]",text)
    def test_partial_update_keeps_other_events(self):
        other=dict(self.event,id="y",home="大连英博",away="上海申花")
        self.assertEqual(len(updater.merge([other],[self.event],[])),2)

if __name__=="__main__": unittest.main()
