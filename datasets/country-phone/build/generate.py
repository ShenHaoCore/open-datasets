"""生成 country-phone 数据集的全部交付文件。

输入：build/upstream.json（由 build/extract-upstream.mjs 抽取的上游原始事实）
输出：数据集根目录下的
    countries.json / countries.csv / countries.js
    flags.css / flags.png / flags@2x.png
    flags/<iso2>.png

用法::

    python build/generate.py [--out DIR] [--check]

--out 指定输出目录，默认是 build/ 的上一级（即数据集根目录）。
--check 只生成到临时目录并与现有文件逐字节比对，不写回，用于回归验证。

依赖：Python ≥3.10、Pillow。所有文本文件统一 CRLF、UTF-8。
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
DATASET_DIR = HERE.parent
CACHE_DIR = HERE / ".upstream"
UPSTREAM = HERE / "upstream.json"

# 输出文件名（常量集中在此，便于核对）
JSON_NAME = "countries.json"
CSV_NAME = "countries.csv"
JS_NAME = "countries.js"
CSS_NAME = "flags.css"
FLAGS_DIR = "flags"
SPRITE_NAMES = ("flags.png", "flags@2x.png")

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
    "ISO2",
    "ISO3",
    "电话区号",
    "国旗文件",
    "国旗emoji",
]


def regional_indicator(iso2: str) -> str:
    """ISO2 → 区域指示符 emoji（即国旗 emoji）。"""
    return "".join(chr(0x1F1E6 + ord(ch) - ord("A")) for ch in iso2)


def build_records(upstream: dict) -> list[dict]:
    """按上游顺序组装 244 条国家/地区记录。"""
    known_iso3: dict[str, str] = upstream["iso3"]
    names_en: dict[str, str] = upstream["names"]["en"]
    names_zh: dict[str, str] = upstream["names"]["zh"]

    records = []
    for row in upstream["countries"]:
        key = row["iso2"]
        iso2 = key.upper()
        override = NAME_OVERRIDES.get(iso2, {})

        name_en = override.get("name_en") or names_en.get(key)
        name_zh = override.get("name_zh") or names_zh.get(key)
        if not name_en or not name_zh:
            raise SystemExit(f"缺少名称且无覆盖: {iso2}")

        # 国旗 emoji 只在 ISO 3166-1 正式条目上给出；AC 等非正式码留空。
        emoji = regional_indicator(iso2) if iso2 in known_iso3 else ""

        records.append(
            {
                "iso2": iso2,
                "iso3": known_iso3.get(iso2, ""),
                "name_zh": name_zh,
                "name_en": name_en,
                "dial_code": row["dial_code"],
                "phone_prefix": "+" + row["dial_code"],
                "priority": row["priority"],
                "area_codes": row["area_codes"],
                "flag_emoji": emoji,
                "flag_file": f"{FLAGS_DIR}/{key}.png",
                "has_flag": key in upstream["flags"],
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


def write_csv(path: Path, records: list[dict]) -> None:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(CSV_HEADER)
    for r in records:
        writer.writerow(
            [
                r["name_zh"],
                r["name_en"],
                r["iso2"],
                r["iso3"],
                r["phone_prefix"],
                r["flag_file"],
                r["flag_emoji"],
            ]
        )
    # 带 BOM，便于 Excel 直接打开不乱码
    path.write_bytes(b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8"))


def write_css(path: Path, flags: dict[str, dict], sprite_w: int, sprite_h: int) -> None:
    lines = [
        "/* 国旗雪碧图样式：与 flags.png / flags@2x.png 配套 */",
        ".iti-flag {",
        "  display: inline-block;",
        f"  width: 20px; height: {sprite_h}px;",
        f"  background-image: url('{SPRITE_NAMES[0]}');",
        "  background-repeat: no-repeat;",
        f"  background-size: {sprite_w}px {sprite_h}px;",
        "}",
        "@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {",
        f"  .iti-flag {{ background-image: url('{SPRITE_NAMES[1]}'); }}",
        "}",
        "",
    ]
    for code in sorted(flags):
        lines.append(f".iti-flag-{code} {{ background-position: -{flags[code]['offset']}px 0; }}")
    for code in sorted(flags):
        width = flags[code]["width"]
        if width != 20:
            lines.append(f".iti-flag-{code} {{ width: {width}px; }}")
    write_text(path, "\r\n".join(lines) + "\r\n")


def write_flags(flags_dir: Path, flags: dict[str, dict], sprite_path: Path) -> None:
    """从 @2x 精灵图按 CSS 参数切出逐国 PNG。

    雪碧图里各旗不是等高等宽的：高度取自 CSS 的 --iti-flag-height 分档
    （10/11/12/13/15 与默认 14），宽度取自 --iti-flag-width 覆盖（默认 20），
    旗间水平间距 2px；上游给出的 offset 已把间距算在内。

    optimize=True（等价 compress_level=9）是刻意保留的：它让产物与历史版本
    逐字节一致，便于用 md5 直接判定「数据有没有变」。
    """
    sheet = Image.open(sprite_path).convert("RGBA")
    flags_dir.mkdir(parents=True, exist_ok=True)
    for code, spec in flags.items():
        x0 = spec["offset"] * 2
        box = (x0, 0, x0 + spec["width"] * 2, spec["height"] * 2)
        sheet.crop(box).save(flags_dir / f"{code}.png", optimize=True)


def generate(out_dir: Path) -> None:
    upstream = json.loads(UPSTREAM.read_text(encoding="utf-8"))
    records = build_records(upstream)
    flags = upstream["flags"]

    sprite_1x = CACHE_DIR / SPRITE_NAMES[0]
    sprite_2x = CACHE_DIR / SPRITE_NAMES[1]
    for sprite in (sprite_1x, sprite_2x):
        if not sprite.exists():
            raise SystemExit(f"缺少精灵图 {sprite}，请先运行 node build/extract-upstream.mjs")

    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / JSON_NAME, records)
    write_csv(out_dir / CSV_NAME, records)
    write_js(out_dir / JS_NAME, records)

    width_2x, height_2x = Image.open(sprite_2x).size
    write_css(out_dir / CSS_NAME, flags, width_2x // 2, height_2x // 2)

    for name in SPRITE_NAMES:
        (out_dir / name).write_bytes((CACHE_DIR / name).read_bytes())

    write_flags(out_dir / FLAGS_DIR, flags, sprite_2x)

    print(f"[generate] {JSON_NAME} / {CSV_NAME} / {JS_NAME} / {CSS_NAME} → {out_dir}")
    print(f"[generate] 记录 {len(records)} 条 · 国旗 {len(flags)} 张 · 精灵图 {width_2x // 2}×{height_2x // 2}")


def check(out_dir: Path) -> int:
    """生成到临时目录并与现有文件比对。PNG 会比像素，其余比字节。"""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        generate(tmp_dir)
        diffs = []

        for name in [JSON_NAME, CSV_NAME, JS_NAME, CSS_NAME, *SPRITE_NAMES]:
            a, b = out_dir / name, tmp_dir / name
            if not a.exists():
                diffs.append(f"{name}: 现有文件缺失")
            elif a.read_bytes() != b.read_bytes():
                diffs.append(f"{name}: 字节不一致")

        existing = sorted(p.name for p in (out_dir / FLAGS_DIR).glob("*.png"))
        fresh = sorted(p.name for p in (tmp_dir / FLAGS_DIR).glob("*.png"))
        if existing != fresh:
            diffs.append(f"{FLAGS_DIR}/: 文件清单不一致（{len(existing)} vs {len(fresh)}）")
        else:
            for name in fresh:
                pa, pb = out_dir / FLAGS_DIR / name, tmp_dir / FLAGS_DIR / name
                with Image.open(pa) as ia, Image.open(pb) as ib:
                    if ia.size != ib.size or ia.convert("RGBA").tobytes() != ib.convert("RGBA").tobytes():
                        diffs.append(f"{FLAGS_DIR}/{name}: 像素不一致")

        if diffs:
            print(f"[check] 发现 {len(diffs)} 处差异：")
            for d in diffs[:20]:
                print("   ", d)
            return 1
        print(f"[check] 全部一致：{len(existing)} 张国旗 + {4 + len(SPRITE_NAMES)} 个文件")
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
