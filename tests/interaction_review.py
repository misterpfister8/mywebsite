"""Real browser touch, motion and optional axe checks. Run against the HTTP site."""
import argparse
import json
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
report = {'browser': args.browser, 'touch': [], 'motion': {}, 'accessibility': []}
errors = []
with sync_playwright() as pw:
    browser = getattr(pw, args.browser).launch(headless=not args.headed)
    report['version'] = browser.version
    touch = browser.new_context(has_touch=True, is_mobile=True, locale='de-CH', timezone_id='Europe/Zurich')
    p = touch.new_page(); p.on('pageerror', lambda error: errors.append(str(error)))
    for width in [320, 375, 402]:
        p.set_viewport_size({'width': width, 'height': 874}); p.goto(args.base_url)
        for name in ['grade', 'sleep', 'code']:
            p.locator(f'[data-select={name}]').tap(); p.wait_for_timeout(550)
            assert p.locator(f'[data-module={name}]').get_attribute('aria-pressed') == 'true'
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
                print(p.locator('.scene').evaluate('el=>({box:el.getBoundingClientRect().toJSON(),scroll:scrollY,width:innerWidth,selection:el.parentElement.dataset.selection,modules:[...el.querySelectorAll("button")].map(e=>({name:e.dataset.module,box:e.getBoundingClientRect().toJSON()}))})'))
            assert point, f'No exposed touch area: {width} {name}'
            p.touchscreen.tap(point['x'], point['y']); p.wait_for_timeout(550)
            actual = p.locator('[data-workbench]').get_attribute('data-selection')
            if actual != name: p.screenshot(path=str(args.output/f'touch-failure-{width}-{name}.png'))
            assert actual == name, f'Touch {width}px expected {name}, got {actual} at {point}'
        p.locator('[data-motion-toggle]').tap()
        assert p.locator('[data-motion-toggle]').get_attribute('aria-pressed') == 'true'
        report['touch'].append(f'{width}px: all spatial cards and selector buttons, pause')
    touch.close()
    context = browser.new_context(viewport={'width': 1440, 'height': 1000}, locale='de-CH', color_scheme='dark', reduced_motion='no-preference', record_video_dir=str(args.output/'video'))
    context.add_init_script('''(() => {
      const native = window.requestAnimationFrame;
      window.__frameRequests = 0;
      window.requestAnimationFrame = callback => { window.__frameRequests++; return native.call(window,callback); };
      window.__transitions = [];
      addEventListener('pagereveal', e => {
        if(e.viewTransition) {
          const record = {ready:false,finished:false}; __transitions.push(record);
          e.viewTransition.ready.then(()=>{record.ready=true},err=>{record.error=String(err)});
          e.viewTransition.finished.then(()=>{record.finished=true},err=>{record.error=String(err)});
        }
      });
    })();''')
    p = context.new_page(); p.on('pageerror', lambda error: errors.append(str(error)))
    p.goto(args.base_url)
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
    assert p.locator('.scene').evaluate('(el)=>el.getAnimations({subtree:true}).length') == 0, 'Scene animation never settles'
    p.locator('[data-motion-toggle]').click()
    p.mouse.move(scene['x']+50,scene['y']+100)
    count = p.evaluate('__frameRequests'); p.wait_for_timeout(300)
    assert p.evaluate('__frameRequests') == count
    report['motion']['pause_stops_frames'] = True
    p.locator('[data-motion-toggle]').click()
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
    p.go_back(); p.wait_for_timeout(550)
    report['motion']['back_transition_events'] = p.evaluate('__transitions')
    p.emulate_media(reduced_motion='reduce'); p.locator('[data-select=code]').click()
    assert p.locator('.scene').evaluate('(el)=>el.getAnimations({subtree:true}).length') == 0
    report['motion']['reduced_motion_no_scene_animation'] = True
    p.emulate_media(reduced_motion='no-preference')
    if args.axe:
        for route in ['', 'sechserrechner/', 'sleepcalculator/']:
            for theme in ['light','dark']:
                for width in [402,1440]:
                    p.set_viewport_size({'width':width,'height':874}); p.goto(args.base_url.rstrip('/')+'/'+route)
                    if p.locator('html').get_attribute('data-theme') != theme: p.locator('[data-theme-toggle]').click()
                    if route == 'sechserrechner/': p.locator('#loadExample').click(); p.locator('#closeToast').click()
                    p.add_script_tag(path=str(args.axe))
                    result = p.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}});return {violations:r.violations,incomplete:r.incomplete.map(i=>({id:i.id,nodes:i.nodes.map(n=>n.target)}))}}")
                    report['accessibility'].append({'route':route,'theme':theme,'width':width,**result})
    context.close(); browser.close()
report['errors'] = errors
(args.output/'interaction-report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
assert not errors, errors
violations = [item for item in report['accessibility'] if item['violations']]
assert not violations, [(v['route'],v['theme'],v['width'],[i['id'] for i in v['violations']]) for v in violations]
print('PASS: real touch, finite scene motion, native view transitions' + (' and axe checks' if args.axe else ''))
