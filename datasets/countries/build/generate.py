"""生成 countries 数据集的全部交付文件。

输入：build/upstream.json + build/.upstream/flags/*.svg
      （由 build/extract-upstream.mjs 抽取）
输出：数据集根目录下的
    countries.json / countries.csv / countries.js
    flags/<iso2>.svg

用法::

    python build/generate.py [--out DIR] [--check]

--out 指定输出目录，默认是 build/ 的上一级（即数据集根目录）。
--check 只生成到临时目录并与现有文件逐字节比对，不写回，用于回归验证。

依赖：Python ≥3.10。文本产物统一 CRLF、UTF-8；SVG 按上游原样复制（不改字节）。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE.parent
CACHE_DIR = HERE / ".upstream"
FLAG_CACHE = CACHE_DIR / "flags"
UPSTREAM = HERE / "upstream.json"

JSON_NAME = "countries.json"
CSV_NAME = "countries.csv"
JS_NAME = "countries.js"
FLAGS_DIR = "flags"

# 名称覆盖表。
# 分两类，都必须在数据集 README 里同步说明：
#   1. 上游缺名 —— intl-tel-input 的 i18n 表里没有这两条，必须补；
#   2. 命名口径 —— 港澳台按中国官方口径标注（上游 en 表写作 "Hong Kong SAR China"、
#      zh 表写作 "台湾"，与 ISO 3166 的表述都不一致，此处统一为中国官方口径）；
#      BQ 取更通行的「荷兰加勒比区」而非上游的「荷属加勒比区」。
NAME_OVERRIDES: dict[str, dict[str, str]] = {
    "AC": {"name_en": "Ascension Island", "name_zh": "阿森松岛"},
    "XK": {"name_en": "Kosovo", "name_zh": "科索沃"},
    "BQ": {"name_zh": "荷兰加勒比区"},
    "HK": {"name_en": "Hong Kong, China", "name_zh": "中国香港"},
    "MO": {"name_en": "Macao, China", "name_zh": "中国澳门"},
    "TW": {"name_en": "Taiwan, China", "name_zh": "中国台湾"},
}

CSV_HEADER = [
    "国家/地区(中文)",
    "Country/Region",
    "官方英文名",
    "ISO2",
    "ISO3",
    "数字码",
    "首都",
    "大洲",
    "地区",
    "纬度",
    "经度",
    "面积km2",
    "货币代码",
    "语言",
    "域名后缀",
    "独立",
    "联合国会员",
    "内陆国",
    "电话区号",
    "国旗文件",
    "国旗emoji",
]

# 旧版 PNG 雪碧图产物，重建时清掉，避免与 SVG 并存误导。
LEGACY_ARTIFACTS = ("flags.css", "flags.png", "flags@2x.png")

EMPTY_PROFILE = {
    "iso3": "",
    "ccn3": "",
    "capital": [],
    "region": "",
    "subregion": "",
    "latlng": None,
    "area": None,
    "tld": [],
    "currencies": {},
    "languages": {},
    "borders": [],
    "independent": None,
    "un_member": None,
    "landlocked": None,
    "status": "",
    "name_official": "",
}


def regional_indicator(iso2: str) -> str:
    """ISO2 → 区域指示符 emoji（即国旗 emoji）。"""
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in iso2)


def build_records(upstream: dict) -> list[dict]:
    """按上游顺序组装国家/地区记录（国家主数据 + 电话区号 + 国旗）。"""
    names_en: dict[str, str] = upstream["names"]["en"]
    names_zh: dict[str, str] = upstream["names"]["zh"]
    profiles: dict[str, dict] = upstream["profiles"]
    flag_set = set(upstream["flags"])

    records = []
    for row in upstream["countries"]:
        key = row["iso2"]
        iso2 = key.upper()
        override = NAME_OVERRIDES.get(iso2, {})
        profile = profiles.get(key) or EMPTY_PROFILE

        name_en = override.get("name_en") or names_en.get(key)
        name_zh = override.get("name_zh") or names_zh.get(key)
        if not name_en or not name_zh:
            raise SystemExit(f"缺少名称且无覆盖: {iso2}")

        # 国旗 emoji 只在 countries（npm: world-countries）有档案时给出；AC 留空。
        in_iso = key in profiles
        emoji = regional_indicator(iso2) if in_iso else ""
        has_flag = key in flag_set

        latlng = profile.get("latlng")
        lat = latlng[0] if isinstance(latlng, list) and len(latlng) >= 2 else None
        lng = latlng[1] if isinstance(latlng, list) and len(latlng) >= 2 else None
        capitals = profile.get("capital") or []

        records.append(
            {
                "iso2": iso2,
                "iso3": profile.get("iso3") or "",
                "ccn3": profile.get("ccn3") or "",
                "name_zh": name_zh,
                "name_en": name_en,
                "name_en_official": profile.get("name_official") or "",
                "capital": capitals[0] if capitals else "",
                "capitals": capitals,
                "region": profile.get("region") or "",
                "subregion": profile.get("subregion") or "",
                "lat": lat,
                "lng": lng,
                "area": profile.get("area"),
                "tld": profile.get("tld") or [],
                "currencies": profile.get("currencies") or {},
                "languages": profile.get("languages") or {},
                "borders": profile.get("borders") or [],
                "independent": profile.get("independent"),
                "un_member": profile.get("un_member"),
                "landlocked": profile.get("landlocked"),
                "status": profile.get("status") or "",
                "dial_code": row["dial_code"],
                "phone_prefix": "+" + row["dial_code"],
                "priority": row["priority"],
                "area_codes": row["area_codes"],
                "flag_emoji": emoji,
                "flag_file": f"{FLAGS_DIR}/{key}.svg" if has_flag else "",
                "has_flag": has_flag,
            }
        )
    return records


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="")


def write_json(path: Path, records: list[dict]) -> None:
    body = json.dumps(records, ensure_ascii=False, indent=2)
    write_text(path, body.replace("\n", "\r\n"))


def write_js(path: Path, records: list[dict]) -> None:
    write_text(path, "window.COUNTRIES = " + json.dumps(records, ensure_ascii=False) + ";\r\n")


def _join(values: list | dict) -> str:
    if isinstance(values, dict):
        return "|".join(values.keys())
    return "|".join(str(v) for v in values)


def _tri(value: bool | None) -> str:
    if value is True:
        return "是"
    if value is False:
        return "否"
    return ""


def write_csv(path: Path, records: list[dict]) -> None:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for r in records:
        writer.writerow(
            [
                r["name_zh"],
                r["name_en"],
                r["name_en_official"],
                r["iso2"],
                r["iso3"],
                r["ccn3"],
                r["capital"],
                r["region"],
                r["subregion"],
                "" if r["lat"] is None else r["lat"],
                "" if r["lng"] is None else r["lng"],
                "" if r["area"] is None else r["area"],
                _join(r["currencies"]),
                _join(r["languages"]),
                _join(r["tld"]),
                _tri(r["independent"]),
                _tri(r["un_member"]),
                _tri(r["landlocked"]),
                r["phone_prefix"],
                r["flag_file"],
                r["flag_emoji"],
            ]
        )
    # 带 BOM，便于 Excel 直接打开不乱码
    path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def write_flags(flags_dir: Path, flag_codes: list[str]) -> None:
    """把缓存中的 SVG 原样拷到输出目录（不改字节，保证 --check 跨平台一致）。"""
    if flags_dir.exists():
        shutil.rmtree(flags_dir)
    flags_dir.mkdir(parents=True, exist_ok=True)
    for code in flag_codes:
        src = FLAG_CACHE / f"{code}.svg"
        if not src.exists():
            raise SystemExit(f"缺少国旗缓存 {src}，请先运行 node build/extract-upstream.mjs")
        shutil.copyfile(src, flags_dir / f"{code}.svg")


def clear_legacy(out_dir: Path) -> None:
    for name in LEGACY_ARTIFACTS:
        p = out_dir / name
        if p.exists():
            p.unlink()


def generate(out_dir: Path) -> None:
    if not UPSTREAM.exists():
        raise SystemExit(f"缺少 {UPSTREAM}，请先运行 node build/extract-upstream.mjs")
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    records = build_records(upstream)
    flag_codes: list[str] = upstream["flags"]

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / JSON_NAME, records)
    write_csv(out_dir / CSV_NAME, records)
    write_js(out_dir / JS_NAME, records)
    write_flags(out_dir / FLAGS_DIR, flag_codes)
    clear_legacy(out_dir)

    missing = upstream.get("flags_missing") or []
    with_profile = sum(1 for r in records if r["iso3"] or r["region"])
    print(f"[generate] {JSON_NAME} / {CSV_NAME} / {JS_NAME} → {out_dir}")
    print(
        f"[generate] 记录 {len(records)} 条 · 主数据 {with_profile} · 国旗 SVG {len(flag_codes)} 张"
        + (f" · 缺图 {','.join(missing)}" if missing else "")
    )


def check(out_dir: Path) -> int:
    """生成到临时目录并与现有文件逐字节比对。"""
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

        existing = sorted(p.name for p in (out_dir / FLAGS_DIR).glob("*.svg"))
        fresh = sorted(p.name for p in (tmp_dir / FLAGS_DIR).glob("*.svg"))
        if existing != fresh:
            diffs.append(f"{FLAGS_DIR}/: 文件清单不一致（{len(existing)} vs {len(fresh)}）")
        else:
            for name in fresh:
                pa, pb = out_dir / FLAGS_DIR / name, tmp_dir / FLAGS_DIR / name
                if pa.read_bytes() != pb.read_bytes():
                    diffs.append(f"{FLAGS_DIR}/{name}: 字节不一致")

        leftover_png = sorted(p.name for p in (out_dir / FLAGS_DIR).glob("*.png"))
        if leftover_png:
            diffs.append(f"{FLAGS_DIR}/: 仍有旧 PNG {len(leftover_png)} 张，应已全部替换为 SVG")

        for name in LEGACY_ARTIFACTS:
            if (out_dir / name).exists():
                diffs.append(f"{name}: 旧产物仍存在，应已删除")

        if diffs:
            print(f"[check] 发现 {len(diffs)} 处差异：")
            for d in diffs[:20]:
                print("   ", d)
            return 1
        print(f"[check] 全部一致：{len(existing)} 张 SVG + {JSON_NAME}/{CSV_NAME}/{JS_NAME}")
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
