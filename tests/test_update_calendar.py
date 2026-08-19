import importlib.util, json, unittest
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("updater",ROOT/"scripts/update_calendar.py")
updater=importlib.util.module_from_spec(spec); spec.loader.exec_module(updater)

class Tests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((ROOT/"config.json").read_text())
        self.event={"id":"x","competition":"中超","round":"第1轮","start":"2026-03-07T17:00:00+08:00","home":"上海申花","away":"大连英博","venue":"上海体育场","status":"scheduled","source":"test"}
    def test_parse_official(self):
        raw={"match_id":18,"match_status_text":"未开始","match_info":{"start_time":"2026-08-18 19:35","match_type_name":"中超","match_rounds":"第18轮"},"home_team":{"name":"上海申花"},"visiting_team":{"name":"北京国安"},"stadium_info":{"stadium_name":"上海体育场"}}
        event=updater.parse_official(raw,self.config)
        self.assertEqual(event["start"],"2026-08-18T19:35:00+08:00")
        self.assertEqual(event["away"],"北京国安")
        self.assertEqual(event["round"],"第18轮")
    def test_uid_stable_after_time_change(self):
        changed=dict(self.event,start="2026-03-08T19:35:00+08:00")
        self.assertEqual(updater.uid(self.event),updater.uid(changed))
    def test_postponed_label(self):
        text=updater.make_ics([dict(self.event,status="postponed")],self.config,"2026-08-11T00:00:00+00:00")
        self.assertIn("[延期]",text)
    def test_partial_update_keeps_other_events(self):
        other=dict(self.event,id="y",home="大连英博",away="上海申花")
        self.assertEqual(len(updater.merge([other],[self.event],[])),2)
    def test_temporary_override_expires_after_official_reschedule(self):
        delayed=dict(self.event,status="postponed",until_official_changes=True)
        official=dict(self.event,start="2026-08-18T19:35:00+08:00",source="上海申花官网")
        merged=updater.merge([self.event],[official],[delayed])
        self.assertEqual(merged[0]["start"],official["start"])
    def test_cfl_is_authoritative_for_league(self):
        seasons={"data":{"dataList":[{"id":"season-2026","name":"2026"}]}}
        matches={"data":{"dataList":[{"id":"m18","home_contestant_name":"上海申花","away_contestant_name":"北京国安","local_date_time":"2026-08-18 19:35:00","week":18,"match_status":"Fixture","venue_long_name":"上海体育场"}]}}
        with patch.object(updater,"fetch_json",side_effect=[seasons,matches]):
            events=updater.fetch_cfl(self.config)
        self.assertEqual(events[0]["source"],"中足联官网")
        self.assertEqual(events[0]["start"],"2026-08-18T19:35:00+08:00")
    def test_afc_matchday_dates_support_abbreviated_months(self):
        text="MD6 Thursday, 3 Dec 2026 MD1 Thursday, 17 Sep 2026"
        dates=updater.afc_dates(text,2026)
        self.assertEqual(dates[1].strftime("%Y-%m-%d"),"2026-09-17")
        self.assertEqual(dates[6].strftime("%Y-%m-%d"),"2026-12-03")
    def test_afc_variants_share_event_identity(self):
        elite=dict(self.event,competition="亚冠精英")
        two=dict(self.event,competition="亚冠二级")
        self.assertEqual(updater.identity(elite),updater.identity(two))
    def test_two_seasons_against_same_afc_opponent_have_unique_uids(self):
        old=dict(self.event,id="sh-2026-acl-1",competition="亚冠",round="",away="町田泽维亚")
        new=dict(self.event,id="afc-two-g2-g1",competition="亚冠二级",round="第3轮",away="町田泽维亚")
        self.assertNotEqual(updater.uid(old),updater.uid(new))
    def test_waiting_venue_does_not_erase_known_venue(self):
        afc=dict(self.event,competition="亚冠二级",venue="待定",source="AFC官网")
        old=dict(self.event,competition="亚冠",venue="上海体育场")
        self.assertEqual(updater.merge([old],[afc],[])[0]["venue"],"上海体育场")

if __name__=="__main__": unittest.main()
