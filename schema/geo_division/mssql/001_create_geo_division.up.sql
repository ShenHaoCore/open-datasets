-- geo_division：全球行政区划自连表（SQL Server）
-- 主键 (country, code)；下级按 (country, parent_code) 查；国家层见 datasets/countries
--
-- 两个 sqlcmd 相关的坑，改本文件前务必先读：
--   1. 本表带**过滤索引**（UQ_geo_division_code_iso），建它与之后任何 DML 都要求
--      SET QUOTED_IDENTIFIER ON / ANSI_NULLS ON。ODBC 版 sqlcmd 默认 OFF，
--      所以脚本自己打开；手工用 sqlcmd 做 INSERT/UPDATE/DELETE 时也要加 -I。
--   2. 播种脚本 002 含中文，**必须存成 UTF-8 with BOM**，否则 sqlcmd 按系统 ACP
--      解码后静默丢弃整批（exit 0、无消息、零落库）。

SET QUOTED_IDENTIFIER ON;
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
GO

SET NOCOUNT ON;
SET XACT_ABORT ON;
BEGIN TRANSACTION;

IF OBJECT_ID(N'dbo.geo_division', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.geo_division (
        country          CHAR(2)        NOT NULL,
        code             NVARCHAR(32)   NOT NULL,
        sort_key         NVARCHAR(32)   NOT NULL CONSTRAINT DF_geo_division_sort_key DEFAULT (N''),
        code_iso         NVARCHAR(16)   NULL,
        parent_code      NVARCHAR(32)   NULL,
        depth            SMALLINT       NOT NULL,
        name_local       NVARCHAR(128)  NOT NULL,
        name_local_short NVARCHAR(64)   NOT NULL CONSTRAINT DF_geo_division_name_local_short DEFAULT (N''),
        name_en          NVARCHAR(128)  NOT NULL CONSTRAINT DF_geo_division_name_en DEFAULT (N''),
        name_zh          NVARCHAR(128)  NOT NULL CONSTRAINT DF_geo_division_name_zh DEFAULT (N''),
        type             NVARCHAR(32)   NOT NULL,
        abbrev           NVARCHAR(16)   NOT NULL CONSTRAINT DF_geo_division_abbrev DEFAULT (N''),
        status           NVARCHAR(16)   NOT NULL CONSTRAINT DF_geo_division_status DEFAULT (N'active'),
        updated_at       DATETIMEOFFSET NOT NULL CONSTRAINT DF_geo_division_updated_at DEFAULT (SYSUTCDATETIME()),

        CONSTRAINT PK_geo_division PRIMARY KEY CLUSTERED (country, code),
        CONSTRAINT FK_geo_division_parent FOREIGN KEY (country, parent_code)
            REFERENCES dbo.geo_division (country, code),
        CONSTRAINT CK_geo_division_depth CHECK (depth >= 1),
        CONSTRAINT CK_geo_division_parent_root
            CHECK (CASE WHEN parent_code IS NULL THEN 1 ELSE 0 END
                 = CASE WHEN depth = 1 THEN 1 ELSE 0 END),
        CONSTRAINT CK_geo_division_status CHECK (status IN (N'active', N'deprecated'))
    );
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'UQ_geo_division_code_iso'
      AND object_id = OBJECT_ID(N'dbo.geo_division')
)
BEGIN
    CREATE UNIQUE NONCLUSTERED INDEX UQ_geo_division_code_iso
        ON dbo.geo_division (code_iso)
        WHERE code_iso IS NOT NULL;
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_geo_division_children'
      AND object_id = OBJECT_ID(N'dbo.geo_division')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_geo_division_children
        ON dbo.geo_division (country, parent_code);
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_geo_division_depth'
      AND object_id = OBJECT_ID(N'dbo.geo_division')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_geo_division_depth
        ON dbo.geo_division (country, depth);
END
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = N'IX_geo_division_sort_key'
      AND object_id = OBJECT_ID(N'dbo.geo_division')
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_geo_division_sort_key
        ON dbo.geo_division (country, sort_key);
END
GO

IF OBJECT_ID(N'dbo.geo_division', N'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM sys.extended_properties
        WHERE major_id = OBJECT_ID(N'dbo.geo_division') AND minor_id = 0 AND name = N'MS_Description'
    )
        EXEC sys.sp_addextendedproperty
            @name = N'MS_Description',
            @value = N'全球行政区划自连表；联动 country + parent_code；国家见 countries',
            @level0type = N'SCHEMA', @level0name = N'dbo',
            @level1type = N'TABLE',  @level1name = N'geo_division';

    DECLARE @cols TABLE (col SYSNAME NOT NULL, descr NVARCHAR(500) NOT NULL);
    INSERT INTO @cols (col, descr) VALUES
        (N'country',          N'ISO 3166-1 alpha-2，如 CN、US'),
        (N'code',             N'国内区划代码，同国内唯一'),
        (N'sort_key',         N'国别排序键（定长补齐等）；不保证唯一'),
        (N'code_iso',         N'ISO 3166-2；无则为 NULL'),
        (N'parent_code',      N'上级 code；一级为 NULL'),
        (N'depth',            N'树深度：根=1，子=父+1'),
        (N'name_local',       N'当地名称（主展示）'),
        (N'name_local_short', N'当地简称'),
        (N'name_en',          N'英文译名；同当地名则空'),
        (N'name_zh',          N'中文译名；同当地名则空'),
        (N'type',             N'类型机读值（国别口径）'),
        (N'abbrev',           N'缩写，如美国州 USPS'),
        (N'status',           N'active / deprecated'),
        (N'updated_at',       N'更新时间');

    DECLARE @col SYSNAME, @descr NVARCHAR(500);
    DECLARE c CURSOR LOCAL FAST_FORWARD FOR SELECT col, descr FROM @cols;
    OPEN c;
    FETCH NEXT FROM c INTO @col, @descr;
    WHILE @@FETCH_STATUS = 0
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM sys.extended_properties ep
            INNER JOIN sys.columns sc
                ON sc.object_id = ep.major_id AND sc.column_id = ep.minor_id
            WHERE ep.major_id = OBJECT_ID(N'dbo.geo_division')
              AND ep.name = N'MS_Description'
              AND sc.name = @col
        )
            EXEC sys.sp_addextendedproperty
                @name = N'MS_Description',
                @value = @descr,
                @level0type = N'SCHEMA', @level0name = N'dbo',
                @level1type = N'TABLE',  @level1name = N'geo_division',
                @level2type = N'COLUMN', @level2name = @col;

        FETCH NEXT FROM c INTO @col, @descr;
    END
    CLOSE c;
    DEALLOCATE c;
END
GO

COMMIT TRANSACTION;
GO
