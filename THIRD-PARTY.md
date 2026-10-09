# 第三方来源与许可

本仓库的数据集都是对上游公开数据的整理与再加工。**数据部分的许可随上游，不随本仓库。**
转载、再分发或商用前，请按下列条款确认。

## country-phone

| 上游 | 版本 | 用到的部分 | 许可 |
|---|---|---|---|
| [intl-tel-input](https://github.com/jackocnr/intl-tel-input) | 23.0.4 | 区号、`priority`、`area_codes`、国旗图标与雪碧图、中英文名称表 | MIT |
| [world-countries](https://github.com/mledoze/countries) | 5.1.0 | ISO 3166-1 alpha-3 码、成员资格 | ODbL-1.0 |

- **ODbL-1.0 的署名要求**：使用本数据集时需注明数据来源为 world-countries（ODbL-1.0）。
  数据集 README 与演示页均已给出署名，二次分发时请保留。
- **国旗图标**随 intl-tel-input 以 MIT 分发。图标本身的上游版权状态见该项目说明。
- 本数据集对上游内容做了命名口径调整（港澳台按中国官方口径标注），并在
  `build/generate.py` 中显式列出，详见数据集 README。

## 新增数据集时

在本文件追加一节，写明上游名称、版本、许可与署名要求。仓库级的 MIT 只覆盖脚本与文档。
