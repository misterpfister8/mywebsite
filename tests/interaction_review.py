"""Real browser touch, motion, hero engine and optional axe checks. Run against the HTTP site."""
import argparse
import io
import json
import math
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--base-url', default='http://127.0.0.1:8000/')
parser.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
parser.add_argument('--axe', type=Path)
parser.add_argument('--headed', action='store_true')
parser.add_argument('--output', type=Path, default=Path('output/playwright/interaction'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
BASE = args.base_url.rstrip('/') + '/'
report = {'browser': args.browser, 'touch': [], 'motion': {}, 'hero': {}, 'accessibility': []}
errors = []
# Tests wait for a settled engine before counting frames (the software still frame JITs for ~750 ms).
SETTLED = "['idle','still','fallback'].includes(document.querySelector('.hero-visual')?.dataset.glassState)"
STATE = "document.querySelector('.hero-visual').dataset.glassState"
# Cumulative layout shift of the load (spec §10: CLS <= .02); input-driven shifts are excluded by the API.
CLS = '''(() => { window.__cls = 0; window.__shifts = [];
  try { new PerformanceObserver(list => { for (const e of list.getEntries()) if (!e.hadRecentInput) { __cls += e.value;
    __shifts.push({value: +e.value.toFixed(4), sources: (e.sources || []).map(s => s.node && (s.node.id || s.node.className || s.node.nodeName))}); } }).observe({type: 'layout-shift', buffered: true}); } catch {}
})();'''
INIT = '''(() => {
  const native = window.requestAnimationFrame;
  window.__frameRequests = 0; window.__lastFrameAt = 0;
  window.requestAnimationFrame = callback => { window.__frameRequests++; window.__lastFrameAt = performance.now(); return native.call(window,callback); };
  window.__transitions = [];
  addEventListener('pagereveal', e => {
    if(e.viewTransition) {
      const record = {ready:false,finished:false}; __transitions.push(record);
      e.viewTransition.ready.then(()=>{record.ready=true; try { record.types=[...e.viewTransition.types]; } catch { record.types=null; }},err=>{record.error=String(err)});
      e.viewTransition.finished.then(()=>{record.finished=true},err=>{record.error=String(err)});
    }
  });
  window.__glassStates = []; window.__lastInputAt = 0;
  for (const type of ['pointermove', 'pointerdown', 'click', 'keydown']) addEventListener(type, () => { window.__lastInputAt = performance.now(); }, true);
  document.addEventListener('DOMContentLoaded', () => {
    const visual = document.querySelector('.hero-visual');
    if (!visual) return;
    const record = () => __glassStates.push(visual.dataset.glassState);
    record(); new MutationObserver(record).observe(visual, {attributes: true, attributeFilter: ['data-glass-state']});
  });
})();'''


def frames_stop(page, within_ms, quiet_ms=300):
    """Frames stop at most `within_ms` after the last input and stay stopped."""
    page.wait_for_timeout(within_ms + 400)
    count = page.evaluate('__frameRequests'); page.wait_for_timeout(quiet_ms)
    gap = page.evaluate('__lastFrameAt - __lastInputAt')
    return page.evaluate('__frameRequests') == count and gap <= within_ms, round(gap)


def seed(page):
    """Saved data the tools rebuild on load: three grade subjects (six grades in the active one) and five sleep presets."""
    page.goto(BASE + 'sechserrechner/', wait_until='networkidle'); page.locator('#loadExample').click()
    grades = json.loads(page.evaluate("localStorage.getItem('misterpfister-grades-v2')"))
    subject = grades['subjects'][grades['active']]
    subject['entries'] += [dict(entry, name=f'Prüfung {index + 5}') for index, entry in enumerate(subject['entries'][:2])]
    grades['subjects'] = [dict(subject, name=name) for name in ('Mathematik', 'Deutsch', 'Physik')]; grades['active'] = 1
    page.goto(BASE + 'sleepcalculator/', wait_until='networkidle')
    sleep = json.loads(page.evaluate("localStorage.getItem('misterpfister-sleep-v2')"))
    sleep['presets'] += [dict(sleep['presets'][0], name=f'Eigenes Preset {index}', time=f'0{index}:15') for index in range(1, 4)]
    page.evaluate("([grades, sleep]) => { localStorage.setItem('misterpfister-grades-v2', grades); localStorage.setItem('misterpfister-sleep-v2', sleep); }", [json.dumps(grades), json.dumps(sleep)])


def layout_shift(browser):
    """CLS of a fresh load of every page at desktop and phone size, with motion allowed; the tools also with saved data."""
    out = {}
    for label, options in [('1440', {'viewport': {'width': 1440, 'height': 1000}}), ('402', {'viewport': {'width': 402, 'height': 874}, 'has_touch': True, 'is_mobile': True}),
                           ('360', {'viewport': {'width': 360, 'height': 800}, 'has_touch': True, 'is_mobile': True}), ('320', {'viewport': {'width': 320, 'height': 640}, 'has_touch': True, 'is_mobile': True})]:
        ctx = browser.new_context(locale='de-CH', timezone_id='Europe/Zurich', reduced_motion='no-preference', **options); ctx.add_init_script(CLS)
        # Deferred scripts arrive after the first paint, as on a phone network; this makes late DOM building measurable.
        ctx.route(re.compile(r'/assets/(motion|tool-storage|tool-math|grades|sleep|workbench|hero-gl|wisper)\.js'), lambda route: (time.sleep(.2), route.continue_()))
        page = ctx.new_page(); page.on('pageerror', lambda error: errors.append(str(error)))
        for route in ['', 'sechserrechner/', 'sleepcalculator/', 'wisperpfister/']:
            page.goto(BASE + route, wait_until='networkidle'); page.wait_for_timeout(1500)
            out[f'{route or "home"} {label}px'] = {'cls': round(page.evaluate('__cls'), 4), 'shifts': page.evaluate('__shifts')}
        seed(page)
        for route in ['sechserrechner/', 'sleepcalculator/']:
            page.goto(BASE + route, wait_until='networkidle'); page.wait_for_timeout(1500)
            out[f'{route} saved data {label}px'] = {'cls': round(page.evaluate('__cls'), 4), 'shifts': page.evaluate('__shifts')}
        ctx.close()
    return out


def pixels(page, clip):
    """RGB of every pixel in a small screenshot clip (PNG decoded without extra libraries)."""
    import struct, zlib
    data = page.screenshot(clip=clip, animations='disabled', caret='hide')
    stream = io.BytesIO(data); stream.read(8); width = height = 0; raw = b''
    while True:
        length, kind = struct.unpack('>I4s', stream.read(8)); chunk = stream.read(length); stream.read(4)
        if kind == b'IHDR': width, height, depth, color = struct.unpack('>IIBB', chunk[:10])
        elif kind == b'IDAT': raw += chunk
        elif kind == b'IEND': break
    channels = {2: 3, 6: 4}[color]; rows = zlib.decompress(raw); stride = width * channels; out = []; previous = bytearray(stride)
    for y in range(height):
        kind, line = rows[y * (stride + 1)], bytearray(rows[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0; b = previous[i]; c = previous[i - channels] if i >= channels else 0
            if kind == 1: line[i] = (line[i] + a) & 255
            elif kind == 2: line[i] = (line[i] + b) & 255
            elif kind == 3: line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        out += [tuple(line[x * channels:x * channels + 3]) for x in range(width)]; previous = line
    return out


with sync_playwright() as pw:
    browser = getattr(pw, args.browser).launch(headless=not args.headed)
    report['version'] = browser.version
    touch = browser.new_context(has_touch=True, is_mobile=True, locale='de-CH', timezone_id='Europe/Zurich')
    p = touch.new_page(); p.on('pageerror', lambda error: errors.append(str(error)))
    for width in [320, 375, 402]:
        p.set_viewport_size({'width': width, 'height': 874}); p.goto(args.base_url)
        assert p.locator('.scene').is_hidden() and p.locator('.scene-dock').is_visible(), f'Phones use the specimen dock without spatial cards: {width}'
        assert p.locator('.tool-card').first.bounding_box()['y'] < 950, f'Sample and band keep tool cards within 950px: {width}'
        band = p.locator('.hero-visual').bounding_box()
        assert p.locator('.hero-visual').is_visible() and band['height'] <= 170, f'Phones keep the glass object as a band of at most 170px: {width} {band}'
        assert p.locator('.glass-stage').is_visible(), f'Glass stage visible on phones: {width}'
        report['touch'].append(f'{width}px: accessible specimen dock, glass band {band["height"]:.0f}px, sample before tool cards')
    # The dial handles follow a finger; the page must not scroll while a handle is dragged (CDP touch: Chromium only).
    p.set_viewport_size({'width': 402, 'height': 874}); p.goto(BASE + 'sleepcalculator/')
    # The load stagger (load-rise) still slides the panels by up to 16px; the finger path is computed from the settled dial.
    p.wait_for_function("!document.getAnimations().some(a => a.timeline === document.timeline && a.playState === 'running')", timeout=5000)
    p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
    if args.browser == 'chromium':
        wrap = p.locator('.sleep-clock-wrap').bounding_box(); handle = p.locator('#dialAnchor').bounding_box()
        cx, cy, half = wrap['x'] + wrap['width'] / 2, wrap['y'] + wrap['height'] / 2, wrap['width'] / 2
        cdp = touch.new_cdp_session(p); scroll_before = p.evaluate('scrollY')
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': handle['x'] + handle['width'] / 2, 'y': handle['y'] + handle['height'] / 2}]})
        for degrees in [103, 100, 97, 94, 92, 90]:
            rad = math.radians(degrees)
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': cx + math.sin(rad) * .9 * half, 'y': cy - math.cos(rad) * .9 * half}]})
            p.wait_for_timeout(20)
        p.evaluate('() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))')
        reading = p.evaluate("() => ({label: document.querySelector('#sleepResultLabel').textContent, time: document.querySelector('#sleepResultTime').textContent, anchor: document.querySelector('#anchorTime').value, tip: document.querySelector('#dialAnchor .dial-tip').checkVisibility({opacityProperty: true, visibilityProperty: true})})")
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []}); p.wait_for_timeout(100)
        assert reading['label'] == 'AUFSTEHEN' and reading['time'] == reading['anchor'] and not reading['tip'], f'During a touch drag the readout shows the dragged wake time and the tip under the finger stays hidden: {reading}'
        assert p.locator('#sleepResultLabel').text_content() == 'INS BETT', 'After the touch drag the readout shows the bedtime again'
        assert p.locator('#anchorTime').input_value() == '06:00' and p.locator('#sleepResultTime').inner_text() == '21:50', f'Touch drag moves the wake time: {p.locator("#anchorTime").input_value()}'
        assert p.evaluate('scrollY') == scroll_before, 'Dragging a dial handle does not scroll the page'
        touch_size = p.locator('#dialAnchor').bounding_box()
        assert touch_size['width'] >= 48 and touch_size['height'] >= 48, f'Dial handles are 48px on touch: {touch_size}'
        report['touch'].append('402px: dial handle follows a touch drag to 06:00 without scrolling the page')
    # Touch tablets keep the spatial preview.
    for width in [768, 1024]:
        p.set_viewport_size({'width': width, 'height': 1024}); p.goto(args.base_url)
        for name in ['grade', 'sleep', 'code']:
            p.locator(f'[data-select={name}]').tap(); p.wait_for_timeout(550)
            assert p.locator(f'[data-select={name}]').get_attribute('aria-pressed') == 'true'
            assert p.locator('[data-workbench]').get_attribute('data-selection') == name
        for name in ['grade', 'sleep', 'code']:
            # Find an actually exposed part of the spatial card; never force clicks.
            point = p.locator(f'[data-module={name}]').evaluate('''el => {
              const r = el.getBoundingClientRect();
              for (let y = Math.max(0,r.top+8); y < Math.min(innerHeight,r.bottom-8); y+=5)
                for (let x = Math.max(0,r.left+8); x < Math.min(innerWidth,r.right-8); x+=5)
                  if ([-12,0,12].every(dx => [-12,0,12].every(dy => el.contains(document.elementFromPoint(x+dx,y+dy))))) return {x,y};
              return null;
            }''')
            if not point:
                p.screenshot(path=str(args.output/f'touch-unexposed-{width}-{name}.png'))
                print(p.locator('.scene').evaluate('el=>({box:el.getBoundingClientRect().toJSON(),scroll:scrollY,width:innerWidth,selection:el.parentElement.dataset.selection,modules:[...el.querySelectorAll("[data-module]")].map(e=>({name:e.dataset.module,box:e.getBoundingClientRect().toJSON()}))})'))
            assert point, f'No exposed touch area: {width} {name}'
            p.touchscreen.tap(point['x'], point['y']); p.wait_for_timeout(550)
            actual = p.locator('[data-workbench]').get_attribute('data-selection')
            if actual != name: p.screenshot(path=str(args.output/f'touch-failure-{width}-{name}.png'))
            assert actual == name, f'Touch {width}px expected {name}, got {actual} at {point}'
        # The front card is a real link.
        p.locator('[data-select=grade]').tap(); p.wait_for_timeout(550)
        box = p.locator('.module-grade').bounding_box()
        p.touchscreen.tap(box['x'] + box['width'] * .4, box['y'] + box['height'] * .55)
        p.wait_for_url('**/sechserrechner/')
        report['touch'].append(f'{width}px: all spatial cards and selector buttons, front card opens its tool')
    # Rotating or resizing while the arrival morph runs must not leak an uncaught promise rejection.
    before = len(errors)
    p.set_viewport_size({'width': 402, 'height': 874}); p.wait_for_timeout(700)
    resize_errors = errors[before:]; del errors[before:]
    report['motion']['resize_during_arrival'] = {'page_errors': resize_errors}
    # Phone band, live tier: scrolling scrubs gauge -> ring -> cube, captions follow, frames stop after scrolling.
    # A 3x phone screen proves the touch DPR cap of 1.25 (spec §5.5.6).
    band_context = browser.new_context(has_touch=True, is_mobile=True, device_scale_factor=3, viewport={'width': 402, 'height': 874}, locale='de-CH', timezone_id='Europe/Zurich', reduced_motion='no-preference')
    band_context.add_init_script(INIT)
    p = band_context.new_page(); p.on('pageerror', lambda error: errors.append(str(error)))
    p.goto(BASE + '?gl=force'); p.wait_for_function(SETTLED, timeout=15000)
    if p.evaluate(STATE) == 'fallback':
        report['hero']['phone_band'] = 'skipped: no WebGL (fallback)'
    else:
        seen = []
        band_top = p.locator('.hero-visual').evaluate('el => el.getBoundingClientRect().top + scrollY')
        for y in range(0, int(band_top) + 40, 20):
            p.evaluate(f'scrollTo(0, {y}); window.__lastInputAt = performance.now()'); p.wait_for_timeout(50)
            form = p.locator('.hero-visual').get_attribute('data-glass-form')
            active = p.locator('.orb-captions li[data-active]').evaluate_all('els => els.map(el => el.dataset.form)')
            assert active == [form], f'Band captions follow the shown form: {form} {active}'
            if not seen or seen[-1] != form: seen.append(form)
        assert seen == ['grade', 'sleep', 'code'], f'Band scroll scrubs gauge -> ring -> cube: {seen}'
        stopped, gap = frames_stop(p, 1200)
        assert stopped and p.evaluate(STATE) == 'idle', f'Band frames stop after scrolling ({gap} ms)'
        assert p.evaluate('HeroGL.stats.backing[0] * HeroGL.stats.backing[1]') <= 1.1e6
        band_stats, band_css = p.evaluate('HeroGL.stats'), p.locator('.glass-stage').bounding_box()
        assert band_stats['backing'][0] <= round(band_css['width'] * 1.25) + 1, f'Touch band caps the device pixel ratio at 1.25 on a 3x screen: {band_stats} {band_css}'
        report['hero']['phone_band'] = {'forms': seen, 'last_frame_after_input_ms': gap, 'backing': band_stats['backing'], 'css_width': band_css['width']}
    band_context.close(); touch.close()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='de-CH', color_scheme='dark', reduced_motion='no-preference', record_video_dir=str(args.output/'video'))
    context.add_init_script(INIT)
    p = context.new_page(); p.on('pageerror', lambda error: errors.append(str(error)))
    p.goto(args.base_url)
    p.wait_for_function(SETTLED, timeout=15000)
    report['hero']['default_state'] = p.evaluate(STATE)
    scene = p.locator('.scene').bounding_box()
    p.mouse.move(scene['x']+scene['width']*.85, scene['y']+scene['height']*.4)
    p.wait_for_timeout(1000)
    before = p.evaluate('__frameRequests'); p.wait_for_timeout(350)
    assert p.evaluate('__frameRequests') == before, 'Scene schedules frames while idle'
    report['motion']['pointer_settled_requests'] = before
    p.locator('[data-select=sleep]').click()
    transforms = []
    for wait, label in [(80,'early'),(140,'middle'),(380,'settled')]:
        p.wait_for_timeout(wait)
        transforms.append(p.locator('.module-sleep').evaluate('(el)=>getComputedStyle(el).transform'))
        p.screenshot(path=str(args.output/f'scene-{label}.png'))
    assert len(set(transforms)) == 3, 'Scene selection did not animate through distinct transforms'
    report['motion']['selection_transforms'] = transforms
    assert p.locator('.hero-visual').get_attribute('data-glass-form') == 'sleep', 'Glass object follows the sleep selection'
    assert p.locator('.scene').evaluate('(el)=>el.getAnimations({subtree:true}).length') == 0, 'Scene animation never settles'
    assert p.locator('[data-motion-toggle]').count() == 0, 'No manual motion toggle'
    p.locator('#hintergrund').scroll_into_view_if_needed(); p.wait_for_timeout(350)
    count = p.evaluate('__frameRequests'); p.wait_for_timeout(300)
    assert p.evaluate('__frameRequests') == count
    report['motion']['offscreen_stops_frames'] = True
    p.evaluate('scrollTo(0,0)'); p.wait_for_timeout(450)
    p.mouse.move(scene['x']+45,scene['y']+75)
    if args.browser == 'chromium':
        native_focus = context.new_cdp_session(p)
        native_focus.send('Emulation.setFocusEmulationEnabled', {'enabled':False})
    other = context.new_page(); other.goto('about:blank'); other.bring_to_front(); p.wait_for_timeout(200)
    hidden = p.evaluate('document.hidden')
    cdp = None
    if not hidden and args.headed and args.browser == 'chromium':
        cdp = context.new_cdp_session(p)
        window_id = cdp.send('Browser.getWindowForTarget')['windowId']
        cdp.send('Browser.setWindowBounds', {'windowId':window_id,'bounds':{'windowState':'minimized'}})
        p.wait_for_timeout(300); hidden = p.evaluate('document.hidden')
    if hidden:
        count = p.evaluate('__frameRequests'); p.wait_for_timeout(300)
        assert p.evaluate('__frameRequests') == count
    report['motion']['hidden_document_observed'] = hidden
    report['motion']['hidden_method'] = 'Native browser window minimised' if cdp else 'Second browser page brought to foreground'
    if cdp: cdp.send('Browser.setWindowBounds', {'windowId':window_id,'bounds':{'windowState':'normal'}})
    other.close(); p.bring_to_front()
    p.locator('.hero-actions a').first.click(); p.wait_for_url('**/sechserrechner/')
    p.screenshot(path=str(args.output/'transition-grade.png'))
    p.wait_for_timeout(550)
    report['motion']['cross_document_events'] = p.evaluate('__transitions')
    assert report['motion']['cross_document_events'] and any(t['ready'] and t['finished'] for t in report['motion']['cross_document_events']), 'Cross-document transition was not observed'
    types_supported = p.evaluate("typeof ViewTransition !== 'undefined' && 'types' in ViewTransition.prototype")
    if types_supported:
        assert all('forward' in (t.get('types') or []) for t in report['motion']['cross_document_events'] if t['ready']), f"Home -> tool transition carries the forward type: {report['motion']['cross_document_events']}"
    # After the morph the page is still: the load stagger must not replay once html.vt-arrival is removed.
    p.wait_for_function("!document.documentElement.classList.contains('vt-arrival')"); p.wait_for_timeout(150)
    replayed = p.evaluate("document.getAnimations().filter(a => a.animationName === 'load-rise' && a.playState === 'running').length")
    report['motion']['load_rise_after_arrival'] = replayed
    assert p.evaluate("document.documentElement.classList.contains('vt-arrived')"), 'The arrival morph leaves html.vt-arrived behind, so the stagger stays off'
    p.go_back(); p.wait_for_timeout(550)
    report['motion']['back_transition_events'] = p.evaluate('__transitions')
    if types_supported:
        assert all('back' in (t.get('types') or []) for t in report['motion']['back_transition_events'] if t['ready']) and any(t['ready'] for t in report['motion']['back_transition_events']), f"Tool -> home transition carries the back type: {report['motion']['back_transition_events']}"
    p.emulate_media(reduced_motion='reduce'); p.locator('[data-select=code]').click()
    assert p.locator('.scene').evaluate('(el)=>el.getAnimations({subtree:true}).length') == 0
    report['motion']['reduced_motion_no_scene_animation'] = True
    # Reduced motion: navigation is instant, without a view transition or the arrival class.
    p.locator('[data-select=grade]').click(); p.locator('.hero-actions a').first.click(); p.wait_for_url('**/sechserrechner/'); p.wait_for_timeout(300)
    reduced_nav = {'transitions': p.evaluate('__transitions'), 'classes': p.evaluate('document.documentElement.className')}
    assert not any(t['ready'] for t in reduced_nav['transitions']) and 'vt-arrival' not in reduced_nav['classes'], f'Reduced motion navigates without a view transition: {reduced_nav}'
    report['motion']['reduced_motion_navigation'] = reduced_nav
    p.emulate_media(reduced_motion='no-preference')

    # Reduced motion from the first frame: a still frame or the fallback, then no frame requests at all.
    g = context.new_page(); g.on('pageerror', lambda error: errors.append(str(error)))
    g.emulate_media(reduced_motion='reduce'); g.goto(BASE); g.wait_for_function(SETTLED, timeout=15000)
    reduced_state = g.evaluate(STATE)
    assert reduced_state in ('still', 'fallback'), f'Reduced motion renders a still frame or the fallback: {reduced_state}'
    count = g.evaluate('__frameRequests'); g.wait_for_timeout(500)
    assert g.evaluate('__frameRequests') == count, 'Reduced motion requests no frames after the hero settles'
    drawn = g.evaluate('HeroGL.stats.frames')
    g.locator('[data-select=sleep]').click(); g.wait_for_timeout(300)
    assert g.evaluate('__frameRequests') == count, 'Reduced motion selection redraws without an animation loop'
    assert reduced_state == 'fallback' or g.evaluate('HeroGL.stats.frames') > drawn, 'Still tier draws the new form'
    report['hero']['reduced_motion'] = {'state': reduced_state, 'frames_drawn': g.evaluate('HeroGL.stats.frames')}
    g.close()

    # ?gl=off: the CSS/SVG specimen, no page errors, selection still works.
    g = context.new_page(); g.on('pageerror', lambda error: errors.append(str(error)))
    g.goto(BASE + '?gl=off'); g.wait_for_function(SETTLED, timeout=15000)
    assert g.evaluate(STATE) == 'fallback' and g.locator('.hero-visual').get_attribute('data-glass-tier') == 'fallback', '?gl=off selects the fallback tier'
    assert g.locator('.glass-fallback svg[data-form=grade]').is_visible(), 'Fallback shows the grade specimen'
    g.locator('[data-select=code]').click(); g.wait_for_timeout(400)
    assert g.locator('.hero-visual').get_attribute('data-glass-form') == 'code' and g.locator('.glass-fallback svg[data-form=code]').evaluate('el => getComputedStyle(el).opacity') == '1', 'Fallback specimen follows the selection'
    box = g.locator('.scene').bounding_box(); g.mouse.move(box['x'] + box['width'] * .8, box['y'] + box['height'] * .3); g.wait_for_timeout(1000)
    count = g.evaluate('__frameRequests'); g.wait_for_timeout(350)
    assert g.evaluate('__frameRequests') == count, 'Fallback tilt loop settles'
    report['hero']['gl_off'] = 'fallback specimen, selection crossfade, tilt settles'
    g.close()

    # ?gl=force: the live tier on a software renderer (skipped when there is no WebGL at all).
    # Rendered on a 3x screen so the desk DPR cap of 1.5 is observable.
    dense = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=3, locale='de-CH', color_scheme='dark', reduced_motion='no-preference')
    dense.add_init_script(INIT)
    g = dense.new_page(); g.on('pageerror', lambda error: errors.append(str(error)))
    g.goto(BASE + '?gl=force'); g.wait_for_function(SETTLED, timeout=15000)
    if g.evaluate(STATE) == 'fallback':
        report['hero']['gl_force'] = 'skipped: no WebGL (fallback)'
    else:
        live = {}
        states = g.evaluate('__glassStates')
        assert 'live' in states and states[-1] == 'idle' and g.evaluate('HeroGL.tier') == 'live', f'?gl=force reaches live, then idle: {states}'
        stats = g.evaluate('HeroGL.stats')
        assert stats['backing'][0] * stats['backing'][1] <= 1.1e6, f'Backing store at most 1.1 MP: {stats}'
        css = g.locator('.glass-stage').bounding_box()
        assert stats['backing'][0] <= round(css['width'] * 1.5) + 1, f'Device pixel ratio capped at 1.5 on a 3x screen: {stats} {css}'
        live['backing'] = stats['backing']; live['css_width'] = css['width']
        count = g.evaluate('__frameRequests'); g.wait_for_timeout(300)
        assert g.evaluate('__frameRequests') == count, 'Live tier requests no frames when idle'
        # Pointer burst: the object follows, then rendering stops within 1.2 s.
        stage = g.locator('.hero-visual').bounding_box(); drawn = g.evaluate('HeroGL.stats.frames')
        for i in range(14):
            g.mouse.move(stage['x'] + stage['width'] * (.3 + i * .03), stage['y'] + stage['height'] * (.35 + (i % 3) * .05)); g.wait_for_timeout(30)
        stopped, gap = frames_stop(g, 1200)
        assert g.evaluate('HeroGL.stats.frames') > drawn and stopped and g.evaluate(STATE) == 'idle', f'Frames stop within 1.2 s after a pointer burst ({gap} ms)'
        live['pointer_burst_last_frame_ms'] = gap
        # Selection morph: form flips at morph start, frames stop within 1.2 s.
        g.locator('[data-select=code]').click()
        assert g.locator('.hero-visual').get_attribute('data-glass-form') == 'code', 'Selecting code sets data-glass-form=code'
        stopped, gap = frames_stop(g, 1200)
        assert stopped and g.evaluate(STATE) == 'idle', f'Frames stop within 1.2 s after a selection ({gap} ms)'
        live['selection_last_frame_ms'] = gap
        g.locator('[data-select=grade]').click(); frames_stop(g, 1200)
        # The canvas background is transparent: no grey wash over the page at the stage corner.
        g.mouse.move(5, 500); g.evaluate('scrollTo(0, 0)'); g.wait_for_function(f"{SETTLED}", timeout=5000); frames_stop(g, 1200)
        corner = g.locator('.glass-stage').bounding_box(); clip = {'x': corner['x'], 'y': corner['y'], 'width': 4, 'height': 4}
        with_canvas = pixels(g, clip)
        g.locator('.glass-canvas').evaluate("el => el.style.visibility = 'hidden'"); without = pixels(g, clip)
        g.locator('.glass-canvas').evaluate("el => el.style.visibility = ''")
        wash = max(abs(a - b) for pa, pb in zip(with_canvas, without) for a, b in zip(pa, pb))
        alpha = g.evaluate('''() => { HeroGL.render(); const c = document.querySelector('.glass-canvas'); const gl = c.getContext('webgl2') || c.getContext('webgl');
          const px = new Uint8Array(4), out = []; for (const [x, y] of [[0, 0], [c.width - 1, 0], [0, c.height - 1], [c.width - 1, c.height - 1]]) { gl.readPixels(x, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px); out.push(px[3]); } return out; }''')
        bg = g.evaluate("getComputedStyle(document.body).backgroundColor")
        assert wash <= 3 and alpha == [0, 0, 0, 0], f'Stage corner shows the page background through the canvas (delta {wash}, alpha {alpha})'
        live['corner'] = {'delta_vs_hidden_canvas': wash, 'canvas_corner_alpha': alpha, 'sample': with_canvas[0], 'page_bg': bg}
        # Hover over the object shows the pointer cursor; a drag rotates and never opens the tool.
        centre = (stage['x'] + stage['width'] * .5, stage['y'] + stage['height'] * .46)
        g.mouse.move(*centre); g.wait_for_timeout(100)
        assert g.locator('.hero-visual').evaluate("el => el.classList.contains('is-over-object')"), 'Hovering the glass object marks it as clickable'
        g.mouse.move(stage['x'] + 8, stage['y'] + stage['height'] * .5); g.wait_for_timeout(100)
        assert not g.locator('.hero-visual').evaluate("el => el.classList.contains('is-over-object')"), 'Leaving the object clears the pointer cursor'
        g.mouse.move(*centre); g.mouse.down(); g.mouse.move(centre[0] + 90, centre[1], steps=6); g.mouse.up(); g.wait_for_timeout(200)
        assert 'sechserrechner' not in g.url, 'Dragging the object rotates it and does not open the tool'
        stopped, gap = frames_stop(g, 1200)
        assert stopped, f'Frames stop after a drag ({gap} ms)'
        # Theme toggle with motion: the circle reveal renders the new theme, then idle again.
        drawn = g.evaluate('HeroGL.stats.frames')
        g.locator('[data-theme-toggle]').click(); g.wait_for_function("document.documentElement.dataset.theme === 'light'")
        stopped, gap = frames_stop(g, 1200)
        assert g.evaluate('HeroGL.stats.frames') > drawn and stopped, 'Theme change renders the porcelain frame, then stops'
        g.locator('[data-theme-toggle]').click(); g.wait_for_function("document.documentElement.dataset.theme === 'dark'")
        frames_stop(g, 1200)
        # Offscreen and hidden: no frames.
        g.locator('#hintergrund').scroll_into_view_if_needed(); g.wait_for_timeout(350)
        count = g.evaluate('__frameRequests'); g.wait_for_timeout(300)
        assert g.evaluate('__frameRequests') == count, 'Live tier stops at once when the hero scrolls away'
        g.evaluate('scrollTo(0, 0)'); g.wait_for_timeout(200)
        other = context.new_page(); other.goto('about:blank'); other.bring_to_front(); g.wait_for_timeout(200)
        if g.evaluate('document.hidden'):
            count = g.evaluate('__frameRequests'); g.wait_for_timeout(300)
            assert g.evaluate('__frameRequests') == count, 'Hidden tab renders no frames'
        live['hidden_document_observed'] = g.evaluate('document.hidden')
        other.close(); g.bring_to_front()
        # The specimen is safe to play with; only its explicit link navigates.
        frames_stop(g, 1200)
        before = g.evaluate('HeroGL.stats.frames'); home = g.url
        g.mouse.click(*centre)
        stopped, gap = frames_stop(g, 1200)
        assert g.url == home and g.evaluate('HeroGL.stats.frames') > before and stopped, 'Object click plays a finite effect without navigating'
        live['object_click_stays'] = home
        g.locator('[data-scene-link]').click(); g.wait_for_url('**/sechserrechner/')
        live['explicit_link_opens'] = g.url
        report['hero']['gl_force'] = live
    g.close(); dense.close()

    report['motion']['layout_shift'] = shifts = layout_shift(browser)

    if args.axe:
        for route, states in [('', ['start', 'json']), ('sechserrechner/', ['example', 'overview']), ('sleepcalculator/', ['start', 'preset-form'])]:
            for theme in ['light','dark']:
                for width in [402,1440]:
                    for state in states:
                        p.set_viewport_size({'width':width,'height':874}); p.goto(args.base_url.rstrip('/')+'/'+route)
                        if route == 'sechserrechner/': p.evaluate("localStorage.removeItem('misterpfister-grades-v2')"); p.reload()
                        if p.locator('html').get_attribute('data-theme') != theme: p.locator('[data-theme-toggle]').click()
                        # With motion allowed the theme lands inside the view-transition callback, one frame later.
                        p.wait_for_function(f"document.documentElement.dataset.theme === '{theme}' && !document.documentElement.classList.contains('theme-vt')")
                        if route == 'sechserrechner/': p.locator('#loadExample').click(); p.locator('#closeToast').click()
                        if state == 'json': p.locator('[data-format=json]').click(); p.evaluate("document.querySelector('.story-details').open = true")
                        if state == 'overview':
                            p.locator('#addSubject').click(); p.locator('#subjectName').fill('Mathematik'); p.locator('#subjectName').press('Enter'); p.locator('.grade-grade').first.fill('4')
                            assert p.locator('#overviewPanel').is_visible(), 'The overview is scanned with two subjects'
                        if state == 'preset-form': p.locator('#showPresetForm').click()
                        p.wait_for_timeout(250)
                        p.add_script_tag(path=str(args.axe))
                        result = p.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa','best-practice']}});return {violations:r.violations,incomplete:r.incomplete.map(i=>({id:i.id,nodes:i.nodes.map(n=>n.target)}))}}")
                        report['accessibility'].append({'route':route,'state':state,'theme':theme,'width':width,**result})
    context.close(); browser.close()
report['errors'] = errors
(args.output/'interaction-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
failures = []
if errors: failures.append(f'Page errors: {errors}')
if resize_errors: failures.append(f'Resizing during the arrival view transition leaks an uncaught rejection: {resize_errors}')
unstable = {page: value['cls'] for page, value in shifts.items() if value['cls'] > .02}
if unstable: failures.append(f"Layout shift above CLS .02 on load: {unstable} {[(page, value['shifts']) for page, value in shifts.items() if value['cls'] > .02]}")
if replayed: failures.append(f'The .load-rise stagger replays after the arrival view transition ({replayed} running animations)')
violations = [item for item in report['accessibility'] if item['violations']]
if violations: failures.append(f"axe violations: {[(v['route'],v['state'],v['theme'],v['width'],[(i['id'],[n['target'] for n in i['nodes']][:3]) for i in v['violations']]) for v in violations]}")
assert not failures, ' | '.join(failures)
print('PASS: real touch, dial drag, finite scene motion, hero tiers, native view transitions, load CLS (fresh and saved data)' + (f" and {len(report['accessibility'])} axe scans" if args.axe else ''))
