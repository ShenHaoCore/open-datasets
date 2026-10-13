"""生成 us-divisions 数据集（州 + 县自连表）。

字段与 cn-divisions 对齐，便于同一套联动代码：
  code / code6 / parent_code / level / name_zh / name_zh_short /
  name_en / iso3166_2 / type / type_zh
另加 usps（仅州级有值）。

输入：
- build/states.source.json（51 州/特区）
- build/national_county2020.txt（Census 2020 县级码表）

输出：divisions.json / divisions.csv / divisions.js

口径：
- 州级含首府；县级仅保留这 51 个 STATEFP 下的记录
- 哥伦比亚特区只保留州级一行，丢弃 county FIPS 11001
- 不含 PR 等海外领地

用法::

    python build/generate.py [--out DIR] [--check]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE.parent
STATES_SOURCE = HERE / "states.source.json"
COUNTIES_SOURCE = HERE / "national_county2020.txt"

JSON_NAME = "divisions.json"
CSV_NAME = "divisions.csv"
JS_NAME = "divisions.js"

SKIP_COUNTY_CODES = {"11001"}

STATE_TYPE_ZH = {
    "state": "州",
    "district": "特区",
}

COUNTY_TYPE_ZH = {
    "county": "县",
    "parish": "堂区",
    "borough": "自治市镇",
    "census_area": "普查区",
    "municipality": "市镇",
    "city": "独立市",
    "other": "其他",
}

# 列顺序与 cn-divisions 对齐，末尾多 usps / 首府（美国扩展）
CSV_HEADER = [
    "区划代码",
    "六位代码",
    "上级代码",
    "层级",
    "名称(中文)",
    "简称",
    "Name",
    "ISO3166-2",
    "类型",
    "类型(中文)",
    "USPS",
    "首府(中文)",
    "Capital",
]


def infer_county_type(name: str) -> str:
    if name.endswith("Parish"):
        return "parish"
    if name.endswith("Borough"):
        return "borough"
    if name.endswith("Census Area"):
        return "census_area"
    if name.endswith("Municipality"):
        return "municipality"
    if name.endswith("city") or name.endswith("City"):
        return "city"
    if name.endswith("County"):
        return "county"
    return "other"


def code6_of(code: str) -> str:
    """与 cn-divisions 同名的定长排序键：州 2 位补 0000，县 5 位补 0。"""
    if len(code) == 2:
        return code + "0000"
    if len(code) == 5:
        return code + "0"
    raise SystemExit(f"无法规范化 code6: {code!r}")


def record(
    *,
    code: str,
    parent: str,
    level: str,
    name_zh: str,
    name_zh_short: str,
    name_en: str,
    kind: str,
    type_zh: str,
    iso3166_2: str = "",
    usps: str = "",
    capital_zh: str = "",
    capital_en: str = "",
) -> dict:
    return {
        "code": code,
        "code6": code6_of(code),
        "parent_code": parent,
        "level": level,
        "name_zh": name_zh,
        "name_zh_short": name_zh_short,
        "name_en": name_en,
        "iso3166_2": iso3166_2,
        "type": kind,
        "type_zh": type_zh,
        "usps": usps,
        "capital_zh": capital_zh,
        "capital_en": capital_en,
    }


def load_counties(path: Path, state_fips: set[str]) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("STATE|"):
        raise SystemExit(f"县级源格式异常: {path}")
    rows = []
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 6:
            raise SystemExit(f"县级行列数不足: {line!r}")
        statefp, countyfp, name = parts[1], parts[2], parts[4]
        if statefp not in state_fips:
            continue
        code = statefp + countyfp
        if code in SKIP_COUNTY_CODES:
            continue
        kind = infer_county_type(name)
        rows.append(
            record(
                code=code,
                parent=statefp,
                level="county",
                name_zh="",
                name_zh_short="",
                name_en=name,
                kind=kind,
                type_zh=COUNTY_TYPE_ZH[kind],
            )
        )
    return rows


def build_records() -> list[dict]:
    source = json.loads(STATES_SOURCE.read_text(encoding="utf-8"))
    records: list[dict] = []
    state_fips: set[str] = set()

    for row in source["states"]:
        kind = row["type"]
        if kind not in STATE_TYPE_ZH:
            raise SystemExit(f"未知州级 type: {kind} ({row.get('usps')})")
        fips = row["fips"]
        usps = row["usps"]
        if len(fips) != 2 or not fips.isdigit():
            raise SystemExit(f"fips 须为两位数字: {fips!r}")
        state_fips.add(fips)
        records.append(
            record(
                code=fips,
                parent="",
                level="state",
                name_zh=row["name_zh"],
                name_zh_short=row["name_zh_short"],
                name_en=row["name_en"],
                kind=kind,
                type_zh=STATE_TYPE_ZH[kind],
                iso3166_2=f"US-{usps}",
                usps=usps,
                capital_zh=row["capital_zh"],
                capital_en=row["capital_en"],
            )
        )

    if len(records) != 51:
        raise SystemExit(f"期望 51 条州级，实际 {len(records)}")

    if not COUNTIES_SOURCE.exists():
        raise SystemExit(f"缺少 {COUNTIES_SOURCE}")
    counties = load_counties(COUNTIES_SOURCE, state_fips)
    if len(counties) < 3000:
        raise SystemExit(f"县级条数异常偏少: {len(counties)}")

    parent_ok = {r["code"] for r in records}
    for c in counties:
        if c["parent_code"] not in parent_ok:
            raise SystemExit(f"县上级州不存在: {c['code']} → {c['parent_code']}")
    records.extend(counties)
    records.sort(key=lambda r: r["code6"])
    return records


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def write_json(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records]
    body = "[\r\n" + ",\r\n".join(lines) + "\r\n]"
    write_text(path, body)


def write_js(path: Path, records: list[dict]) -> None:
    write_text(path, "window.US_DIVISIONS = " + json.dumps(records, ensure_ascii=False) + ";\r\n")


def write_csv(path: Path, records: list[dict]) -> None:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for r in records:
        writer.writerow(
            [
                r["code"],
                r["code6"],
                r["parent_code"],
                r["level"],
                r["name_zh"],
                r["name_zh_short"],
                r["name_en"],
                r["iso3166_2"],
                r["type"],
                r["type_zh"],
                r["usps"],
                r["capital_zh"],
                r["capital_en"],
            ]
        )
    path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def generate(out_dir: Path) -> None:
    records = build_records()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / JSON_NAME, records)
    write_csv(out_dir / CSV_NAME, records)
    write_js(out_dir / JS_NAME, records)

    counts = Counter(r["level"] for r in records)
    types = Counter(r["type"] for r in records)
    print(f"[generate] {JSON_NAME} / {CSV_NAME} / {JS_NAME} → {out_dir}")
    print(f"[generate] 记录 {len(records)} 条 · " + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"[generate] 类型 · " + " · ".join(f"{k} {v}" for k, v in sorted(types.items())))


def check(out_dir: Path) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        generate(tmp_dir)
        diffs = []
        for name in (JSON_NAME, CSV_NAME, JS_NAME):
            a, b = out_dir / name, tmp_dir / name
            if not a.exists():
                diffs.append(f"{name}: 现有文件缺失")
            elif a.read_bytes() != b.read_bytes():
                diffs.append(f"{name}: 字节不一致")
        if diffs:
            print(f"[check] 发现 {len(diffs)} 处差异：")
            for d in diffs:
                print("   ", d)
            return 1
        print(f"[check] 全部一致：{JSON_NAME} / {CSV_NAME} / {JS_NAME}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=DATASET_DIR, help="输出目录（默认数据集根目录）")
    parser.add_argument("--check", action="store_true", help="只校验现有文件能否被复现，不写回")
    args = parser.parse_args()

    if args.check:
        return check(args.out)
    generate(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
