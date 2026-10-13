/**
 * 抽取上游原始事实 → build/upstream.json
 *
 * 省级事实来自 provinces.source.json；地级/区县来自 china-division。
 * 不做命名改写；编辑决策集中在 generate.py。
 */
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const pkgDir = dirname(require.resolve('china-division/package.json'));
const dist = join(pkgDir, 'dist');

const cities = JSON.parse(readFileSync(join(dist, 'cities.json'), 'utf8'));
const areas = JSON.parse(readFileSync(join(dist, 'areas.json'), 'utf8'));
const provinceSource = JSON.parse(readFileSync(join(HERE, 'provinces.source.json'), 'utf8'));

const version = JSON.parse(readFileSync(join(pkgDir, 'package.json'), 'utf8')).version;

const payload = {
  sources: {
    'china-division': version,
    provinces_source: provinceSource.schema,
  },
  provinces: provinceSource.provinces,
  cities,
  areas,
};

writeFileSync(join(HERE, 'upstream.json'), `${JSON.stringify(payload, null, 2)}\n`);

console.log(
  `[extract] china-division ${version} · 省级 ${provinceSource.provinces.length} · 地级原料 ${cities.length} · 区县原料 ${areas.length}`,
);
