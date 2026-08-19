# 上海申花赛程订阅

订阅地址：<https://joesysgs.github.io/shenhua-calendar/shenhua.ics>

系统每天北京时间 02:17 自动核查中足联、中国足协、AFC 和上海申花官网，合并后校验并生成 ICS。年份自动识别，新赛季公布后无需更换订阅地址。

## 本地运行

```bash
python3 scripts/update_calendar.py
python3 scripts/update_calendar.py --offline --check
python3 -m unittest discover -s tests -v
```

## 数据策略

- 中超以中足联官方结构化赛程接口为最高优先级。
- 足协杯扫描中国足协官网近期公告；申花官网用于补充公告尚未提供的精确开球时间和场地。
- 亚冠精英联赛、亚冠二级联赛自动发现 AFC 官网最新版官方赛程 PDF，并将当地开球时间换算为北京时间。
- 上海申花官网作为全部赛事的交叉校验和故障兜底来源。
- 任一来源不可用或返回异常数据时，只忽略该来源并保留上次有效数据。
- `data/overrides.json` 用于延期、补赛和官网尚未同步的官方调整。
- 原有赛事 UID 被保留，改期不会在订阅端产生重复事件。
- 进入新年度但赛程尚未发布时，不会生成空日历。
