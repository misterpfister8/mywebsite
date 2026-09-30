"""Exercise the homepage demos as visitors, without changing calculator drafts."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
parser.add_argument('--output', type=Path, default=Path('output/playwright/showcase'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
BASE = args.base_url.rstrip('/') + '/'
SETTLED = "['idle', 'still', 'fallback'].includes(document.querySelector('.hero-visual')?.dataset.glassState)"
report = {'browser': args.browser, 'checks': [], 'layouts': [], 'errors': [], 'network_errors': [], 'external_requests': []}
active_page = None


def check(condition, label):
    assert condition, label
    report['checks'].append(label)


def watch(page):
    global active_page
    active_page = page
    page.set_default_timeout(7000)
    page.on('pageerror', lambda error: report['errors'].append(str(error)))
    page.on('console', lambda message: report['errors'].append(message.text) if message.type == 'error' else None)
    page.on('response', lambda response: report['network_errors'].append(f'{response.status} {response.url}') if response.status >= 400 else None)
    page.on('request', lambda request: report['external_requests'].append(request.url) if not request.url.startswith((BASE, 'data:', 'blob:', 'about:')) else None)


def open_home(page, query=''):
    page.goto(BASE + query, wait_until='networkidle')
    page.wait_for_function(SETTLED, timeout=15000, polling=100)


def settle(page):
    page.wait_for_function(SETTLED, timeout=7000, polling=100)


def set_range(locator, value):
    """Use native arrow keys and the range's real step on either browser."""
    low, step = locator.evaluate("el => [Number(el.min), Number(el.step || 1)]")
    target_step = round((value - low) / step)
    assert target_step >= 0 and abs(low + target_step * step - value) < 1e-8, f'Value {value} is a native range step'
    delta = round((value - float(locator.input_value())) / step)
    assert abs(delta) <= 200, f'Value {value} is reachable without excessive input'
    for _ in range(abs(delta)):
        locator.press('ArrowRight' if delta > 0 else 'ArrowLeft')
    check(float(locator.input_value()) == value, f'Keyboard sets {locator.get_attribute("data-demo-grade") or locator.get_attribute("data-demo-sleep") or "range"} to {value}')


def select_preview(page, name):
    page.locator(f'[data-select="{name}"]').click()
    check(page.locator('[data-workbench]').get_attribute('data-selection') == name, f'Dock selects {name}')
    check(page.locator('.hero-visual').get_attribute('data-glass-form') == name, f'Specimen follows {name}')
    check(page.locator(f'[data-demo-panel="{name}"]').is_visible(), f'{name} sample is visible')


def saved_tools(page):
    return page.evaluate("Object.fromEntries(Object.keys(localStorage).filter(k => /^misterpfister-(grades|sleep)/.test(k)).map(k => [k, localStorage.getItem(k)]))")


