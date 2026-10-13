# geo_division

全球行政区划**自连表**的数据库迁移（MSSQL / PostgreSQL）。

逻辑模型：主键 `(country, code)`；下级用同国的 `parent_code` 指向上级 `code`，
一级行政区的 `parent_code` 为 `NULL`（外键因此可用）。国家主数据仍用
`datasets/countries`，本表从各国一级行政区起（`depth = 1` 且 `parent_code` 为 `NULL`）。

## 文件

| 文件 | 说明 |
|---|---|
| `postgresql/001_create_geo_division.up.sql` | PostgreSQL 建表 |
| `postgresql/001_create_geo_division.down.sql` | PostgreSQL 回滚建表 |
| `postgresql/002_seed_geo_division.up.sql` | PostgreSQL 播种 CN+US |
| `postgresql/002_seed_geo_division.down.sql` | PostgreSQL 回滚播种 |
| `mssql/001_create_geo_division.up.sql` | SQL Server 建表 |
| `mssql/001_create_geo_division.down.sql` | SQL Server 回滚建表 |
| `mssql/002_seed_geo_division.up.sql` | SQL Server 播种 CN+US |
| `mssql/002_seed_geo_division.down.sql` | SQL Server 回滚播种 |
| `build/generate_seed.py` | 从 datasets 重新生成播种 SQL（带 `--check`） |

## 应用

```bash
# PostgreSQL
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f schema/geo_division/postgresql/001_create_geo_division.up.sql
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f schema/geo_division/postgresql/002_seed_geo_division.up.sql

# SQL Server（sqlcmd）
sqlcmd -S localhost -d your_db -E -b -i schema/geo_division/mssql/001_create_geo_division.up.sql
sqlcmd -S localhost -d your_db -E -b -i schema/geo_division/mssql/002_seed_geo_division.up.sql
```

播种是**幂等**的：先按 `country IN ('CN','US')` 删掉本批数据再整批重插。
因为主键是自然键 `(country, code)`，重播种不会产生代理键漂移，下游外键不受影响。

### SQL Server 侧两个必读的坑

1. **脚本必须带 UTF-8 BOM。** ODBC 版 `sqlcmd` 用 `-i` 读文件时按**系统 ACP** 解码，
   不带 BOM 的 UTF-8 中文会被静默丢弃 —— 表现为 exit 0、无任何消息、零落库。
   实测：同一份播种文件，非 ASCII 换成 `x` 或存成带 BOM，都能正常写入；
   不带 BOM 则一行都不进。手工改这些文件时请保持 BOM（`.gitattributes` 已为
   `schema/geo_division/mssql/*.sql` 单独放行 EOL；BOM 属于文件内容，不会被归一化）。
2. **表上有过滤索引，DML 要求 `SET QUOTED_IDENTIFIER ON`。**
   `UQ_geo_division_code_iso` 是带 `WHERE code_iso IS NOT NULL` 的过滤唯一索引，
   建它和之后任何 INSERT/UPDATE/DELETE 都要求 `QUOTED_IDENTIFIER`/`ANSI_NULLS` 为 ON，
   而 sqlcmd 默认 OFF。迁移脚本首行已自行打开；**用 sqlcmd 手工做 DML 时要加 `-I`**。
   （SSMS、ADO.NET、ODBC 默认 ON，只有 sqlcmd/osql 是 OFF。）

## 字段

| 字段 | 类型 | 可空 | 说明 |
|---|---|---|---|
| `country` | `CHAR(2)` | 否 | ISO 3166-1 alpha-2，如 `CN`、`US` |
| `code` | `VARCHAR(32)` | 否 | 国内区划代码，同一国家内唯一 |
| `sort_key` | `VARCHAR(32)` | 否 | **国别排序键**（定长补齐等）；**不保证唯一**；空串表示无排序需求 |
| `code_iso` | `VARCHAR(16)` | 是 | ISO 3166-2；**全局唯一**（部分唯一索引）；无则为 `NULL` |
| `parent_code` | `VARCHAR(32)` | 是 | 同国上级 `code`；一级为 `NULL` |
| `depth` | `SMALLINT` | 否 | 树深度：根=`1`，子=`父 depth + 1`（直辖市区县多为 `2`） |
| `name_local` | `VARCHAR(128)` | 否 | 当地官方名（主展示名） |
| `name_local_short` | `VARCHAR(64)` | 否 | 当地简称 |
| `name_en` | `VARCHAR(128)` | 否 | 英文**译名**；与当地名相同时留空 |
| `name_zh` | `VARCHAR(128)` | 否 | 中文**译名**；与当地名相同时留空 |
| `type` | `VARCHAR(32)` | 否 | 行政类型机读值；**国别口径**（`province` / `municipality` / `district`…） |
| `abbrev` | `VARCHAR(16)` | 否 | 国别缩写；美国州为 USPS，如 `CA` |
| `status` | `VARCHAR(16)` | 否 | `active` / `deprecated` |
| `updated_at` | 时间戳 | 否 | 行最后更新时间 |

名称展示：

```sql
-- 中文界面
COALESCE(NULLIF(name_zh, ''), name_local)
-- 英文界面
COALESCE(NULLIF(name_en, ''), name_local)
```

播种约定：CN 当地名即中文 → 只填 `name_local*`，`name_zh` 空；
US 当地名即英文 → 只填 `name_local`，`name_en` 空，州级中文进 `name_zh`（优先简称如「加州」）。

## 层级与容易踩的语义

1. **`depth` 是树深度，不是行政大档。** 直辖市区县 `depth=2`，普通省市区 `depth=3`；
   「是省还是区」看 `type`，不要用 `depth` 当省/市/县。
2. **`sort_key` 不是唯一键。** 唯一键是 `(country, code)`。CN/US 播种时由数据集
   `code6` 映射而来；别国可自定补齐规则，或留空。
3. **`type` 是细分类机读值。** CN 如 `municipality`、`province`、`district`；
   US 如 `state`、`parish`。解读必须带 `country`（两边都有 `district` 等词）。
   中文标签用应用侧小字典，或看 `cn-divisions` / `us-divisions` 的 `type_zh`，不入库。
4. **叶子**用「是否存在 `parent_code = 本行 code` 的子行」判断，不要固化 `is_leaf` 列。
5. **`abbrev` 目前主要是美国州。** 首府不入库：US 首府是城市名，对本表州/县层对不齐；
   需要时再加可空 `capital_code` 外键。

## 从本仓库导入的口径

- `cn-divisions` → `country='CN'`；`code6`→`sort_key`；`depth` 由 `parent_code` 算出；`type` 原样落入（`type_zh` 不入库）
- `us-divisions` → `country='US'`；同上（`level` / `type_zh` / `capital_*` 不入库）

## 重建与自证

```bash
python schema/geo_division/build/generate_seed.py          # 重新生成播种 SQL
python schema/geo_division/build/generate_seed.py --check  # 与已入库文件逐字节比对
```
