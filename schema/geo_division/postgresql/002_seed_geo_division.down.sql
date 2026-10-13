-- 回滚本批播种数据（PostgreSQL）
DELETE FROM geo_division WHERE country IN ('CN', 'US');