def demo_flows(page, query='?gl=still'):
    open_home(page, query)
    select_preview(page, 'grade')
    check(page.locator('[data-demo-grade]').input_value() == '6', 'Next grade starts at 6')
    check(page.locator('output[data-demo-average]').inner_text() == '5.40', 'Four grades totalling 21 plus grade 6 produce 5.40')
    check(page.locator('[data-demo-module-average]').inner_text().replace('\n', '') == '5.40', 'Spatial label shows the projected average')
    # A real still-frame change confirms the slider reaches the illustration, not only its text.
    canvas_before = page.locator('.glass-canvas').screenshot() if page.locator('.hero-visual').get_attribute('data-glass-tier') != 'fallback' else None
    frames_before = page.evaluate('HeroGL.stats.frames')
    set_range(page.locator('[data-demo-grade]'), 1)
    check(page.locator('output[data-demo-average]').inner_text() == '4.40', 'Grade 1 changes the projected average to 4.40')
    check(page.locator('[data-demo-grade-value]').inner_text() == '1.00', 'Sample identifies the selected next grade')
    check('4.40' in page.locator('[data-hud-data]').text_content(), 'HUD reports the changed average')
    settle(page)
    if canvas_before is not None:
        check(page.evaluate('HeroGL.stats.frames') > frames_before, 'Sample grade redraws the specimen')
        check(page.locator('.glass-canvas').screenshot() != canvas_before, 'The grade specimen visibly changes with the sample')
    select_preview(page, 'sleep')
    check(page.locator('output[data-demo-bed]').inner_text() == '22:50', 'Eight hours of sleep and ten minutes latency end at 07:00')
    set_range(page.locator('[data-demo-sleep]'), 360)
    check(page.locator('output[data-demo-bed]').inner_text() == '00:50', 'Six hours of sleep move bedtime past midnight to 00:50')
    check('6 h' in page.locator('[data-demo-duration]').inner_text(), 'Duration label follows the selected six hours')
    check(page.locator('[data-demo-module-bed]').inner_text() == '00:50', 'Spatial bedtime follows the sample')
    check('00:50' in page.locator('[data-hud-data]').text_content(), 'Sleep HUD follows the calculated bedtime')
    select_preview(page, 'grade')
    check(page.locator('output[data-demo-average]').inner_text() == '4.40', 'Returning to grades keeps the visitor sample')
    page.locator('[data-select="grade"]').press('ArrowRight')
    check(page.locator('[data-demo-panel="sleep"]').is_visible(), 'Arrow key selects the sleep sample')
    page.locator('[data-select="sleep"]').press('End')
    check(page.locator('[data-demo-panel="code"]').is_visible(), 'End key selects the data sample')
    page.locator('[data-select="code"]').press('Home')
    check(page.locator('[data-demo-panel="grade"]').is_visible(), 'Home key returns to grades')


def appearance(page):
    details = page.locator('[data-look-panel]')
    if page.locator('.hero-visual').get_attribute('data-glass-tier') == 'fallback':
        check(details.is_hidden(), 'Unsupported appearance controls stay hidden in the SVG fallback')
        return
    check(not details.evaluate('el => el.open'), 'Appearance controls start as an optional disclosure')
    summary = details.locator('summary')
    summary.press('Enter')
    check(details.evaluate('el => el.open'), 'Keyboard opens appearance controls')
    defaults = [page.locator(selector).input_value() for selector in ('select[data-look-material]', 'select[data-look-palette]', 'input[data-look-light]')]
    before = page.locator('.glass-canvas').screenshot() if page.locator('.hero-visual').get_attribute('data-glass-tier') != 'fallback' else None
    page.locator('select[data-look-material]').select_option('satin')
    page.locator('select[data-look-palette]').select_option('mint')
    set_range(page.locator('input[data-look-light]'), 100)
    settle(page)
    visual = page.locator('.hero-visual')
    check(visual.get_attribute('data-look-material') == 'satin' and visual.get_attribute('data-look-palette') == 'mint' and float(visual.get_attribute('data-look-light')) == 1, 'Material, palette and light reach the selected specimen')
    if before is not None:
        check(page.locator('.glass-canvas').screenshot() != before, 'Appearance controls visibly alter the specimen')
    page.locator('[data-look-reset]').press('Enter')
    check([page.locator(selector).input_value() for selector in ('select[data-look-material]', 'select[data-look-palette]', 'input[data-look-light]')] == defaults, 'Reset restores the original appearance settings')
    check(visual.get_attribute('data-look-material') == 'default' and visual.get_attribute('data-look-palette') == 'original' and float(visual.get_attribute('data-look-light')) == 0, 'Reset restores the actual specimen appearance')
    summary.press('Enter')


