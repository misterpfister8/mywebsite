"""Check gradient-endpoint text contrasts that automated axe reports as incomplete."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

results=[]
with sync_playwright() as w:
    b=w.chromium.launch();p=b.new_page(viewport={'width':1440,'height':1000})
    for route in ['', 'sleepcalculator/']:
        p.goto('http://127.0.0.1:8000/'+route)
        for theme in ['dark','light']:
            if p.locator('html').get_attribute('data-theme')!=theme:p.locator('[data-theme-toggle]').click()
            p.wait_for_timeout(100)
            pairs=p.evaluate('''()=>{
              const style = el=>getComputedStyle(el);
              const rgb = value => value.match(/rgb\\([^)]*\\)/g) || [];
              let pairs=[];
              for(const module of document.querySelectorAll('.module')) {
                const backgrounds=rgb(style(module).backgroundImage);
                for(const foreground of [style(module).color,...[...module.querySelectorAll('.mini-clock')].map(el=>style(el).color)])
                  for(const background of backgrounds) pairs.push({label:module.dataset.module,foreground,background});
              }
              const clock=document.querySelector('.sleep-visual');
              if(clock) for(const el of clock.querySelectorAll('h2,span,output,b,small'))
                for(const background of rgb(style(clock).backgroundImage)) pairs.push({label:el.id||el.tagName,foreground:style(el).color,background});
              const brand=document.querySelector('.brand-mark');
              pairs.push({label:'brand',foreground:style(brand).color,background:style(brand).backgroundColor});
              const preview=document.querySelector('.sleep-preview .mini-clock');
              if(preview) pairs.push({label:'mini clock',foreground:style(preview).color,background:style(document.querySelector('.card-sleep')).backgroundColor});
              return pairs;
            }''')
            def lum(color):
                channels=[int(x.strip())/255 for x in color.split('(')[1].split(')')[0].split(',')[:3]]
                linear=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in channels]
                return sum(v*c for v,c in zip(linear,[.2126,.7152,.0722]))
            for pair in pairs:
                a,bg=lum(pair['foreground']),lum(pair['background'])
                ratio=(max(a,bg)+.05)/(min(a,bg)+.05)
                assert ratio>=4.5,(route,theme,pair,ratio)
                results.append({'route':route,'theme':theme,**pair,'ratio':round(ratio,2)})
    b.close()
Path('output/playwright/gradient-contrast.json').write_text(json.dumps(results,indent=2))
print(f'PASS: {len(results)} gradient/brand text pairs >= 4.5:1; minimum {min(r["ratio"] for r in results)}:1')
