"""生成 cn-divisions 数据集（省 / 地级 / 区县自连表）。

输入：build/upstream.json（由 extract-upstream.mjs 抽取）
输出：divisions.json / divisions.csv / divisions.js

口径：
- 省级 34 条（含港澳台），来自 provinces.source.json
- 地级挂 parent_code → 省 code；直辖市只保留省级一行，不造市级重复
- 上游「市辖区 / 县」占位丢弃；「省/自治区直辖县级」展开为 level=city
- 区县挂所属地级；直辖市区县直接挂省级 code

用法::

    python build/generate.py [--out DIR] [--check]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE.parent
UPSTREAM = HERE / "upstream.json"

JSON_NAME = "divisions.json"
CSV_NAME = "divisions.csv"
JS_NAME = "divisions.js"

# 直辖市地级占位：省级已有同名行，整行丢弃
SKIP_CITY_CODES = {"1101", "1201", "3101", "5001", "5002"}

# 区县若挂在这些占位上，改挂到省级 code（直辖市无市级行）
MUNI_CITY_TO_PROVINCE = {
    "1101": "11",
    "1201": "12",
    "3101": "31",
    "5001": "50",
    "5002": "50",
}

PROVINCE_TYPE_ZH = {
    "province": "省",
    "municipality": "直辖市",
    "autonomous_region": "自治区",
    "sar": "特别行政区",
}

CITY_TYPE_ZH = {
    "prefecture_city": "地级市",
    "autonomous_prefecture": "自治州",
    "prefecture": "地区",
    "league": "盟",
    "county_level": "县级",
}

COUNTY_TYPE_ZH = {
    "district": "市辖区",
    "county": "县",
    "autonomous_county": "自治县",
    "county_city": "县级市",
    "banner": "旗",
    "autonomous_banner": "自治旗",
    "forestry_area": "林区",
    "special_zone": "特区",
    "other": "其他",
}

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
]


def short_name(name: str) -> str:
    for suffix in (
        "自治县",
        "自治旗",
        "自治州",
        "林区",
        "特区",
        "地区",
        "群岛",
        "区",
        "县",
        "市",
        "旗",
        "盟",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def infer_city_type(name: str, code: str) -> str:
    if len(code) == 6:
        return "county_level"
    if name.endswith("自治州"):
        return "autonomous_prefecture"
    if name.endswith("地区"):
        return "prefecture"
    if name.endswith("盟"):
        return "league"
    if name.endswith("市"):
        return "prefecture_city"
    return "prefecture_city"


def infer_county_type(name: str) -> str:
    if name.endswith("自治县"):
        return "autonomous_county"
    if name.endswith("自治旗"):
        return "autonomous_banner"
    if name.endswith("林区"):
        return "forestry_area"
    if name.endswith("特区"):
        return "special_zone"
    if name.endswith("区"):
        return "district"
    if name.endswith("县"):
        return "county"
    if name.endswith("市"):
        return "county_city"
    if name.endswith("旗"):
        return "banner"
    return "other"


def code6_of(code: str) -> str:
    if len(code) == 2:
        return code + "0000"
    if len(code) == 4:
        return code + "00"
    if len(code) == 6:
        return code
    raise SystemExit(f"无法规范化 code6: {code!r}")


def base_record(
    *,
    code: str,
    parent: str,
    level: str,
    name: str,
    name_short: str,
    kind: str,
    type_zh: str,
    name_en: str = "",
    iso3166_2: str = "",
) -> dict:
    return {
        "code": code,
        "code6": code6_of(code),
        "parent_code": parent,
        "level": level,
        "name_zh": name,
        "name_zh_short": name_short,
        "name_en": name_en,
        "iso3166_2": iso3166_2,
        "type": kind,
        "type_zh": type_zh,
    }


def city_record(code: str, parent: str, name: str) -> dict:
    kind = infer_city_type(name, code)
    return base_record(
        code=code,
        parent=parent,
        level="city",
        name=name,
        name_short=short_name(name),
        kind=kind,
        type_zh=CITY_TYPE_ZH[kind],
    )


def county_record(code: str, parent: str, name: str) -> dict:
    kind = infer_county_type(name)
    return base_record(
        code=code,
        parent=parent,
        level="county",
        name=name,
        name_short=short_name(name),
        kind=kind,
        type_zh=COUNTY_TYPE_ZH[kind],
    )


def build_records(upstream: dict) -> list[dict]:
    province_codes = {p["code"] for p in upstream["provinces"]}
    records: list[dict] = []

    for row in upstream["provinces"]:
        kind = row["type"]
        if kind not in PROVINCE_TYPE_ZH:
            raise SystemExit(f"未知省级 type: {kind} ({row.get('code')})")
        code = row["code"]
        records.append(
            base_record(
                code=code,
                parent="",
                level="province",
                name=row["name_zh"],
                name_short=row["name_zh_short"],
                kind=kind,
                type_zh=PROVINCE_TYPE_ZH[kind],
                name_en=row["name_en"],
                iso3166_2=row["iso3166_2"],
            )
        )

    expand_parents = {
        row["code"] for row in upstream["cities"] if re.search(r"直辖县级", row["name"])
    }

    for row in upstream["cities"]:
        code = row["code"]
        parent = row["provinceCode"]
        name = row["name"]

        if code in SKIP_CITY_CODES:
            continue
        if parent not in province_codes:
            raise SystemExit(f"城市上级省不存在: {code} → {parent}")

        if code in expand_parents:
            kids = [a for a in upstream["areas"] if a["cityCode"] == code]
            if not kids:
                raise SystemExit(f"直辖县级父级无子节点: {code} {name}")
            for area in kids:
                records.append(city_record(area["code"], parent, area["name"]))
            continue

        records.append(city_record(code, parent, name))

    existing_codes = {r["code"] for r in records}
    city_codes = {r["code"] for r in records if r["level"] == "city"}

    for row in upstream["areas"]:
        code = row["code"]
        # 已作为「省直辖县级」提升到 city 的条目，不再重复为 county
        if code in existing_codes:
            continue

        city_code = row["cityCode"]
        if city_code in MUNI_CITY_TO_PROVINCE:
            parent = MUNI_CITY_TO_PROVINCE[city_code]
        elif city_code in expand_parents:
            raise SystemExit(f"直辖县级下仍有未提升区县: {code} cityCode={city_code}")
        elif city_code in city_codes:
            parent = city_code
        else:
            raise SystemExit(f"区县无法解析上级: {code} cityCode={city_code}")

        if parent not in existing_codes:
            raise SystemExit(f"区县上级不存在: {code} → {parent}")

        records.append(county_record(code, parent, row["name"]))
        existing_codes.add(code)

    records.sort(key=lambda r: r["code6"])
    n_prov = sum(1 for r in records if r["level"] == "province")
    n_city = sum(1 for r in records if r["level"] == "city")
    n_county = sum(1 for r in records if r["level"] == "county")
    if n_prov != 34:
        raise SystemExit(f"期望 34 条省级，实际 {n_prov}")
    if n_city < 300:
        raise SystemExit(f"地级条数异常偏少: {n_city}")
    if n_county < 2000:
        raise SystemExit(f"区县条数异常偏少: {n_county}")
    return records


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def write_json(path: Path, records: list[dict]) -> None:
    # 每条记录一行紧凑 JSON，便于浏览与 diff
    lines = [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records]
    body = "[\r\n" + ",\r\n".join(lines) + "\r\n]"
    write_text(path, body)


def write_js(path: Path, records: list[dict]) -> None:
    write_text(path, "window.CN_DIVISIONS = " + json.dumps(records, ensure_ascii=False) + ";\r\n")


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
            ]
        )
    path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def generate(out_dir: Path) -> None:
    if not UPSTREAM.exists():
        raise SystemExit(f"缺少 {UPSTREAM}，请先运行 node build/extract-upstream.mjs")
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    records = build_records(upstream)

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
