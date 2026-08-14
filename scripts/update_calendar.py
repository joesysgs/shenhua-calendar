#!/usr/bin/env python3
"""Update Shanghai Shenhua's stable iCalendar feed from the club website."""
from __future__ import annotations

import argparse, hashlib, json, re, sys, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"
SCHEDULE = ROOT / "data/schedule.json"
OVERRIDES = ROOT / "data/overrides.json"
CALENDAR = ROOT / "shenhua.ics"

LEGACY_UIDS = {
 "中超|上海申花|大连英博":"023cc9f7-5fed-49d8-9d48-70ae1cd86e39@chatgpt-shenhua-2026",
 "中超|浙江俱乐部|上海申花":"a1e91712-9dcb-4f7b-867e-4911850dab2f@chatgpt-shenhua-2026",
 "中超|北京国安|上海申花":"f1b8aa03-e0e6-4313-89a4-b695cc157310@chatgpt-shenhua-2026",
 "中超|天津津门虎|上海申花":"d9641737-d59a-4a28-b505-c44d3af28c94@chatgpt-shenhua-2026",
 "中超|上海申花|上海海港":"dea6d717-d1f0-4c0e-b6ca-32165513d5b7@chatgpt-shenhua-2026",
 "中超|上海申花|辽宁铁人":"6c24b0db-bd81-408f-bdbb-11ba9395039d@chatgpt-shenhua-2026",
 "中超|上海申花|青岛海牛":"f173c46f-a796-43e3-9e53-fad5b2ffacca@chatgpt-shenhua-2026",
 "中超|河南俱乐部|上海申花":"bb227da2-612b-4973-b2d5-c26500900905@chatgpt-shenhua-2026",
 "中超|上海申花|成都蓉城":"0d360631-75cb-4b82-9211-846d0afb8554@chatgpt-shenhua-2026",
 "中超|山东泰山|上海申花":"2930b0e6-2431-4003-a6a3-f0673d437762@chatgpt-shenhua-2026",
 "中超|上海申花|重庆铜梁龙":"60e7dbdd-a69d-4049-8241-cb36bdfbea9b@chatgpt-shenhua-2026",
 "中超|云南玉昆|上海申花":"3c290729-e186-41b3-b133-d05fae942435@chatgpt-shenhua-2026",
 "中超|上海申花|武汉三镇":"8372567c-b644-49f2-8772-8cbb31b8397b@chatgpt-shenhua-2026",
 "中超|上海申花|深圳新鹏城":"a74f1b12-b55b-4da8-b12b-e21ef11b38d2@chatgpt-shenhua-2026",
 "中超|青岛西海岸|上海申花":"cbb81754-1c0f-41df-ba1c-1874e76034c0@chatgpt-shenhua-2026",
 "中超|大连英博|上海申花":"2e67bf32-c0a9-48bf-9ca8-d896ce95f018@chatgpt-shenhua-2026",
 "中超|上海申花|浙江俱乐部":"388f133f-a8df-43b9-a04d-89f4633cd306@chatgpt-shenhua-2026",
 "中超|上海申花|北京国安":"e59e0fbc-4f65-4736-ab92-b4d4261eb492@chatgpt-shenhua-2026",
 "中超|上海申花|天津津门虎":"d30f1f9c-6631-4e8b-970d-69ff454645d8@chatgpt-shenhua-2026",
 "中超|上海海港|上海申花":"b6e7b157-1465-4ee2-ace9-948b47362ae3@chatgpt-shenhua-2026",
 "中超|辽宁铁人|上海申花":"e559d0e0-be2b-4522-b818-6ea85b194f47@chatgpt-shenhua-2026",
 "中超|青岛海牛|上海申花":"54107f2f-8002-4864-b0f3-c1cda1566ebc@chatgpt-shenhua-2026",
 "中超|上海申花|河南俱乐部":"be593ae5-78a6-45a4-bfc0-d14c555534c8@chatgpt-shenhua-2026",
 "中超|成都蓉城|上海申花":"da8ea499-b63d-45dc-89b4-6bca001976bc@chatgpt-shenhua-2026",
 "中超|上海申花|山东泰山":"cfe14664-a613-430b-b9c8-dd77c55eab1a@chatgpt-shenhua-2026",
 "中超|重庆铜梁龙|上海申花":"46f92584-6bb0-4a8e-a1ad-0af64399e13f@chatgpt-shenhua-2026",
 "中超|上海申花|云南玉昆":"13fba1c1-ebe2-401f-920e-8f8c576e5d01@chatgpt-shenhua-2026",
 "中超|武汉三镇|上海申花":"0323bd60-78db-4e03-a3e1-36e1687c7dac@chatgpt-shenhua-2026",
 "中超|深圳新鹏城|上海申花":"371519dd-ccc5-48bb-9ab6-ac860357d2bc@chatgpt-shenhua-2026",
 "中超|上海申花|青岛西海岸":"16026c9c-e7ea-44c7-bdc5-1bd0d789f5ac@chatgpt-shenhua-2026",
 "亚冠|上海申花|町田泽维亚":"4cfbecc6-d904-4dd4-a99e-739545c75412@chatgpt-shenhua-2026",
 "亚冠|武里南联|上海申花":"b5d6d5cd-f532-4028-9df3-76e8228937ab@chatgpt-shenhua-2026",
 "足协杯|石家庄功夫|上海申花":"a2efbd75-5af8-4b91-9092-59b77abc9b6e@chatgpt-shenhua-2026",
 "足协杯|上海申花|青岛海牛":"5aab4e83-74eb-42a9-b516-24ee417a7361@chatgpt-shenhua-2026"
}

