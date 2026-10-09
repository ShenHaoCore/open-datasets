/**
 * 抽取上游原始事实 → build/upstream.json + build/.upstream/*.png
 *
 * 本步骤刻意不含任何编辑加工（命名覆盖、排序、格式化），
 * 只负责把两个上游 npm 包里的原始数据落成一份可读的 JSON，
 * 编辑决策与输出格式全部集中在 generate.py。
 */
import { createRequire } from 'node:module';
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const CACHE = join(HERE, '.upstream');

const pkgDir = (name) => dirname(require.resolve(`${name}/package.json`));
const itiDir = pkgDir('intl-tel-input');
const wcDir = pkgDir('world-countries');

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

// ── 3. world-countries：只取 ISO3 与成员资格（成员资格决定是否给国旗 emoji）。
const iso3 = {};
for (const c of JSON.parse(readFileSync(join(wcDir, 'countries.json'), 'utf8'))) {
  if (c.cca2) iso3[c.cca2] = c.cca3 || '';
}

// ── 4. 国旗雪碧图逐旗参数。上游 CSS 自带权威的 offset（1x 基准），
//      宽度/高度按需覆盖，未列出的旗即默认 20×14（@2x 后 40×28）。
//      offset 统一取绝对值存成「距左边缘的像素距离」，生成端再补负号。
const css = readFileSync(join(itiDir, 'build/css/intlTelInput.css'), 'utf8');
const flags = {};
const blockRe = /((?:\.iti__[a-z]{2}\s*,\s*)*\.iti__[a-z]{2})\s*\{([^}]*)\}/g;
for (const m of css.matchAll(blockRe)) {
  const pick = (key) => {
    const mm = m[2].match(new RegExp(`--iti-flag-${key}:\\s*(-?\\d+)px`));
    return mm ? Number(mm[1]) : null;
  };
  const rawOffset = pick('offset');
  const offset = rawOffset === null ? null : Math.abs(rawOffset);
  const width = pick('width');
  const height = pick('height');
  for (const sel of m[1].matchAll(/\.iti__([a-z]{2})/g)) {
    const code = sel[1];
    flags[code] ??= { offset: 0, width: 20, height: 14 };
    if (offset !== null) flags[code].offset = offset;
    if (width !== null) flags[code].width = width;
    if (height !== null) flags[code].height = height;
  }
}

// ── 5. 精灵图原样带出，切片交给 generate.py（需要图像库）。
mkdirSync(CACHE, { recursive: true });
copyFileSync(join(itiDir, 'build/img/flags.png'), join(CACHE, 'flags.png'));
copyFileSync(join(itiDir, 'build/img/flags@2x.png'), join(CACHE, 'flags@2x.png'));

const pkgVersion = (name) => JSON.parse(readFileSync(join(pkgDir(name), 'package.json'), 'utf8')).version;
const payload = {
  sources: {
    'intl-tel-input': pkgVersion('intl-tel-input'),
    'world-countries': pkgVersion('world-countries'),
  },
  countries,
  names,
  iso3,
  flags,
};

writeFileSync(join(HERE, 'upstream.json'), `${JSON.stringify(payload, null, 2)}\n`);

console.log(
  `[extract] intl-tel-input ${payload.sources['intl-tel-input']} / ` +
    `world-countries ${payload.sources['world-countries']}`,
);
console.log(`[extract] 区号条目 ${countries.length} · 名称表 en/zh ${Object.keys(names.en).length}/${Object.keys(names.zh).length} · 国旗 ${Object.keys(flags).length}`);