def preserve_drafts(page):
    # Populate real calculator drafts through their UI rather than inventing their storage schema.
    page.goto(BASE + 'sechserrechner/', wait_until='networkidle')
    page.locator('.grade-grade').first.fill('4.5')
    page.locator('.grade-grade').nth(1).fill('6')
    page.locator('.grade-weight').nth(1).fill('2')
    check(page.locator('#average').inner_text() == '5.50', 'A real grade draft is created')
    page.goto(BASE + 'sleepcalculator/', wait_until='networkidle')
    page.locator('#anchorTime').fill('06:45')
    check(page.locator('#sleepResultTime').inner_text() == '22:35', 'A real sleep draft is created')
    saved = saved_tools(page)
    demo_flows(page)
    appearance(page)
    check(saved_tools(page) == saved, 'Homepage samples and appearance controls preserve calculator drafts exactly')
    page.reload(wait_until='networkidle')
    check(page.locator('[data-demo-grade]').input_value() == '6' and page.locator('[data-demo-sleep]').input_value() == '480', 'Homepage samples reset on a fresh load')
    page.goto(BASE + 'sechserrechner/', wait_until='networkidle')
    check(page.locator('#average').inner_text() == '5.50', 'Saved grades survive homepage interaction')
    check(page.locator('[data-result-example]').is_hidden(), 'Sample CTA disappears once the result has valid own grades')
    page.goto(BASE + 'sleepcalculator/', wait_until='networkidle')
    check(page.locator('#sleepResultTime').inner_text() == '22:35', 'Saved sleep plan survives homepage interaction')


def example_entry(browser):
    context = browser.new_context(locale='de-CH', timezone_id='Europe/Zurich', reduced_motion='reduce')
    page = context.new_page()
    watch(page)
    page.goto(BASE + 'sechserrechner/', wait_until='networkidle')
    button = page.locator('[data-result-example]')
    check(button.is_visible() and page.locator('#average').get_attribute('data-state') == 'empty', 'The empty result offers its own sample entry')
    button.press('Enter')
    check(page.locator('#average').inner_text() == '5.25' and page.locator('.grade-row').count() == 4, 'Sample entry loads the complete existing example')
    check(button.is_hidden(), 'Sample entry leaves room for the loaded result')
    page.reload(wait_until='networkidle')
    check(page.locator('#average').inner_text() == '5.25', 'Sample entry uses the existing draft persistence')
    context.close()


def conversion(browser, reduced):
    context = browser.new_context(viewport={'width': 1366, 'height': 900}, reduced_motion='reduce' if reduced else 'no-preference', locale='de-CH', timezone_id='Europe/Zurich')
    page = context.new_page()
    watch(page)
    open_home(page, '?gl=off')
    demo = page.locator('[data-conversion-demo]')
    run = page.locator('[data-conversion-run]')
    check(demo.get_attribute('data-conversion-stage') == 'output', 'Conversion sample starts with its completed result')
    page.locator('[data-format="csv"]').click()
    csv = page.locator('[data-conversion-example]').inner_text().splitlines()
    check(csv[0] == 'name,url,username' and len(csv) == 3 and all('https://example.com/' in row for row in csv[1:]), 'CSV sample contains a header and two fictional accounts')
    page.locator('[data-format="csv"]').press('End')
    check(page.locator('[data-format="json"]').get_attribute('aria-pressed') == 'true', 'Keyboard selects JSON output')
    parsed = json.loads(page.locator('[data-conversion-example]').inner_text())
    check(len(parsed['items']) == 2 and all(item['name'].startswith('Beispiel') and item['login']['username'].startswith('demo.') and item['login']['uris'][0]['uri'].startswith('https://example.com/') for item in parsed['items']), 'JSON sample is parseable and preserves both fictional accounts')
    run.press('Enter')
    if reduced:
        check(demo.get_attribute('data-conversion-stage') == 'output' and demo.get_attribute('data-conversion-playing') == 'false', 'Reduced motion provides the conversion result immediately')
    else:
        check(demo.get_attribute('data-conversion-stage') == 'export', 'Play starts at the sample export')
        page.wait_for_function("document.querySelector('[data-conversion-demo]').dataset.conversionStage === 'mapping'", polling=50)
        check(page.locator('[data-conversion-step="mapping"]').get_attribute('aria-current') == 'step', 'The mapping step is announced during playback')
        # Changing the output format in flight starts a coherent run with that format.
        page.locator('[data-format="csv"]').click()
        check(demo.get_attribute('data-conversion-stage') == 'export', 'Changing format restarts the sample cleanly')
        page.wait_for_function("document.querySelector('[data-conversion-demo]').dataset.conversionStage === 'output' && document.querySelector('[data-conversion-demo]').dataset.conversionPlaying === 'false'", polling=50)
        check(page.locator('[data-conversion-example]').inner_text().splitlines() == csv, 'The completed run uses the format selected during playback')
        run.click()
        run.click()
        page.wait_for_function("document.querySelector('[data-conversion-demo]').dataset.conversionStage === 'output' && document.querySelector('[data-conversion-demo]').dataset.conversionPlaying === 'false'", polling=50)
        check(page.locator('[data-conversion-step="output"]').get_attribute('aria-current') == 'step', 'Repeated play finishes at the output step')
    page.screenshot(path=str(args.output / f'conversion-{"reduced" if reduced else "motion"}.png'), full_page=True, animations='disabled')
    context.close()


