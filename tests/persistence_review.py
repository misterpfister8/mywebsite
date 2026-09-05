"""Native browser profile persistence across process restarts, plus storage disabled."""
import argparse
import tempfile
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--browser', choices=['chromium','webkit'], default='chromium')
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
args = parser.parse_args()
with sync_playwright() as w, tempfile.TemporaryDirectory(prefix='misterpfister-profile-') as profile:
    engine = getattr(w, args.browser)
    def launch():
        context = engine.launch_persistent_context(profile, headless=True, locale='de-CH')
        return context, context.pages[0]
    c,p = launch(); p.goto(args.base_url+'sechserrechner/')
    p.locator('.grade-grade').first.fill('4.5'); p.locator('.grade-grade').nth(1).fill('6'); p.locator('.grade-weight').nth(1).fill('2')
    p.goto(args.base_url+'sleepcalculator/'); p.locator('#anchorTime').fill('06:45')
    c.close()
    c,p = launch(); p.goto(args.base_url+'sechserrechner/')
    assert p.locator('#average').inner_text() == '5.50'
    p.locator('.grade-weight').first.fill('')
    p.goto(args.base_url+'sleepcalculator/')
    assert p.locator('#sleepResultTime').inner_text() == '22:30'
    p.locator('#sleepHours').fill(''); c.close()
    c,p = launch(); p.goto(args.base_url+'sechserrechner/')
    assert p.locator('.grade-weight').first.input_value() == ''
    assert p.locator('.grade-grade').nth(1).input_value() == '6'
    assert p.locator('#average').inner_text() == '—'
    p.locator('#saveGrades').uncheck()
    p.goto(args.base_url+'sleepcalculator/')
    assert p.locator('#sleepResultTime').inner_text() == '22:30'
    p.locator('#saveSleep').uncheck(); c.close()
    c,p = launch()
    for route,checkbox,key in [('sechserrechner/','#saveGrades','misterpfister-grades-v2'),('sleepcalculator/','#saveSleep','misterpfister-sleep-v2')]:
        p.goto(args.base_url+route)
        assert not p.locator(checkbox).is_checked()
        assert p.evaluate('(key)=>localStorage.getItem(key)',key) is None
    c.close()
    if args.browser == 'chromium':
        browser = engine.launch(args=['--disable-local-storage'])
        p = browser.new_page()
        p.goto(args.base_url+'sechserrechner/')
        assert p.evaluate('localStorage === null'), 'Native disable-local-storage flag not effective'
        p.locator('#loadExample').click()
        assert p.locator('#average').inner_text() == '5.25'
        assert p.locator('#saveStatus').get_attribute('data-error') == 'true'
        p.goto(args.base_url+'sleepcalculator/'); p.locator('#anchorTime').fill('06:45')
        assert p.locator('#sleepResultTime').inner_text() == '22:30'
        assert p.locator('#sleepSaveStatus').get_attribute('data-error') == 'true'
        browser.close()
print('PASS: native profile restart, incomplete drafts, last valid sleep state, opt-out' + (' and browser-disabled storage' if args.browser=='chromium' else ''))