def read_json(path: Path, default: Any) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

def year_for(config: dict) -> int:
    return datetime.now(ZoneInfo(config["timezone"])).year if config["season"] == "auto" else int(config["season"])

def identity(event: dict) -> str:
    return "|".join((event["competition"], event["home"], event["away"]))

def value(raw: dict, *keys: str):
    for key in keys:
        if raw.get(key) not in (None, ""): return raw[key]

def team(raw: dict, side: str) -> str:
    keys = (f"{side}_team_name", f"{side}_name", f"{side}TeamName", side)
    if side == "home":
        keys += ("home_team",)
    if side == "away":
        keys += ("visiting_team", "visitor_team")
    result = value(raw, *keys)
    if isinstance(result, dict): result = value(result, "name", "team_name", "display_name", "short_name")
    aliases={"Zhejiang Professional FC":"浙江俱乐部","Henan":"河南俱乐部","Shanghai Shenhua":"上海申花"}
    return aliases.get(str(result or ""), str(result or ""))

def walk(item: Any):
    if isinstance(item, dict):
        yield item
        for child in item.values(): yield from walk(child)
    elif isinstance(item, list):
        for child in item: yield from walk(child)

def parse_time(raw: Any, tz: ZoneInfo) -> datetime | None:
    text=str(raw or "").strip().replace("/","-")
    if not text: return None
    try:
        if text.isdigit() and len(text)>=10: return datetime.fromtimestamp(int(text[:10]),tz)
        result=datetime.fromisoformat(text.replace("Z","+00:00"))
        return result.replace(tzinfo=tz) if result.tzinfo is None else result.astimezone(tz)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M","%Y-%m-%d %H:%M:%S","%Y-%m-%d"):
            try: return datetime.strptime(text,fmt).replace(tzinfo=tz)
            except ValueError: pass
    return None

def parse_official(raw: dict, config: dict) -> dict | None:
    home,away=team(raw,"home"),team(raw,"away")
    if config["team_name"] not in (home,away): return None
    info=raw.get("match_info") if isinstance(raw.get("match_info"),dict) else {}
    stadium=raw.get("stadium_info") if isinstance(raw.get("stadium_info"),dict) else {}
    start=parse_time(value(info,"start_time","start_at") or value(raw,"match_time","start_time","start_at","match_date","date","time"),ZoneInfo(config["timezone"]))
    if not start: return None
    type_text=str(value(info,"match_type_name","match_title") or value(raw,"match_type_name","competition_name","league_name","type_name","match_type") or "")
    round_text=str(value(info,"match_rounds") or value(raw,"round_name","round","match_round","turn","stage_name") or "")
    joined=type_text+round_text
    competition="足协杯" if "足协杯" in joined else "亚冠" if "亚冠" in joined else "中超"
    chinese_rounds={"第一轮":"第1轮","第二轮":"第2轮","第三轮":"第3轮","第四轮":"第4轮","第五轮":"第5轮","第六轮":"第6轮","第七轮":"第7轮","第八轮":"第8轮"}
    round_text=chinese_rounds.get(round_text,round_text)
    number=re.search(r"(\d+)",round_text)
    if number: round_text=f"第{number.group(1)}轮"
    venue=str(value(stadium,"stadium_name") or value(raw,"stadium_name","venue","match_address","address","stadium") or "待定")
    status=str(value(raw,"match_status_text","status_name","match_status_name","status","match_status") or "scheduled")
    if any(x in status.lower() for x in ("延期","推迟","待定","postpon")): status="postponed"
    return {"id":str(value(raw,"match_id","schedule_id","id") or identity({"competition":competition,"home":home,"away":away})),"competition":competition,"round":round_text,"start":start.isoformat(),"home":home,"away":away,"venue":venue,"status":status,"source":"上海申花官网"}

def fetch_official(config: dict) -> list[dict]:
    request=urllib.request.Request(config["official_source"],headers={
        "User-Agent":"shenhua-calendar/2.1",
        "X-Requested-With":"XMLHttpRequest",
        "bp-client-type":"21",
        "bp-client-id":"OWPC",
        "bp-client-version":"2.0.0"
    })
    with urllib.request.urlopen(request,timeout=30) as response: payload=json.load(response)
    events={}
    for raw in walk(payload):
        event=parse_official(raw,config)
        if event and datetime.fromisoformat(event["start"]).year==year_for(config): events[identity(event)]=event
    return sorted(events.values(),key=lambda e:e["start"])

