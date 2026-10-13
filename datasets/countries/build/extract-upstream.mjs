/**
 * 抽取上游原始事实 → build/upstream.json + build/.upstream/flags/*.svg
 *
 * 本步骤刻意不含任何编辑加工（命名覆盖、排序、格式化），
 * 只负责把上游 npm 包里的原始数据落成一份可读的 JSON / 国旗缓存，
 * 编辑决策与输出格式全部集中在 generate.py。
 *
 * 国旗来源：svg-country-flags（准确矢量）。若某 ISO2 在包内缺失，
 * 可放 build/overrides/flags/<iso2>.svg 作为补丁（优先于 npm 包）。
 */
import { createRequire } from 'node:module';
import {
  copyFileSync,
  existsSync,
  mkdirSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const CACHE = join(HERE, '.upstream');
const FLAG_CACHE = join(CACHE, 'flags');
const OVERRIDE_DIR = join(HERE, 'overrides', 'flags');

const pkgDir = (name) => dirname(require.resolve(`${name}/package.json`));
const itiDir = pkgDir('intl-tel-input');
const wcDir = pkgDir('world-countries');
const flagDir = join(pkgDir('svg-country-flags'), 'svg');

// ── 1. 国家与区号数据。上游数组顺序即最终输出顺序，不做二次排序。
const countries = require(join(itiDir, 'build/js/data.js')).map((c) => ({
  iso2: c.iso2.toLowerCase(),
  dial_code: c.dialCode,
  priority: c.priority || 0,
  area_codes: c.areaCodes || null,
}));

// ── 2. 中英文名称表。上游是 ESM（export default {...}），用正则取常量表，
//      避免为读两个文件引入打包器。
const readNameTable = (file) => {
  const table = {};
  const re = /^\s*([a-z]{2}):\s*"((?:[^"\\]|\\.)*)",\s*$/gm;
  for (const m of readFileSync(file, 'utf8').matchAll(re)) {
    table[m[1]] = JSON.parse(`"${m[2]}"`);
  }
  return table;
};
const names = {
  en: readNameTable(join(itiDir, 'build/js/i18n/en/countries.js')),
  zh: readNameTable(join(itiDir, 'build/js/i18n/zh/countries.js')),
};

// ── 3. countries（npm 包名 world-countries）：国家主数据（按 iso2 小写索引）。
//      电话区号仍以 intl-tel-input 为准；此处只抽地理 / 行政 / 货币等字段。
const profiles = {};
for (const c of JSON.parse(readFileSync(join(wcDir, 'countries.json'), 'utf8'))) {
  if (!c.cca2) continue;
  profiles[c.cca2.toLowerCase()] = {
    iso3: c.cca3 || '',
    ccn3: c.ccn3 || '',
    capital: Array.isArray(c.capital) ? c.capital.slice() : [],
    region: c.region || '',
    subregion: c.subregion || '',
    latlng: Array.isArray(c.latlng) ? c.latlng.slice() : null,
    area: typeof c.area === 'number' ? c.area : null,
    tld: Array.isArray(c.tld) ? c.tld.slice() : [],
    currencies: c.currencies && typeof c.currencies === 'object' ? c.currencies : {},
    languages: c.languages && typeof c.languages === 'object' ? c.languages : {},
    borders: Array.isArray(c.borders) ? c.borders.slice() : [],
    independent: typeof c.independent === 'boolean' ? c.independent : null,
    un_member: typeof c.unMember === 'boolean' ? c.unMember : null,
    landlocked: typeof c.landlocked === 'boolean' ? c.landlocked : null,
    status: c.status || '',
    name_official: c.name?.official || '',
  };
}

// ── 4. 准确矢量国旗：按国家列表复制 SVG；overrides/ 优先于 npm 包。
rmSync(FLAG_CACHE, { recursive: true, force: true });
mkdirSync(FLAG_CACHE, { recursive: true });

const available = new Set(
  readdirSync(flagDir)
    .filter((n) => n.endsWith('.svg'))
    .map((n) => n.slice(0, -4)),
);

const flags = [];
const missing = [];
for (const c of countries) {
  const code = c.iso2;
  const override = join(OVERRIDE_DIR, `${code}.svg`);
  const upstream = join(flagDir, `${code}.svg`);
  let src = null;
  if (existsSync(override)) src = override;
  else if (available.has(code)) src = upstream;
  if (src) {
    copyFileSync(src, join(FLAG_CACHE, `${code}.svg`));
    flags.push(code);
  } else {
    missing.push(code);
  }
}

const pkgVersion = (name) => JSON.parse(readFileSync(join(pkgDir(name), 'package.json'), 'utf8')).version;
const payload = {
  sources: {
    'intl-tel-input': pkgVersion('intl-tel-input'),
    countries: pkgVersion('world-countries'),
    'svg-country-flags': pkgVersion('svg-country-flags'),
  },
  countries,
  names,
  profiles,
  flags,
  flags_missing: missing,
};

writeFileSync(join(HERE, 'upstream.json'), `${JSON.stringify(payload, null, 2)}\n`);

const withProfile = countries.filter((c) => profiles[c.iso2]).length;
console.log(
  `[extract] intl-tel-input ${payload.sources['intl-tel-input']} / ` +
    `countries ${payload.sources.countries} / ` +
    `svg-country-flags ${payload.sources['svg-country-flags']}`,
);
console.log(
  `[extract] 区号条目 ${countries.length} · 名称表 en/zh ${Object.keys(names.en).length}/${Object.keys(names.zh).length} · ` +
    `主数据档案 ${withProfile}/${countries.length} · 国旗 SVG ${flags.length}` +
    (missing.length ? ` · 缺图 ${missing.join(',')}` : ''),
);
