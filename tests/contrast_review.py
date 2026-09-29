"""Check gradient-endpoint text contrasts that automated axe reports as incomplete.

Every text colour is compared with every opaque gradient stop behind it (and with solid
backgrounds where the gradient sits on one). Runs on all three pages in both themes.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
parser.add_argument('--output', type=Path, default=Path('output/playwright'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
BASE = args.base_url.rstrip('/') + '/'

PAIRS = '''()=>{
  const style = el=>getComputedStyle(el);
  const rgb = value => value.match(/rgba?\\([^)]*\\)/g) || [];
  const page = style(document.body).backgroundColor;
  const name = el => el.id || (typeof el.className === 'string' && el.className.split(' ')[0]) || el.tagName;
  const texts = (root, selector) => [...root.querySelectorAll(selector)].filter(el => el.textContent.trim());
  let pairs=[];
  const add = (label, foreground, backgrounds) => { for (const background of backgrounds) pairs.push({label, foreground, background, page}); };
  for(const module of document.querySelectorAll('.module')) {
    const backgrounds=rgb(style(module).backgroundImage);
    for(const foreground of [style(module).color,...[...module.querySelectorAll('.mini-clock')].map(el=>style(el).color)])
      for(const background of backgrounds) pairs.push({label:module.dataset.module,foreground,background,page});
    for (const el of texts(module, 'span, b, strong, small')) add(`${module.dataset.module} ${name(el)}`, style(el).color, backgrounds);
  }
  const clock=document.querySelector('.sleep-visual');
  if(clock) for(const el of clock.querySelectorAll('h2,span,output,b,small'))
    for(const background of rgb(style(clock).backgroundImage)) pairs.push({label:name(el),foreground:style(el).color,background,page});
  const brand=document.querySelector('.brand-mark');
  pairs.push({label:'brand',foreground:style(brand).color,background:style(brand).backgroundColor,page});
  const preview=document.querySelector('.sleep-preview .mini-clock');
  if(preview) pairs.push({label:'mini clock',foreground:style(preview).color,background:style(document.querySelector('.card-sleep')).backgroundColor,page});
  // Tool cards: solid background colour plus both gradient stops behind the heading, copy and CTA.
  for (const card of document.querySelectorAll('.tool-card'))
    for (const el of card.querySelectorAll('h3, p, .text-cta'))
      add(`${card.dataset.transitionCard} card ${el.tagName === 'SPAN' ? 'cta' : el.tagName.toLowerCase()}`, style(el).color, [style(card).backgroundColor, ...rgb(style(card).backgroundImage)]);
  // Result instrument: gradient stops against the numeral, heading and detail line.
  const result = document.querySelector('.result-panel');
  if (result) for (const el of result.querySelectorAll('#average, h2, #averageDetail, #averageExact, #gradeCount, #resultSubject'))
    add(`result ${name(el)}`, style(el).color, rgb(style(result).backgroundImage));
  // Film text: every gradient stop must read as text on the page background.
  for (const el of document.querySelectorAll('.film-text')) {
    const stops = rgb(style(el).backgroundImage);
    for (const stop of stops.length ? stops : [style(el).color]) pairs.push({label: 'film-text stop', foreground: stop, background: page, page});
  }
  // HUD lines around the hero stage sit directly on the page background.
  for (const el of document.querySelectorAll('.scene-hud [data-hud-channel], .scene-hud [data-hud-data]'))
    pairs.push({label: `hud ${el.hasAttribute('data-hud-channel') ? 'channel' : 'data'}`, foreground: style(el).color, background: page, page});
  return pairs;
}'''


def parse(color):
    values = [float(x) for x in color.split('(')[1].split(')')[0].replace('/', ',').replace(' ', ',').split(',') if x.strip()]
    return values[:3], (values[3] if len(values) > 3 else 1.0)


def over(color, base):
    channels, alpha = parse(color)
    below, _ = parse(base)
    return [c * alpha + b * (1 - alpha) for c, b in zip(channels, below)]


def lum(channels):
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in (c / 255 for c in channels)]
    return sum(v * c for v, c in zip(linear, [.2126, .7152, .0722]))


results = []
seen = {}
with sync_playwright() as w:
    b = w.chromium.launch()
    p = b.new_page(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
    for route in ['', 'sechserrechner/', 'sleepcalculator/']:
        p.goto(BASE + route)
        states = ['empty', 'example'] if route == 'sechserrechner/' else ['default']
        for state in states:
            if state == 'example':
                p.locator('#loadExample').click(); p.locator('#closeToast').click()
            for theme in ['dark', 'light']:
                if p.locator('html').get_attribute('data-theme') != theme: p.locator('[data-theme-toggle]').click()
                p.wait_for_function(f"document.documentElement.dataset.theme === '{theme}'")
                p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                p.wait_for_timeout(100)
                pairs = p.evaluate(PAIRS)
                labels = {pair['label'] for pair in pairs}
                expected = {'brand', 'film-text stop'} | ({'mini clock', 'grade card h3', 'sleep card cta', 'hud channel', 'hud data', 'grade', 'sleep', 'code'} if route == '' else set())
                expected |= {'result average', 'result averageDetail', 'result result-title'} if route == 'sechserrechner/' else set()
                expected |= {'dial-tip', 'midnight', 'sleepResultTime'} if route == 'sleepcalculator/' else set()
                missing = expected - labels
                assert not missing, (route, theme, 'pairs not found', missing)
                for pair in pairs:
                    background = over(pair['background'], pair['page'])
                    foreground = over(pair['foreground'], pair['background'] if parse(pair['background'])[1] == 1 else pair['page'])
                    a, bg = lum(foreground), lum(background)
                    ratio = (max(a, bg) + .05) / (min(a, bg) + .05)
                    assert ratio >= 4.5, (route, state, theme, pair, ratio)
                    results.append({'route': route, 'state': state, 'theme': theme, **pair, 'ratio': round(ratio, 2)})
    b.close()
(args.output / 'gradient-contrast.json').write_text(json.dumps(results, indent=2))
worst = min(results, key=lambda r: r['ratio'])
print(f'PASS: {len(results)} gradient/brand text pairs >= 4.5:1; minimum {worst["ratio"]}:1 ({worst["route"] or "home"} {worst["theme"]} {worst["label"]})')
