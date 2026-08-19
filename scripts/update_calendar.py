#!/usr/bin/env python3
"""Update Shanghai Shenhua's stable iCalendar feed from official sources."""
from __future__ import annotations

import argparse, gzip, hashlib, html, json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urljoin, urlsplit, urlunsplit
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

def fetch_bytes(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    parts=urlsplit(url)
    safe_url=urlunsplit((parts.scheme,parts.netloc,quote(parts.path,safe="/%:"),quote(parts.query,safe="=&"),parts.fragment))
    request=urllib.request.Request(safe_url,headers={"User-Agent":"shenhua-calendar/3.0","Accept-Encoding":"gzip",**(headers or {})})
    with urllib.request.urlopen(request,timeout=timeout) as response:
        data=response.read()
        return gzip.decompress(data) if response.headers.get("Content-Encoding")=="gzip" else data

def fetch_json(url: str, headers: dict | None = None) -> Any:
    return json.loads(fetch_bytes(url,headers).decode("utf-8"))

def base_identity(event: dict) -> str:
    competition="亚冠" if event["competition"].startswith("亚冠") else event["competition"]
    return "|".join((competition, event["home"], event["away"]))

def identity(event: dict) -> str:
    return "|".join((base_identity(event),str(event.get("round") or "")))

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
    payload=fetch_json(config["official_source"],{
        "X-Requested-With":"XMLHttpRequest",
        "bp-client-type":"21",
        "bp-client-id":"OWPC",
        "bp-client-version":"2.0.0"
    })
    events={}
    for raw in walk(payload):
        event=parse_official(raw,config)
        if event and datetime.fromisoformat(event["start"]).year==year_for(config): events[identity(event)]=event
    return sorted(events.values(),key=lambda e:e["start"])

def clean_team_name(name: str) -> str:
    aliases={
        "Shanghai Shenhua FC":"上海申花","Shanghai Shenhua":"上海申花",
        "FC Machida Zelvia":"町田泽维亚","Tampines Rovers FC":"淡滨尼流浪者",
        "Preah Khan Reach Svay Rieng FC":"柏威夏瑞恩格",
        "大连英博海发":"大连英博","辽宁铁人楠波湾":"辽宁铁人",
        "河南俱乐部彩陶坊":"河南俱乐部","浙江俱乐部绿城":"浙江俱乐部",
    }
    name=re.sub(r"\s*\([A-Z]{3}\)\s*$","",name).strip()
    name=re.sub(r"足球俱乐部$","",name)
    return aliases.get(name,name)

def fetch_cfl(config: dict) -> list[dict]:
    base=config["cfl_api"].rstrip("/")
    seasons=fetch_json(f"{base}/tournaments?competition_code=CSL")["data"]["dataList"]
    season=next((item for item in seasons if str(item.get("name"))==str(year_for(config))),None)
    if not season: return []
    query=urlencode({"tournament_calendar_id":season["id"],"competition_code":"CSL","contestant_id":"","week":"","stage_id":"","curPage":1,"pageSize":999})
    rows=fetch_json(f"{base}/matches/page?{query}")["data"]["dataList"]
    result=[]; tz=ZoneInfo(config["timezone"])
    for row in rows:
        home=clean_team_name(str(row.get("home_contestant_name") or "")); away=clean_team_name(str(row.get("away_contestant_name") or ""))
        if config["team_name"] not in (home,away): continue
        start=parse_time(row.get("local_date_time"),tz)
        if not start: continue
        status=str(row.get("match_status") or "scheduled")
        result.append({"id":str(row.get("id") or identity({"competition":"中超","home":home,"away":away})),"competition":"中超","round":f"第{row.get('week')}轮" if row.get("week") else "","start":start.isoformat(),"home":home,"away":away,"venue":str(row.get("venue_long_name") or row.get("venue_short_name") or "待定"),"status":status,"source":"中足联官网"})
    return sorted(result,key=lambda e:e["start"])

COUNTRY_TZ={"CHN":"Asia/Shanghai","JPN":"Asia/Tokyo","KOR":"Asia/Seoul","THA":"Asia/Bangkok","CAM":"Asia/Phnom_Penh","SGP":"Asia/Singapore","MAS":"Asia/Kuala_Lumpur","HKG":"Asia/Hong_Kong","VIE":"Asia/Ho_Chi_Minh","AUS":"Australia/Sydney"}
MONTH_NAMES=("","January","February","March","April","May","June","July","August","September","October","November","December")
MONTHS={name:i for i,name in enumerate(MONTH_NAMES)}
MONTHS.update({name[:3]:i for i,name in enumerate(MONTH_NAMES) if name})

def afc_dates(text: str, year: int) -> dict[int, datetime]:
    dates={}
    month_pattern="|".join(sorted(MONTHS,key=len,reverse=True))
    for md,day,month,found_year in re.findall(rf"MD(\d).*?(\d{{1,2}})\s+({month_pattern})\s+(\d{{4}})",text,re.S):
        dates[int(md)]=datetime(int(found_year),MONTHS[month],int(day))
    return dates

def parse_afc_pdf(data: bytes, competition: str, config: dict, source_url: str) -> list[dict]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("AFC PDF reader is not installed; run pip install -r requirements.txt") from exc
    target="Shanghai Shenhua FC"; result=[]; output_tz=ZoneInfo(config["timezone"])
    for page in PdfReader(BytesIO(data)).pages:
        raw=page.extract_text() or ""
        if target not in raw or "Day / Date" not in raw: continue
        flat=re.sub(r"\s+"," ",raw)
        match_part=flat.split("as of",1)[0]
        matches=re.findall(r"([A-H][1-4])\s+(.+?)\s+vs\s+(.+?)\s+([A-H][1-4])\s+(\d{1,2}:\d{2})",match_part)
        dates=afc_dates(flat,year_for(config))
        for index,(home_code,home,away,away_code,kickoff) in enumerate(matches):
            if target not in home and target not in away: continue
            md=index//2+1; date=dates.get(md)
            if not date: continue
            country=re.search(r"\(([A-Z]{3})\)\s*$",home)
            local_tz=ZoneInfo(COUNTRY_TZ.get(country.group(1) if country else "CHN",config["timezone"]))
            hour,minute=map(int,kickoff.split(":")); start=date.replace(hour=hour,minute=minute,tzinfo=local_tz).astimezone(output_tz)
            home_name=clean_team_name(home); away_name=clean_team_name(away)
            venue="上海体育场" if home_name==config["team_name"] else "待定"
            result.append({"id":f"afc-{competition}-{home_code}-{away_code}-{date:%Y%m%d}","competition":competition,"round":f"第{md}轮","start":start.isoformat(),"home":home_name,"away":away_name,"venue":venue,"status":"scheduled","source":"AFC官网","source_url":source_url})
    return result

def fetch_afc(config: dict) -> list[dict]:
    result=[]
    for source in config.get("afc_schedule_pages",[]):
        landing=fetch_bytes(source["url"]).decode("utf-8","replace")
        links=re.findall(r"https://www\.the-afc\.com/en/more/content/[^\"< ]*match-schedule",landing)
        pages=[source["url"],*links[:4]]
        pdf_urls=[]
        for page_url in pages:
            page=fetch_bytes(page_url).decode("utf-8","replace") if page_url!=source["url"] else landing
            for link in re.findall(r"https://assets\.the-afc\.com[^\"<]+?\.pdf",page):
                link=html.unescape(link).replace("\\u2013","–")
                if link not in pdf_urls: pdf_urls.append(link)
        for pdf_url in pdf_urls:
            result.extend(parse_afc_pdf(fetch_bytes(pdf_url),source["competition"],config,pdf_url))
    return sorted({identity(e):e for e in result}.values(),key=lambda e:e["start"])

def html_text(raw: str) -> str:
    raw=re.sub(r"<(script|style)[^>]*>.*?</\1>"," ",raw,flags=re.I|re.S)
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",raw))).strip()

def fetch_cfa_announcements(config: dict) -> list[dict]:
    """Read structured Shenhua fixture statements from recent CFA announcements.

    The CFA currently exposes articles rather than a public fixture JSON API. Only
    explicit date + kick-off + opponent statements are accepted; ambiguous draw
    previews are ignored and the club feed remains the exact-time fallback.
    """
    base=config["cfa_base"].rstrip("/"); article_urls=[]
    for channel in config.get("cfa_channels",[]):
        for page_no in (1,2):
            suffix="index.html" if page_no==1 else f"index_{page_no}.html"
            page_url=f"{base}/{channel}/{suffix}"
            try: listing=fetch_bytes(page_url,timeout=10).decode("utf-8","replace")
            except Exception: continue
            for href,title in re.findall(r"<a[^>]+href=[\"']([^\"']+\.html)[\"'][^>]*>(.*?)</a>",listing,re.I|re.S):
                title_text=html_text(title)
                if any(keyword in title_text for keyword in ("足协杯","足球","赛程","抽签","赛事")):
                    article_urls.append(urljoin(base,href))
    events=[]; year=year_for(config); tz=ZoneInfo(config["timezone"])
    team_pattern=r"[\u4e00-\u9fffA-Za-z·]+(?:俱乐部(?:彩陶坊)?|队|FC)?"
    articles={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending={pool.submit(fetch_bytes,url,None,10):url for url in dict.fromkeys(article_urls)}
        for future in as_completed(pending):
            try: articles[pending[future]]=future.result().decode("utf-8","replace")
            except Exception: pass
    for article_url,raw_article in articles.items():
        text=html_text(raw_article)
        if "足协杯" not in text or config["team_name"] not in text: continue
        for match in re.finditer(rf"({team_pattern})\s*(?:VS|vs|对阵|迎战)\s*({team_pattern})",text):
            home=clean_team_name(match.group(1)); away=clean_team_name(match.group(2))
            if config["team_name"] not in (home,away): continue
            window=text[max(0,match.start()-180):match.end()+180]
            date_match=re.search(r"(?:(\d{4})年)?(\d{1,2})月(\d{1,2})日",window)
            time_match=re.search(r"(?:开球时间|比赛时间|北京时间)?[^0-9]{0,8}(\d{1,2})[:：](\d{2})",window)
            if not date_match or not time_match: continue
            start=datetime(int(date_match.group(1) or year),int(date_match.group(2)),int(date_match.group(3)),int(time_match.group(1)),int(time_match.group(2)),tzinfo=tz)
            round_match=re.search(r"(第[一二三四五六七八九十\d]+轮|1/8决赛|1/4决赛|半决赛|决赛)",window)
            events.append({"id":hashlib.sha256((article_url+identity({"competition":"足协杯","home":home,"away":away})).encode()).hexdigest()[:20],"competition":"足协杯","round":round_match.group(1) if round_match else "","start":start.isoformat(),"home":home,"away":away,"venue":"待定","status":"scheduled","source":"中国足协官网","source_url":article_url})
    return sorted({identity(e):e for e in events}.values(),key=lambda e:e["start"])

def merge(baseline: list[dict], official: list[dict], overrides: list[dict]) -> list[dict]:
    events={identity(e):e for e in baseline}
    for event in official:
        old=events.get(identity(event))
        if old:
            event=dict(event,id=old["id"],round=event["round"] or old.get("round",""))
            if event.get("venue") in (None,"","待定") and old.get("venue"): event["venue"]=old["venue"]
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
    legacy=LEGACY_UIDS.get(base_identity(event))
    if legacy and not str(event.get("id","")).startswith("afc-"): return legacy
    return hashlib.sha256(identity(event).encode()).hexdigest()[:20]+"@shenhua-calendar"

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
    official=[]; source_counts={}
    if not args.offline:
        fetchers=(("申花官网",fetch_official),("中国足协",fetch_cfa_announcements),("AFC",fetch_afc),("中足联",fetch_cfl))
        for source_name,fetcher in fetchers:
            try:
                found=fetcher(config)
                if source_name=="申花官网" and len(found)<config["official_minimum_events"]:
                    print(f"{source_name}仅返回{len(found)}场，忽略本次结果",file=sys.stderr); found=[]
                if source_name=="中足联" and found and len(found)<20:
                    print(f"{source_name}仅返回{len(found)}场中超，忽略本次结果",file=sys.stderr); found=[]
                source_counts[source_name]=len(found); official.extend(found)
            except Exception as exc:
                source_counts[source_name]=0; print(f"{source_name}不可用，保留其他来源和旧数据：{exc}",file=sys.stderr)
    events=merge(baseline,official,overrides)
    current=[e for e in events if datetime.fromisoformat(e["start"]).year==year_for(config)]
    if current: events=current
    validate(events,config)
    updated=schedule.get("updated_at") or datetime.now(timezone.utc).isoformat()
    if events!=baseline: updated=datetime.now(timezone.utc).isoformat()
    calendar=make_ics(events,config,updated)
    if args.check: print(f"验证通过：{len(events)}场"); return 0
    SCHEDULE.write_text(json.dumps({"updated_at":updated,"events":events},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    CALENDAR.write_bytes(calendar.encode()); details="，".join(f"{name}{count}场" for name,count in source_counts.items()); print(f"已生成{len(events)}场"+(f"（{details}）" if details else "")); return 0

if __name__ == "__main__": raise SystemExit(main())
