"""Check gradient-endpoint text contrasts that automated axe reports as incomplete.

Every text colour is compared with every opaque gradient stop behind it (and with solid
backgrounds where the gradient sits on one). Runs on all four pages in both themes.
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
  // New components use opaque surfaces. Transparent children inherit the nearest
  // surface; gradients are checked against every stop rather than one average.
  const backdrops = (el, root) => {
    for (let node = el; node; node = node.parentElement) {
      const css = style(node), stops = rgb(css.backgroundImage);
      if (stops.length) return stops;
      if (!['transparent', 'rgba(0, 0, 0, 0)'].includes(css.backgroundColor)) return [css.backgroundColor];
      if (node === root) break;
    }
    return [page];
  };
  const componentText = (root, selector, label) => {
    for (const el of texts(root, selector))
      if (el.checkVisibility({visibilityProperty: true})) add(label, style(el).color, backdrops(el, root));
  };
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
  const demo = document.querySelector('[data-hero-demo]');
  if (demo) for (const [selector, label] of [
    ['.hero-demo-heading > span', 'hero sample heading'],
    ['.demo-control-label label', 'hero sample label'],
    ['.demo-control-label output', 'hero sample value'],
    ['.demo-answer', 'hero sample answer'],
    ['.demo-answer output', 'hero sample result'],
    ['.demo-answer > span', 'hero sample detail'],
    ['.demo-data-intro p', 'hero data description'],
    ['.demo-data-intro a', 'hero data link'],
    ['.hero-look summary > span', 'hero look summary'],
    ['.hero-look-controls label', 'hero look label'],
    ['.hero-look-controls select', 'hero look select'],
    ['[data-look-reset]', 'hero look reset'],
  ]) componentText(demo, selector, label);
  const conversion = document.querySelector('[data-conversion-demo]');
  if (conversion) {
    for (const [selector, label] of [
      ['.demo-title', 'conversion title'],
      ['.demo-tag', 'conversion tag'],
      ['.conversion-file', 'conversion file'],
      ['.conversion-file small', 'conversion file detail'],
      ['.conversion-bay > span', 'conversion bay label'],
      ['.conversion-field-key > span:first-child', 'conversion source key'],
      ['[data-conversion-key]', 'conversion target key'],
      ['.conversion-field-value', 'conversion field value'],
      ['[data-format]', 'conversion format button'],
      ['[data-conversion-run]', 'conversion play button'],
      ['[data-conversion-status]', 'conversion status'],
      ['[data-conversion-example]', 'conversion output'],
      ['[data-conversion-pending]', 'conversion pending'],
      ['.fineprint', 'conversion note'],
    ]) componentText(conversion, selector, label);
    // Source/target keys and pending text fade between phases. Their full text
    // colours are checked on their actual backplates, including when opacity is 0.
    // CSS state snapshots cover all chip colours; showcase_review tests playback.
    for (const step of conversion.querySelectorAll('[data-conversion-step]')) {
      const original = step.dataset.state;
      for (const state of ['waiting', 'current', 'done']) {
        step.dataset.state = state;
        add(`conversion step ${state} label`, style(step).color, backdrops(step, conversion));
        componentText(step, 'span', `conversion step ${state} number`);
      }
      step.dataset.state = original;
    }
  }
  // Wisperpfister: teaser on home, panels on its page, each against the gradient stops behind it.
  const teaser = document.querySelector('.app-teaser');
  if (teaser) componentText(teaser, '.tool-number, h2, p, .text-cta', 'wisper teaser');
  for (const [selector, label] of [['.wisper-demo', 'wisper demo'], ['.wisper-facts', 'wisper facts'], ['.platform-card', 'wisper platform'], ['.wisper-privacy', 'wisper privacy'], ['.wisper-beta', 'wisper beta']])
    for (const panel of document.querySelectorAll(selector))
      componentText(panel, 'h2, h3, p, li span, li b, .tag, .wisper-label, .wisper-step-num, kbd, del, .wisper-chips li, .button', label);
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
    for route in ['', 'sechserrechner/', 'sleepcalculator/', 'wisperpfister/']:
        p.goto(BASE + route)
        states = ['grade', 'sleep', 'code-csv', 'code-json'] if route == '' else ['empty', 'example'] if route == 'sechserrechner/' else ['default']
        for state in states:
            if route == '':
                p.locator(f'[data-select="{state.split("-")[0]}"]').click()
                if state.startswith('code-'):
                    p.locator(f'[data-format="{state.split("-")[1]}"]').click()
                look = p.locator('[data-look-panel]')
                if look.is_visible() and not look.evaluate('el => el.open'):
                    look.locator('summary').click()
            if state == 'example':
                p.locator('#loadExample').click(); p.locator('#closeToast').click()
            for theme in ['dark', 'light']:
                if p.locator('html').get_attribute('data-theme') != theme: p.locator('[data-theme-toggle]').click()
                p.wait_for_function(f"document.documentElement.dataset.theme === '{theme}'")
                p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                p.wait_for_timeout(100)
                pairs = p.evaluate(PAIRS)
                labels = {pair['label'] for pair in pairs}
                expected = {'brand', 'film-text stop'} | ({'mini clock', 'grade card h3', 'sleep card cta', 'hud channel', 'hud data', 'grade', 'sleep', 'code', 'wisper teaser'} if route == '' else set())
                expected |= {'result average', 'result averageDetail', 'result result-title'} if route == 'sechserrechner/' else set()
                expected |= {'dial-tip', 'midnight', 'sleepResultTime'} if route == 'sleepcalculator/' else set()
                expected |= {'wisper demo', 'wisper facts', 'wisper platform', 'wisper privacy', 'wisper beta'} if route == 'wisperpfister/' else set()
                if route == '':
                    expected |= {'hero sample heading', 'conversion title', 'conversion tag', 'conversion file', 'conversion file detail', 'conversion bay label', 'conversion source key', 'conversion target key', 'conversion field value', 'conversion format button', 'conversion play button', 'conversion status', 'conversion output', 'conversion pending', 'conversion note'}
                    expected |= {'hero data description', 'hero data link'} if state.startswith('code-') else {'hero sample label', 'hero sample value', 'hero sample answer', 'hero sample result', 'hero sample detail'}
                    if p.locator('[data-look-panel]').is_visible():
                        expected |= {'hero look summary', 'hero look label', 'hero look select', 'hero look reset'}
                    expected |= {f'conversion step {step} {text}' for step in ['waiting', 'current', 'done'] for text in ['label', 'number']}
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
