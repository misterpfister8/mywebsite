"""Browser regression checks.

Default: real HTTP navigation and native localStorage against a local server.
--offline-fixture: embed the identical assets and substitute an in-memory Storage
object, for environments whose browser policy blocks all navigation. This mode
DOES NOT verify native navigation, deployed asset delivery, or real-origin storage.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
parser.add_argument('--offline-fixture', action='store_true')
parser.add_argument('--chromium', default=None)
parser.add_argument('--output', default=str(ROOT / 'test-results'))
args = parser.parse_args()
OUT = Path(args.output)
OUT.mkdir(parents=True, exist_ok=True)


def fixture(route, storage, blocked=False):
    from bs4 import BeautifulSoup
    path = ROOT / route / 'index.html'
    doc = BeautifulSoup(path.read_text(), 'html.parser')
    for tag in doc.select('link[rel="stylesheet"]'):
        asset = (path.parent / tag['href'].split('?')[0]).resolve()
        style = doc.new_tag('style'); style.string = asset.read_text(); tag.replace_with(style)
    for tag in doc.select('script[src]'):
        asset = (path.parent / tag['src'].split('?')[0]).resolve()
        script = doc.new_tag('script'); script.string = asset.read_text()
        if tag.has_attr('defer'):
            tag.decompose(); doc.body.append(script)
        else:
            tag.replace_with(script)
    shim = doc.new_tag('script')
    if blocked:
        shim.string = "Object.defineProperty(window,'localStorage',{configurable:true,get(){throw new DOMException('Storage blocked','SecurityError')}});"
    else:
        encoded = json.dumps(storage).replace('<', '\\u003c')
        shim.string = f"""window.__fixtureStore = {encoded};
