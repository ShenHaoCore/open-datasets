# cn-divisions

中国**省 / 地级 / 区县**自连表：**34 省级** + **365 地级** + **2946 区县**，共 **3345** 条。
用 `parent_code` 挂上级；直辖市只保留省级一行，其下区县**直接挂省级 code**。

省级口径对齐 `GB/T 2260` 与 `ISO 3166-2:CN`；地级与区县来自
[Administrative-divisions-of-China](https://github.com/modood/Administrative-divisions-of-China)
（npm: `china-division`）**2.7.0**。记录按 `code6` 升序。

## 文件清单

| 文件 | 说明 |
|---|---|
| `divisions.json` | 主数据，3345 条，UTF-8（无 BOM），CRLF，**每条记录一行** |
| `divisions.csv` | 同上的表格版，UTF-8 **含 BOM**，10 列 |
| `divisions.js` | `window.CN_DIVISIONS = [...]`，浏览器 `<script src>` 直接引 |
| `build/` | 省级事实源、上游抽取、生成脚本、回归校验 |

## 字段字典

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | 区划代码：省 2 位、地级 4 位、区县/省直辖县级 6 位 |
| `code6` | string | 六位代码（2 位补 `0000`，4 位补 `00`） |
| `parent_code` | string | 上级 `code`；省级为空串 |
| `level` | string | `province` / `city` / `county` |
| `name_zh` | string | 中文全称 |
| `name_zh_short` | string | 简称 |
| `name_en` | string | 英文名（仅省级有值；其余为空串） |
| `iso3166_2` | string | ISO 3166-2:CN（仅省级有值；其余为空串） |
| `type` | string | 行政类型，见下 |
| `type_zh` | string | 类型中文名 |

### `level` + 数量

| level | 含义 | 数量 |
|---|---|---|
| `province` | 省 / 直辖市 / 自治区 / 特别行政区 | **34** |
| `city` | 地级市 / 自治州 / 地区 / 盟 / 省直辖县级 | **365** |
| `county` | 市辖区 / 县 / 县级市 / 旗 等 | **2946** |

## 容易踩的语义

1. **直辖市无市级行。** `level=city` 且 `parent_code==='11'` 为空；区县直接 `parent_code==='11'`（如东城区）。联动：选省后跳过市，或用 `parent_code===省code` 取区。
2. **拼地址不必对直辖市去重市名**——表里没有第二份「北京市」。
3. **省直辖县级（济源、仙桃等）是 `level=city`**，一般不再有下级区县。
4. **`code` 位数不统一。** 统一键请用 `code6`。
5. **港澳台只有省级行**，不含其下市县。

## 数据来源

| 来源 | 版本 | 用途 |
|---|---|---|
| `build/provinces.source.json` | — | 34 省级：代码、ISO、中英文名、类型 |
| [china-division](https://github.com/modood/Administrative-divisions-of-China) | 2.7.0 | 地级、区县；省直辖县级展开 |

编辑决策（丢弃直辖市地级占位、区县改挂省码、展开直辖县级）在 `build/generate.py`。

## 重建

依赖：Node.js ≥18、Python ≥3.10。

```bash
cd datasets/cn-divisions
./build/build.sh
./build/build.sh --check
```

Windows 分步：

```bash
cd datasets/cn-divisions/build
npm install
node extract-upstream.mjs
python generate.py
python generate.py --check
```

## 用法

与 [us-divisions](../us-divisions/) 字段对齐，联动同一写法：

```js
const roots = rows => rows.filter(r => r.parent_code === '');
const kids  = (rows, code) => rows.filter(r => r.parent_code === code);

roots(CN_DIVISIONS);        // 34 省
kids(CN_DIVISIONS, '44');   // 广东地级
kids(CN_DIVISIONS, '4401'); // 广州区县
kids(CN_DIVISIONS, '11');   // 北京区县（无市级中间层）
```

```python
import json
rows = json.load(open("divisions.json", encoding="utf-8"))
kids = lambda code: [r for r in rows if r["parent_code"] == code]
```

## 已知缺口

- **没有乡镇 / 街道 / 村居。**
- **地级与区县无英文名。**
- **港澳台市县未收录。**

## 许可与署名

- 省级为公开标准事实整理；地级 / 区县上游 **MIT**（china-division / modood）。
- 本目录生成脚本与文档：MIT。
