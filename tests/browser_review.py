"""Real HTTP browser regression tests; no embedded-page or storage substitutes.

Only explicit storage fault tests inject exceptions; normal cases use native
origin-backed localStorage. Requires a running static HTTP server.
"""
import argparse
import json
import math
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
# Hero engine state contract (spec §5.5.1): tests wait for a settled state before judging frames or pixels.
SETTLED = "['idle','still','fallback'].includes(document.querySelector('.hero-visual')?.dataset.glassState)"
GLASS = "(() => { const v = document.querySelector('.hero-visual'); const api = globalThis.HeroGL; return {state: v.dataset.glassState, tier: v.dataset.glassTier || null, form: v.dataset.glassForm, api: api ? [api.state, api.tier] : null, frames: api ? api.stats.frames : 0}; })()"
TWO_FRAMES = '() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))'
BENCH_EVENTS = "window.__bench = []; addEventListener('benchselect', event => __bench.push(event.detail), true);"
# Focusable elements must never sit inside aria-hidden or role=img (tabindex=-1 labels in .scene are the documented exception).
HIDDEN_FOCUSABLES = '''() => [...document.querySelectorAll('a[href], button, input, select, textarea, summary, [tabindex]')]
  .filter(el => el.tabIndex >= 0 && !el.disabled && el.closest('[aria-hidden="true"], [role="img"]'))
  .map(el => el.id || el.className || el.tagName)'''
# Diagnostics for an overflow failure: the widest boxes past the viewport edge, then the same after 500 ms.
OVERFLOWING = '''async () => {
  const scan = () => [...document.querySelectorAll('body *')].map(el => [el, el.getBoundingClientRect()]).filter(([, r]) => r.width && r.right > innerWidth + 1)
    .sort((a, b) => b[1].right - a[1].right).slice(0, 6).map(([el, r]) => `${el.tagName.toLowerCase()}.${(el.getAttribute('class') || '').split(' ')[0]} ${Math.round(r.left)}..${Math.round(r.right)}`);
  const first = {scrollWidth: document.documentElement.scrollWidth, width: innerWidth, boxes: scan()};
  await new Promise(resolve => setTimeout(resolve, 500));
  return {...first, after500ms: {scrollWidth: document.documentElement.scrollWidth, boxes: scan()}};
}'''
INFINITE_ANIMATIONS = "document.getAnimations().filter(a => a.effect && a.effect.getTiming().iterations === Infinity).length"
# Every aria-labelledby / aria-describedby / aria-controls id must exist on the page.
BROKEN_REFS = '''() => [...document.querySelectorAll('[aria-labelledby], [aria-describedby], [aria-controls]')]
  .flatMap(el => ['aria-labelledby', 'aria-describedby', 'aria-controls'].flatMap(a => (el.getAttribute(a) || '').split(/\\s+/).filter(Boolean)))
  .filter(id => !document.getElementById(id))'''
# Spec §8.2: every stylesheet and script is local and carries the werkplatz-5 cache bust.
ASSET_URLS = "[...document.querySelectorAll('link[rel=stylesheet], script[src]')].map(el => el.getAttribute('href') || el.getAttribute('src'))"
# The live result of each page; decorative count-ups must refuse it (spec §4.5: result numbers never tween).
LIVE_RESULT = {'home': '#hero-title', 'home-fallback': '#hero-title', 'grade': '#average', 'sleep': '#sleepResultTime'}
# Touch targets on phones: at least 44px high; icon-only controls also 44px wide.
SMALL_TARGETS = '''() => {
  const icon = '.icon-button, .theme-toggle, .brand, [data-scene-link], .dial-handle';
  return [...document.querySelectorAll('button, [role=slider], summary, select, a.button, .text-button, .main-nav a, .brand, .footer-row a, [data-scene-link], .chip')]
    .filter(el => { const r = el.getBoundingClientRect(); return r.width > 2 && r.height > 2 && (!el.checkVisibility || el.checkVisibility({visibilityProperty: true}))
      && !el.closest('[aria-hidden="true"], .sr-only'); })
    .filter(el => { const r = el.getBoundingClientRect(); return r.height < 43.5 || (el.matches(icon) && r.width < 43.5); })
    .map(el => { const r = el.getBoundingClientRect(); return `${el.id || el.className || el.tagName} ${Math.round(r.width)}x${Math.round(r.height)}`; });
}'''
# A clip-path cuts into its element unless it is 'none' or an inset() with no positive edge (inset(-120px) only widens the box).
BITES = "const bites = clip => clip !== 'none' && !(/^inset\\(/.test(clip) && clip.slice(6, -1).split(/\\s+round\\s+/)[0].trim().split(/\\s+/).every(v => parseFloat(v) <= 0));"
# Hero text that must never look half-drawn once the load has settled (spec §5.3).
HERO_TEXT = '.hero .eyebrow, .hero h1 .line > span, .hero-description, .hero-actions > *, .hero-note, .scene-hud > span, .scene-note, .scene-switches button'
# Visible elements that are cut: a clip-path biting into the box, a clipping ancestor it pokes out of, or opacity below 1 on it or an ancestor.
CUT_TEXT = '''selector => { ''' + BITES + '''
  return [...document.querySelectorAll(selector)].filter(el => el.getClientRects().length).flatMap(el => {
    const r = el.getBoundingClientRect(), name = `${el.tagName.toLowerCase()}.${el.getAttribute('class') || ''} "${el.textContent.trim().slice(0, 24)}"`, out = [];
    if (bites(getComputedStyle(el).clipPath)) out.push(`${name} clip-path ${getComputedStyle(el).clipPath}`);
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (+cs.opacity < 1) out.push(`${name} opacity ${cs.opacity} on ${a.getAttribute('class') || a.tagName}`);
      if (a !== el && (cs.overflowX !== 'visible' || cs.overflowY !== 'visible' || bites(cs.clipPath))) {
        const b = a.getBoundingClientRect();
        if (r.left < b.left - .5 || r.right > b.right + .5 || r.top < b.top - .5 || r.bottom > b.bottom + .5) out.push(`${name} cut by ${a.getAttribute('class') || a.tagName}`);
      }
    }
    return out; }); }'''
# The load choreography frozen at the given times: lead, CTAs and note may move, but no clip-path may slice them.
FROZEN_LOAD = '''times => { ''' + BITES + '''
  const els = [...document.querySelectorAll('.hero-description, .hero-actions > *, .hero-note')], sliced = [];
  const animated = els.filter(el => el.getAnimations().some(a => a.timeline === document.timeline)).length;
  for (const t of times) {
    document.getAnimations().filter(a => a.timeline === document.timeline).forEach(a => { a.pause(); a.currentTime = t; });
    for (const el of els) if (bites(getComputedStyle(el).clipPath)) sliced.push(`${el.textContent.trim().slice(0, 20)} at ${t} ms: ${getComputedStyle(el).clipPath}`);
  }
  return {animated, sliced}; }'''
# The focused element after a Tab press: visible (or its label is), at least 8x8 px and scrolled into view. null/'again' end the walk.
TAB_STOP = '''async () => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  if (el.dataset.tabSeen) return 'again';
  el.dataset.tabSeen = '1';
  await Promise.all(el.getAnimations().filter(a => a.timeline === document.timeline).map(a => a.finished.catch(() => null)));
  const seen = node => { const r = node.getBoundingClientRect(); return r.width >= 8 && r.height >= 8 && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth
    && node.checkVisibility({opacityProperty: true, visibilityProperty: true}); };
  const label = el.closest('label') || (el.id && document.querySelector(`label[for="${el.id}"]`));
  const r = el.getBoundingClientRect();
  return {name: `${el.id || el.getAttribute('class') || el.tagName} ${Math.round(r.width)}x${Math.round(r.height)} @${Math.round(r.left)},${Math.round(r.top)}`, bad: !seen(el) && !(label && seen(label))};
}'''
# Once a reveal is fully in view it has settled: no transform, no clip-path that bites, full opacity (spec §4.4).
REVEALS = '''async () => { ''' + BITES + '''
  const out = [], frames = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  for (const el of [...document.querySelectorAll('.reveal')].filter(el => el.getClientRects().length)) {
    const box = el.getBoundingClientRect();
    if (box.height > innerHeight - 100) continue;
    scrollBy({top: box.bottom - innerHeight + 8, behavior: 'instant'}); await frames();
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    if (!['none', 'matrix(1, 0, 0, 1, 0, 0)'].includes(cs.transform) || bites(cs.clipPath) || cs.opacity !== '1')
      out.push(`${el.getAttribute('class')} at ${Math.round(r.top)}..${Math.round(r.bottom)}: ${cs.transform} ${cs.clipPath} ${cs.opacity}`);
  }
  return out; }'''
# Stylesheet validity: Chromium drops a rejected declaration, a whole rule for one rejected selector, a block for a rejected condition.
# var() resolves against :root; declarations that need component-scoped variables stay untested (counted in the message).
CSS_CHECK = '''items => {
  const root = getComputedStyle(document.documentElement), sheet = new CSSStyleSheet(), bad = [];
  let tested = 0, skipped = 0;
  const parses = css => { try { sheet.replaceSync(css); return sheet.cssRules[0] || null; } catch { return null; } };
  const resolve = value => {
    for (let k = 0; k < 20 && value.includes('var('); k++) {
      const m = value.match(/var\\(\\s*(--[\\w-]+)\\s*(?:,((?:[^()]|\\((?:[^()]|\\([^()]*\\))*\\))*))?\\)/); if (!m) return null;
      const v = root.getPropertyValue(m[1]).trim() || (m[2] === undefined ? null : m[2].trim()); if (v === null) return null;
      value = value.replace(m[0], v);
    }
    return value.includes('var(') ? null : value; };
  for (const [kind, file, line, a, b] of items) {
    const at = `${file}:${line}`;
    if (kind === 'junk') bad.push(`${at} unparsable text "${a.slice(0, 60)}"`);
    else if (kind === 'decl' && !a.startsWith('--')) {
      const value = resolve(b.replace(/\\s*!important$/i, ''));
      if (value === null) { skipped++; continue; }
      tested++;
      if (!CSS.supports(a, value)) bad.push(`${at} ${CSS.supports(a, 'inherit') ? 'rejected value' : 'unknown property'} ${a}: ${b}`);
    } else if (kind === 'rule' && !parses(`${a}{}`)) bad.push(`${at} rejected selector ${a}`);
    else if (kind === 'at') {
      const [, name, cond] = a.match(/^@([\\w-]+)\\s*(.*)$/) || [null, a, ''];
      if (['media', 'supports', 'container'].includes(name)) {
        // An unknown media feature parses (as general-enclosed) but then matches neither itself nor its negation.
        const unknown = name === 'media' && cond.split(/,(?![^()]*\\))/).map(q => q.trim().replace(/^only\\s+/, '')).some(q =>
          matchMedia(q.startsWith('not ') ? q.slice(4) : q).matches === matchMedia(q.startsWith('not ') ? q : /^[a-z]/i.test(q) ? `not ${q}` : `not (${q})`).matches);
        if (!parses(`@${name} ${cond}{}`) || unknown) bad.push(`${at} rejected @${name} ${cond}`);
      } else if (!['keyframes', 'starting-style', 'view-transition'].includes(name)) bad.push(`${at} unexpected @${name}`);
    }
  }
  return {bad, tested, skipped}; }'''
# Deliberate cross-engine CSS that Chromium does not parse: Safari's hanging-punctuation and -webkit-backdrop-filter,
# Firefox's range parts (one selector per rule, so no other selector is dropped with them).
CSS_ALLOWED = re.compile(r'^\S+ (unknown property (hanging-punctuation|-webkit-backdrop-filter): |rejected selector [^,]*::-moz-range-(track|thumb|progress)$)')


def css_items(text):
    """Every at-rule prelude, style-rule selector and declaration of a stylesheet as (kind, line, a, b); comments are stripped."""
    items, stack, buf, start, line, i = [], [], [], None, 1, 0
    def flush():
        raw = ''.join(buf).strip(); buf.clear()
        top = stack[-1] if stack else '@'
        if not raw or top.startswith('@view-transition'):
            return  # descriptors, not declarations
        if top.startswith('@') and not top.startswith('@frame'):
            items.append(('at' if raw.startswith('@') else 'junk', start or line, raw, ''))  # statements (or stray text) outside a rule
        elif ':' in raw:
            items.append(('decl', start or line, *(s.strip() for s in raw.split(':', 1))))
        else:
            items.append(('junk', start or line, raw, ''))
    while i < len(text):
        c = text[i]
        if text.startswith('/*', i):
            j = text.find('*/', i + 2); j = len(text) if j < 0 else j + 2
            line += text.count('\n', i, j); buf.append(' '); i = j
            continue
        if c in '"\'(':  # strings and balanced parentheses (url(), data URIs, :is()) are copied whole
            j, depth, quote = i, 0, None
            while j < len(text):
                ch = text[j]
                if quote:
                    if ch == '\\': j += 1
                    elif ch == quote: quote = None
                elif ch in '"\'': quote = ch
                elif ch == '(': depth += 1
                elif ch == ')': depth -= 1
                if (c != '(' and j > i and quote is None) or (c == '(' and depth == 0):
                    break
                j += 1
            segment = text[i:j + 1]; start = start or line; line += segment.count('\n'); buf.append(segment); i = j + 1
            continue
        if c == '{':
            prelude = ' '.join(''.join(buf).split()); buf.clear()
            if stack and stack[-1].startswith('@keyframes'):
                prelude = '@frame ' + prelude
            else:
                items.append(('at' if prelude.startswith('@') else 'rule', start or line, prelude, ''))
            stack.append(prelude); start = None
        elif c in ';}':
            flush(); start = None
            if c == '}':
                if stack: stack.pop()
                else: items.append(('junk', line, '}', ''))
        else:
            if start is None and not c.isspace(): start = line
            if c == '\n': line += 1
            buf.append(c)
        i += 1
    if stack:
        items.append(('junk', line, f'unclosed {stack[-1]}', ''))
    return items


parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
parser.add_argument('--chromium', default=None)
parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
parser.add_argument('--output', default=str(ROOT / 'output' / 'playwright'))
args = parser.parse_args()
OUT = Path(args.output)
OUT.mkdir(parents=True, exist_ok=True)