Object.defineProperty(window,'localStorage',{{configurable:true,value:{{
 getItem(k){{return Object.hasOwn(window.__fixtureStore,k)?window.__fixtureStore[k]:null}},
 setItem(k,v){{window.__fixtureStore[String(k)]=String(v)}},
 removeItem(k){{delete window.__fixtureStore[k]}},
 clear(){{window.__fixtureStore={{}}}},
 key(i){{return Object.keys(window.__fixtureStore)[i]??null}},
 get length(){{return Object.keys(window.__fixtureStore).length}}
}}}});"""
    doc.head.insert(0, shim)
    return str(doc)


class Review:
    def __init__(self, browser):
        self.context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='de-CH', timezone_id='Europe/Zurich', color_scheme='dark', reduced_motion='reduce')
        self.page = None; self.route = ''; self.storage = {}; self.results = []; self.errors = []; self.blocked = False

    def open(self, route='', blocked=False):
        if self.page:
            if args.offline_fixture and not self.blocked:
                self.storage = self.page.evaluate('window.__fixtureStore || {}')
            self.page.close()
        self.page = self.context.new_page(); self.page.set_default_timeout(5000)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.route = route; self.blocked = blocked
        if args.offline_fixture:
            self.page.set_content(fixture(route, self.storage, blocked), wait_until='load')
        else:
            if blocked:
                self.page.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})")
            self.page.goto(args.base_url.rstrip('/') + '/' + route, wait_until='networkidle')
        return self.page

    def reset(self):
        if self.page and not self.blocked:
            self.page.evaluate('localStorage.clear()')
        self.storage = {}

    def check(self, condition, description):
        if not condition:
            self.page.screenshot(path=str(OUT / 'failure.png'), full_page=True)
            raise AssertionError(description)
        self.results.append(description)

    def text(self, selector):
        return self.page.locator(selector).inner_text()

    def screenshot(self, name):
        self.page.screenshot(path=str(OUT / name), full_page=True)


def run(review):
    r = review
    p = r.open()
    r.check(p.locator('h1').inner_text() == 'Kleine Ideen.\nEchte Tools.', 'Home heading')
    p.locator('[data-select="sleep"]').click()
    r.check(p.locator('[data-workbench]').get_attribute('data-selection') == 'sleep', 'Hero sleep selection')
    r.check(p.locator('[data-scene-link]').get_attribute('href') == './sleepcalculator/', 'Hero links to sleep route')
    p.locator('[data-select="sleep"]').press('ArrowRight')
    r.check(p.locator('[data-select="code"]').get_attribute('aria-pressed') == 'true', 'Hero arrow-key selection')
    p.locator('[data-format="json"]').click()
    r.check('"username":"demo"' in r.text('[data-conversion-example]'), 'Fictional format demo switches to JSON')
    r.check(p.locator('[data-motion-toggle]').is_hidden(), 'Reduced motion respects system preference')
    p.locator('[data-theme-toggle]').click()
    r.check(p.locator('html').get_attribute('data-theme') == 'light', 'Light theme toggle')
    p = r.open('sechserrechner/')
    r.check(p.locator('html').get_attribute('data-theme') == 'light', 'Theme state retained across pages')
    p.locator('[data-theme-toggle]').click()
    r.check(r.text('#average') == '—', 'Empty grades have no fake result')
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
    r.check(r.text('#scenarioResult') == '—', 'Scenario rejects a value outside the selected grade steps')
    p.locator('#scenarioGrade').fill('5.5')
    p.locator('.grade-grade').nth(0).fill('7')
    r.check(r.text('#average') == '—' and p.locator('.grade-grade').nth(0).get_attribute('aria-invalid') == 'true', 'Invalid grade clears stale result')
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
    r.check(r.text('#average') == '—' and not p.locator('#saveGrades').is_checked(), 'Saving opt-out persists without retaining grades')
    p.locator('#pointsEarned').fill('30'); r.check(r.text('#pointsResult') == '3.50', 'Points conversion reacts immediately')
    p.locator('#pointsEarned').fill('61'); r.check(r.text('#pointsResult') == '—', 'Points outside maximum rejected')
    p = r.open('sleepcalculator/')
    r.check(r.text('#sleepResultTime') == '22:45', 'Sleep initial result')
    p.locator('#anchorTime').fill('06:45'); r.check(r.text('#sleepResultTime') == '22:30', 'Wake time updates immediately')
    p.locator('#sleepMinutes').fill('15'); r.check(r.text('#sleepResultTime') == '22:15', 'Quarter-hour durations supported')
    p.locator('input[value="bed"]').check(); p.locator('#anchorTime').fill('23:30'); p.locator('#sleepMinutes').fill('0')
    r.check(r.text('#sleepResultTime') == '07:45' and 'Folgetag' in r.text('#sleepDayLabel'), 'Arbitrary bedtime handles midnight')
    p.locator('#sleepLatency').fill('0'); r.check(r.text('#sleepResultTime') == '07:30', 'Zero sleep latency')
    p.locator('#sleepHours').fill('17'); r.check(r.text('#sleepResultTime') == '—:—', 'Invalid sleep duration clears result, keeping layout')
    p.locator('#sleepHours').fill('7'); p.locator('#sleepMinutes').fill('23')
    r.check(r.text('#sleepResultTime') == '06:53' and p.locator('#durationSlider').input_value() == '443', 'Minute-precise duration and slider agree')
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
    r.check(r.text('#sleepResultTime') == '22:30' and 'nicht möglich' in r.text('#sleepSaveStatus'), 'Sleep still works when Storage is blocked')
    p = r.open('sechserrechner/', blocked=True)
    p.locator('#loadExample').click()
    r.check(r.text('#average') == '5.25' and 'nicht möglich' in r.text('#saveStatus'), 'Grades still work when Storage is blocked')
    # Layout, errors, both themes, small phone through wide desktop.
    for route, name in [('', 'home'), ('sechserrechner/', 'grade'), ('sleepcalculator/', 'sleep')]:
        p = r.open(route)
        if name == 'grade':
            p.locator('#loadExample').click(); p.locator('#closeToast').click()
        for theme in ['dark', 'light']:
            p.evaluate('(theme)=>document.documentElement.dataset.theme=theme', theme)
            for width in [320, 375, 402, 680, 768, 1024, 1440]:
                p.set_viewport_size({'width': width, 'height': 874 if width < 681 else 1000})
                p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                overflow = p.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)>innerWidth+1')
                
                if overflow:
                    print('OVERFLOW', name,theme,width,p.evaluate('({body:document.body.scrollWidth,html:document.documentElement.scrollWidth,width:innerWidth})'))
                    print(p.evaluate("[...document.querySelectorAll('body *')].map(e=>({tag:e.tagName,cls:String(e.className),left:e.getBoundingClientRect().left,right:e.getBoundingClientRect().right,sw:e.scrollWidth,cw:e.clientWidth})).filter(e=>e.right>innerWidth+1).slice(0,20)"))
                r.check(not overflow, f'No horizontal overflow: {name} {theme} {width}px')
                if width in [402, 1440]: r.screenshot(f'{name}-{theme}-{width}.png')
                if width == 402 and theme == 'dark':
                    if name == 'home':
                        y = p.locator('.hero-actions').bounding_box()['y']
                        r.check(y < 400, 'Mobile direct tool links are above 400px')
                    if name == 'grade':
                        y = p.locator('.grade-grade').first.bounding_box()['y']
                        r.check(y < 700, 'Mobile first grade input in first screen')
                        r.check(float(p.locator('.grade-grade').first.evaluate('(el)=>getComputedStyle(el).fontSize').replace('px','')) >= 16, 'Mobile numeric inputs avoid small-font zoom')
                    if name == 'sleep':
                        y = p.locator('#anchorTime').bounding_box()['y']
                        r.check(y < 650, 'Mobile time input in first screen')
        if name == 'home':
            p.emulate_media(reduced_motion='no-preference')
            p.locator('[data-motion-toggle]').click()
            r.check(p.locator('[data-workbench]').evaluate("el=>el.classList.contains('motion-paused')"), 'Explicit motion pause')
    r.check(not r.errors, 'No JavaScript page errors: ' + repr(r.errors))


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=args.chromium, headless=True, args=['--no-sandbox'])
    review = Review(browser)
    try:
        run(review)
        report = {'mode': 'offline embedded assets with simulated Storage' if args.offline_fixture else 'real HTTP navigation with native Storage', 'assertions': len(review.results), 'passed': review.results, 'page_errors': review.errors, 'not_verified': ['Real iPhone/Safari', 'Production network or FPS measurements'] + (['Real navigation', 'Native origin-backed localStorage', 'Asset delivery'] if args.offline_fixture else [])}
        (OUT / 'browser-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"PASS: {len(review.results)} browser assertions. Mode: {report['mode']}")
    finally:
        browser.close()