def layouts(browser):
    for width in (320, 390, 768, 1366):
        for theme in ('dark', 'light'):
            context = browser.new_context(viewport={'width': width, 'height': 900 if width >= 768 else 844}, color_scheme=theme, reduced_motion='reduce', locale='de-CH', timezone_id='Europe/Zurich', has_touch=width < 768, is_mobile=width < 768)
            page = context.new_page()
            watch(page)
            open_home(page)
            for name in ('grade', 'sleep', 'code'):
                button = page.locator(f'[data-select="{name}"]')
                check(button.is_visible(), f'{width}px {theme}: {name} selection is visible')
                select_preview(page, name)
                check(page.evaluate('Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= innerWidth + 1'), f'{width}px {theme}: {name} preview has no page overflow')
                bounds = button.bounding_box()
                check(bounds['x'] >= -1 and bounds['x'] + bounds['width'] <= width + 1, f'{width}px {theme}: dock button stays inside the viewport')
                if width < 768:
                    band = page.locator('.hero-visual').bounding_box()
                    check(bounds['y'] >= band['y'] - 1 and bounds['y'] + bounds['height'] <= band['y'] + band['height'] + 1, f'{width}px {theme}: the phone band does not trim dock controls')
            select_preview(page, 'grade')
            details = page.locator('[data-look-panel]')
            if details.is_visible():
                details.locator('summary').click()
                check(page.evaluate('Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= innerWidth + 1'), f'{width}px {theme}: expanded appearance controls have no overflow')
            controls = page.locator('[data-demo-grade], [data-demo-sleep], select[data-look-material], select[data-look-palette], input[data-look-light], [data-look-reset], [data-conversion-run]')
            check(controls.evaluate_all("els => els.every(el => !el.closest('a') && !el.closest('[aria-hidden=true]'))"), f'{width}px {theme}: interactive controls have no link or decorative ancestor')
            check(controls.evaluate_all("els => els.every(el => el.tagName === 'BUTTON' ? !!el.textContent.trim() || !!el.getAttribute('aria-label') : el.labels?.length || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))"), f'{width}px {theme}: sample and appearance inputs have accessible labels')
            page.evaluate('scrollTo(0, 0)')
            page.screenshot(path=str(args.output / f'home-{width}-{theme}.png'), full_page=True, animations='disabled')
            report['layouts'].append({'width': width, 'theme': theme, 'tier': page.locator('.hero-visual').get_attribute('data-glass-tier')})
            context.close()


def duration_layouts(browser):
    # Intermediate durations are longer than whole hours; check the real card,
    # including its smaller back position, rather than only page overflow.
    for width in (681, 768, 1024, 1366, 1920):
        context = browser.new_context(viewport={'width': width, 'height': 1000}, color_scheme='dark', reduced_motion='reduce', locale='de-CH')
        page = context.new_page()
        watch(page)
        open_home(page, '?gl=off')
        page.locator('[data-select="sleep"]').click()
        for minutes in range(360, 541, 15):
            set_range(page.locator('[data-demo-sleep]'), minutes)
            for selection in ('sleep', 'grade', 'code'):
                page.locator(f'[data-select="{selection}"]').click()
                sizes = page.locator('.module-sleep').evaluate('''card =>
                  [card, card.querySelector('.module-row'), card.querySelector('.module-meta')]
                    .map(el => ({width: el.clientWidth, scroll: el.scrollWidth, height: el.clientHeight, scrollHeight: el.scrollHeight}))''')
                check(all(s['scroll'] <= s['width'] + 1 and s['scrollHeight'] <= s['height'] + 1 for s in sizes), f'{width}px {minutes}min: sleep text fits its {selection} card position: {sizes}')
            page.locator('[data-select="sleep"]').click()
            if width == 1366 and minutes == 495:
                page.locator('.module-sleep').screenshot(path=str(args.output / 'sleep-duration-8h15.png'))
        context.close()