class Review:
    def __init__(self, browser):
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='de-CH', timezone_id='Europe/Zurich', color_scheme='dark', reduced_motion='reduce')
        self.page = None; self.route = ''; self.results = []; self.errors = []; self.network_errors = []; self.blocked = False; self.warnings = []; self.soft_failures = []; self.external = []

    def watch_requests(self, page):
        # No external requests: every fetch stays on the tested origin (data:/blob: URLs are local).
        base = args.base_url.rstrip('/') + '/'
        page.on('request', lambda request: self.external.append(request.url) if not request.url.startswith((base, 'data:', 'blob:', 'about:')) else None)

    def open(self, route='', blocked=False, init=None, media=None, viewport=None):
        if self.page:
            self.page.close()
        self.page = self.context.new_page(); self.page.set_default_timeout(5000)
        if viewport:
            self.page.set_viewport_size(viewport)
        if init:
            self.page.add_init_script(init)
        if media:
            self.page.emulate_media(**media)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.page.on('console', lambda message: self.warnings.append(f'{route}: {message.text}') if message.type == 'warning' else None)
        self.route = route; self.blocked = blocked
        self.page.on('response', lambda response: self.network_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
        self.watch_requests(self.page)
        if blocked:
            self.page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
        self.page.goto(args.base_url.rstrip('/') + '/' + route, wait_until='networkidle')
        return self.page

    def reset(self):
        if self.page and not self.blocked:
            self.page.evaluate('localStorage.clear()')

    def check(self, condition, description):
        if not condition:
            self.page.screenshot(path=str(OUT / 'failure.png'), full_page=True)
            raise AssertionError(description)
        self.results.append(description)

    def soft(self, condition, description):
        # Recorded like check(), but the run continues so every layout and flow is still verified.
        if condition:
            self.results.append(description)
        else:
            self.page.screenshot(path=str(OUT / f'soft-failure-{len(self.soft_failures) + 1}.png'), full_page=True)
            self.soft_failures.append(description)

    def disclosure_is_instant(self, selector, label):
        details = self.page.locator(selector).first
        details.locator('summary').scroll_into_view_if_needed(); details.locator('summary').click(); self.frames()
        first = details.bounding_box()['height']; self.page.wait_for_timeout(400); last = details.bounding_box()['height']
        self.soft(details.evaluate('el => el.open') and abs(first - last) < 1, f'Reduced motion opens {label} instantly ({first:.0f} -> {last:.0f}px)')
        details.locator('summary').click(); self.frames()

    def text(self, selector):
        return self.page.locator(selector).inner_text()

    def screenshot(self, name):
        self.page.screenshot(path=str(OUT / name), full_page=True)

    def settle(self, timeout=15000):
        # The software-renderer still frame JITs for about 750 ms after load.
        self.page.wait_for_function(SETTLED, timeout=timeout)
        return self.page.evaluate(GLASS)

    def frames(self):
        self.page.evaluate(TWO_FRAMES)

    def number(self, selector, prop):
        return float(self.page.locator(selector).evaluate(f"el => getComputedStyle(el).getPropertyValue('{prop}') || el.style.getPropertyValue('{prop}')") or 'nan')


def run(review):
    r = review
    p = r.open()
    r.check(p.locator('h1').inner_text() == 'Kleine Ideen.\nEchte Tools.', 'Home heading')
    glass = r.settle()
    r.check(glass['state'] in ('still', 'fallback') and glass['tier'] == glass['state'], f'Hero settles on a still frame or the fallback under reduced motion: {glass}')
    p.locator('[data-select="sleep"]').click()
    r.check(p.locator('[data-workbench]').get_attribute('data-selection') == 'sleep', 'Hero sleep selection')
    r.check(p.locator('[data-scene-link]').get_attribute('href') == './sleepcalculator/', 'Hero links to sleep route')
    r.check(p.locator('[data-hud-channel]').text_content() == 'CH 02 · SCHLAF' and p.locator('[data-hud-data]').text_content() == '22:50 → 07:00 · 8 h', 'Hero HUD follows the selection')
    r.check(p.locator('.hero-visual').get_attribute('data-glass-form') == 'sleep', 'Glass object mirrors the selected form')
    p.locator('[data-select="sleep"]').press('ArrowRight')
    r.check(p.locator('[data-select="code"]').get_attribute('aria-pressed') == 'true', 'Hero arrow-key selection')
    p.locator('[data-format="json"]').click()
    r.check('"username":"demo"' in r.text('[data-conversion-example]'), 'Fictional format demo switches to JSON')
    r.check(p.locator('[data-motion-toggle]').count() == 0, 'No manual motion toggle; system preference decides')
    theme_state = "() => ({theme: document.documentElement.dataset.theme, meta: document.querySelector('meta[name=theme-color]').content, stored: localStorage.getItem('misterpfister-theme'), label: document.querySelector('[data-theme-toggle]').getAttribute('aria-label'), events: window.__themes || null})"
    r.check(p.evaluate(theme_state) == {'theme': 'dark', 'meta': '#0B0D0F', 'stored': None, 'label': 'Helles Farbschema verwenden', 'events': None}, f'Dark default theme with its theme-color and toggle label: {p.evaluate(theme_state)}')
    p.evaluate("window.__themes = []; document.addEventListener('themechange', event => __themes.push(event.detail.theme))")
    p.locator('[data-theme-toggle]').click()
    r.check(p.locator('html').get_attribute('data-theme') == 'light', 'Light theme toggle')
    r.check(p.evaluate(theme_state) == {'theme': 'light', 'meta': '#F2F3EE', 'stored': 'light', 'label': 'Dunkles Farbschema verwenden', 'events': ['light']}, f'Theme toggle stores the choice, updates theme-color and announces themechange once: {p.evaluate(theme_state)}')
    p = r.open('sechserrechner/')
    r.check(p.locator('html').get_attribute('data-theme') == 'light', 'Theme state retained across pages')
    p.locator('[data-theme-toggle]').click()
    r.check(r.text('#average') == '-.--' and p.locator('#average').get_attribute('data-state') == 'empty', 'Empty grades have no fake result')
    p.locator('.grade-grade').nth(0).fill('4,5'); p.locator('.grade-grade').nth(1).fill('6'); p.locator('.grade-weight').nth(1).fill('2')
    r.check(r.text('#average') == '5.50', 'Weighted grades accept decimal comma')
    p.locator('#targetAverage').fill('5.50')
    r.check('5.50' in r.text('#targetResult'), 'Planner exact target')
    p.locator('#targetBasis').select_option('display')
    r.check('5.48' in r.text('#targetResult'), 'Planner display-based target')
    p.locator('.settings-details').first.locator('summary').click()
    p.locator('#gradeStep').select_option('0.5')
    r.check('5.50' in r.text('#targetResult'), 'Planner rounds up to permitted grade step')
    p.locator('#scenarioGrade').fill('6')
    r.check(r.text('#scenarioResult') == '5.63', 'Scenario changes weighted result')
    p.locator('#scenarioGrade').fill('5.25')
    r.check(r.text('#scenarioResult') == '-.--', 'Scenario rejects a value outside the selected grade steps')
    p.locator('#scenarioGrade').fill('5.5')
    p.locator('.grade-grade').nth(0).fill('7')
    r.check(r.text('#average') == '-.--' and p.locator('.grade-grade').nth(0).get_attribute('aria-invalid') == 'true', 'Invalid grade clears stale result')
    p = r.open('sechserrechner/')
    r.check(p.locator('.grade-grade').nth(0).input_value() == '7', 'Unfinished/invalid local draft survives reopening')
    p.locator('.grade-grade').nth(0).fill('4.5')
    r.check(r.text('#average') == '5.50', 'Valid draft recovers without losing other rows')
    p.locator('#addEntry').click(); r.check(p.locator('.grade-row').count() == 3, 'Add grade row')
    p.locator('.grade-row').last.locator('button').click(); r.check(p.locator('.grade-row').count() == 2, 'Delete row')
    p.locator('#undoAction').click(); r.check(p.locator('.grade-row').count() == 3, 'Undo delete row')
    p.locator('#addSubject').click(); p.locator('#subjectName').fill('Mathematik'); p.locator('#subjectForm button[type=submit]').click()
    r.check(p.locator('#subjectSelect option:checked').inner_text() == 'Mathematik', 'Create subject')
    p.locator('.grade-grade').first.fill('4.75')
    p = r.open('sechserrechner/')
    r.check(p.locator('#subjectSelect option:checked').inner_text() == 'Mathematik' and r.text('#average') == '4.75', 'Subject and grades persist')
    p.locator('.settings-details').nth(1).locator('summary').click()
    with p.expect_download() as download:
        p.locator('#exportGrades').click()
    exported_path = OUT / 'test-export.json'; download.value.save_as(str(exported_path))
    exported = json.loads(exported_path.read_text())
    r.check(exported['type'] == 'misterpfister-grades' and len(exported['subjects']) == 2, 'Export serialises all subjects')
    p.on('dialog', lambda dialog: dialog.accept())
    p.locator('#importFile').set_input_files({'name': 'backup.json', 'mimeType': 'application/json', 'buffer': json.dumps(exported).encode()})
    p.wait_for_function("document.querySelector('#toastMessage').textContent==='Sicherung importiert.'")
    r.check(r.text('#average') == '4.75', 'JSON backup imports correctly')
    bad = {'name': 'bad.json', 'mimeType': 'application/json', 'buffer': b'{"version":99}'}
    p.locator('#importFile').set_input_files(bad)
    p.wait_for_function("document.querySelector('#toastMessage').textContent.includes('Keine gültige')")
    r.check(r.text('#average') == '4.75', 'Invalid import leaves existing grades intact')
    malicious = json.loads(json.dumps(exported)); malicious['subjects'][1]['name'] = '<img src=x onerror=alert(1)>'
    p.locator('#importFile').set_input_files({'name': 'text-only.json', 'mimeType': 'application/json', 'buffer': json.dumps(malicious).encode()})
    p.wait_for_function("document.querySelector('#toastMessage').textContent==='Sicherung importiert.'")
    r.check(p.locator('#subjectSelect option:checked').inner_text().startswith('<img') and p.locator('img').count() == 0, 'Imported names remain text, not executable markup')
    p.locator('#undoAction').click()
    p.locator('#saveGrades').uncheck()
    r.check(p.evaluate("localStorage.getItem('misterpfister-grades-v2')") is None, 'Turning off saving removes grade data')
    p = r.open('sechserrechner/')
    r.check(r.text('#average') == '-.--' and not p.locator('#saveGrades').is_checked(), 'Saving opt-out persists without retaining grades')
    p.locator('#pointsEarned').fill('30'); r.check(r.text('#pointsResult') == '3.50', 'Points conversion reacts immediately')
    p.locator('#pointsEarned').fill('61'); r.check(r.text('#pointsResult') == '-.--', 'Points outside maximum rejected')
    flags = "['pointsEarned', 'pointsMax', 'pointsMinGrade', 'pointsMaxGrade'].map(id => document.getElementById(id).getAttribute('aria-invalid'))"
    r.check(p.evaluate(flags) == ['true', 'false', 'false', 'false'] and r.text('#pointsError') == 'Erreichte Punkte: 0 bis 60.', f'Only the wrong points field is marked and named: {p.evaluate(flags)} {r.text("#pointsError")!r}')
    r.check(r.text('#pointsNeeded') == '36 von 60', 'Needed points stay independent of the points earned')
    p.locator('#pointsTarget').fill('5,5'); r.check(r.text('#pointsNeeded') == '54 von 60' and 'Nötig für eine 5.50' in r.text('#pointsNeededLabel'), 'Needed points for a wished grade')
    p.locator('#pointsMax').fill('47'); p.locator('#pointsTarget').fill('4'); r.check(r.text('#pointsNeeded') == '28.2 von 47', 'Needed points keep two decimals')
    p.locator('#pointsTarget').fill('6.5'); r.check(r.text('#pointsNeeded') == '–' and p.locator('#pointsTarget').get_attribute('aria-invalid') == 'true', 'Wished grade outside the scale rejected')
    p = r.open('sleepcalculator/')
    r.check(r.text('#sleepResultTime') == '22:50' and p.locator('#sleepLatency').input_value() == '10', 'Sleep initial result with 10 minutes to fall asleep')
    p.locator('#anchorTime').fill('06:45'); r.check(r.text('#sleepResultTime') == '22:35', 'Wake time updates immediately')
    invalid = lambda: p.locator('#anchorTime').get_attribute('aria-invalid') == 'true'
    for typed, expected in [('7:00', '22:50'), ('7.00', '22:50'), ('7,30', '23:20'), ('700', '22:50'), ('7', '22:50'), ('24:00', '—:—'), ('7:7', '—:—'), ('99', '—:—')]:
        p.locator('#anchorTime').fill(typed)
        r.check(r.text('#sleepResultTime') == expected and invalid() == (expected == '—:—'), f'Lenient 24-hour input: {typed} -> {expected}')
    # A half-typed time that can still become one waits while typing: no error flash, no re-render, no save. Leaving the field decides.
    p.locator('#anchorTime').fill('07:00')
    stored = "JSON.parse(localStorage.getItem('misterpfister-sleep-v2')).state.time"
    for typed in ['', '0', '2', '07:', '7.4', '064', '233', '7:5']:
        p.locator('#anchorTime').fill(typed)
        r.check(r.text('#sleepResultTime') == '22:50' and not invalid() and r.text('#sleepError') == '' and p.evaluate(stored) == '07:00', f'A half-typed time waits without an error or a save: {typed!r}')
    p.locator('#anchorTime').press('Tab')
    r.check(r.text('#sleepResultTime') == '—:—' and invalid() and r.text('#sleepError') != '', 'Leaving a half-typed time that is no time shows the error')
    p.locator('#anchorTime').fill('1'); p.locator('#anchorTime').press('Enter')
    r.check(p.locator('#anchorTime').input_value() == '01:00' and r.text('#sleepResultTime') == '16:50' and not invalid(), 'Enter completes a single digit to a full hour')
    p.locator('#anchorTime').fill('6.45'); p.locator('#anchorTime').press('Tab')
    r.check(p.locator('#anchorTime').input_value() == '06:45' and r.text('#sleepResultTime') == '22:35', 'Time input normalises to HH:MM on leave')
    p.locator('#sleepMinutes').fill('15'); r.check(r.text('#sleepResultTime') == '22:20', 'Quarter-hour durations supported')
    r.check(p.locator('[data-duration][aria-pressed=true]').count() == 0, 'No quick duration matches 8 h 15')
    p.locator('[data-duration="450"]').click()
    r.check(p.locator('#sleepHours').input_value() == '7' and p.locator('#sleepMinutes').input_value() == '30' and r.text('#sleepResultTime') == '23:05' and p.locator('[data-duration="450"]').get_attribute('aria-pressed') == 'true', 'Quick duration sets 7 h 30')
    p.locator('[data-duration="480"]').click(); p.locator('#sleepMinutes').fill('15')
    p.locator('input[value="bed"]').check(); p.locator('#anchorTime').fill('23:30'); p.locator('#sleepMinutes').fill('0')
    r.check(r.text('#sleepResultTime') == '07:40' and 'Folgetag' in r.text('#sleepDayLabel'), 'Arbitrary bedtime handles midnight')
    p.locator('#sleepLatency').fill('0'); r.check(r.text('#sleepResultTime') == '07:30', 'Zero sleep latency')
    valid_height = p.locator('.sleep-visual').bounding_box()['height']
    p.locator('#sleepHours').fill('17')
    r.check(abs(p.locator('.sleep-visual').bounding_box()['height'] - valid_height) < 2, 'Invalid sleep input keeps result panel stable')
    r.check(r.text('#sleepResultTime') == '—:—', 'Invalid sleep duration clears result, keeping layout')
    p.locator('#sleepHours').fill('7'); p.locator('#sleepMinutes').fill('23')
    r.check(r.text('#sleepResultTime') == '06:53' and p.locator('#durationSlider').input_value() == '443', 'Minute-precise duration and slider agree')
    toggle = p.locator('#showPresetForm')
    toggle.click()
    r.check(toggle.get_attribute('aria-expanded') == 'true' and toggle.get_attribute('aria-controls') == 'presetForm' and toggle.inner_text().strip() == 'Abbrechen' and p.evaluate('document.activeElement.id') == 'presetName', 'The preset form opens as a disclosure and focuses the name')
    p.keyboard.press('Escape')
    r.check(p.locator('#presetForm').is_hidden() and toggle.get_attribute('aria-expanded') == 'false' and toggle.inner_text().strip() == 'Merken' and p.evaluate('document.activeElement.id') == 'showPresetForm', 'Escape closes the preset form and returns focus to its button')
    p.locator('#showPresetForm').click(); p.locator('#presetName').fill('Mein Test'); p.locator('#presetForm button[type=submit]').click()
    r.check(p.locator('.preset-chip').count() == 3, 'Custom sleep preset created')
    p = r.open('sleepcalculator/')
    r.check(r.text('#sleepResultTime') == '06:53' and p.locator('.preset-chip').count() == 3, 'Sleep state and presets restored')
    p.locator('#sleepNow').click(); r.check(p.locator('input[value="bed"]').is_checked(), 'Now action selects bedtime mode')
    expected = p.evaluate("new Date().getHours()*60+new Date().getMinutes()")
    actual = p.locator('#anchorTime').input_value(); hh, mm = map(int, actual.split(':'))
    r.check(abs((hh*60+mm)-expected) <= 1, 'Now uses current local browser clock')
    p.locator('[aria-label="Preset Mein Test löschen"]').click(); r.check(p.locator('.preset-chip').count() == 2, 'Preset deletion')
    p.locator('#saveSleep').uncheck(); r.check(p.evaluate("localStorage.getItem('misterpfister-sleep-v2')") is None, 'Sleep opt-out removes stored data')
    p = r.open('sleepcalculator/', blocked=True)
    p.locator('#anchorTime').fill('06:45')
    r.check(r.text('#sleepResultTime') == '22:35' and 'nicht lesbar' in r.text('#sleepSaveStatus'), 'Sleep still works when Storage is blocked')
    p = r.open('sechserrechner/', blocked=True)
    p.locator('#loadExample').click()
    r.check(r.text('#average') == '5.25' and 'nicht lesbar' in r.text('#saveStatus'), 'Grades still work when Storage is blocked')
    extended(r)
    workflow(r)
    hero(r)
    instruments(r)
    dial(r)
    static_fallbacks(r)
    hero_load(r)
    home_layout(r)
    card_counts(r)
    reveals(r)
    if args.browser == 'chromium':  # WebKit on macOS skips links on Tab by default; the CSS check is about Chromium's parser
        tab_order(r)
        stylesheets(r)
    # Both motion modes, both themes and every relevant layout boundary (plus the hero without WebGL).
    small_targets = {}  # collected across the sweep, asserted once so every layout is still checked
    for route, name in [('', 'home'), ('?gl=off', 'home-fallback'), ('sechserrechner/', 'grade'), ('sleepcalculator/', 'sleep')]:
        p = r.open(route)
        if name == 'grade':
            p.locator('#loadExample').click(); p.locator('#closeToast').click()
        if name.startswith('home'):
            r.settle()
        r.check(p.evaluate(HIDDEN_FOCUSABLES) == [], f'No focusable element inside aria-hidden or role=img: {name}')
        r.check(p.evaluate(BROKEN_REFS) == [], f'ARIA id references resolve: {name} {p.evaluate(BROKEN_REFS)}')
        assets = p.evaluate(ASSET_URLS)
        r.check(assets and all(re.fullmatch(r'\.{1,2}/assets/[\w-]+\.(css|js)\?v=werkplatz-5', url) for url in assets), f'Local assets with the werkplatz-5 cache bust: {name} {assets}')
        if name in ('grade', 'sleep'):
            r.check(p.evaluate("document.querySelectorAll('canvas').length === 0 && !performance.getEntriesByType('resource').some(e => /hero-gl|workbench/.test(e.name))"), f'No WebGL and no home scripts on the tool page: {name}')
        live, shown = LIVE_RESULT[name], r.text(LIVE_RESULT[name])
        r.check(p.evaluate(f"Motion.countUp(document.querySelector('{live}'), {{to: 9}})") is False and r.text(live) == shown, f'Decorative count-up refuses the live result: {name}')
        for motion in ['reduce', 'no-preference']:
            p.emulate_media(reduced_motion=motion)
            for theme in ['dark', 'light']:
                if p.locator('html').get_attribute('data-theme') != theme:
                    p.locator('[data-theme-toggle]').click()
                    # With motion allowed the theme lands inside the view-transition callback, one frame later.
                    p.wait_for_function(f"document.documentElement.dataset.theme === '{theme}'")
                for width in [320, 370, 371, 375, 390, 402, 680, 681, 768, 900, 901, 1024, 1025, 1150, 1151, 1440, 1600, 1601, 1920]:
                    p.set_viewport_size({'width': width, 'height': 874 if width < 681 else 1000})
                    p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                    overflow = p.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)>innerWidth+1')
                    r.check(not overflow, f'No overflow: {name} {theme} {motion} {width}px' + (f' {p.evaluate(OVERFLOWING)}' if overflow else ''))
                    if width in [320, 402, 768, 1024, 1440] and motion == 'reduce' and name != 'home-fallback':
                        r.screenshot(f'{name}-{theme}-{width}.png')
                        p.screenshot(path=str(OUT / f'{name}-{theme}-{width}-viewport.png'))
                    if name == 'home' and width in [320, 375, 402]:
                        r.check(p.locator('.main-nav a').evaluate_all('els => els.length === 2 && els.every(el => el.checkVisibility())'), f'Both home links stay in the phone header: {width}')
                        r.check(p.locator('.hero-actions').bounding_box()['y'] < 400, f'Direct links before 400px: {width}')
                        r.check(p.locator('.tool-card').first.bounding_box()['y'] < 700, f'First project card begins early in the first mobile screen: {width}')
                        band = p.locator('.hero-visual').bounding_box()
                        r.check(p.locator('.glass-stage').is_visible() and band and 0 < band['height'] <= 170, f'Phones keep the glass object as a band of at most 170px: {width}')
                    if width == 402:
                        if name == 'home':
                            r.check(p.locator('.hero-actions').bounding_box()['y'] < 400, 'Direct links before 400px')
                            r.check(p.locator('[data-workbench]').is_hidden(), 'Phones skip the spatial preview')
                            r.check(p.locator('.tool-card').first.bounding_box()['y'] < 700, 'First project card begins early in the first mobile screen')
                        if name == 'grade':
                            r.check(p.locator('.grade-grade').first.bounding_box()['y'] < 700, 'First grade in first mobile screen')
                        if name == 'sleep':
                            r.check(p.locator('#anchorTime').bounding_box()['y'] < 650, 'Time input before 650px')
                        if name != 'home' and name != 'home-fallback':
                            sizes = p.locator('input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]),select').evaluate_all('(els)=>els.filter(el=>el.getBoundingClientRect().width).map(el=>parseFloat(getComputedStyle(el).fontSize))')
                            r.check(all(size >= 16 for size in sizes), f'All mobile text inputs >=16px: {name}')
                    if width in (320, 375, 768, 1440, 1920) and motion == 'reduce' and theme == 'dark' and name != 'home-fallback':
                        spare = p.evaluate("document.querySelector('.site-footer').getBoundingClientRect().bottom - document.querySelector('.footer-mark text').getBoundingClientRect().bottom")
                        r.check(spare >= 0, f'The footer mark keeps its descenders inside the footer: {name} {width}px ({spare:.1f}px)')
                    if width in (320, 402) and motion == 'reduce' and theme == 'dark':
                        small = p.evaluate(SMALL_TARGETS)
                        if small: small_targets[f'{name} {width}px'] = small
                r.check(p.evaluate(INFINITE_ANIMATIONS) == 0, f'No infinite animation: {name} {theme} {motion}')
    r.check(not r.errors, 'No JavaScript errors: ' + repr(r.errors))
    r.check(not r.network_errors, 'No failed assets: ' + repr(r.network_errors))
    r.check(not r.external, 'No external requests: ' + repr(r.external))
    r.soft(not small_targets, f'Touch targets of at least 44px on phones (320/402): {small_targets}')
    r.check(not r.soft_failures, 'Soft checks failed: ' + ' | '.join(r.soft_failures))


