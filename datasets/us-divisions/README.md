# us-divisions

美国**州 + 县**自连表：**51 州/特区** + **3142 县级等价单位**，共 **3193** 条。

字段与 [cn-divisions](../cn-divisions/) **对齐**（同一套 `parent_code` 联动）；另含 `usps`、州级首府。
哥伦比亚特区只保留州级一行。记录按 `code6` 升序。不含海外领地与市（place）。

## 与 cn-divisions 共用联动

```js
const roots = rows => rows.filter(r => r.parent_code === '');
const kids  = (rows, code) => rows.filter(r => r.parent_code === code);

roots(US_DIVISIONS);          // 51 州
kids(US_DIVISIONS, '06');     // 加州各县
kids(US_DIVISIONS, '11');     // [] 特区无县

roots(CN_DIVISIONS);          // 34 省
kids(CN_DIVISIONS, '44');     // 广东地级
```

展示名：`name_zh || name_en`。

## 文件清单

| 文件 | 说明 |
|---|---|
| `divisions.json` | 主数据，3193 条，UTF-8（无 BOM），CRLF，**每条记录一行** |
| `divisions.csv` | 同上的表格版，UTF-8 **含 BOM**，13 列 |
| `divisions.js` | `window.US_DIVISIONS = [...]` |
| `build/` | 州事实源、Census 县级码表、生成脚本、回归校验 |

## 字段字典

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | string | FIPS：州 2 位；县 5 位 |
| `code6` | string | 定长键：州补 `0000`，县补 `0` |
| `parent_code` | string | 上级 `code`；州级为空串 |
| `level` | string | `state` / `county` |
| `name_zh` | string | 中文名（**仅州级**；县级为空串） |
| `name_zh_short` | string | 中文简称（仅州级） |
| `name_en` | string | 英文名 |
| `iso3166_2` | string | 如 `US-CA`（仅州级） |
| `type` | string | 行政类型 |
| `type_zh` | string | 类型中文名 |
| `usps` | string | 两位邮政缩写（仅州级；cn 无此字段） |
| `capital_zh` | string | 首府中文（仅州级；县级为空串） |
| `capital_en` | string | 首府英文（仅州级） |

### 数量

| level | 数量 |
|---|---|
| `state`（含 1 个 `district`） | **51** |
| `county`（含 parish / borough / 独立市等） | **3142** |

## 容易踩的语义

1. **`code` 不是 USPS。** `06` 是 FIPS，加州缩写在 `usps=CA`。
2. **特区无县级子节点。**
3. **路易斯安那 Parish、阿拉斯加 Borough/Census Area、弗吉尼亚独立市** 都是 `level=county`。
4. **县级无中文名、无首府字段值。**

## 数据来源

| 来源 | 用途 |
|---|---|
| `build/states.source.json` | 51 州/特区（含首府） |
| `build/national_county2020.txt` | Census 2020 县级 FIPS 与英文名 |

## 重建

```bash
cd datasets/us-divisions
./build/build.sh
./build/build.sh --check
```

## 许可与署名

- 州级公开标准事实 + 通行中文译名；县级为 Census 公开码表整理（公有领域）。
- 生成脚本与文档：MIT。