def merge(baseline: list[dict], official: list[dict], overrides: list[dict]) -> list[dict]:
    events={identity(e):e for e in baseline}
    for event in official:
        old=events.get(identity(event))
        if old: event=dict(event,id=old["id"],round=event["round"] or old.get("round",""))
        events[identity(event)]=event
    official_by_key={identity(e):e for e in official}
    for event in overrides:
        current=official_by_key.get(identity(event))
        # A temporary postponement override expires automatically after the club
        # publishes a genuinely different kick-off time.
        if event.get("until_official_changes") and current and current["start"] != event["start"]:
            continue
        events[identity(event)]=event
    return sorted(events.values(),key=lambda e:e["start"])

def escape(text: str) -> str:
    return str(text).replace("\\","\\\\").replace(";","\\;").replace(",","\\,").replace("\n","\\n")

def fold(line: str) -> list[str]:
    parts=[]; current=""
    for char in line:
        if len((current+char).encode()) > (75 if not parts else 74): parts.append(current); current=char
        else: current+=char
    parts.append(current)
    return [parts[0],*[" "+x for x in parts[1:]]]

def uid(event: dict) -> str:
    return LEGACY_UIDS.get(identity(event),hashlib.sha256(identity(event).encode()).hexdigest()[:20]+"@shenhua-calendar")

def make_ics(events: list[dict], config: dict, updated_at: str) -> str:
    stamp=datetime.fromisoformat(updated_at).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tz=config["timezone"]
    lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//joesysgs//Shanghai Shenhua Calendar//CN","CALSCALE:GREGORIAN","METHOD:PUBLISH","REFRESH-INTERVAL;VALUE=DURATION:PT6H","X-PUBLISHED-TTL:PT6H",f"X-WR-CALNAME:上海申花 {year_for(config)} 全赛事赛程",f"X-WR-TIMEZONE:{tz}","BEGIN:VTIMEZONE",f"TZID:{tz}","BEGIN:STANDARD","DTSTART:19700101T000000","TZOFFSETFROM:+0800","TZOFFSETTO:+0800","TZNAME:CST","END:STANDARD","END:VTIMEZONE"]
    for event in events:
        start=datetime.fromisoformat(event["start"]); end=start+timedelta(minutes=config["duration_minutes"])
        label=event["competition"]+event.get("round",""); home=event["home"]==config["team_name"]
        summary=f"{'🏟️' if home else '✈️'} {label}：{event['home']} vs {event['away']}"
        if event.get("status")=="postponed": summary="⏸️ [延期] "+summary.split(" ",1)[-1]
        description=f"{label}\\n主队：{event['home']}\\n客队：{event['away']}\\n数据来源：{event.get('source','')}\\n开球时间为北京时间；赛程可能调整。"
        lines += ["BEGIN:VEVENT",f"UID:{uid(event)}",f"DTSTAMP:{stamp}","SEQUENCE:1",f"DTSTART;TZID={tz}:{start:%Y%m%dT%H%M%S}",f"DTEND;TZID={tz}:{end:%Y%m%dT%H%M%S}",f"SUMMARY:{escape(summary)}",f"LOCATION:{escape(event['venue'])}",f"DESCRIPTION:{escape(description)}",f"CATEGORIES:上海申花\\,{event['competition']}","BEGIN:VALARM","ACTION:DISPLAY",f"DESCRIPTION:{escape(summary)}","TRIGGER:-P1D","END:VALARM","BEGIN:VALARM","ACTION:DISPLAY",f"DESCRIPTION:{escape(summary)}","TRIGGER:-PT3H","END:VALARM","END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in fold(line))+"\r\n"

def validate(events: list[dict], config: dict):
    if not events: raise ValueError("赛程为空")
    if len({uid(e) for e in events})!=len(events): raise ValueError("UID重复")
    for event in events:
        if config["team_name"] not in (event["home"],event["away"]): raise ValueError("发现非申花赛事")
        datetime.fromisoformat(event["start"])

def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--offline",action="store_true"); parser.add_argument("--check",action="store_true"); args=parser.parse_args()
    config=read_json(CONFIG,{}); schedule=read_json(SCHEDULE,{"events":[]}); baseline=schedule["events"]; overrides=read_json(OVERRIDES,{"events":[]})["events"]
    official=[]
    if not args.offline:
        try:
            official=fetch_official(config)
            if len(official)<config["official_minimum_events"]: print(f"官网仅返回{len(official)}场，保留旧数据",file=sys.stderr); official=[]
        except Exception as exc: print(f"官网不可用，保留旧数据：{exc}",file=sys.stderr)
    events=merge(baseline,official,overrides)
    current=[e for e in events if datetime.fromisoformat(e["start"]).year==year_for(config)]
    if current: events=current
    validate(events,config)
    updated=schedule.get("updated_at") or datetime.now(timezone.utc).isoformat()
    if events!=baseline: updated=datetime.now(timezone.utc).isoformat()
    calendar=make_ics(events,config,updated)
    if args.check: print(f"验证通过：{len(events)}场"); return 0
    SCHEDULE.write_text(json.dumps({"updated_at":updated,"events":events},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    CALENDAR.write_bytes(calendar.encode()); print(f"已生成{len(events)}场，官网更新{len(official)}场"); return 0

if __name__ == "__main__": raise SystemExit(main())
