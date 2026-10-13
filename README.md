# open-datasets

个人收集、整理并**可复现**的公开数据集。每个数据集一个目录，数据文件与生成脚本一起版本化 ——
改动可 diff，也能回推到上游的哪个版本产生了它。

## 数据集清单

| 数据集 | 内容 | 规模 | 上游 | 数据许可 |
|---|---|---|---|---|
| [countries](datasets/countries/) | 国家主数据（ISO/首都/区域/坐标/货币/语言等）+ 电话区号 + 准确国旗 SVG | 244 条 · 244 张 SVG | `intl-tel-input` + `countries`（npm: world-countries）+ `svg-country-flags`（`AC` 补自 flag-icons） | MIT / ODbL-1.0（详见数据集说明） |
| [cn-divisions](datasets/cn-divisions/) | 中国省/地级/区县自连表：区划代码、上级、层级、中英文名（省级）、类型 | 3345 条（34 省 + 365 地级 + 2946 区县） | GB/T 2260 + ISO 3166-2:CN + china-division 2.7.0 | 公开标准事实 / MIT（详见数据集说明） |
| [us-divisions](datasets/us-divisions/) | 美国州+县自连表：FIPS、上级、层级、中英文名/首府（州级）、类型 | 3193 条（51 州 + 3142 县） | states.source + Census national_county2020 | 公开标准事实（详见数据集说明） |

## 目录约定

```
datasets/<数据集名>/
├── README.md          数据集说明：字段字典、来源版本、许可、重建方法
├── <数据文件>          直接可读的产物（json / csv / js / png …）
├── index.html         可选，浏览器里的演示页
└── build/             生成脚本 + 锁定的上游依赖 + 回归校验
```

原则：

1. **产物入库，脚本也入库。** 使用者 clone 下来即可直接用，不必先跑构建。
2. **上游版本写死。** 依赖用精确版本锁定，上游一变产物必然变，便于用 md5 判定。
3. **`build/` 可自证。** 生成脚本带 `--check`，重跑一遍与已入库文件逐字节比对，不一致就报错。

## 直接引用

按 raw 链接取用（`main` 换成具体 tag / commit 可锁定版本）：

```
https://raw.githubusercontent.com/ShenHaoCore/open-datasets/main/datasets/countries/countries.json
https://cdn.jsdelivr.net/gh/ShenHaoCore/open-datasets@main/datasets/countries/countries.json

https://raw.githubusercontent.com/ShenHaoCore/open-datasets/main/datasets/cn-divisions/divisions.json
https://cdn.jsdelivr.net/gh/ShenHaoCore/open-datasets@main/datasets/cn-divisions/divisions.json

https://raw.githubusercontent.com/ShenHaoCore/open-datasets/main/datasets/us-divisions/divisions.json
https://cdn.jsdelivr.net/gh/ShenHaoCore/open-datasets@main/datasets/us-divisions/divisions.json
```

## 许可

- 本仓库的**生成脚本与文档**：MIT，见 [LICENSE](LICENSE)。
- 各数据集的**数据**许可**不统一**，取决于上游，见对应数据集 README 与本仓库
  [THIRD-PARTY.md](THIRD-PARTY.md)。转载或商用前请自行确认。