def mobile_selection(browser):
    context = browser.new_context(viewport={'width': 390, 'height': 844}, has_touch=True, is_mobile=True, reduced_motion='no-preference', locale='de-CH', timezone_id='Europe/Zurich')
    page = context.new_page()
    watch(page)
    open_home(page, '?gl=force')
    # Explicit touch selection remains intentional when the band moves through the viewport.
    page.evaluate('scrollTo(0, 80)')
    page.locator('[data-select="code"]').tap()
    settle(page)
    page.evaluate('scrollTo(0, 0)')
    page.wait_for_timeout(350)
    check(page.locator('.hero-visual').get_attribute('data-glass-form') == 'code' and page.locator('[data-select="code"]').get_attribute('aria-pressed') == 'true', 'Phone selection survives subsequent scroll movement')
    if args.browser == 'chromium' and page.locator('.hero-visual').get_attribute('data-glass-tier') != 'fallback':
        select_preview(page, 'grade')
        bounds = page.locator('.glass-stage').bounding_box()
        start_x, y = bounds['x'] + bounds['width'] * .75, bounds['y'] + bounds['height'] * .45
        end_x = bounds['x'] + bounds['width'] * .2
        check(start_x - end_x > 45, 'The phone specimen provides enough room for a swipe')
        cdp = context.new_cdp_session(page)
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': start_x, 'y': y}]})
        for fraction in (.25, .5, .75, 1):
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': start_x + (end_x - start_x) * fraction, 'y': y}]})
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        page.wait_for_function("document.querySelector('.hero-visual').dataset.glassForm === 'sleep'", polling=100)
        check(page.locator('[data-select="sleep"]').get_attribute('aria-pressed') == 'true' and page.locator('[data-demo-panel="sleep"]').is_visible(), 'A real horizontal touch swipe selects the next specimen and sample')
    page.screenshot(path=str(args.output / 'home-390-touch-selection.png'), full_page=True, animations='disabled')
    context.close()


with sync_playwright() as playwright:
    browser = getattr(playwright, args.browser).launch(headless=True)
    report['version'] = browser.version
    page = None
    try:
        context = browser.new_context(viewport={'width': 1366, 'height': 900}, color_scheme='dark', reduced_motion='reduce', locale='de-CH', timezone_id='Europe/Zurich')
        page = context.new_page()
        watch(page)
        preserve_drafts(page)
        context.close()
        example_entry(browser)
        layouts(browser)
        duration_layouts(browser)
        mobile_selection(browser)
        conversion(browser, reduced=True)
        conversion(browser, reduced=False)
        context = browser.new_context(viewport={'width': 1366, 'height': 900}, reduced_motion='reduce', locale='de-CH', timezone_id='Europe/Zurich')
        page = context.new_page()
        watch(page)
        demo_flows(page, '?gl=off')
        check(page.locator('.hero-visual').get_attribute('data-glass-tier') == 'fallback', 'Samples remain usable without WebGL')
        appearance(page)
        context.close()
        check(not report['errors'], f'No JavaScript or console errors: {report["errors"]}')
        check(not report['network_errors'], f'All local assets load: {report["network_errors"]}')
        check(not report['external_requests'], f'Showcase interaction makes no external requests: {report["external_requests"]}')
        report['status'] = 'pass'
    except Exception as error:
        report['status'] = f'fail: {error}'
        if active_page and not active_page.is_closed():
            active_page.screenshot(path=str(args.output / 'failure.png'), full_page=True)
        raise
    finally:
        (args.output / 'showcase-report.json').write_text(json.dumps(report, indent=2, ensure_ascii=False))
        browser.close()
    print(f'PASS: {len(report["checks"])} showcase assertions, {len(report["layouts"])} width/theme combinations ({args.browser}).')
