-- 回滚本批播种数据（SQL Server）
DELETE FROM dbo.geo_division WHERE country IN (N'CN', N'US');
GO
