import fs from 'node:fs';

const html = fs.readFileSync(new URL('../site/index.html', import.meta.url), 'utf8');
const config = JSON.parse(fs.readFileSync(new URL('../protected-content.json', import.meta.url), 'utf8'));

const failures = [];
for (const text of config.mustContain) {
  if (!html.includes(text)) failures.push(`Missing protected text: ${text}`);
}
for (const heading of config.weekHeadings) {
  if (!html.includes(heading)) failures.push(`Missing protected week heading: ${heading}`);
}
const weekMarkers = [...html.matchAll(/class="num">(\d{2})</g)].map(m => Number(m[1]));
if (weekMarkers.length !== config.constraints.weekCount) {
  failures.push(`Expected ${config.constraints.weekCount} week cards, found ${weekMarkers.length}`);
}
if (!weekMarkers.includes(config.constraints.midtermWeek)) failures.push('Week 8 midterm marker missing');
if (!weekMarkers.includes(config.constraints.reviewWeek)) failures.push('Week 15 review marker missing');

if (failures.length) {
  console.error('PROTECTED CONTENT CHECK FAILED');
  failures.forEach(f => console.error(`- ${f}`));
  process.exit(1);
}
console.log('Protected academic content: PASS');