def workflow(r):
    p = r.open('sechserrechner/'); r.reset(); p.reload()
    focused = "document.activeElement.getAttribute('aria-label')"
    # Enter moves from a name to its grade, from a grade to the next row, and adds a row after the last grade.
    p.locator('.grade-name').first.fill('Test 1'); p.locator('.grade-name').first.press('Enter')
    r.check(p.evaluate(focused) == 'Note 1', 'Enter in a name moves to its grade')
    p.keyboard.type('5'); p.keyboard.press('Enter')
    r.check(p.evaluate(focused) == 'Note 2', 'Enter in a grade moves to the next row')
    p.keyboard.type('4,5'); p.keyboard.press('Enter')
    r.check(p.locator('.grade-row').count() == 3 and p.evaluate(focused) == 'Note 3', 'Enter after the last grade adds a row')
    p.keyboard.press('Enter')
    r.check(p.locator('.grade-row').count() == 3, 'Enter in an empty last row adds no further rows')
    r.check(r.text('#average') == '4.75', 'Keyboard entry computes the average')
    # A pointer deletion keeps the phone keyboard closed; a keyboard deletion continues in the next row.
    p.locator('.grade-row').nth(2).locator('button').click()
    r.check(p.evaluate("document.activeElement.tagName") != 'INPUT', 'Pointer deletion does not focus an input')
    r.check(p.evaluate('document.activeElement.id') == 'undoAction', 'Pointer deletion focuses "Rückgängig"')
    p.locator('#undoAction').click()
    r.check(p.locator('.grade-row').count() == 3 and p.evaluate('document.activeElement.id') == 'addEntry', 'Pointer undo focuses "Note hinzufügen", never <body>')
    p.locator('.grade-row').nth(1).locator('button').focus(); p.keyboard.press('Enter')
    r.check(p.evaluate(focused) == 'Note 2', 'Keyboard deletion focuses the next grade')
    p.locator('#undoAction').focus(); p.keyboard.press('Enter')
    r.check(p.locator('.grade-row').count() == 3 and p.evaluate(focused) == 'Note 1', 'Keyboard undo restores the row and focuses the first grade')
    # The overview appears once there are two subjects.
    r.check(p.locator('#overviewPanel').is_hidden(), 'Overview hidden with a single subject')
    p.locator('#addSubject').click(); p.keyboard.press('Escape')
    r.check(p.locator('#subjectForm').is_hidden() and p.evaluate('document.activeElement.id') == 'addSubject', 'Escape closes the new-subject form and returns focus to its button')
    p.locator('#addSubject').click(); p.locator('#subjectName').fill('Mathematik'); p.locator('#subjectForm button[type=submit]').click()
    p.locator('.grade-grade').nth(0).fill('4'); p.locator('.grade-grade').nth(1).fill('5'); p.locator('.grade-weight').nth(1).fill('3')
    rows = p.locator('#overviewRows tr')
    r.check(p.locator('#overviewPanel').is_visible() and rows.count() == 2, 'Overview appears with two subjects')
    r.check(rows.nth(1).get_attribute('aria-current') == 'true', 'Overview marks the active subject')
    r.check(rows.nth(0).locator('td').last.inner_text() == '4.75' and rows.nth(1).locator('td').last.inner_text() == '4.75', 'Overview lists rounded subject averages')
    r.check(r.text('#overviewAverage') == '4.75' and p.locator('#overviewCount').text_content() == '2 von 2 mit Noten', 'Overview mean of subject averages')
    rows.nth(0).locator('button').click()
    r.check(r.text('#subjectSelect option:checked') == 'Allgemein' and p.locator('#overviewRows tr').nth(0).get_attribute('aria-current') == 'true', 'Overview switches subjects')
    r.check(p.evaluate("document.querySelector('.input-panel').classList.contains('fits-viewport')"), 'Short input panel follows the reader on wide screens')
    # The result instrument is the sticky element now (spec §6.3); the input-panel class stays as a legacy hook.
    p.locator('#loadExample').click(); r.frames()
    sticky = p.locator('.result-panel').evaluate("el => ({fits: el.classList.contains('fits-viewport'), position: getComputedStyle(el).position})")
    r.check(p.viewport_size == {'width': 1440, 'height': 1000} and sticky == {'fits': True, 'position': 'sticky'}, f'Result instrument is sticky at 1440x1000 with the example loaded: {sticky}')
    natural = p.locator('.result-panel').evaluate('el => el.getBoundingClientRect().top + scrollY')
    header = p.locator('.site-header').bounding_box()['height']
    p.evaluate(f'scrollTo(0, {natural - header + 160})'); r.frames()
    top = p.locator('.result-panel').bounding_box()['y']
    r.check(header <= top <= header + 24, f'Sticky result stays under the header while the inputs scroll ({top:.0f}px)')
    r.check(p.locator('#compactResult').is_hidden(), 'Wide screens need no compact result bar')
    # Short laptop screens: a smaller gauge keeps the instrument sticky and whole while the inputs scroll.
    for w, h in [(1366, 657), (1024, 640), (1280, 560)]:
        p.set_viewport_size({'width': w, 'height': h}); p.evaluate('scrollTo(0, 0)'); r.frames()
        natural = p.locator('.result-panel').evaluate('el => el.getBoundingClientRect().top + scrollY'); bar = p.locator('.site-header').bounding_box()['height']
        p.evaluate(f'scrollTo(0, {natural - bar + 160})'); r.frames()
        box = p.locator('.result-panel').bounding_box()
        sticky = p.locator('.result-panel').evaluate("el => el.classList.contains('fits-viewport') && getComputedStyle(el).position === 'sticky'")
        r.check(sticky and bar <= box['y'] <= bar + 24 and box['y'] + box['height'] <= h, f'Result instrument stays sticky and whole at {w}x{h}: top {box["y"]:.0f}, bottom {box["y"] + box["height"]:.0f}')
    p.set_viewport_size({'width': 1440, 'height': 1000})
    p.evaluate('scrollTo(0, 0)'); p.locator('#undoAction').click()
    r.check(p.locator('.grade-grade').first.input_value() == '5' and p.locator('.grade-row').count() == 3, 'Undo removes the example again')
    # Phones: the undo notice sits next to the rows and is scrolled into view.
    p.set_viewport_size({'width': 390, 'height': 700})
    p.locator('.grade-row').first.scroll_into_view_if_needed()
    p.locator('.grade-row').first.locator('button').click(); p.wait_for_timeout(300)
    box = p.locator('#gradeToast').bounding_box()
    r.check(box is not None and box['y'] >= 0 and box['y'] + box['height'] <= 700, 'Mobile undo notice is visible after deleting')
    p.locator('#undoAction').click()
    r.check(p.locator('.grade-grade').first.input_value() == '5', 'Mobile undo restores the row')
    p.set_viewport_size({'width': 1440, 'height': 1000})
    # Backups from before the shared weight still import; their separate simulation weight is ignored.
    legacy = {'type': 'misterpfister-grades', 'version': 1, 'active': 0, 'subjects': [{'name': 'Alt', 'entries': [{'name': '', 'grade': '5', 'weight': '1'}], 'rounding': '0.01', 'gradeStep': '0.01', 'target': '4.00', 'nextWeight': '1', 'scenario': '5.00', 'scenarioWeight': '3', 'basis': 'exact'}]}
    p.once('dialog', lambda dialog: dialog.accept())
    p.locator('#importFile').set_input_files({'name': 'legacy.json', 'mimeType': 'application/json', 'buffer': json.dumps(legacy).encode()})
    p.wait_for_function("document.querySelector('#toastMessage').textContent==='Sicherung importiert.'")
    r.check(r.text('#subjectSelect option:checked') == 'Alt' and r.text('#scenarioWeightLabel') == 'mit Gewicht 1' and 'scenarioWeight' not in p.evaluate("localStorage.getItem('misterpfister-grades-v2')"), 'Legacy backups with a separate simulation weight still import')


