# 上海申花赛程订阅

订阅地址：<https://joesysgs.github.io/shenhua-calendar/shenhua.ics>

系统每天北京时间 02:17 自动访问上海申花官网赛程接口，合并人工确认的临时调整，校验后生成 ICS。年份自动识别，新赛季公布后无需更换订阅地址。

## 本地运行

```bash
python3 scripts/update_calendar.py
python3 scripts/update_calendar.py --offline --check
python3 -m unittest discover -s tests -v
```

## 数据策略

- 上海申花官网是唯一自动覆盖赛程的主数据源。
- 官网不可用或返回少于安全阈值时保留上次有效数据。
- `data/overrides.json` 用于延期、补赛和官网尚未同步的官方调整。
- 原有赛事 UID 被保留，改期不会在订阅端产生重复事件。
- 进入新年度但赛程尚未发布时，不会生成空日历。
