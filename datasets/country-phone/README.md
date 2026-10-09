# country-phone

国家/地区电话区号数据集：**中英文名 + ISO 3166 码 + 国际电话区号 + 国旗图标**，
244 条国家/地区、263 张本地 PNG 国旗。

数据口径与 `intl-tel-input` / libphonenumber 一致。国旗一律为**本地图片**，不依赖
Regional Indicator emoji —— Windows 不把 `🇨🇳` 渲染成旗帜，emoji 只能当补充字段。

## 文件清单

| 文件 | 说明 |
|---|---|
| `countries.json` | 主数据，244 条，UTF-8（无 BOM），CRLF，2 空格缩进 |
| `countries.csv` | 同上的表格版，UTF-8 **含 BOM**（Excel 直接打开不乱码），7 列 |
| `countries.js` | `window.COUNTRIES = [...]`，浏览器 `<script src>` 直接引 |
| `flags/<iso2>.png` | 逐国国旗，2 倍图（宽 26–40px、高 16–30px，见下） |
| `flags.png` | 国旗雪碧图，1x，5762×15 |
| `flags@2x.png` | 国旗雪碧图，2x，11524×30 |
| `flags.css` | 雪碧图定位规则，与上面两张图配套 |
| `index.html` | 演示页：带搜索的国家选择器（区号 + 国旗 + 键盘操作） |
| `build/` | 生成脚本、锁定的上游依赖、回归校验 |

## 字段字典

`countries.json` / `countries.js` 每条记录的字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `iso2` | string | ISO 3166-1 alpha-2，大写。含少量非正式码，见下 |
| `iso3` | string | ISO 3166-1 alpha-3，大写。**`AC` 为空串**（非 ISO 正式条目） |
| `name_zh` | string | 中文名，如 `中国`、`中国香港` |
| `name_en` | string | 英文名，如 `China`、`Hong Kong, China` |
| `dial_code` | string | 国际电话区号，**不含 `+`**，如 `86`、`852` |
| `phone_prefix` | string | 展示用前缀 = `"+" + dial_code`，如 `+86` |
| `priority` | number | 排序权重，0 表示普通项；非 0 共 38 条，最大 24 |
| `area_codes` | array \| null | 共享区号时的内部区号，如美国 `["201","202",…]`；非空 36 条 |
| `flag_emoji` | string | 区域指示符 emoji。**`AC` 为空串**（无 ISO 正式码，故不给） |
| `flag_file` | string | 相对数据集根目录的国旗路径，如 `flags/cn.png` |
| `has_flag` | boolean | 是否有国旗图。本数据集 244 条**全部为 `true`** |

`countries.csv` 是同一份数据的**扁平子集**（7 列，不含 `priority` / `area_codes` / `has_flag`）：
`国家/地区(中文)`、`Country/Region`、`ISO2`、`ISO3`、`电话区号`、`国旗文件`、`国旗emoji`。
含逗号的值按 RFC 4180 加引号（如 `"Hong Kong, China"`）。

## 三个容易踩的语义

1. **共享区号不能拼字符串。** 244 条只对应 **206 个不同区号**：`+1` 一条被 25 个国家和地区共用，
   `+44` 4 条、`+61` 3 条、`+590` 3 条，共 11 组、49 条。想区分要另加 `area_codes`
   （如 `+1` 下 `["201"]` 是美属萨摩亚）。**直接 `dial_code + number` 会算出 `+1201` 这种假值。**
2. **`priority` 是给选择器排序用的，不是区号位数或国家规模。** 它来自上游的「常用国家」标记，
   仅 38 条非 0；做下拉框「常用在前」时按它降序排，其余按名称排。
3. **`flag_emoji` 与 `flag_file` 是互补关系而非等价。** emoji 只在有 ISO 正式码时给出，
   且 Windows 下不渲染成旗帜；真正可靠的是 `flags/<iso2>.png`。

## 国旗图

两种用法，按场景选：

```html
<!-- A. 逐张 PNG：简单直接，适合列表 -->
<img src="flags/cn.png" width="20" alt="中国">

<!-- B. 雪碧图 + CSS：一次请求拿全部 263 张，适合长列表 -->
<link rel="stylesheet" href="flags.css">
<span class="iti-flag iti-flag-cn"></span>
```

雪碧图里的国旗**不是等宽等高的**：宽度默认 20px，另有 13 / 15 / 18 / 19px 的例外；
高度按 10 / 11 / 12 / 13 / 14 / 15px 分档；旗间水平间距 2px。
`flags/<iso2>.png` 是从 2 倍图按同一套参数切出来的，因此共 11 种尺寸（宽 26–40、高 16–30），
**不要假设统一尺寸去写 `width`/`height`**，用容器约束或 `object-fit`。

