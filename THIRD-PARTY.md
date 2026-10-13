# 第三方来源与许可

本仓库的数据集都是对上游公开数据的整理与再加工。**数据部分的许可随上游，不随本仓库。**
转载、再分发或商用前，请按下列条款确认。

## countries

| 上游 | 版本 | 用到的部分 | 许可 |
|---|---|---|---|
| [intl-tel-input](https://github.com/jackocnr/intl-tel-input) | 23.0.4 | 列表顺序、区号、`priority`、`area_codes`、中英文常用名 | MIT |
| [countries](https://github.com/mledoze/countries)（npm: `world-countries`） | 5.1.0 | ISO3/数字码、首都、区域、坐标、面积、货币、语言、TLD、邻国、独立/UN/内陆等 | ODbL-1.0 |
| [svg-country-flags](https://github.com/hampusborgos/country-flags) | 1.2.10 | 准确国旗 SVG（除 `AC`） | 旗帜多为公有领域（见该项目说明） |
| [flag-icons](https://github.com/lipis/flag-icons) | 7.5.0 | 仅 `AC`（源文件 `sh-ac.svg`） | MIT |

- **ODbL-1.0 的署名要求**：使用本数据集时需注明数据来源为 countries / world-countries（ODbL-1.0）。
  数据集 README 与演示页均已给出署名，二次分发时请保留。
- **国旗 SVG** 主要来自 svg-country-flags；`AC` 来自 flag-icons（MIT）。旗帜图案本身多为
  公有领域，但各国对官方标志的 **使用方式**仍可能另有限制，商用展示前请自行确认。
- 本数据集对上游内容做了命名口径调整（港澳台按中国官方口径标注），并在
  `build/generate.py` 中显式列出，详见数据集 README。

## cn-divisions

| 来源 | 版本 | 用到的部分 | 许可 |
|---|---|---|---|
| GB/T 2260 + ISO 3166-2:CN（整理于 `provinces.source.json`） | — | 34 省级代码、中英文名、ISO | 公开标准事实 |
| [Administrative-divisions-of-China](https://github.com/modood/Administrative-divisions-of-China)（npm: `china-division`） | 2.7.0 | 地级、区县；省/自治区直辖县级展开 | MIT |

- 直辖市只保留省级一行，区县直接挂省码；丢弃地级「市辖区/县」占位；展开直辖县级。见 `datasets/cn-divisions/build/generate.py`。
- 本数据集的生成脚本与文档：MIT。

## us-divisions

| 来源 | 版本 | 用到的部分 | 许可 |
|---|---|---|---|
| FIPS / USPS / ISO 3166-2:US（整理于 `states.source.json`） | — | 51 州/特区 FIPS、USPS、中英文名、首府 | 公开标准事实 |
| [national_county2020.txt](https://www2.census.gov/geo/docs/reference/codes2020/national_county2020.txt)（U.S. Census Bureau） | 2020 | 县级 FIPS、英文名、县等价单位 | 美国政府公有领域作品 |

- 中文州名 / 首府名为通行译名整理，非美国官方中文。
- 仅保留 50 州 + DC 下的县；丢弃 DC 的 `11001` 重复行；不含海外领地。
- 县级中文名本版未收录。见 `datasets/us-divisions/build/generate.py`。
- 本数据集的生成脚本与文档：MIT。

## 新增数据集时

在本文件追加一节，写明上游名称、版本、许可与署名要求。仓库级的 MIT 只覆盖脚本与文档。
