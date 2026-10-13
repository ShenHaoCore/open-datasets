"""从 cn-divisions / us-divisions 生成 geo_division 播种 SQL。

用法::

    python schema/geo_division/build/generate_seed.py
    python schema/geo_division/build/generate_seed.py --check

约定：MSSQL 产物 UTF-8 BOM + CRLF，并 SET QUOTED_IDENTIFIER ON；
PostgreSQL 产物无 BOM + LF；parent_code / code_iso 空值输出 NULL。
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = HERE.parent
REPO = SCHEMA_DIR.parent.parent
CN_JSON = REPO / "datasets" / "cn-divisions" / "divisions.json"
US_JSON = REPO / "datasets" / "us-divisions" / "divisions.json"

BATCH = 100
BOM = b"\xef\xbb\xbf"
PG_EOL = "\n"
MSSQL_EOL = "\r\n"

# 本批播种覆盖的国家；重播时按 country 删，不另存 source 列
SEED_COUNTRIES = ("CN", "US")

COLS = [
    "country",
    "code",
    "sort_key",
    "code_iso",
    "parent_code",
    "depth",
    "name_local",
    "name_local_short",
    "name_en",
    "name_zh",
    "type",
    "abbrev",
    "status",
]


def esc(value: str) -> str:
    return value.replace("'", "''")


def assign_depth(rows: list[dict]) -> None:
    """按 parent_code 填 depth：根=1，子=父+1。原地写回。"""
    by_key = {(r["country"], r["code"]): r for r in rows}
    memo: dict[tuple[str, str], int] = {}

    def depth_of(country: str, code: str) -> int:
        key = (country, code)
        if key in memo:
            return memo[key]
        row = by_key[key]
        parent = row["parent_code"]
        if parent is None:
            d = 1
        else:
            d = depth_of(country, parent) + 1
        memo[key] = d
        return d

    for r in rows:
        r["depth"] = depth_of(r["country"], r["code"])


def load_rows() -> list[dict]:
    cn = json.loads(CN_JSON.read_text(encoding="utf-8"))
    us = json.loads(US_JSON.read_text(encoding="utf-8"))

    rows: list[dict] = []
    for r in cn:
        rows.append(
            {
                "country": "CN",
                "code": r["code"],
                # 数据集字段仍叫 code6；入库为国别无关的 sort_key
                "sort_key": r.get("code6") or r["code"],
                "code_iso": r.get("iso3166_2") or None,
                "parent_code": r.get("parent_code") or None,
                # 当地名即中文：只写入 name_local*，name_zh 留空避免双写
                "name_local": r["name_zh"],
                "name_local_short": r.get("name_zh_short") or "",
                "name_en": r.get("name_en") or "",
                "name_zh": "",
                "type": r.get("type") or "",
                "abbrev": "",
                "status": "active",
            }
        )

    for r in us:
        # 中文展示优先常用简称（加州），否则全称
        name_zh = r.get("name_zh_short") or r.get("name_zh") or ""
        rows.append(
            {
                "country": "US",
                "code": r["code"],
                "sort_key": r.get("code6") or r["code"],
                "code_iso": r.get("iso3166_2") or None,
                "parent_code": r.get("parent_code") or None,
                # 当地名即英文：只写入 name_local，name_en 留空避免双写
                "name_local": r["name_en"],
                "name_local_short": "",
                "name_en": "",
                "name_zh": name_zh,
                "type": r.get("type") or "",
                "abbrev": r.get("usps") or "",
                "status": "active",
            }
        )

    assign_depth(rows)
    rows.sort(key=lambda r: (r["country"], r["sort_key"], r["code"]))
    return rows


def validate(rows: list[dict]) -> list[str]:
    """校验不变量；返回非致命的提示列表，致命问题直接 SystemExit。"""
    keys = Counter((r["country"], r["code"]) for r in rows)
    dup = [k for k, v in keys.items() if v > 1]
    if dup:
        raise SystemExit(f"(country, code) 重复：{dup[:5]}")

    known = {(r["country"], r["code"]): r for r in rows}
    for r in rows:
        if r["type"] == "":
            raise SystemExit(f"type 为空：{r['country']} {r['code']}")
        parent = r["parent_code"]
        if (parent is None) != (r["depth"] == 1):
            raise SystemExit(
                f"父子/深度不自洽：{r['country']} {r['code']} "
                f"parent={parent!r} depth={r['depth']}"
            )
        if parent is not None:
            pkey = (r["country"], parent)
            if pkey not in known:
                raise SystemExit(f"上级不存在：{r['country']} {r['code']} → {parent}")
            if r["depth"] != known[pkey]["depth"] + 1:
                raise SystemExit(
                    f"depth 不等于父+1：{r['country']} {r['code']} "
                    f"depth={r['depth']} parent_depth={known[pkey]['depth']}"
                )

    iso = Counter(r["code_iso"] for r in rows if r["code_iso"])
    iso_dup = [k for k, v in iso.items() if v > 1]
    if iso_dup:
        raise SystemExit(f"code_iso 重复：{iso_dup[:5]}")

    notes = []
    sort_dup = sorted(
        k for k, v in Counter((r["country"], r["sort_key"]) for r in rows).items() if v > 1
    )
    if sort_dup:
        notes.append(
            f"sort_key 不唯一（已知现象，直筒子市等同键多行）：{len(sort_dup)} 组 "
            + ", ".join(f"{c}/{k}" for c, k in sort_dup[:5])
        )
    return notes


def sql_literal(row: dict, col: str, dialect: str) -> str:
    val = row[col]
    if val is None:
        return "NULL"
    if col == "depth":
        return str(val)
    if dialect == "mssql":
        return "N'" + esc(val) + "'"
    return "'" + esc(val) + "'"


def render_insert_batch(rows: list[dict], dialect: str, eol: str) -> str:
    table = "dbo.geo_division" if dialect == "mssql" else "geo_division"
    col_list = ", ".join(COLS)
    value_lines = [
        "(" + ", ".join(sql_literal(r, c, dialect) for c in COLS) + ")" for r in rows
    ]
    body = ("," + eol).join(value_lines)
    return f"INSERT INTO {table} ({col_list}) VALUES{eol}{body};"


def render_batches(rows: list[dict], dialect: str, eol: str) -> list[str]:
    parts = []
    for i in range(0, len(rows), BATCH):
        parts.append(render_insert_batch(rows[i : i + BATCH], dialect, eol))
        parts.append("")
    return parts


def seed_country_in_list(dialect: str) -> str:
    if dialect == "mssql":
        return ", ".join(f"N'{c}'" for c in SEED_COUNTRIES)
    return ", ".join(f"'{c}'" for c in SEED_COUNTRIES)


def render_pg_up(rows: list[dict]) -> str:
    countries = seed_country_in_list("pg")
    parts = [
        "-- geo_division 播种：CN + US（由 build/generate_seed.py 生成，勿手改）",
        "-- 来源：datasets/cn-divisions、datasets/us-divisions",
        "-- 本文件为 UTF-8 无 BOM + LF；MSSQL 侧刻意不同，勿互相复制",
        "",
        "BEGIN;",
        "",
        f"DELETE FROM geo_division WHERE country IN ({countries});",
        "",
    ]
    parts.extend(render_batches(rows, "pg", PG_EOL))
    parts.append("COMMIT;")
    return PG_EOL.join(parts) + PG_EOL


def render_pg_down() -> str:
    countries = seed_country_in_list("pg")
    return PG_EOL.join(
        [
            "-- 回滚本批播种数据（PostgreSQL）",
            f"DELETE FROM geo_division WHERE country IN ({countries});",
            "",
        ]
    )


def render_mssql_up(rows: list[dict]) -> str:
    countries = seed_country_in_list("mssql")
    parts = [
        "-- geo_division 播种：CN + US（由 build/generate_seed.py 生成，勿手改）",
        "-- 来源：datasets/cn-divisions、datasets/us-divisions",
        "-- 本文件必须为 UTF-8 with BOM：sqlcmd 按系统 ACP 解码，缺 BOM 会静默丢弃整批",
        "",
        "-- 表带过滤索引，DML 要求 QUOTED_IDENTIFIER/ANSI_NULLS 为 ON（sqlcmd 默认 OFF）",
        "SET QUOTED_IDENTIFIER ON;",
        "SET ANSI_NULLS ON;",
        "GO",
        "",
        "SET NOCOUNT ON;",
        "SET XACT_ABORT ON;",
        "BEGIN TRANSACTION;",
        "",
        f"DELETE FROM dbo.geo_division WHERE country IN ({countries});",
        "",
    ]
    parts.extend(render_batches(rows, "mssql", MSSQL_EOL))
    parts.append("COMMIT TRANSACTION;")
    parts.append("GO")
    return MSSQL_EOL.join(parts) + MSSQL_EOL


def render_mssql_down() -> str:
    countries = seed_country_in_list("mssql")
    return MSSQL_EOL.join(
        [
            "-- 回滚本批播种数据（SQL Server）",
            f"DELETE FROM dbo.geo_division WHERE country IN ({countries});",
            "GO",
            "",
        ]
    )


def render_all(rows: list[dict]) -> dict[str, bytes]:
    return {
        "postgresql/002_seed_geo_division.up.sql": render_pg_up(rows).encode("utf-8"),
        "postgresql/002_seed_geo_division.down.sql": render_pg_down().encode("utf-8"),
        "mssql/002_seed_geo_division.up.sql": BOM + render_mssql_up(rows).encode("utf-8"),
        "mssql/002_seed_geo_division.down.sql": BOM + render_mssql_down().encode("utf-8"),
    }


def generate(rows: list[dict], out_dir: Path) -> None:
    for rel, data in render_all(rows).items():
        path = out_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def check(rows: list[dict]) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        generate(rows, tmp_dir)
        diffs = []
        for rel in render_all(rows):
            a, b = SCHEMA_DIR / rel, tmp_dir / rel
            if not a.exists():
                diffs.append(f"{rel}: 现有文件缺失")
            elif a.read_bytes() != b.read_bytes():
                diffs.append(f"{rel}: 字节不一致")
        if diffs:
            print(f"[check] 发现 {len(diffs)} 处差异：")
            for d in diffs:
                print("   ", d)
            return 1
        print("[check] 全部一致：4 个播种文件")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--check", action="store_true", help="只校验现有文件能否被复现，不写回")
    args = parser.parse_args()

    if not CN_JSON.exists() or not US_JSON.exists():
        raise SystemExit(f"缺少数据文件：{CN_JSON} 或 {US_JSON}")

    rows = load_rows()
    notes = validate(rows)
    for n in notes:
        print(f"[warn] {n}")

    if args.check:
        return check(rows)

    generate(rows, SCHEMA_DIR)
    cn_n = sum(1 for r in rows if r["country"] == "CN")
    us_n = sum(1 for r in rows if r["country"] == "US")
    ids = sum(1 for r in rows if r["code_iso"])
    print(f"[seed] 写入 {len(rows)} 行（CN {cn_n} · US {us_n} · code_iso {ids}）")
    print("[seed] postgresql/002_seed_geo_division.*.sql（LF，无 BOM）")
    print("[seed] mssql/002_seed_geo_division.*.sql（CRLF，UTF-8 with BOM）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