263 张国旗比 244 条数据多 19 张，多出的是上游雪碧图自带、但本数据集不收录为「国家/地区」的条目：
`aq bv cp cq dg ea eu ez fx gs hm ic pn su ta tf uk um un`（南极洲、法属南部领地、欧盟、苏联、
联合国及若干属地/飞地）。

## 数据来源与版本

| 上游 | 版本 | 用途 |
|---|---|---|
| [intl-tel-input](https://github.com/jackocnr/intl-tel-input) | 23.0.4 | 国家与区号数据、`priority`、`area_codes`、国旗雪碧图、中英文名称表 |
| [world-countries](https://github.com/mledoze/countries) | 5.1.0 | `iso3`、是否给 `flag_emoji` 的成员资格判定 |

- 记录**顺序即上游 `intl-tel-input` 的原生顺序**（按英文名的字母序，`Åland Islands` 排在
  `Zimbabwe` 之后），未做二次排序。
- 名称取自 `intl-tel-input` 自带的 `i18n/{en,zh}/countries.js`，非 world-countries。
- 上游一条数据缺失即会导致产物变化，故 `build/package.json` 用**精确版本**锁定。

### 命名口径（6 条显式覆盖）

上游名称与本地口径有 6 处不同，全部写在 `build/generate.py` 的 `NAME_OVERRIDES`
里，**不是手工改产物**：

| ISO2 | 上游 | 本数据集 | 原因 |
|---|---|---|---|
| `HK` | en `Hong Kong SAR China` / zh `中国香港特别行政区` | `Hong Kong, China` / `中国香港` | 统一为中国官方口径并精简 |
| `MO` | en `Macao SAR China` / zh `中国澳门特别行政区` | `Macao, China` / `中国澳门` | 同上 |
| `TW` | en `Taiwan` / zh `台湾` | `Taiwan, China` / `中国台湾` | 同上 |
| `BQ` | zh `荷属加勒比区` | `荷兰加勒比区` | 取更通行的译名 |
| `AC` | 两表均无 | `Ascension Island` / `阿森松岛` | 上游缺名，必须补 |
| `XK` | 两表均无 | `Kosovo` / `科索沃` | 上游缺名，必须补 |

## 重建

依赖：Node.js ≥18、Python ≥3.10 且装有 Pillow。

```bash
cd datasets/country-phone
./build/build.sh            # 重建并写回本目录
./build/build.sh --check    # 只校验：重跑一遍与已入库文件逐字节比对
```

`--check` 是目前最强的回归手段：重跑生成脚本，**269 个产物（263 张国旗 + `countries.*` +
`flags.css` + 两张精灵图）与入库版本逐字节一致**，包括 PNG。这依赖两件事，改动时别丢：

- 上游依赖用精确版本（`build/package.json`）；
- 切片统一用 `optimize=True` 存 PNG（等价 `compress_level=9`），已在 `generate.py` 注释说明。

上游升级后 `--check` 会报差异，此时看 diff 决定是否接受新数据，并把版本号写回
`build/package.json` 与本 README。

## 用法

```python
import json
countries = json.load(open("countries.json", encoding="utf-8"))
by_iso2 = {c["iso2"]: c for c in countries}
by_iso2["CN"]           # {'iso2': 'CN', 'phone_prefix': '+86', ...}

# 常用国家排在前面
hot = sorted(countries, key=lambda c: (-c["priority"], c["name_en"]))[:10]
```

```js
// <script src="countries.js"></script>
const cn = COUNTRIES.find(c => c.iso2 === 'CN');
`${cn.flag_file}`                       // 'flags/cn.png'
COUNTRIES.filter(c => c.name_zh.includes('新加坡'));
```

## 已知缺口

- **只有主区号，没有号码长度校验规则。** 想按国家校验手机号格式需另接 libphonenumber，
  本数据集不含 `possibleLengths` 之类元数据。
- **`area_codes` 只覆盖 36 条**，且是上游的口径（主要用于北美 NANP 与少数共享区号地区），
  不等价于完整的「国家内区号表」。
- **`AC` 的 `iso3` 与 `flag_emoji` 为空串**，这是刻意的 —— 它没有 ISO 3166-1 正式码，
  硬编一个假码比留空更误导。

## 许可与署名

- 数据部分：`intl-tel-input`（MIT）+ `world-countries`（**ODbL-1.0**）。
- ODbL-1.0 要求署名，使用时请注明来源：*Data derived from world-countries (ODbL-1.0)
  and intl-tel-input (MIT).* 演示页 `index.html` 已内置该署名。
- 本目录的生成脚本与文档：MIT。
