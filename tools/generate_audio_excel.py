import os
import json
import csv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CALENDAR_PATH = os.path.join(PROJECT_ROOT, "calendar_config.json")

CATEGORIES = ["start", "end", "interval", "resume", "exit"]

def load_calendar():
    if os.path.exists(CALENDAR_PATH):
        with open(CALENDAR_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"holidays": [], "seasons": []}

def base_rows():
    rows = []
    for cat in CATEGORIES:
        rows.append(["基础", "", cat, ""])
    return rows

def holiday_rows(cal):
    rows = []
    holidays = cal.get("holidays", [])
    for h in holidays:
        hid = h.get("id")
        if not hid:
            continue
        rows.append(["节日", hid, "greeting", ""])
        for cat in CATEGORIES:
            rows.append(["节日", hid, cat, ""])
    return rows

def season_rows(cal):
    rows = []
    seasons = cal.get("seasons", [])
    for s in seasons:
        sid = s.get("id")
        if not sid:
            continue
        for cat in CATEGORIES:
            rows.append(["季节", sid, cat, ""])
    return rows

def write_csv(rows, out_path):
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["类型", "名称", "事件", "台词"])
        w.writerows(rows)

def write_xlsx(rows, out_path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "voice_lines"
    ws.append(["类型", "名称", "事件", "台词"])
    for r in rows:
        ws.append(r)
    wb.save(out_path)

def main():
    cal = load_calendar()
    rows = base_rows() + holiday_rows(cal) + season_rows(cal)
    csv_out = os.path.join(PROJECT_ROOT, "audio_assets.csv")
    write_csv(rows, csv_out)
    xlsx_out = os.path.join(PROJECT_ROOT, "audio_assets.xlsx")
    try:
        write_xlsx(rows, xlsx_out)
        print(f"Wrote Excel: {xlsx_out}")
    except Exception as e:
        print(f"Excel failed: {e}")

if __name__ == "__main__":
    main()