def extended(r):
    p = r.open('sechserrechner/'); r.reset(); p.reload()
    p.locator('.grade-grade').nth(0).fill('4,5'); p.locator('.grade-grade').nth(1).fill('6'); p.locator('.grade-weight').nth(1).fill('2')
    p.locator('#scenarioGrade').fill('6'); p.locator('#nextWeight').fill('2')
    r.check(r.text('#scenarioResult') == '5.70' and r.text('#scenarioWeightLabel') == 'mit Gewicht 2', 'Simulation uses the weight of the next grade')
    p.locator('#nextWeight').fill('0')
    r.check(r.text('#scenarioResult') == '-.--' and 'prüfen' in r.text('#targetResult'), 'Invalid next weight clears simulation and plan')
    p.locator('#nextWeight').fill('1')
    p.locator('.grade-weight').first.fill('')
    p.reload(); r.check(r.text('#average') == '-.--' and p.locator('.grade-grade').nth(1).input_value() == '6', 'Incomplete weight draft survives real reload without losing other grades')
    p.locator('.grade-weight').first.fill('1')
    r.check(r.text('#average') == '5.50', 'Draft completes after reload')
    p.locator('.settings-details').nth(1).locator('summary').click()
    p.locator('#renameSubject').fill('Testfach'); p.locator('#renameSubject').press('Tab')
    r.check(r.text('#subjectSelect option:checked') == 'Testfach', 'Rename subject')
    p.once('dialog', lambda dialog: dialog.dismiss()); p.locator('#deleteSubject').click()
    r.check(r.text('#subjectSelect option:checked') == 'Testfach' and p.locator('#gradeToast').is_hidden(), 'Cancelled subject deletion keeps the subject')
    messages = []
    p.once('dialog', lambda dialog: (messages.append(dialog.message), dialog.accept())); p.locator('#deleteSubject').click()
    r.check(messages and 'Testfach' in messages[0] and '2 Noten' in messages[0], 'Subject deletion asks with name and grade count')
    p.locator('#undoAction').click()
    r.check(r.text('#average') == '5.50' and r.text('#subjectSelect option:checked') == 'Testfach', 'Undo subject deletion restores values')
    backup = p.evaluate("JSON.parse(localStorage.getItem('misterpfister-grades-v2'))")
    p.once('dialog', lambda dialog: dialog.dismiss())
    replacement = json.loads(json.dumps(backup)); replacement['subjects'][0]['name'] = 'Ersetzt'
    p.locator('#importFile').set_input_files({'name':'replace.json','mimeType':'application/json','buffer':json.dumps(replacement).encode()})
    p.wait_for_timeout(100)
    r.check(r.text('#subjectSelect option:checked') == 'Testfach', 'Cancelled replacement import keeps subjects')
    for content in [b'not json', b' ' * (512*1024+1), json.dumps({'type':'misterpfister-grades','version':1,'subjects':[]}).encode()]:
        p.locator('#importFile').set_input_files({'name':'invalid.json','mimeType':'application/json','buffer':content})
        p.wait_for_timeout(100)
        r.check(r.text('#average') == '5.50', 'Invalid/oversize import cannot destroy grades')
    invalid = json.loads(json.dumps(backup)); invalid['subjects'][0]['entries'][0]['grade'] = '6.01'
    p.locator('#importFile').set_input_files({'name':'range.json','mimeType':'application/json','buffer':json.dumps(invalid).encode()})
    p.wait_for_timeout(100); r.check('zwischen 1 und 6' in r.text('#toastMessage'), 'Import validates grade bounds')
    for id_, value in [('pointsMax','0'),('pointsMax','-1'),('pointsEarned','-1')]:
        p.locator('#'+id_).fill(value); r.check(r.text('#pointsResult') == '-.--', 'Invalid points clear result')
    # Delayed undo must not silently overwrite newer edits.
    p.locator('#loadExample').click()
    names = p.locator('#subjectSelect option').all_text_contents()
    r.check(r.text('#subjectSelect option:checked') == 'Beispiel' and 'Testfach' in names and r.text('#average') == '5.25' and r.text('#toastMessage') == 'Beispiel als neues Fach «Beispiel» geöffnet.', f'With own grades the example opens as a new subject: {names}')
    p.locator('.grade-grade').first.fill('6')
    p.once('dialog', lambda dialog: dialog.dismiss()); p.locator('#undoAction').click()
    r.check(p.locator('.grade-grade').first.input_value() == '6', 'Cancelled delayed undo preserves newer edits')
    p.once('dialog', lambda dialog: dialog.accept()); p.locator('#undoAction').click()
    r.check(r.text('#average') == '5.50' and p.locator('#subjectSelect option').all_text_contents() == ['Testfach'], 'Confirmed delayed undo restores previous state, without the example subject')
    # A separate same-origin tab has access to real stored drafts.
    tab = r.context.new_page(); tab.goto(args.base_url.rstrip('/')+'/sechserrechner/')
    r.check(tab.locator('#average').inner_text() == '5.50', 'Second tab restores native saved grade data'); tab.close()
    p.evaluate("localStorage.setItem('misterpfister-grades-v2','unreadable backup')")
    p.reload(); p.locator('.grade-grade').first.fill('5')
    r.check(p.evaluate("localStorage.getItem('misterpfister-grades-v2')") == 'unreadable backup', 'Unreadable backup is not overwritten by edits')
    p.locator('#saveGrades').uncheck(); p.locator('#saveGrades').check()
    r.check('Lokal gespeichert' in r.text('#saveStatus'), 'Explicit storage reset recovers backup')
    # Quota fault injection only. Normal storage checks above remain native.
    p.evaluate("() => { Storage.prototype.setItem=function(){throw new DOMException('quota','QuotaExceededError')}; }")
    p.locator('.grade-grade').first.fill('4.75')
    r.check(r.text('#average') == '4.75' and 'nicht möglich' in r.text('#saveStatus'), 'Quota errors do not break calculation')
    p.locator('#saveGrades').uncheck()
    r.check(p.evaluate("localStorage.getItem('misterpfister-grades-v2')") is None, 'Opt-out deletes data before quota-sensitive preference write')
    p = r.open('sleepcalculator/'); r.reset(); p.reload()
    p.locator('#anchorTime').fill('0645'); r.check(p.locator('#anchorTime').input_value() == '06:45', 'Numeric HHMM input normalises to 24-hour time')
    p.locator('#sleepHours').fill(''); r.check(r.text('#sleepResultTime') == '—:—', 'Incomplete sleep input has no stale result')
    p.reload(); r.check(r.text('#sleepResultTime') == '22:35', 'Sleep reload restores last valid settings')
    p.locator('#showPresetForm').click(); p.locator('#presetName').fill('Testzeit'); p.locator('#presetForm button[type=submit]').click()
    p.locator('#sleepMinutes').fill('')
    p.locator('[aria-label="Preset Testzeit löschen"]').click(); p.reload()
    r.check(p.locator('.preset-chip').count() == 2, 'Preset deletion persists even during incomplete time edit')
    p.locator('.preset-delete').first.click(); p.locator('#undoPreset').click()
    r.check(p.locator('.preset-chip').count() == 2, 'Undo preset deletion')
    p.locator('input[value=bed]').check(); p.locator('#anchorTime').fill('23:50'); p.locator('#sleepLatency').fill('30')
    r.check(r.text('#onsetDay') == 'Folgetag' and r.text('#bedDay') == '', 'Timeline day labels only mark midnight crossings')
    p.locator('#anchorTime').fill('09:00'); r.check(r.text('#wakeDay') == '', 'Same-day times carry no day label')
    p.locator('#sleepLatency').fill('0')
    r.check(p.locator('#latencyArc').get_attribute('stroke-dasharray').startswith('0 '), 'Zero latency has no arc')
    r.check(r.text('#legendLatency') == 'Sofort eingeschlafen', f'Zero latency reads "Sofort eingeschlafen": {r.text("#legendLatency")!r}')
    p.locator('#sleepLatency').fill('180')
    r.check(r.text('#legendLatency') == '3 h Einschlafen', f'Latency legend names the time to fall asleep: {r.text("#legendLatency")!r}')
    p.locator('#sleepLatency').fill('0')
    p.locator('#saveSleep').uncheck(); p.reload()
    r.check(not p.locator('#saveSleep').is_checked() and r.text('#sleepResultTime') == '22:50', 'Sleep opt-out survives reload')
    p = r.open(); p.emulate_media(reduced_motion='no-preference')
    for name in ['grade', 'sleep', 'code']:
        p.locator(f'[data-select="{name}"]').focus(); p.keyboard.press('Space')
        r.check(p.locator(f'[data-select="{name}"]').get_attribute('aria-pressed') == 'true' and p.locator('[data-workbench]').get_attribute('data-selection') == name, 'Keyboard selects '+name)
    p.locator('[data-select=code]').press('Home'); r.check(p.locator('[data-select=grade]').get_attribute('aria-pressed') == 'true', 'Home key selects first preview')
    p.locator('[data-select=grade]').press('End'); r.check(p.locator('[data-select=code]').get_attribute('aria-pressed') == 'true', 'End key selects last preview')
    r.check(p.locator('.scene').get_attribute('aria-hidden') == 'true' and p.locator('[data-module][tabindex="-1"]').count() == 3, 'Spatial cards stay out of the tab order and accessibility tree')
    # Motion allowed: magnetic primary button, decorative count-up, format flip (all finite, text stays synchronous).
    # Switching to motion mid-page starts the load choreography; hover once the buttons have settled.
    waits(p, "[...document.querySelectorAll('.hero-actions a')].every(el => el.getAnimations().length === 0)", 3000)
    button = p.locator('.hero-actions a').first; box = button.bounding_box()
    p.mouse.move(box['x'] + box['width'] * .8, box['y'] + box['height'] * .5); p.mouse.move(box['x'] + box['width'] * .95, box['y'] + box['height'] * .7)
    offset = numbers(button.evaluate("el => el.style.getPropertyValue('--mag-x') + ' ' + el.style.getPropertyValue('--mag-y')"))
    r.check(len(offset) == 2 and 0 < abs(offset[0]) <= 8 and abs(offset[1]) <= 6, f'Magnetic primary button follows the pointer within 8/6px: {offset}')
    p.mouse.move(5, 500)
    r.check(waits(p, "!document.querySelector('.hero-actions a').style.getPropertyValue('--mag-x')"), 'Magnetic offset resets when the pointer leaves')
    p.locator('.card-grade').scroll_into_view_if_needed()
    r.check(waits(p, "[...document.querySelectorAll('.tool-card [data-count-to]')].every(el => el.textContent === el.dataset.countTo)", 3000), 'Decorative card numbers count up to their final values')
    flip = p.locator('[data-conversion-format]')
    flip.evaluate("el => { window.__flip = false; new MutationObserver(() => { if (el.classList.contains('is-flipping')) window.__flip = true; }).observe(el, {attributes: true, attributeFilter: ['class']}); }")
    p.locator('[data-format="json"]').click()
    r.check(flip.text_content().startswith('.json') and p.locator('[data-format="json"]').get_attribute('aria-pressed') == 'true', 'Format demo text switches synchronously')
    r.check(waits(p, 'window.__flip === true') and waits(p, "!document.querySelector('[data-conversion-format]').classList.contains('is-flipping')", 4000), 'Format badge flips once and cleans up')
    p.locator('[data-format="csv"]').click(); p.evaluate('scrollTo(0, 0)')
    p.locator('[data-select=grade]').click()
    p.locator('.module-sleep').click(position={'x': 150, 'y': 60}); p.wait_for_timeout(100)
    r.check(p.url == args.base_url.rstrip('/')+'/' and p.locator('[data-workbench]').get_attribute('data-selection') == 'sleep', 'A card behind the front card comes forward first')
    p.locator('.module-sleep').click(position={'x': 150, 'y': 60}); p.wait_for_url('**/sleepcalculator/')
    r.check(p.locator('#sleepClock').is_visible(), 'The front card opens its tool')
    p.go_back(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    p.locator('.hero-actions a').first.click(); p.wait_for_url('**/sechserrechner/')
    r.check(p.locator('h1').inner_text() == 'Noten. Mit Überblick.', 'Native hero navigation')
    p.go_back(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    r.check(p.locator('[data-workbench]').is_visible(), 'Browser back restores workbench')
    p.go_forward(); p.wait_for_url('**/sechserrechner/'); p.reload()
    r.check(p.locator('#gradeForm').is_visible(), 'Forward and reload keep tool operational')
    p.locator('.main-nav a').last.click(); p.wait_for_url('**/sleepcalculator/')
    r.check(p.locator('#sleepClock').is_visible(), 'Native navigation between tools')
    p.locator('.brand').click(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    r.check(p.locator('[data-workbench]').get_attribute('data-selection') == 'sleep' and waits(p, "document.querySelector('.hero-visual').dataset.glassForm === 'sleep'"), 'Returning from the sleep tool preselects sleep')
    p.locator('.card-sleep').click(); p.wait_for_url('**/sleepcalculator/')
    p.go_back(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    r.check(p.locator('.card-sleep').is_visible(), 'Project card navigation and back')


def waits(page, expression, timeout=2500):
    try:
        page.wait_for_function(expression, timeout=timeout)
        return True
    except Exception:
        return False


def numbers(value):
    return [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', value or '')]


def hero(r):
    """Hero engine tiers, DOM state contract, HUD and selection events (spec §5.4, §5.5, §5.6)."""
    p = r.open(init=BENCH_EVENTS)
    glass = r.settle()
    r.check(glass['api'] == [glass['state'], glass['tier']], f'HeroGL API mirrors the DOM state contract: {glass}')
    r.check(glass['form'] == 'grade' and p.locator('[data-workbench]').get_attribute('data-selection') == 'grade', 'A fresh visit without referrer starts on grade')
    r.check(p.evaluate('__bench') == [{'name': 'grade', 'source': 'init'}], 'Workbench announces its initial selection once, as init')
    hud = lambda: (p.locator('[data-hud-channel]').text_content(), p.locator('[data-hud-data]').text_content())
    r.check(hud() == ('CH 01 · NOTEN', 'Ø 5.25 · 4 Noten'), 'HUD starts on the grade channel')
    r.disclosure_is_instant('details.story-details', 'the project story details')
    p.evaluate('scrollTo(0, 0)')
    structure = p.evaluate('''() => ({
      outside: !document.querySelector('[data-workbench] .glass-stage, [data-workbench] canvas, [data-workbench] .glass-fallback, [data-workbench] .orb-captions'),
      canvas: document.querySelectorAll('.hero-visual .glass-stage canvas.glass-canvas').length,
      fallback: [...document.querySelectorAll('.glass-fallback svg[data-form]')].map(el => el.dataset.form),
      captions: [...document.querySelectorAll('.orb-captions li[data-form]')].map(el => el.dataset.form),
      stageHidden: document.querySelector('.glass-stage').getAttribute('aria-hidden')})''')
    r.check(structure == {'outside': True, 'canvas': 1, 'fallback': ['grade', 'sleep', 'code'], 'captions': ['grade', 'sleep', 'code'], 'stageHidden': 'true'}, f'Canvas, fallback specimens and captions sit outside the workbench: {structure}')
    about = p.evaluate("({labelled: document.querySelector('#hintergrund').getAttribute('aria-labelledby'), heading: document.querySelector('#about-title').innerText, words: document.querySelectorAll('#about-title .w').length})")
    r.check(about == {'labelled': 'about-title', 'heading': 'Technik verstehen.\nDinge selber bauen.', 'words': 5}, f'About section is labelled by its heading; the word spans keep the text: {about}')
    frames = glass['frames']
    p.locator('[data-select="code"]').click()
    r.check(p.evaluate('__bench')[-1] == {'name': 'code', 'source': 'user'}, 'A dock selection dispatches benchselect from the user')
    r.check(hud() == ('CH 03 · DATEN', '.spass → .csv · lokal') and p.locator('.hero-visual').get_attribute('data-glass-form') == 'code', 'HUD and glass form follow the data preview')
    link = p.locator('[data-scene-link]')
    r.check(link.get_attribute('target') == '_blank' and 'noopener' in (link.get_attribute('rel') or '') and link.get_attribute('href').startswith('https://github.com/'), 'The data preview opens GitHub in a new tab without opener access')
    if glass['tier'] == 'still':
        r.check(waits(p, f'HeroGL.stats.frames > {frames}'), 'Still tier redraws the selected form without an animation loop')
    p.locator('[data-select="grade"]').click()
    r.check(link.get_attribute('target') is None and link.get_attribute('rel') is None and hud()[0] == 'CH 01 · NOTEN', 'Tool previews open in the same tab again')
    frames = p.evaluate(GLASS)['frames']
    p.locator('[data-theme-toggle]').click()
    r.check(p.locator('html').get_attribute('data-theme') == 'light', 'Theme toggle on the hero page')
    if glass['tier'] == 'still':
        r.check(waits(p, f'HeroGL.stats.frames > {frames}'), 'Still tier renders the porcelain theme on themechange')
        r.check(p.evaluate('HeroGL.stats.backing[0] * HeroGL.stats.backing[1]') <= 1.1e6, 'Hero canvas backing store stays at or below 1.1 MP')
    p.locator('[data-theme-toggle]').click()
    r.check(p.evaluate('HeroGL.state') == glass['state'], 'Hero returns to its settled state after theme and selection changes')
    # Forced tiers via query flags (spec §5.5.1).
    p = r.open('?gl=still')
    still = r.settle()
    r.check(still['tier'] in ('still', 'fallback') and still['state'] == still['tier'], f'?gl=still forces the still tier (or the fallback without WebGL): {still}')
    before = len(r.warnings)
    p = r.open('?gl=off')
    off = r.settle()
    r.check(off == {**off, 'state': 'fallback', 'tier': 'fallback', 'frames': 0} and off['api'] == ['fallback', 'fallback'], f'?gl=off shows the CSS/SVG fallback without rendering: {off}')
    opacity = lambda selector: p.locator(selector).evaluate('el => getComputedStyle(el).opacity')
    r.frames()
    r.check(p.locator('.glass-fallback svg[data-form=grade]').is_visible() and opacity('.glass-fallback') == '1' and opacity('.glass-fallback svg[data-form=grade]') == '1' and opacity('.glass-fallback svg[data-form=sleep]') == '0', 'Fallback shows the grade specimen')
    r.check(opacity('.glass-canvas') == '0' and opacity('.glass-placeholder') == '0', 'Fallback hides the canvas and the droplet placeholder')
    p.locator('[data-select="sleep"]').click()
    waits(p, "getComputedStyle(document.querySelector('.glass-fallback svg[data-form=sleep]')).opacity === '1'")
    r.check(p.locator('.hero-visual').get_attribute('data-glass-form') == 'sleep' and opacity('.glass-fallback svg[data-form=sleep]') == '1' and opacity('.glass-fallback svg[data-form=grade]') == '0', 'Fallback crossfades to the sleep specimen on selection')
    r.check(not [w for w in r.warnings[before:] if 'HeroGL' in w], 'The ?gl=off fallback logs no warning')
    # No WebGL at all (the CI path on GPU-less runners): one warning, never a console error.
    before = len(r.warnings)
    p = r.open(init="(() => { const native = HTMLCanvasElement.prototype.getContext; HTMLCanvasElement.prototype.getContext = function (type, ...rest) { return /webgl/i.test(type) ? null : native.call(this, type, ...rest); }; })();")
    none = r.settle()
    warned = [w for w in r.warnings[before:] if 'HeroGL' in w]
    r.check(none['state'] == 'fallback' and none['tier'] == 'fallback' and len(warned) == 1, f'Without WebGL the hero falls back with exactly one warning: {none} {warned}')
    # Forced colours: decorative layers make way for system colours (emulation is Chromium-only).
    if args.browser == 'chromium':
        p = r.open(media={'forced_colors': 'active'})
        forced = r.settle()
        r.check(forced['state'] == 'fallback', f'Forced colours use the static fallback: {forced}')


def instruments(r):
    """Grade instruments added in Werkplatz 5 (spec §6.4, §6.5)."""
    p = r.open('sechserrechner/'); r.reset(); p.reload(); r.frames()
    p.set_viewport_size({'width': 402, 'height': 874}); r.frames()
    r.check(p.locator('#entryChart').is_hidden(), 'Phones hide the empty chart on a first visit')
    p.set_viewport_size({'width': 1440, 'height': 1000}); r.frames()
    r.disclosure_is_instant('.settings-details', 'the rounding settings')
    p.evaluate('scrollTo(0, 0)')
    dash = lambda selector: numbers(p.locator(selector).evaluate('el => el.style.strokeDasharray'))
    wrap = p.locator('.gauge-wrap').evaluate("el => ({empty: el.classList.contains('is-empty'), intro: el.hasAttribute('data-intro')})")
    r.check(wrap == {'empty': True, 'intro': False} and p.locator('#scalePointer').is_hidden() and dash('#scaleFill')[:1] == [0], f'Empty gauge: no bead, no fill, intro finished: {wrap}')
    r.check(p.locator('#entryChart').get_attribute('data-empty') == 'true' and p.locator('#entryChart .chart-bars i').count() == 0, 'Empty chart without bars')
    r.check(p.locator('#scenarioDelta').get_attribute('data-dir') == 'none' and p.locator('#scenarioDelta').text_content() == '', 'No delta chip without a current grade')
    r.check(p.locator('#resultSubject').text_content() == p.locator('#subjectSelect option:checked').text_content() == 'Allgemein', 'Result instrument names the active subject')
    r.check(p.locator('#subjectSummary').is_hidden(), 'Subject summary hidden with one subject')
    r.check(p.locator('#pointsResult').evaluate('el => el.previousElementSibling && el.previousElementSibling.tagName') == 'SPAN', 'The label span stays directly before the points result')
    r.check(p.locator('#pointsFormula').text_content() == '1 + (45 ÷ 60) × 5 = 4.75' and p.locator('#pointsNeededFormula').text_content() == '(4 − 1) ÷ 5 × 60 = 36', 'Points formulas show the calculation')
    p.locator('#pointsEarned').fill('30')
    r.check(p.locator('#pointsFormula').text_content() == '1 + (30 ÷ 60) × 5 = 3.50' and abs(r.number('.points-meter:not(.is-need)', '--p') - .5) < 1e-3, 'Points formula and meter follow the input')
    p.locator('#pointsEarned').fill('61')
    r.check(p.locator('#pointsFormula').text_content() == '–' and r.text('#pointsResult') == '-.--', 'Invalid points clear the formula')
    p.locator('#pointsEarned').fill('45')
    p.locator('#loadExample').click()
    r.check(p.locator('#gradeToast').evaluate('el => getComputedStyle(el).position') == 'fixed', 'Undo notice floats on wide screens')
    covers = p.evaluate("() => { const t = document.querySelector('#gradeToast').getBoundingClientRect(), g = document.querySelector('.result-panel').getBoundingClientRect(); return Math.min(t.right, g.right) > Math.max(t.left, g.left) && Math.min(t.bottom, g.bottom) > Math.max(t.top, g.top); }")
    r.check(not covers, 'The floating undo notice never covers the result instrument')
    p.locator('#closeToast').click()
    r.check(p.evaluate('document.activeElement && document.activeElement.id') == 'addEntry', 'Closing the notice with a pointer focuses "Note hinzufügen", never <body>')
    r.check(p.locator('.grade-row').evaluate_all('rows => rows.length === 4 && rows.every(row => row.querySelectorAll("button").length === 1)'), 'Each grade row keeps exactly one button')
    r.frames()
    bars = p.locator('#entryChart .chart-bars i:not(.is-ghost)')
    heights = bars.evaluate_all("els => els.map(el => parseFloat(el.style.getPropertyValue('--h')))")
    r.check(bars.count() == 4 and p.locator('#entryChart').get_attribute('data-empty') == 'false', 'Chart draws one bar per valid grade after Beispiel laden')
    r.check([round(h, 3) for h in heights] == [.7, .9, .8, 1.0], f'Bar heights encode the grades: {heights}')
    r.check(p.locator('#entryChart .chart-bars i.is-ghost').count() == 1 and p.locator('#entryChart .chart-line.is-avg').is_visible(), 'Chart shows the simulation as a ghost bar and the average line')
    p.locator('.grade-grade').first.fill('7')
    r.check(p.locator('#entryChart').get_attribute('data-invalid') == 'true', 'An invalid grade dims the chart bars')
    p.locator('.grade-grade').first.fill('4.5')
    r.check(p.locator('#entryChart').get_attribute('data-invalid') == 'false' and r.text('#average') == '5.25', 'The chart is live again once the grade is valid')
    # Planning: the slider takes the panel width, planning starts in the first 1440x900 screen, 901-1150px rows keep a usable name field,
    # and the two subject icon buttons stay on one row.
    sizes = {}
    for w, h in [(1440, 900), (1151, 900), (1150, 900), (901, 900), (768, 1024), (402, 874), (360, 800)]:
        p.set_viewport_size({'width': w, 'height': h}); p.evaluate('scrollTo(0, 0)'); r.frames()
        sizes[w] = p.evaluate("() => ({slider: Math.round(document.querySelector('#scenarioSlider').getBoundingClientRect().width), next: Math.round(document.querySelector('.next-panel').getBoundingClientRect().top), name: Math.round(document.querySelector('.grade-name').getBoundingClientRect().width), bar: [...new Set([...document.querySelectorAll('#addSubject, #openSubjectSettings')].map(el => Math.round(el.getBoundingClientRect().top)))].length})")
    p.set_viewport_size({'width': 1440, 'height': 1000}); r.frames()
    r.check(all(sizes[w]['slider'] >= 400 for w in (1440, 1151, 768)), f'The simulation slider gets the panel width: {[(w, v["slider"]) for w, v in sizes.items()]}')
    r.check(sizes[1440]['next'] < 900, f'The planning panel starts in the first 1440x900 screen ({sizes[1440]["next"]}px)')
    r.check(sizes[901]['name'] >= 150 and sizes[1150]['name'] >= 150, f'Rows at 901-1150px keep a usable exam name field: {sizes[901]["name"]}/{sizes[1150]["name"]}px')
    r.check(all(v['bar'] == 1 for v in sizes.values()), f'The subject icon buttons share one row: {[(w, v["bar"]) for w, v in sizes.items()]}')
    r.check(abs(r.number('#gradeScale', '--avg') - .85) < 1e-3 and abs(dash('#scaleFill')[0] - 63.75) < .01 and p.locator('#scalePointer').is_visible(), 'Gauge fill and bead sit at 5.25')
    delta = p.locator('#scenarioDelta')
    r.check(re.match(r'^[▲▼=] [+−]?\d\.\d\d', delta.text_content()) and delta.text_content() == '▼ −0.05 ggü. jetzt' and delta.get_attribute('data-dir') == 'down', f'Delta chip shows a lower simulation: {delta.text_content()}')
    arc = dash('#scenarioArc')
    r.check(p.locator('#scenarioPointer').is_visible() and abs(r.number('#gradeScale', '--sim') - .84) < 1e-3 and len(arc) == 4 and arc[0] == 0 and abs(arc[2] - .75) < .01, f'Simulation ring and arc on the gauge: {arc}')
    p.locator('#scenarioGrade').fill('6')
    r.check(re.match(r'^[▲▼=] [+−]?\d\.\d\d', delta.text_content()) and delta.text_content() == '▲ +0.15 ggü. jetzt' and delta.get_attribute('data-dir') == 'up', f'Delta chip shows a higher simulation: {delta.text_content()}')
    p.locator('#scenarioGrade').fill('5.25')
    r.check(re.match(r'^[▲▼=] [+−]?\d\.\d\d', delta.text_content()) and delta.text_content() == '= 0.00 ggü. jetzt' and delta.get_attribute('data-dir') == 'flat', f'Delta chip shows an unchanged simulation: {delta.text_content()}')
    chip = lambda value: p.locator(f'[data-next-weight="{value}"]')
    chip('2').click()
    r.check(p.locator('#nextWeight').input_value() == '2' and r.text('#scenarioWeightLabel') == 'mit Gewicht 2', 'Weight chip 2 sets the next weight')
    r.check(chip('2').get_attribute('aria-pressed') == 'true' and chip('1').get_attribute('aria-pressed') == 'false', 'Weight chips mirror the next weight')
    r.check(p.locator('#entryChart .chart-bars i.is-ghost').evaluate("el => el.style.getPropertyValue('--w')") == '2', 'Ghost bar width follows the next weight')
    p.locator('#nextWeight').fill('0.5')
    r.check(chip('0.5').get_attribute('aria-pressed') == 'true' and chip('2').get_attribute('aria-pressed') == 'false' and r.text('#scenarioWeightLabel') == 'mit Gewicht 0.5', 'Typing a weight presses the matching chip')
    chip('2').click()
    p.locator('#targetAverage').fill('5.5')
    r.check(r.text('#targetResult') == 'Du brauchst mindestens eine 6.00.' and p.locator('#targetResult').get_attribute('data-tone') is None, 'Reachable target asks for a grade')
    r.check(p.locator('#entryChart .chart-line.is-need').is_visible() and abs(r.number('#entryChart .chart-line.is-need', '--h') - 1) < 1e-3, 'Chart marks the needed grade')
    r.check(p.locator('#targetPointer').is_visible() and abs(r.number('#gradeScale', '--target') - .9) < 1e-3, 'Target triangle sits at the target')
    p.locator('#targetAverage').fill('5.6')
    r.check(p.locator('#targetResult').get_attribute('data-tone') == 'danger' and p.locator('#entryChart .chart-line.is-need').is_hidden(), 'Unreachable target is marked as danger')
    r.check(r.text('#targetDetail').startswith('Mit einer 6.00 höchstens ≈ 5.5000'), f'An unreachable target names the best reachable average: {r.text("#targetDetail")!r}')
    p.locator('#targetAverage').fill('1')
    r.check(p.locator('#targetResult').get_attribute('data-tone') == 'secured' and 'erreicht' in r.text('#targetResult') and p.locator('#entryChart .chart-line.is-need').is_hidden(), 'A target already secured gets the secured tone')
    p.locator('#targetAverage').fill('4.00')
    # The glint appears after discrete events only, never under reduced motion.
    p.emulate_media(reduced_motion='no-preference')
    p.locator('.grade-metric').evaluate("el => { window.__glint = false; new MutationObserver(() => { if (el.classList.contains('is-glint')) window.__glint = true; }).observe(el, {attributes: true, attributeFilter: ['class']}); }")
    p.locator('#scenarioGrade').fill('5')
    r.check(p.evaluate('__glint') is False, 'Typing does not glint the result')
    p.locator('#loadExample').click()
    r.check(waits(p, 'window.__glint === true', 1500) and r.text('#average') == '5.25', 'Beispiel laden glints the result without changing the number')
    p.emulate_media(reduced_motion='reduce'); p.locator('#closeToast').click()
    p.locator('#addSubject').click(); p.locator('#subjectName').fill('Physik'); p.locator('#subjectForm button[type=submit]').click()
    r.check(p.locator('#resultSubject').text_content() == 'Physik', 'Result instrument follows a new subject')
    summary = p.locator('#subjectSummary')
    r.check(summary.is_visible() and 'Fächer' in summary.text_content() and summary.text_content() == '2 Fächer · Gesamt 5.25 ↓' and summary.get_attribute('href') == '#overviewPanel', f'Subject summary with two subjects: {summary.text_content()}')
    rows = p.locator('#overviewRows tr')
    cells = rows.evaluate_all('''rows => rows.map(row => ({current: row.getAttribute('aria-current'), badge: row.querySelector('th small.tag') ? row.querySelector('th small.tag').textContent : null,
      badgeInButton: !!row.querySelector('th button small, th button .tag'), bar: !!row.querySelector('td:last-child span.ov-bar[aria-hidden="true"]'), value: row.querySelector('td:last-child').innerText}))''')
    r.check([c['badge'] for c in cells] == [None, 'Aktiv'] and [c['current'] == 'true' for c in cells] == [False, True] and all(c['bar'] and not c['badgeInButton'] for c in cells) and cells[0]['value'] == '5.25', f'Overview rows carry a bar and an "Aktiv" badge outside the button: {cells}')
    summary.click(); r.frames()
    box = p.locator('#overviewPanel').bounding_box()
    r.check(0 <= box['y'] < 1000, 'Subject summary jumps to the overview')
    p.evaluate('scrollTo(0, 0)')
    p.locator('#openSubjectSettings').click(); r.frames()
    opened = p.locator('.settings-details').evaluate_all('els => els.map(el => el.open)')
    r.check(opened == [False, True] and p.evaluate("document.activeElement === document.querySelector('#subjectSettings summary')"), f'Settings button opens "Fach & Datensicherung" and focuses it: {opened}')
    # A subject switch is a discrete event: it glints with motion allowed and never under reduced motion.
    p.emulate_media(reduced_motion='no-preference'); p.evaluate('window.__glint = false')
    p.locator('#subjectSelect').select_option(index=0)
    r.check(waits(p, 'window.__glint === true', 1500) and r.text('#average') == '5.25' and p.locator('#resultSubject').text_content() == 'Allgemein', 'Switching subjects glints the result and renames the instrument')
    p.emulate_media(reduced_motion='reduce'); p.evaluate('window.__glint = false')
    p.locator('#subjectSelect').select_option(index=1); r.frames()
    r.check(p.evaluate('__glint') is False and p.locator('#resultSubject').text_content() == 'Physik', 'Reduced motion switches subjects without the glint')
    # Row layout (spec §6.3): index and "#" column only from 681px; at 370px and below the name takes its own line.
    row_layout = '''() => { const row = document.querySelector('.grade-row'), top = s => Math.round(row.querySelector(s).getBoundingClientRect().top);
      const hidden = el => !el.getClientRects().length || getComputedStyle(el).display === 'none';
      return {index: getComputedStyle(row, '::before').display !== 'none', hash: !hidden(document.querySelector('.grade-columns > :first-child')), optional: !hidden(document.querySelector('.col-optional')),
        columns: !hidden(document.querySelector('.grade-columns')), name: top('.grade-name'), nameBottom: Math.round(row.querySelector('.grade-name').getBoundingClientRect().bottom), grade: top('.grade-grade'), weight: top('.grade-weight'), remove: top('button')}; }'''
    wide = p.evaluate(row_layout)
    r.check(wide['index'] and wide['hash'] and wide['optional'] and wide['name'] == wide['grade'] == wide['weight'], f'Wide rows show the index, the "#" column and "(optional)" on one line: {wide}')
    p.set_viewport_size({'width': 360, 'height': 800}); r.frames()
    narrow = p.evaluate(row_layout)
    r.check(not narrow['index'] and not narrow['columns'] and narrow['nameBottom'] <= narrow['grade'] and narrow['grade'] == narrow['weight'] and abs(narrow['remove'] - narrow['grade']) <= 2, f'At 360px the exam name takes line 1; grade, weight and remove share line 2: {narrow}')
    # Phones: the compact result appears once the instrument has scrolled away; the notice sits in the flow.
    p.set_viewport_size({'width': 402, 'height': 874}); r.frames()
    phone = p.evaluate(row_layout)
    r.check(not phone['index'] and not phone['hash'] and not phone['optional'] and phone['columns'] and phone['name'] == phone['grade'] == phone['weight'], f'At 402px rows stay on one line without index, "#" and "(optional)": {phone}')
    p.locator('.grade-row').first.locator('.grade-grade').fill('4.5')
    p.locator('.next-panel').scroll_into_view_if_needed()
    r.check(waits(p, "!document.querySelector('#compactResult').hidden") and p.locator('#compactResult').is_visible(), 'Phones show the compact result after scrolling past the instrument')
    r.check(r.text('#compactAverage') == 'Noch kein gültiger Schnitt' or r.text('#compactAverage').startswith('Schnitt '), 'Compact result carries the average')
    p.evaluate('scrollTo(0, 0)')
    r.check(waits(p, "document.querySelector('#compactResult').hidden"), 'Compact result hides again at the top')
    p.locator('.grade-row').first.locator('button').click()
    r.check(p.locator('#gradeToast').evaluate('el => getComputedStyle(el).position') in ('static', 'relative'), 'Phones keep the undo notice in the panel flow')
    p.locator('#undoAction').click()
    p.set_viewport_size({'width': 1440, 'height': 1000})
    # A full subject (100 rows): one bar per grade, a dense chart, no further rows; undo restores the previous subjects.
    full = {'type': 'misterpfister-grades', 'version': 1, 'active': 0, 'subjects': [{'name': 'Voll', 'entries': [{'name': '', 'grade': str(4 + (i % 5) * .5), 'weight': '1'} for i in range(100)], 'rounding': '0.01', 'gradeStep': '0.01', 'target': '4.00', 'nextWeight': '1', 'scenario': '5.00', 'basis': 'exact'}]}
    p.once('dialog', lambda dialog: dialog.accept())
    p.locator('#importFile').set_input_files({'name': 'full.json', 'mimeType': 'application/json', 'buffer': json.dumps(full).encode()})
    p.wait_for_function("document.querySelector('#toastMessage').textContent==='Sicherung importiert.'"); r.frames()
    chart = p.locator('#entryChart').evaluate("el => ({bars: el.querySelectorAll('.chart-bars i:not(.is-ghost)').length, dense: el.hasAttribute('data-dense'), rows: document.querySelectorAll('.grade-row').length, add: document.querySelector('#addEntry').disabled, average: document.querySelector('#average').textContent})")
    r.check(chart == {'bars': 100, 'dense': True, 'rows': 100, 'add': True, 'average': '5.00'}, f'100 grades: 100 bars in a dense chart and no 101st row: {chart}')
    p.locator('#undoAction').click()
    r.check(r.text('#subjectSelect option:checked') == 'Physik' and p.locator('#entryChart').get_attribute('data-dense') is None and p.locator('#addEntry').is_enabled(), 'Undoing the import restores the subjects and the normal chart')


def dial(r):
    """Direct manipulation of the 24-hour dial (spec §7.3, §7.4)."""
    p = r.open('sleepcalculator/'); r.reset(); p.reload(); r.frames()
    anchor, end = p.locator('#dialAnchor'), p.locator('#dialEnd')
    aria = lambda loc: loc.evaluate("el => ({now: el.getAttribute('aria-valuenow'), text: el.getAttribute('aria-valuetext'), label: el.getAttribute('aria-label'), disabled: el.getAttribute('aria-disabled'), icon: el.querySelector('.dial-bead').dataset.icon, role: el.getAttribute('role'), tab: el.tabIndex, tip: el.querySelector('.dial-tip').textContent})")
    value = lambda selector: p.locator(selector).input_value()
    r.check(aria(anchor) == {'now': '420', 'text': '07:00 Aufstehen', 'label': 'Aufstehzeit am Zifferblatt', 'disabled': 'false', 'icon': 'sun', 'role': 'slider', 'tab': 0, 'tip': '07:00'}, f'Anchor handle describes the wake time: {aria(anchor)}')
    r.check(aria(end) == {'now': '480', 'text': '8 h Schlaf, ins Bett um 22:50', 'label': 'Schlafdauer, Ende bei der Bettzeit', 'disabled': 'false', 'icon': 'moon', 'role': 'slider', 'tab': 0, 'tip': '8 h'}, f'End handle describes the duration; its tip shows the length only: {aria(end)}')
    r.check(p.locator('#sleepClock [role=slider], #sleepClock [tabindex]').count() == 0 and p.locator('.sleep-clock-wrap').get_attribute('data-ready') is not None, 'Handles sit outside role=img and the dial is ready')
    geometry = '''el => { const w = document.querySelector('.sleep-clock-wrap').getBoundingClientRect(), h = el.getBoundingClientRect();
      const dx = h.left + h.width / 2 - (w.left + w.width / 2), dy = h.top + h.height / 2 - (w.top + w.height / 2);
      return {angle: (Math.atan2(dx, -dy) * 180 / Math.PI + 360) % 360, radius: Math.hypot(dx, dy) / w.width}; }'''
    def on_ring(loc, degrees):
        r.frames(); g = loc.evaluate(geometry)
        return min(abs(g['angle'] - degrees), 360 - abs(g['angle'] - degrees)) < 2.5 and abs(g['radius'] - 127 / 360) < .02
    r.check(on_ring(anchor, 105) and on_ring(end, 342.5), 'Handles sit on the ring at 07:00 and 22:50')
    anchor.focus(); p.keyboard.press('ArrowRight')
    r.check(value('#anchorTime') == '07:05' and r.text('#sleepResultTime') == '22:55' and anchor.get_attribute('aria-valuenow') == '425', 'Dial ArrowRight moves the wake time by 5 minutes')
    p.keyboard.press('Shift+ArrowRight'); r.check(value('#anchorTime') == '07:06', 'Dial Shift+ArrowRight moves by 1 minute')
    p.keyboard.press('PageDown'); r.check(value('#anchorTime') == '06:06', 'Dial PageDown moves back an hour')
    p.keyboard.press('Home'); r.check(value('#anchorTime') == '00:00' and anchor.get_attribute('aria-valuenow') == '0', 'Dial Home goes to 00:00')
    p.keyboard.press('ArrowLeft'); r.check(value('#anchorTime') == '23:55', 'Dial ArrowLeft wraps past midnight')
    p.keyboard.press('ArrowUp'); r.check(value('#anchorTime') == '00:00', 'Dial ArrowUp wraps forward')
    p.keyboard.press('End'); r.check(value('#anchorTime') == '23:55', 'Dial End goes to 23:55')
    p.keyboard.press('PageUp'); r.check(value('#anchorTime') == '00:55', 'Dial PageUp wraps an hour forward')
    p.keyboard.press('a'); r.check(value('#anchorTime') == '00:55', 'Unhandled keys leave the dial alone')
    p.reload(); r.check(value('#anchorTime') == '00:55', 'Dial keyboard changes are saved')
    p.locator('#anchorTime').fill('07:00')
    end.focus(); p.keyboard.press('PageUp')
    r.check(value('#sleepHours') == '9' and value('#sleepMinutes') == '0' and value('#durationSlider') == '540' and end.get_attribute('aria-valuenow') == '540', 'End handle PageUp adds an hour of sleep')
    p.keyboard.press('End'); r.check(value('#sleepHours') == '16' and value('#sleepMinutes') == '0', 'End handle End sets 16 h')
    p.keyboard.press('ArrowRight'); r.check(value('#sleepHours') == '16' and value('#sleepMinutes') == '0', 'End handle clamps at 16 h')
    p.keyboard.press('Home'); r.check(value('#sleepHours') == '1' and value('#sleepMinutes') == '0', 'End handle Home sets 1 h')
    p.keyboard.press('ArrowRight'); r.check(value('#sleepHours') == '1' and value('#sleepMinutes') == '5', 'End handle ArrowRight adds 5 minutes')
    p.keyboard.press('Shift+ArrowLeft'); r.check(value('#sleepMinutes') == '4', 'End handle Shift+ArrowLeft removes 1 minute')
    p.keyboard.press('PageDown'); r.check(value('#sleepHours') == '1' and value('#sleepMinutes') == '0', 'End handle clamps at 1 h')
    p.locator('#sleepHours').fill('8'); p.locator('#sleepMinutes').fill('0')
    r.check(r.text('#sleepResultTime') == '22:50' and abs(r.number('#durationSlider', '--p') - 420 / 900) < 1e-3, 'Duration slider progress follows the length')
    # Pointer drag: 1:1 while dragging, one storage write on release.
    r.frames()
    ring = p.locator('.sleep-clock-wrap').bounding_box(); cx, cy, half = ring['x'] + ring['width'] / 2, ring['y'] + ring['height'] / 2, ring['width'] / 2
    p.evaluate("() => { window.__writes = 0; const native = Storage.prototype.setItem; Storage.prototype.setItem = function (key, value) { if (key === 'misterpfister-sleep-v2') window.__writes++; return native.call(this, key, value); }; }")
    # During a drag: storage writes, the drag class, the screen-reader summary and the tip (mouse at 901px and up: outside the ring, in view).
    drag_state = '''() => { const w = document.querySelector('.sleep-clock-wrap').getBoundingClientRect(), tip = document.querySelector('.dial-handle.is-dragging .dial-tip'), t = tip && tip.getBoundingClientRect();
      const shown = tip && tip.checkVisibility({opacityProperty: true, visibilityProperty: true});
      return {writes: __writes, dragging: document.querySelector('.sleep-clock-wrap').classList.contains('is-dragging'), summary: document.querySelector('#sleepSummary').textContent,
        tip: shown ? {text: tip.textContent, outside: Math.hypot(t.left + t.width / 2 - w.left - w.width / 2, t.top + t.height / 2 - w.top - w.height / 2) > w.width * 127 / 360 + 4, inView: t.left >= 0 && t.top >= 0 && t.right <= innerWidth && t.bottom <= innerHeight} : null}; }'''
    def drag(handle, angles):
        box = handle.bounding_box(); p.mouse.move(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2); p.mouse.down()
        for degrees in angles:
            rad = math.radians(degrees)
            p.mouse.move(cx + math.sin(rad) * .95 * half, cy - math.cos(rad) * .95 * half, steps=2)
        r.frames()
        during = p.evaluate(drag_state)
        p.mouse.up(); r.frames()
        return during
    summary = p.locator('#sleepSummary').text_content()
    during = drag(anchor, [100, 95, 90])
    r.check(during['writes'] == 0 and during['dragging'] and value('#anchorTime') == '06:00', f'Anchor follows the pointer without storage writes during the drag: {during}')
    r.check(during['tip'] == {'text': '06:00', 'outside': True, 'inView': True}, f'A mouse drag at 1440px shows the time tip outside the ring, in view: {during["tip"]}')
    r.check(during['summary'] == summary, 'The screen-reader summary stays quiet during a drag')
    r.check(r.text('#sleepResultTime') == '21:50' and p.evaluate('__writes') == 1 and not p.locator('.sleep-clock-wrap').evaluate("el => el.classList.contains('is-dragging')"), 'Releasing the anchor saves once')
    r.check(on_ring(anchor, 90), 'Anchor handle rests at 06:00 after the drag')
    r.check(waits(p, "document.querySelector('#sleepSummary').textContent.startsWith('Ins Bett um 21:50')", 1500), f'The summary follows once the drag has settled: {p.locator("#sleepSummary").text_content()!r}')
    r.check(p.evaluate('document.activeElement.id') == 'dialAnchor' and not anchor.evaluate("el => el.matches(':focus-visible')"), 'A mouse drag focuses the handle without the keyboard focus ring')
    p.keyboard.press('Shift+Tab'); p.keyboard.press('Tab')
    r.check(p.evaluate('document.activeElement.id') == 'dialAnchor' and anchor.evaluate("el => el.matches(':focus-visible')"), 'Tabbing back to the handle shows the focus ring')
    during = drag(end, [320, 340, 357.5])
    r.check(value('#sleepHours') == '6' and value('#sleepMinutes') == '0' and r.text('#sleepResultTime') == '23:50', 'Dragging the end handle sets the duration')
    drag(end, [340, 300, 260, 230, 215, 207.5, 200, 195])
    r.check(value('#sleepHours') == '16' and value('#sleepMinutes') == '0', 'Dragging past 16 h clamps on the side it came from')
    p.locator('#sleepHours').fill('8')
    # Ring tap moves the nearest handle.
    rad = math.radians(112.5)
    p.mouse.click(cx + math.sin(rad) * .8 * half, cy - math.cos(rad) * .8 * half)
    r.check(value('#anchorTime') == '07:30' and r.text('#sleepResultTime') == '23:20', 'A tap on the ring moves the nearest handle')
    bar = p.locator('.night-bar')
    r.check(p.locator('.night-bar .midnight').get_attribute('hidden') is None and bar.evaluate("el => [el.style.getPropertyValue('--lat'), el.style.getPropertyValue('--len')]") == ['10', '480'], 'Night bar marks midnight for a night across 00:00')
    mid = bar.evaluate("el => [parseFloat(el.style.getPropertyValue('--mid')), el.dataset.edge]")
    r.check(abs(mid[0] - 40 / 490) < 1e-3 and mid[1] == 'start', f'The midnight tick sits at its share of the night (23:20 bed, 490 min) and hugs the start edge: {mid}')
    p.locator('#anchorTime').fill('12:00')
    r.check(p.locator('.night-bar .midnight').get_attribute('hidden') is not None, 'Night bar drops the midnight tick for a same-day plan')
    # Bed before 17:00 of the previous day is no longer "Am Vorabend" (07:00 wake, 16 h, 180 min: bed 12:00, onset 15:00).
    p.locator('#anchorTime').fill('07:00'); p.locator('#sleepHours').fill('16'); p.locator('#sleepLatency').fill('180')
    r.check(r.text('#sleepResultTime') == '12:00' and r.text('#sleepDayLabel') == 'Am Vortag', f'A noon bedtime the day before reads "Am Vortag": {r.text("#sleepDayLabel")!r}')
    days = [p.locator(f'#{id_}Day').text_content() for id_ in ('bed', 'onset', 'wake')]
    r.soft(days == ['Vortag', 'Vortag', ''], f'The timeline agrees with the readout for times before 17:00 of the previous day (bed, onset, wake): {days}')
    p.locator('#sleepHours').fill('8'); p.locator('#sleepLatency').fill('10'); p.locator('#anchorTime').fill('07:30')
    r.check(p.locator('.preset-chip').evaluate_all('els => els.length > 0 && els.every(el => ["wake", "bed"].includes(el.dataset.mode))'), 'Preset chips show their mode')
    chip = p.locator('.preset-chip').first.evaluate("el => ({mode: el.dataset.mode, icon: !!el.querySelector('button i.preset-icon'), name: el.querySelector('.preset-name')?.textContent, time: el.querySelector('.preset-time')?.textContent, label: el.querySelector('button').getAttribute('aria-label')})")
    r.check(chip == {'mode': 'wake', 'icon': True, 'name': 'Früh raus', 'time': '06:30', 'label': 'Früh raus: aufstehen um 06:30'}, f'Default preset chip shows icon, name and time with an unchanged label: {chip}')
    pressed = lambda: p.locator('.preset-chip').evaluate_all("els => els.map(el => el.querySelector('button').getAttribute('aria-pressed'))")
    r.check(pressed() == ['false', 'false'], f'No preset is pressed for a plan that matches none: {pressed()}')
    p.locator('#anchorTime').fill('06:30')
    r.check(pressed() == ['true', 'false'], f'The preset that matches the plan is pressed: {pressed()}')
    p.locator('#anchorTime').fill('07:30')
    # Switching the mode keeps the same night (07:30 wake, 8 h, 10 min: bed 23:20); the other end becomes the typed time.
    p.locator('input[value="bed"]').check()
    a, e = aria(anchor), aria(end)
    r.check(value('#anchorTime') == '23:20' and r.text('#sleepResultTime') == '07:30', f'Bed mode keeps the night: bed {value("#anchorTime")}, wake {r.text("#sleepResultTime")}')
    r.check('Ins Bett' in a['text'] and a['text'] == '23:20 Ins Bett' and a['icon'] == 'moon' and a['label'] == 'Bettzeit am Zifferblatt', f'Bed mode turns the anchor into the bedtime: {a}')
    r.check('aufstehen um' in e['text'] and e['text'] == '8 h Schlaf, aufstehen um 07:30' and e['icon'] == 'sun' and e['label'] == 'Schlafdauer, Ende bei der Aufstehzeit', f'Bed mode turns the end handle into the wake time: {e}')
    p.locator('input[value="wake"]').check()
    r.check('Aufstehen' in anchor.get_attribute('aria-valuetext'), 'Wake mode valuetext says Aufstehen')
    r.check(value('#anchorTime') == '07:30' and r.text('#sleepResultTime') == '23:20', 'Switching back returns to the same wake time')
    # Invalid input: handles stay put, disabled and silent; the readout keeps its height.
    readout = p.locator('.clock-readout').bounding_box()['height']
    p.locator('#sleepHours').fill('17')
    r.check(anchor.get_attribute('aria-disabled') == 'true' and end.get_attribute('aria-disabled') == 'true' and anchor.get_attribute('aria-valuetext') == 'Eingaben prüfen' and p.locator('.sleep-visual').get_attribute('data-invalid') == 'true', 'Invalid input disables the dial handles')
    r.check(abs(p.locator('.clock-readout').bounding_box()['height'] - readout) < 2, 'Invalid input keeps the readout height')
    anchor.focus(); p.keyboard.press('ArrowRight')
    r.check(value('#anchorTime') == '07:30', 'Disabled handles ignore keys')
    p.locator('#sleepHours').fill('8')
    r.check(anchor.get_attribute('aria-disabled') == 'false' and p.locator('.sleep-visual').get_attribute('data-invalid') == 'false', 'Valid input enables the handles again')
    # Phones: the compact bar appears once the dial is scrolled away.
    p.set_viewport_size({'width': 402, 'height': 874}); p.evaluate('scrollTo(0, 0)'); r.frames()
    compact = p.locator('#sleepCompact')
    r.check(compact.is_hidden(), 'Sleep compact bar hidden while the dial is visible')
    p.locator('.sleep-tuning').scroll_into_view_if_needed(); p.evaluate('scrollBy(0, 300)')
    r.check(waits(p, "!document.querySelector('#sleepCompact').hidden") and compact.is_visible(), 'At 402px the compact bar appears after scrolling past the dial')
    r.check(compact.text_content() == f"Ins Bett {r.text('#sleepResultTime')} · {p.locator('#sleepDayLabel').text_content()}", f'Compact bar repeats the result: {compact.text_content()}')
    p.evaluate('scrollTo(0, 0)')
    r.check(waits(p, "document.querySelector('#sleepCompact').hidden"), 'Compact bar hides again at the top')
    # Single-column tablets (up to 900px) get the compact bar as well.
    p.set_viewport_size({'width': 768, 'height': 1024}); r.frames()
    p.locator('.sleep-tuning').scroll_into_view_if_needed(); p.evaluate('scrollBy(0, 400)')
    r.check(waits(p, "!document.querySelector('#sleepCompact').hidden") and compact.is_visible(), 'At 768px the compact bar appears after scrolling past the dial')
    # Wide screens (spec §7.2): the night panel stays under the header while the tuning scrolls; no compact bar.
    p.set_viewport_size({'width': 1440, 'height': 1000}); p.evaluate('scrollTo(0, 0)'); r.frames()
    visual = p.locator('.sleep-visual')
    natural = visual.evaluate('el => el.getBoundingClientRect().top + scrollY'); header = p.locator('.site-header').bounding_box()['height']
    p.evaluate(f'scrollTo(0, {natural - header + 64})'); r.frames()
    top = visual.bounding_box()['y']
    r.check(visual.evaluate('el => getComputedStyle(el).position') == 'sticky' and header <= top <= header + 24, f'The night panel stays under the header at 1440x1000 ({top:.0f}px)')
    r.check(p.locator('#sleepCompact').is_hidden(), 'Wide screens need no sleep compact bar')
    # Short desktops: sticky while the panel fits (measured), otherwise the compact bar takes over.
    for w, h in [(1366, 657), (1024, 600)]:
        p.set_viewport_size({'width': w, 'height': h}); p.evaluate('scrollTo(0, 0)'); r.frames()
        natural = visual.evaluate('el => el.getBoundingClientRect().top + scrollY'); bar = p.locator('.site-header').bounding_box()['height']
        p.evaluate(f'scrollTo(0, {natural - bar + 64})'); r.frames()
        box = visual.bounding_box()
        r.check(visual.evaluate('el => getComputedStyle(el).position') == 'sticky' and bar <= box['y'] <= bar + 24 and box['y'] + box['height'] <= h and p.locator('#sleepCompact').is_hidden(), f'The night panel stays sticky and whole at {w}x{h}: {box["y"]:.0f}..{box["y"] + box["height"]:.0f}')
    p.set_viewport_size({'width': 1280, 'height': 560}); p.evaluate('scrollTo(0, 0)'); r.frames()
    p.locator('.sleep-tuning').scroll_into_view_if_needed(); p.evaluate('scrollBy(0, 300)')
    r.check(visual.evaluate('el => getComputedStyle(el).position') != 'sticky' and waits(p, "!document.querySelector('#sleepCompact').hidden") and compact.is_visible(), 'At 1280x560 the panel no longer fits: the compact bar appears instead of a sticky panel')
    p.set_viewport_size({'width': 1440, 'height': 1000}); p.evaluate('scrollTo(0, 0)')


def hero_load(r):
    """Load choreography (spec §5.3): lead, CTAs and note only move and are never sliced; nothing is cut once it has settled."""
    freeze = "document.addEventListener('DOMContentLoaded', () => document.getAnimations().forEach(a => a.pause()));"
    for viewport in [{'width': 1440, 'height': 1000}, {'width': 1024, 'height': 768}, {'width': 390, 'height': 844}]:
        p = r.open(init=freeze, media={'reduced_motion': 'no-preference'}, viewport=viewport)
        frozen = p.evaluate(FROZEN_LOAD, [0, 100, 250, 400, 550, 700, 900])
        r.check(frozen['animated'] == 4 and not frozen['sliced'], f'The load choreography never slices the lead, the CTAs or the note: {viewport["width"]}px {frozen}')
        p.evaluate('document.getAnimations().forEach(a => a.play())')
        r.settle()
        r.check(waits(p, "!document.getAnimations().some(a => a.timeline === document.timeline && a.playState === 'running')", 5000), 'The load choreography finishes')
        cut = p.evaluate(CUT_TEXT, HERO_TEXT)
        r.check(cut == [], f'No hero text is clipped or faded after the load: {viewport["width"]}px {cut}')


def home_layout(r):
    """Hero fold and front label on short laptop screens, the story badge on narrow phones (spec §5.2, §5.7)."""
    p = r.open(); r.settle()
    box = "s => { const b = document.querySelector(s).getBoundingClientRect(); return {left: b.left, top: b.top, right: b.right, bottom: b.bottom}; }"
    for w, h in [(1280, 720), (1366, 768), (1440, 790), (1536, 730), (1100, 700), (1024, 600), (1366, 657), (901, 1000), (1000, 1000), (1100, 1000), (1200, 1000), (1440, 1000)]:
        p.set_viewport_size({'width': w, 'height': h}); p.evaluate('scrollTo(0, 0)'); r.frames()
        dock, note, label = p.evaluate(box, '.scene-dock'), p.evaluate(box, '.scene-note'), p.evaluate(box, '.module-grade')
        r.check(dock['bottom'] <= h and note['bottom'] <= h, f'Dock and preview note in the first screen at {w}x{h}: {dock["bottom"]:.0f}/{note["bottom"]:.0f}')
        # The front label may sit next to the dock but not on it (2px of anti-aliased shadow allowed).
        apart = dock['top'] - label['bottom'] >= -2 or min(dock['right'], label['right']) <= max(dock['left'], label['left'])
        (r.check if h == 1000 else r.soft)(apart, f'The front label clears the dock at {w}x{h} (gap {dock["top"] - label["bottom"]:.0f}px)')
    for w in [320, 340, 360, 390]:
        p.set_viewport_size({'width': w, 'height': 844})
        for fmt in ['json', 'csv']:
            p.locator(f'[data-format="{fmt}"]').click(); r.frames()
            badge, demo = p.evaluate(box, '[data-conversion-format]'), p.evaluate(box, '.story-demo')
            r.check(demo['left'] <= badge['left'] and badge['right'] <= demo['right'], f'The {fmt} badge stays inside the demo card at {w}px: {badge["left"]:.0f}..{badge["right"]:.0f} in {demo["left"]:.0f}..{demo["right"]:.0f}')
    p.set_viewport_size({'width': 1440, 'height': 1000})


def card_counts(r):
    """Decorative card numbers on a page loaded with motion (spec §4.5): they count once in view, from data-count-from, and the mini gauge follows every frame."""
    p = r.open(media={'reduced_motion': 'no-preference'})
    p.evaluate('''() => { window.__counts = []; window.__gauge = [];
      const gauge = document.querySelector('.card-grade .mini-gauge'), mean = document.querySelector('.card-grade [data-count-to]');
      for (const el of document.querySelectorAll('.tool-card [data-count-to]')) new MutationObserver(() => {
        __counts.push([el.dataset.countFrom || '0', el.textContent]);
        if (el === mean) __gauge.push([el.textContent, gauge.style.getPropertyValue('--v'), gauge.querySelector('.g-value').textContent]);
      }).observe(el, {childList: true, characterData: true, subtree: true}); }''')
    p.locator('.card-grade').scroll_into_view_if_needed()
    r.check(waits(p, "[...document.querySelectorAll('.tool-card [data-count-to]')].every(el => el.textContent === el.dataset.countTo)", 3000), 'With motion the card numbers count up to their final values')
    counts, gauge = p.evaluate('[__counts, __gauge]')
    follows = [(text, v) for text, v, shown in gauge if shown != text or abs(float(v) - min(1, max(0, (float(text) - 1) / 5))) > 1e-3]
    r.check(len(gauge) > 3 and not follows, f'The card gauge follows the counting number in every frame ({len(gauge)} frames, off: {follows[:3]})')
    below = [value for start, value in counts if float(value) < float(start)]
    r.soft(counts and not below, f'Card grades count up from data-count-from and never show a value below the 1-6 scale ({len(counts)} frames, below: {below[:4]})')


def reveals(r):
    """Scroll reveals have settled once their block is fully in view (spec §4.4)."""
    for route in ['', 'sleepcalculator/']:
        for viewport in [{'width': 1440, 'height': 900}, {'width': 390, 'height': 844}]:
            p = r.open(route, media={'reduced_motion': 'no-preference'}, viewport=viewport)
            count = p.evaluate("document.querySelectorAll('.reveal').length")
            moving = p.evaluate(REVEALS)
            r.check(count > 0 and moving == [], f'Reveals have settled once fully in view: {route or "home"} {viewport["width"]}x{viewport["height"]} {moving}')


def tab_order(r):
    """Every Tab stop is visible, at least 8x8 px and scrolled into view: no invisible focus targets (spec §9)."""
    for route in ['', 'sechserrechner/', 'sleepcalculator/']:
        for viewport in [{'width': 1440, 'height': 1000}, {'width': 390, 'height': 844}]:
            p = r.open(route, viewport=viewport)
            if route == 'sechserrechner/':
                r.reset(); p.reload(); p.locator('#loadExample').click(); p.reload(wait_until='networkidle')  # four saved rows, fresh focus start
            stops, bad = 0, []
            for _ in range(200):
                p.keyboard.press('Tab'); r.frames()
                stop = p.evaluate(TAB_STOP)
                if stop in (None, 'again'):
                    break
                stops += 1
                if stop['bad']: bad.append(stop['name'])
            r.check(stops >= 12 and not bad, f'Every Tab stop is visible: {route or "home"} {viewport["width"]}px, {stops} stops {bad}')


def stylesheets(r):
    """Chromium accepts every declaration, selector and condition of the site's stylesheets (apart from deliberate cross-engine CSS)."""
    checked = set()
    for route in ['', 'sechserrechner/', 'sleepcalculator/']:
        p = r.open(route)
        items = []
        for href in p.evaluate("[...document.querySelectorAll('link[rel=stylesheet]')].map(link => link.href)"):
            name = href.split('/')[-1].split('?')[0]; checked.add(name)
            items += [(kind, name, line, a, b) for kind, line, a, b in css_items(p.evaluate('url => fetch(url).then(response => response.text())', href))]
        result = p.evaluate(CSS_CHECK, items)
        rejected = [item for item in result['bad'] if not CSS_ALLOWED.match(item)]
        r.check(result['tested'] > 1000 and not rejected, f'Chromium accepts every stylesheet rule: {route or "home"} ({result["tested"]} declarations, {result["skipped"]} with scoped variables untested) {rejected}')
    r.check(checked == {'core.css', 'home.css', 'grades.css', 'sleep.css'}, f'All four stylesheets were checked: {sorted(checked)}')


def static_fallbacks(r):
    """No JavaScript and an engine that never starts (spec §5.6)."""
    browser = r.context.browser
    context = browser.new_context(java_script_enabled=False, viewport={'width': 1440, 'height': 1000}, locale='de-CH', reduced_motion='reduce')
    page = context.new_page()
    page.on('console', lambda message: r.errors.append('no-js: ' + message.text) if message.type == 'error' else None)
    page.on('response', lambda response: r.network_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
    r.watch_requests(page)
    base = args.base_url.rstrip('/') + '/'
    page.goto(base, wait_until='networkidle')
    style = lambda selector, prop: page.locator(selector).evaluate(f'el => getComputedStyle(el).{prop}')
    r.check(page.locator('h1').inner_text() == 'Kleine Ideen.\nEchte Tools.' and page.locator('.tool-card').count() == 2 and page.locator('.tool-card').first.is_visible(), 'Without JavaScript the home content is complete')
    r.check(page.locator('.hero-visual').get_attribute('data-glass-state') == 'boot' and style('.glass-fallback', 'opacity') == '1' and (style('.glass-placeholder', 'display') == 'none' or style('.glass-placeholder', 'opacity') == '0'), 'Without JavaScript the specimen replaces the droplet placeholder')
    for route, heading in [('sechserrechner/', 'Noten. Mit Überblick.'), ('sleepcalculator/', 'Zeit, abzuschalten.')]:
        page.goto(base + route, wait_until='networkidle')
        r.check(page.locator('h1').inner_text() == heading and page.locator('.noscript').is_visible(), f'Without JavaScript {route} explains what is missing')
        if route == 'sechserrechner/':
            r.check(page.locator('.calculator-layout').is_hidden() and page.locator('.points-cards').is_hidden(), 'Without JavaScript the grade calculator and the points cards stay hidden')
    context.close()
    # Engine never starts (blocked or broken script): the CSS failsafe reveals the specimen after 4 s.
    page = r.context.new_page()
    page.on('pageerror', lambda error: r.errors.append('failsafe: ' + str(error))); r.watch_requests(page)
    page.route('**/assets/hero-gl.js*', lambda route: route.fulfill(status=200, content_type='text/javascript', body='/* blocked */'))
    page.goto(base, wait_until='networkidle')
    r.check(page.locator('.hero-visual').get_attribute('data-glass-state') == 'boot', 'A missing engine leaves the hero in boot')
    page.wait_for_timeout(4300)
    r.check(page.locator('.glass-fallback').evaluate('el => getComputedStyle(el).opacity') == '1' and page.locator('.glass-placeholder').evaluate('el => getComputedStyle(el).opacity') == '0', 'CSS failsafe reveals the specimen when the engine never starts')
    page.close()


with sync_playwright() as playwright:
    browser = getattr(playwright, args.browser).launch(executable_path=args.chromium, headless=True)
    review = Review(browser)
    status = 'incomplete'
    try:
        run(review)
        status = 'pass'
    except AssertionError as error:
        status = f'fail: {error}'
        print(f'FAIL after {len(review.results)} passed browser assertions', flush=True)
        raise
    finally:
        report = {'mode': 'real HTTP navigation with native Storage', 'browser': args.browser, 'version': browser.version, 'status': status, 'assertions': len(review.results), 'passed': review.results, 'soft_failures': review.soft_failures, 'page_errors': review.errors, 'warnings': review.warnings, 'not_verified': ['Physical iPhone and native keyboard', 'FPS/Lighthouse scores', 'Live hero tier on a real GPU'], 'storage_faults': 'Explicit SecurityError and QuotaExceededError injection, separate from native persistence tests'}
        (OUT / 'browser-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        browser.close()
    print(f"PASS: {len(review.results)} browser assertions. Mode: {report['mode']}")
