"""Real HTTP browser regression tests; no embedded-page or storage substitutes.

Only explicit storage fault tests inject exceptions; normal cases use native
origin-backed localStorage. Requires a running static HTTP server.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
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
        self.page = None; self.route = ''; self.results = []; self.errors = []; self.network_errors = []; self.blocked = False

    def open(self, route='', blocked=False):
        if self.page:
            self.page.close()
        self.page = self.context.new_page(); self.page.set_default_timeout(5000)
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('console', lambda message: self.errors.append(message.text) if message.type == 'error' else None)
        self.route = route; self.blocked = blocked
        self.page.on('response', lambda response: self.network_errors.append(f'{response.status} {response.url}') if response.status >= 400 else None)
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
    valid_height = p.locator('.sleep-visual').bounding_box()['height']
    p.locator('#sleepHours').fill('17')
    r.check(abs(p.locator('.sleep-visual').bounding_box()['height'] - valid_height) < 2, 'Invalid sleep input keeps result panel stable')
    r.check(r.text('#sleepResultTime') == '—:—', 'Invalid sleep duration clears result, keeping layout')
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
    r.check(r.text('#sleepResultTime') == '22:30' and 'nicht lesbar' in r.text('#sleepSaveStatus'), 'Sleep still works when Storage is blocked')
    p = r.open('sechserrechner/', blocked=True)
    p.locator('#loadExample').click()
    r.check(r.text('#average') == '5.25' and 'nicht lesbar' in r.text('#saveStatus'), 'Grades still work when Storage is blocked')
    extended(r)
    # Both motion modes, both themes and every relevant layout boundary.
    for route, name in [('', 'home'), ('sechserrechner/', 'grade'), ('sleepcalculator/', 'sleep')]:
        p = r.open(route)
        if name == 'grade':
            p.locator('#loadExample').click(); p.locator('#closeToast').click()
        for motion in ['reduce', 'no-preference']:
            p.emulate_media(reduced_motion=motion)
            for theme in ['dark', 'light']:
                if p.locator('html').get_attribute('data-theme') != theme:
                    p.locator('[data-theme-toggle]').click()
                for width in [320, 370, 371, 375, 402, 680, 681, 768, 900, 901, 1024, 1025, 1150, 1151, 1440, 1600, 1601]:
                    p.set_viewport_size({'width': width, 'height': 874 if width < 681 else 1000})
                    p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
                    overflow = p.evaluate('Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)>innerWidth+1')
                    r.check(not overflow, f'No overflow: {name} {theme} {motion} {width}px')
                    if width in [320, 402, 768, 1024, 1440] and motion == 'reduce':
                        r.screenshot(f'{name}-{theme}-{width}.png')
                        p.screenshot(path=str(OUT / f'{name}-{theme}-{width}-viewport.png'))
                    if width == 402:
                        if name == 'home':
                            r.check(p.locator('.hero-actions').bounding_box()['y'] < 400, 'Direct links before 400px')
                            r.check(p.locator('.tool-card').first.bounding_box()['y'] < 874, 'First project card begins in first mobile screen')
                        if name == 'grade':
                            r.check(p.locator('.grade-grade').first.bounding_box()['y'] < 700, 'First grade in first mobile screen')
                        if name == 'sleep':
                            r.check(p.locator('#anchorTime').bounding_box()['y'] < 650, 'Time input before 650px')
                        if name != 'home':
                            sizes = p.locator('input:not([type=checkbox]):not([type=radio]):not([type=range]):not([type=file]),select').evaluate_all('(els)=>els.filter(el=>el.getBoundingClientRect().width).map(el=>parseFloat(getComputedStyle(el).fontSize))')
                            r.check(all(size >= 16 for size in sizes), f'All mobile text inputs >=16px: {name}')
    r.check(not r.errors, 'No JavaScript errors: ' + repr(r.errors))
    r.check(not r.network_errors, 'No failed assets: ' + repr(r.network_errors))


def extended(r):
    p = r.open('sechserrechner/'); r.reset(); p.reload()
    p.locator('.grade-grade').nth(0).fill('4,5'); p.locator('.grade-grade').nth(1).fill('6'); p.locator('.grade-weight').nth(1).fill('2')
    p.locator('#scenarioGrade').fill('6'); p.locator('#scenarioWeight').fill('2')
    r.check(r.text('#scenarioResult') == '5.70', 'Simulation has independent weight')
    p.locator('#nextWeight').fill('100')
    r.check(r.text('#scenarioResult') == '5.70', 'Target weight does not change simulation')
    p.locator('.grade-weight').first.fill('')
    p.reload(); r.check(r.text('#average') == '—' and p.locator('.grade-grade').nth(1).input_value() == '6', 'Incomplete weight draft survives real reload without losing other grades')
    p.locator('.grade-weight').first.fill('1')
    r.check(r.text('#average') == '5.50', 'Draft completes after reload')
    p.locator('.settings-details').nth(1).locator('summary').click()
    p.locator('#renameSubject').fill('Testfach'); p.locator('#renameSubject').press('Tab')
    r.check(r.text('#subjectSelect option:checked') == 'Testfach', 'Rename subject')
    p.locator('#deleteSubject').click(); p.locator('#undoAction').click()
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
        p.locator('#'+id_).fill(value); r.check(r.text('#pointsResult') == '—', 'Invalid points clear result')
    # Delayed undo must not silently overwrite newer edits.
    p.locator('#loadExample').click(); p.locator('.grade-grade').first.fill('6')
    p.once('dialog', lambda dialog: dialog.dismiss()); p.locator('#undoAction').click()
    r.check(p.locator('.grade-grade').first.input_value() == '6', 'Cancelled delayed undo preserves newer edits')
    p.once('dialog', lambda dialog: dialog.accept()); p.locator('#undoAction').click()
    r.check(r.text('#average') == '5.50', 'Confirmed delayed undo restores previous state')
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
    p.reload(); r.check(r.text('#sleepResultTime') == '22:30', 'Sleep reload restores last valid settings')
    p.locator('#showPresetForm').click(); p.locator('#presetName').fill('Testzeit'); p.locator('#presetForm button[type=submit]').click()
    p.locator('#sleepMinutes').fill('')
    p.locator('[aria-label="Preset Testzeit löschen"]').click(); p.reload()
    r.check(p.locator('.preset-chip').count() == 2, 'Preset deletion persists even during incomplete time edit')
    p.locator('.preset-delete').first.click(); p.locator('#undoPreset').click()
    r.check(p.locator('.preset-chip').count() == 2, 'Undo preset deletion')
    p.locator('input[value=bed]').check(); p.locator('#anchorTime').fill('23:50'); p.locator('#sleepLatency').fill('30')
    r.check(r.text('#onsetDay') == 'Folgetag' and r.text('#bedDay') == 'Derselbe Tag', 'Timeline day labels cross midnight correctly')
    p.locator('#anchorTime').fill('09:00'); r.check(r.text('#wakeDay') == 'Derselbe Tag', 'Same-day timeline labels')
    p.locator('#sleepLatency').fill('0')
    r.check(p.locator('#latencyArc').get_attribute('stroke-dasharray').startswith('0 '), 'Zero latency has no arc')
    p.locator('#saveSleep').uncheck(); p.reload()
    r.check(not p.locator('#saveSleep').is_checked() and r.text('#sleepResultTime') == '22:45', 'Sleep opt-out survives reload')
    p = r.open(); p.emulate_media(reduced_motion='no-preference')
    for name in ['grade', 'sleep', 'code']:
        p.locator(f'[data-select="{name}"]').focus(); p.keyboard.press('Space')
        r.check(p.locator(f'[data-module="{name}"]').get_attribute('aria-pressed') == 'true', 'Keyboard selects '+name)
    p.locator('[data-select=code]').press('Home'); r.check(p.locator('[data-select=grade]').get_attribute('aria-pressed') == 'true', 'Home key selects first preview')
    p.locator('[data-select=grade]').press('End'); r.check(p.locator('[data-select=code]').get_attribute('aria-pressed') == 'true', 'End key selects last preview')
    p.locator('[data-motion-toggle]').click()
    r.check(p.locator('[data-motion-toggle]').get_attribute('aria-pressed') == 'true', 'Manual scene pause')
    p.locator('[data-select=grade]').click()
    r.check(p.locator('.module-grade').evaluate('(el)=>getComputedStyle(el).transitionDuration') == '0s', 'Paused scene switches immediately')
    p.locator('[data-motion-toggle]').click()
    p.locator('.hero-actions a').first.click(); p.wait_for_url('**/sechserrechner/')
    r.check(p.locator('h1').inner_text() == 'Noten. Mit Überblick.', 'Native hero navigation')
    p.go_back(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    r.check(p.locator('[data-workbench]').is_visible(), 'Browser back restores workbench')
    p.go_forward(); p.wait_for_url('**/sechserrechner/'); p.reload()
    r.check(p.locator('#gradeForm').is_visible(), 'Forward and reload keep tool operational')
    p.locator('.main-nav a').last.click(); p.wait_for_url('**/sleepcalculator/')
    r.check(p.locator('#sleepClock').is_visible(), 'Native navigation between tools')
    p.locator('.brand').click(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    p.locator('.card-sleep').click(); p.wait_for_url('**/sleepcalculator/')
    p.go_back(); p.wait_for_url(args.base_url.rstrip('/')+'/')
    r.check(p.locator('.card-sleep').is_visible(), 'Project card navigation and back')



with sync_playwright() as playwright:
    browser = getattr(playwright, args.browser).launch(executable_path=args.chromium, headless=True)
    review = Review(browser)
    try:
        run(review)
        report = {'mode': 'real HTTP navigation with native Storage', 'browser': args.browser, 'version': browser.version, 'assertions': len(review.results), 'passed': review.results, 'page_errors': review.errors, 'not_verified': ['Physical iPhone and native keyboard', 'FPS/Lighthouse scores'], 'storage_faults': 'Explicit SecurityError and QuotaExceededError injection, separate from native persistence tests'}
        (OUT / 'browser-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"PASS: {len(review.results)} browser assertions. Mode: {report['mode']}")
    finally:
        browser.close()
