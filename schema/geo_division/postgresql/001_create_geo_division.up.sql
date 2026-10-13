-- geo_division：全球行政区划自连表（PostgreSQL）
-- 主键 (country, code)；下级按 (country, parent_code) 查；国家层见 datasets/countries
--
-- 注意：PostgreSQL 侧脚本一律 UTF-8 **无 BOM** + LF（psql 按 client_encoding
-- 直传字节，BOM 会被当成语句内容）。MSSQL 侧相反，必须带 BOM，见 mssql/ 目录。

BEGIN;

CREATE TABLE IF NOT EXISTS geo_division (
    country          CHAR(2)        NOT NULL,
    code             VARCHAR(32)    NOT NULL,
    sort_key         VARCHAR(32)    NOT NULL DEFAULT '',
    code_iso         VARCHAR(16)    NULL,
    parent_code      VARCHAR(32)    NULL,
    depth            SMALLINT       NOT NULL,
    name_local       VARCHAR(128)   NOT NULL,
    name_local_short VARCHAR(64)    NOT NULL DEFAULT '',
    name_en          VARCHAR(128)   NOT NULL DEFAULT '',
    name_zh          VARCHAR(128)   NOT NULL DEFAULT '',
    type             VARCHAR(32)    NOT NULL,
    abbrev           VARCHAR(16)    NOT NULL DEFAULT '',
    status           VARCHAR(16)    NOT NULL DEFAULT 'active',
    updated_at       TIMESTAMPTZ    NOT NULL DEFAULT NOW(),

    CONSTRAINT geo_division_pk PRIMARY KEY (country, code),
    CONSTRAINT geo_division_parent_fk FOREIGN KEY (country, parent_code)
        REFERENCES geo_division (country, code),
    CONSTRAINT geo_division_depth_ck CHECK (depth >= 1),
    CONSTRAINT geo_division_parent_root_ck CHECK ((parent_code IS NULL) = (depth = 1)),
    CONSTRAINT geo_division_status_ck CHECK (status IN ('active', 'deprecated'))
);

CREATE UNIQUE INDEX IF NOT EXISTS geo_division_code_iso_uk
    ON geo_division (code_iso)
    WHERE code_iso IS NOT NULL;

CREATE INDEX IF NOT EXISTS geo_division_children_idx
    ON geo_division (country, parent_code);

CREATE INDEX IF NOT EXISTS geo_division_depth_idx
    ON geo_division (country, depth);

CREATE INDEX IF NOT EXISTS geo_division_sort_key_idx
    ON geo_division (country, sort_key);

COMMENT ON TABLE geo_division IS '全球行政区划自连表；联动 country + parent_code；国家见 countries';

COMMENT ON COLUMN geo_division.country IS 'ISO 3166-1 alpha-2，如 CN、US';
COMMENT ON COLUMN geo_division.code IS '国内区划代码，同国内唯一';
COMMENT ON COLUMN geo_division.sort_key IS '国别排序键（定长补齐等）；不保证唯一';
COMMENT ON COLUMN geo_division.code_iso IS 'ISO 3166-2；无则为 NULL';
COMMENT ON COLUMN geo_division.parent_code IS '上级 code；一级为 NULL';
COMMENT ON COLUMN geo_division.depth IS '树深度：根=1，子=父+1';
COMMENT ON COLUMN geo_division.name_local IS '当地名称（主展示）';
COMMENT ON COLUMN geo_division.name_local_short IS '当地简称';
COMMENT ON COLUMN geo_division.name_en IS '英文译名；同当地名则空';
COMMENT ON COLUMN geo_division.name_zh IS '中文译名；同当地名则空';
COMMENT ON COLUMN geo_division.type IS '类型机读值（国别口径）';
COMMENT ON COLUMN geo_division.abbrev IS '缩写，如美国州 USPS';
COMMENT ON COLUMN geo_division.status IS 'active / deprecated';
COMMENT ON COLUMN geo_division.updated_at IS '更新时间';

COMMIT;
