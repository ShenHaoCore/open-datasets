# countries

国家/地区主数据：**ISO 码、中英文名、首都、大洲/地区、经纬度、面积、货币、语言、
域名后缀、邻国、独立/联合国/内陆属性 + 国际电话区号 + 准确国旗 SVG**。

244 条国家/地区、244 张本地 SVG 国旗。列表与区号口径对齐 `intl-tel-input` /
libphonenumber；地理与行政主数据来自 [countries](https://github.com/mledoze/countries)
（npm 包名 `world-countries`）。

国旗为**准确比例的本地 SVG**，不依赖 Regional Indicator emoji —— Windows 不把 `🇨🇳`
渲染成旗帜，emoji 只能当补充字段。

## 文件清单

| 文件 | 说明 |
|---|---|
| `countries.json` | 主数据，244 条，UTF-8（无 BOM），CRLF，2 空格缩进 |
| `countries.csv` | 扁平表格版，UTF-8 **含 BOM**（Excel 直接打开不乱码） |
| `countries.js` | `window.COUNTRIES = [...]`，浏览器 `<script src>` 直接引 |
| `flags/<iso2>.svg` | 逐国国旗矢量图（244 张） |
| `index.html` / `app.js` | 演示页：带搜索的国家选择器（区号 + 国旗 + 键盘操作） |
| `build/` | 生成脚本、锁定的上游依赖、回归校验 |

## 字段字典

`countries.json` / `countries.js` 每条记录的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `iso2` | string | ISO 3166-1 alpha-2，大写。含少量非正式码，见下 |
| `iso3` | string | ISO 3166-1 alpha-3。**`AC` 为空串**（无 countries 档案） |
| `ccn3` | string | ISO 3166-1 数字码，如 `156`；无档案为空串 |
| `name_zh` | string | 中文常用名，如 `中国`、`中国香港` |
| `name_en` | string | 英文常用名（选择器用），如 `China` |
| `name_en_official` | string | 英文官方全称（countries 上游）；无档案为空串 |
| `capital` | string | 首个首都名；无则为空串 |
| `capitals` | array | 全部首都（极少国家有多个） |
| `region` | string | 大洲/区域，如 `Asia` |
| `subregion` | string | 次区域，如 `Eastern Asia` |
| `lat` / `lng` | number \| null | 大致中心坐标 |
| `area` | number \| null | 面积（km²） |
| `tld` | array | 顶级域名后缀，如 `[".cn",".中国"]` |
| `currencies` | object | `{ "CNY": { "name": "Chinese yuan", "symbol": "¥" } }` |
| `languages` | object | `{ "zho": "Chinese" }`（键为 ISO 639-3 风格码） |
| `borders` | array | 陆地邻国 ISO3 列表 |
| `independent` | boolean \| null | 是否独立国家 |
| `un_member` | boolean \| null | 是否联合国会员 |
| `landlocked` | boolean \| null | 是否内陆国 |
| `status` | string | 上游状态，如 `officially-assigned` |
| `dial_code` | string | 国际电话区号，**不含 `+`**，如 `86` |
| `phone_prefix` | string | `"+" + dial_code`，如 `+86` |
| `priority` | number | 选择器排序权重；非 0 共 38 条 |
| `area_codes` | array \| null | 共享区号时的内部区号；非空 36 条 |
| `flag_emoji` | string | 区域指示符 emoji；无 ISO 档案时为空串 |
| `flag_file` | string | 如 `flags/cn.svg`；无图时为空串 |
| `has_flag` | boolean | 是否有国旗 SVG。本数据集 244 条**全部为 `true`** |

主数据档案覆盖 **243/244**（仅 `AC` 阿森松岛不在 countries 上游；电话与国旗仍完整）。

## 容易踩的语义

1. **共享区号不能拼字符串。** 244 条只对应 **206 个不同区号**：`+1` 被 25 个国家和地区共用等。
   要区分须用 `area_codes`。**直接 `dial_code + number` 会算出假值。**
2. **`priority` 只给选择器用**，不是区号位数或国家规模。
3. **`name_en` 与 `name_en_official` 不同。** 前者偏 UI 短名（含本仓库命名覆盖），后者是
   countries 上游官方全称。
4. **货币 / 语言是对象不是字符串。** CSV 里压成 `CNY`、`zho` 这类用 `|` 连接的代码列表。
5. **本版不含时区。** countries 上游 5.1.0（npm `world-countries`）未提供 timezones 字段。

## 国旗图

准确矢量，主要来自 `svg-country-flags`。用法：

```html
<img src="flags/cn.svg" width="20" height="15" alt="中国">
```

SVG 带各国法定宽高比，**不要假设统一尺寸**；UI 请用容器 + `object-fit: contain`。

例外：`AC` 取自 [flag-icons](https://github.com/lipis/flag-icons) 7.5.0 的 `sh-ac.svg`
（该项目 4:3 展示用），见 `build/overrides/flags/ac.svg`。

旧版 PNG 雪碧图已移除。

## 数据来源与版本

| 上游 | 版本 | 用途 |
|---|---|---|
| [intl-tel-input](https://github.com/jackocnr/intl-tel-input) | 23.0.4 | 列表顺序、区号、`priority`、`area_codes`、中英文常用名 |
| [countries](https://github.com/mledoze/countries)（npm: `world-countries`） | 5.1.0 | ISO3/数字码、首都、区域、坐标、面积、货币、语言、TLD、邻国、独立/UN/内陆等 |
| [svg-country-flags](https://github.com/hampusborgos/country-flags) | 1.2.10 | 准确国旗 SVG（除 `AC`） |
| [flag-icons](https://github.com/lipis/flag-icons) | 7.5.0 | 仅 `AC`：`sh-ac.svg` → overrides |

- 记录顺序即 `intl-tel-input` 原生顺序，未做二次排序。
- 常用名取自 intl-tel-input i18n；官方英文全称取自 countries 上游。
- `build/package.json` 用精确版本锁定。

### 命名口径（6 条显式覆盖）

写在 `build/generate.py` 的 `NAME_OVERRIDES`，**不是手工改产物**：

| ISO2 | 上游 | 本数据集 | 原因 |
|---|---|---|---|
| `HK` | en `Hong Kong SAR China` / zh `中国香港特别行政区` | `Hong Kong, China` / `中国香港` | 中国官方口径并精简 |
| `MO` | en `Macao SAR China` / zh `中国澳门特别行政区` | `Macao, China` / `中国澳门` | 同上 |
| `TW` | en `Taiwan` / zh `台湾` | `Taiwan, China` / `中国台湾` | 同上 |
| `BQ` | zh `荷属加勒比区` | `荷兰加勒比区` | 更通行译名 |
| `AC` | 两表均无 | `Ascension Island` / `阿森松岛` | 上游缺名 |
| `XK` | 两表均无 | `Kosovo` / `科索沃` | 上游缺名 |

## 重建

依赖：Node.js ≥18、Python ≥3.10。

```bash
cd datasets/countries
./build/build.sh            # 重建并写回本目录
./build/build.sh --check    # 只校验：重跑一遍与已入库文件逐字节比对
```

`--check`：244 张 SVG + `countries.*` 与入库版本逐字节一致。SVG 原样拷贝、不改换行。

补丁国旗：`build/overrides/flags/<iso2>.svg`（优先于 npm 包）。

## 用法

```python
import json
countries = json.load(open("countries.json", encoding="utf-8"))
by_iso2 = {c["iso2"]: c for c in countries}
cn = by_iso2["CN"]
cn["capital"], cn["currencies"], cn["phone_prefix"]  # Beijing / {CNY:...} / +86
```

```js
// <script src="countries.js"></script>
const cn = COUNTRIES.find(c => c.iso2 === 'CN');
cn.flag_file;                 // 'flags/cn.svg'
Object.keys(cn.currencies);   // ['CNY']
```

## 已知缺口

- **没有时区字段**（上游 5.1.0 不含）。
- **没有号码长度校验**；校验请接 libphonenumber。
- **`area_codes` 只覆盖 36 条**，主要是 NANP 等共享区号场景。
- **`AC` 无主数据档案**（`iso3`/首都/货币等为空）；电话与国旗齐全。
- **首都等专名未做中文翻译**（保持上游英文）。

## 许可与署名

- 主数据与名称：`intl-tel-input`（MIT）+ [countries](https://github.com/mledoze/countries)（**ODbL-1.0**）。
- 国旗：`svg-country-flags`（多为公有领域）+ `AC` 来自 flag-icons（MIT）。
- ODbL 要求署名。演示页已内置：*Data derived from countries / world-countries (ODbL-1.0) and
  intl-tel-input (MIT); flags from svg-country-flags and flag-icons (AC).*
- 本目录生成脚本与文档：MIT。
