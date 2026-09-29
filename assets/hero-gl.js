/* Hero engine (spec §5.5): glass specimen, zero rAF when idle. Compact for the 22 KB budget. */
(()=>{
  'use strict';
  const hv=document.querySelector('.hero-visual[data-glass]'),cv=hv?.querySelector('.glass-canvas');
  if (!cv) return;
  const doc=document,root=doc.documentElement,stage=hv.querySelector('.glass-stage')||hv;
  const bench=doc.querySelector('[data-workbench]'),tiltEl=bench?.querySelector('.scene-stage');
  const link=bench?.querySelector('[data-scene-link]'),hero=hv.closest('.hero')||hv;
  const caps=hv.querySelectorAll('.orb-captions [data-form]');
  const mq=(q)=>matchMedia(q),RM=mq('(prefers-reduced-motion: reduce)'),BAND=mq('(max-width: 680px)');
  const COARSE=mq('(pointer: coarse)'),flag=new URLSearchParams(location.search).get('gl');
  const FORMS=['grade','sleep','code'],POSE=[[-.35,.18],[.3,-.12],[.62,-.55]];
  const hex=(h)=>[1,3,5].map((i)=>parseInt(h.slice(i,i+2),16)/255);
  const PAL=[['#0B0D0F','#CEF779 #7DF3E1 #C6B9FF #FF9EC7','#C4F46A #A896FF #62E6D2',1],
    ['#F2F3EE','#6E9B2A #1E9488 #7C68C8 #C0508A','#6FA626 #6F58D6 #149C8C',.4]]
    .map(([b,c,e,g])=>({b:hex(b),c:c.split(' ').map(hex),e:e.split(' ').map(hex),g}));
  const clamp=(v,a=0,b=1)=>Math.min(b,Math.max(a,v));
  const ss=(a,b,x)=>{const t=clamp((x-a)/(b-a)); return t*t*(3-2*t);};
  const mix=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
  const now=()=>performance.now(),cap=(v)=>Math.min(2,v);
  const FS=`precision highp float;uniform vec2 uRes,uOff;uniform float uFov,uTime,uScale,uFormA,uFormB,uMorph,uWob,uTheme,uFilm,uGradeT,uSteps,uShadow,uSweep,uGlow;uniform mat3 uRot;uniform vec4 uReach,uSleep;uniform vec3 uBg,uC0,uC1,uC2,uC3,uEmit;float gE;float smin(float a,float b,float k){float h=max(k-abs(a-b),0.)/k;return min(a,b)-h*h*k*.25;}float smax(float a,float b,float k){return-smin(-a,-b,k);}vec3 rotZ(vec3 p,float a){float c=cos(a),s=sin(a);return vec3(c*p.x-s*p.y,s*p.x+c*p.y,p.z);}float angDeg(vec3 p){return degrees(atan(p.x,abs(p.y)<1e-5?1e-5:p.y));}vec3 onArc(float deg,float R){float a=radians(deg);return vec3(sin(a)*R,cos(a)*R,0.);}float sdCappedTorus(vec3 p,vec2 sc,float ra,float rb){p.x=abs(p.x);float k=(sc.y*p.x>sc.x*p.y)?dot(p.xy,sc):length(p.xy);return sqrt(max(dot(p,p)+ra*ra-2.*ra*k,0.))-rb;}float sdArc(vec3 p,float midDeg,float halfDeg,float R,float r){float h=radians(halfDeg);return sdCappedTorus(rotZ(p,radians(midDeg)),vec2(sin(h),cos(h)),R,r);}float sdTorusXY(vec3 p,float R,float r){vec2 q=vec2(length(p.xy)-R,p.z);return length(q)-r;}float sdCapsule(vec3 p,vec3 a,vec3 b,float r){vec3 pa=p-a,ba=b-a;float h=clamp(dot(pa,ba)/dot(ba,ba),0.,1.);return length(pa-ba*h)-r;}float sdRoundBox(vec3 p,vec3 b,float r){vec3 q=abs(p)-b+r;return length(max(q,0.))+min(max(q.x,max(q.y,q.z)),0.)-r;}float fGauge(vec3 p){float va=-135.+270.*uGradeT;float track=sdArc(p,0.,135.,.74,.045);float fill=sdArc(p,(va-135.)*.5,(va+135.)*.5,.74,.115);float bead=length(p-onArc(va,.74))-.19;float needle=sdCapsule(p,vec3(0.),onArc(va,.5),.034);float hub=length(p)-.1;float i=clamp(floor((angDeg(p)+135.)/27.+.5),0.,10.);vec3 tq=rotZ(p,radians(-135.+27.*i));float tl=mod(i,2.)<.5?.1:.055;float tick=sdCapsule(tq,vec3(0.,.97,0.),vec3(0.,.97+tl,0.),.02);float ref=length(p-onArc(27.,1.17))-.05;gE=min(fill,needle);float d=smin(fill,bead,.08);d=min(d,track);d=smin(d,min(needle,hub),.05);return min(d,min(tick,ref));}float fRing(vec3 p){float track=sdTorusXY(p,.84,.032);float arc=sdArc(p,uSleep.x+uSleep.y*.5,uSleep.y*.5,.84,.085);float wake=length(p-onArc(uSleep.z,.84))-.125;float bed=length(p-onArc(uSleep.w,.84))-.06;float i=floor(angDeg(p)/15.+.5);vec3 tq=rotZ(p,radians(i*15.));float tl=mod(i,6.)<.5?.1:.05;float tick=sdCapsule(tq,vec3(0.,.96,0.),vec3(0.,.96+tl,0.),.017);float moon=smax(length(p)-.44,-(length(p-vec3(.21,.15,0.))-.37),.02);gE=arc;float d=smin(track,arc,.04);d=smin(d,wake,.06);d=min(d,min(bed,tick));return min(d,moon);}float fCube(vec3 p){float blocks=sdRoundBox(abs(p)-vec3(.33),vec3(.26),.06);float ex=sdRoundBox(p-vec3(.84,.72,.3),vec3(.13),.035);gE=ex;return min(blocks,ex);}float form(float id,vec3 p){if(id<.5)return fGauge(p);if(id<1.5)return fRing(p);return fCube(p);}float map(vec3 p){p=(uRot*p)/uScale;float d;if(uMorph<=0.){d=form(uFormA,p);}else{float drop=length(p)-.56;if(uMorph<.5)d=mix(form(uFormA,p),drop,smoothstep(0.,1.,uMorph*2.));else d=mix(drop,form(uFormB,p),smoothstep(0.,1.,uMorph*2.-1.));}float w=uWob+1.6*uMorph*(1.-uMorph);if(w>.001){d+=w*.03*sin(7.*p.x+uTime*5.)*sin(7.*p.y+uTime*4.)*sin(7.*p.z+uTime*6.);d/=1.+.4*w;}if(uReach.w>.01)d=smin(d,length(p-uReach.xyz)-.16*uReach.w,.45*uReach.w);return d*uScale;}vec3 nrm(vec3 p){vec2 e=vec2(.0015,-.0015)*uScale;return normalize(e.xyy*map(p+e.xyy)+e.yyx*map(p+e.yyx)+e.yxy*map(p+e.yxy)+e.xxx*map(p+e.xxx));}vec3 film(float x){x=abs(fract(x*.5)*2.-1.);vec3 a=mix(uC0,uC1,smoothstep(0.,.33,x));a=mix(a,uC2,smoothstep(.33,.66,x));return mix(a,uC3,smoothstep(.66,1.,x));}vec3 env(vec3 d){vec3 c=mix(uBg*.7,uBg*1.3+.03,d.y*.5+.5);float back=smoothstep(.1,-.9,d.z);c+=back*(uC0*smoothstep(.7,-.6,d.x+d.y)*.55+uC2*smoothstep(-.5,.8,d.x+d.y)*.6+uC1*.12)*mix(1.,.55,uTheme);float box1=smoothstep(.55,.5,abs(d.x+.35))*smoothstep(.2,.14,abs(d.y-.55))*step(0.,.4-d.z);float box2=smoothstep(.32,.28,abs(d.x-.62))*smoothstep(.5,.44,abs(d.y+.05));c+=box1*mix(2.6,1.6,uTheme)+box2*uC2*mix(1.5,.8,uTheme)+smoothstep(-.2,-.6,d.y)*uC0*.4;return c;}float softShadow(vec3 ro,vec3 rd){float res=1.,t=.04;for(int i=0;i<18;i++){float h=map(ro+rd*t);res=min(res,10.*h/t);t+=clamp(h,.03,.25);if(res<.02||t>3.)break;}return clamp(res,0.,1.);}void main(){vec2 uv=(gl_FragCoord.xy-.5*uRes)/uRes.y-uOff;vec3 ro=vec3(0.,0.,4.2),rd=normalize(vec3(uv*uFov,-1.));vec3 L=normalize(vec3(-.45,.85,.5));float pix=uFov/uRes.y;vec4 o=vec4(0.);float glow=1e3,t=0.,dmin=1e3,tmin=4.2;bool hit=false;vec3 p=ro;float b=dot(ro,rd),h=b*b-dot(ro,ro)+2.6244;if(h>0.){float sq=sqrt(h),tf=-b+sq;t=max(-b-sq,0.);for(int i=0;i<96;i++){if(float(i)>=uSteps)break;p=ro+rd*t;float d=map(p);glow=min(glow,gE);if(d<dmin){dmin=d;tmin=t;}if(d<.0006*t){hit=true;break;}t+=d*.85;if(t>tf)break;}}float cov=hit?1.:1.-smoothstep(0.,1.6*pix*tmin,dmin);if(cov>0.){if(!hit)p=ro+rd*tmin;map(p);float ge=gE;vec3 n=nrm(p),v=-rd;float nv=clamp(dot(n,v),0.,1.);float F=.04+.96*pow(1.-nv,5.);vec3 q=(uRot*p)/uScale;vec3 fc=film(.55+.3*sin(3.1*q.y+2.3*q.x+uTime*.25+uFilm)+.35*(1.-nv));vec3 refl=env(reflect(rd,n));vec3 refr=vec3(env(refract(rd,n,.704)).r,env(refract(rd,n,.690)).g,env(refract(rd,n,.671)).b);vec3 glass=mix(refr*mix(vec3(1.),fc,.35),refl*mix(vec3(1.),fc,.8),F)+fc*(.1+.75*pow(1.-nv,1.8));float wrap=clamp((dot(n,L)+.5)/1.5,0.,1.);vec3 alb=mix(vec3(.935,.94,.92),fc,.12);vec3 porc=(alb*(.56+.44*wrap)*(.86+.14*nv)+fc*pow(1.-nv,1.4)*.7+refl*F*.35)*(1.-.28*pow(1.-nv,3.));vec3 col=mix(glass,porc,uTheme);col+=uEmit*exp(-max(ge,0.)*30.)*(.2+.55*nv*nv)*mix(1.,.8,uTheme);vec3 hv=normalize(L+v);col+=pow(max(dot(n,hv),0.),mix(220.,90.,uTheme))*mix(3.2,1.3,uTheme);col+=pow(max(dot(n,normalize(normalize(vec3(.8,-.1,.4))+v)),0.),60.)*.6*uC2;col+=exp(-pow((dot(q.xy,vec2(.857,.514))-uSweep)*5.,2.))*(.25+F)*.8;col=mix(col/(1.+col*.55),min(col,vec3(1.)),uTheme);col=pow(col,vec3(.95));o=vec4(col*cov,cov);}else if(rd.y<0.){float tp=(-1.28-ro.y)/rd.y;vec3 g=ro+rd*tp;float r=length(g.xz);if(r<2.4){float fall=smoothstep(2.4,.2,r),sh;if(uShadow>.5)sh=1.-softShadow(g,L);else{vec2 s=(g.xz-vec2(.68,-.75))*vec2(1.,1.6);sh=exp(-dot(s,s)*1.4)*.9;}float a=sh*mix(.5,.44,uTheme)*fall;vec2 cc=g.xz-vec2(.35,.25);float caus=exp(-dot(cc,cc)*5.)*.36*fall*(1.-.5*uTheme);o=vec4(mix(vec3(0.),vec3(.18,.17,.14),uTheme)*a+film(g.x*.8+g.z*.6+.2)*caus,clamp(a+caus*.6,0.,1.));}}float k=exp(-max(glow,0.)*16.)*uGlow*.5;o+=(1.-o.a)*vec4(uEmit,max(uEmit.r,max(uEmit.g,uEmit.b)))*k;o.rgb=min(o.rgb,vec3(o.a));gl_FragColor=o;}`;

  let gl,prog,U={},ready=false,started=false,soft=false,canLive=false;
  let tier='',state='',raf=0,last=0,lastIn=-1e9,lastScroll=-1e9,visible=true,dirty=false;
  let W=0,H=0,band=BAND.matches,rect=null,heroH=1,bandEnd=1,rT=0;
  let A=0,B=0,m=0,tw=null,sweepT=-1,wob=0,energy=0,time=1.3,shown=-1;
  let dragYaw=0,dragV=0,drag=null,suppress=false,bandP=0,spin=0,tilt='';
  let qAdj=0,stepAdj=0,ema=0,slow=0,fast=0,rolling=false;
  try {[qAdj,stepAdj]=JSON.parse(sessionStorage.getItem('mp-glq'))||[0,0];} catch {/* optional */}
  const stats={tier:'',renderer:'',frames:0,lastFrameMs:0,backing:[0,0],qMove:0};

  const S=(k,c,x=0)=>({k,c,x,v:0,t:x});
  const yaw=S(120,22),pit=S(120,22),px=S(170,26),py=S(170,26);
  const rx=S(200,24),ry=S(200,24),rz=S(200,24,.4),ra=S(200,24);
  const kick=S(90,9.5),base=S(120,16,1),scr=S(140,24),th=S(110,21);
  const SPR=[yaw,pit,px,py,rx,ry,rz,ra,kick,base,scr,th];
  const moving=(s)=>Math.abs(s.x-s.t)>1e-3||Math.abs(s.v)>1e-3;
  const snap=(s)=>{s.x=s.t; s.v=0;};
  const bump=(a)=>{kick.v+=a*17;};
  const touch=()=>band||COARSE.matches;
  const qMove=()=>clamp((touch()?.66:.75)+qAdj,.5,.85);
  const light=()=>(root.dataset.theme==='light'?1:0);
  const selected=()=>Math.max(0,FORMS.indexOf(bench?.dataset.selection));
  const live=()=>tier==='live';
  const canRender=()=>live()&&started&&visible&&!doc.hidden;
  const setState=(s)=>{if (s!==state) hv.dataset.glassState=state=s;};
  const setTier=(t)=>{hv.dataset.glassTier=stats.tier=tier=t;};
  function setForm(id) {
    if (id===shown) return;
    shown=id; hv.dataset.glassForm=FORMS[id];
    caps.forEach((li)=>li.toggleAttribute('data-active',li.dataset.form===FORMS[id]));
  }
  function pose(id,hard) {[yaw.t,pit.t]=POSE[id]; if (hard) {snap(yaw); snap(pit);}}
  function show(id) {tw=null; A=B=id; m=0; pose(id,true); setForm(id);}

  // Band: scroll scrubs the forms; a full turn per morph keeps each hold face-on
  function applyBand() {
    const p=live()?bandP:0,w1=ss(.25,.42,p),w2=ss(.58,.75,p);
    spin=6.2832*(w1+w2);
    [A,B,m]=p<.25?[0,0,0]:p<.42?[0,1,w1]:p<.58?[1,1,0]:p<.75?[1,2,w2]:[2,2,0];
    const d=m<.5?A:B;
    setForm(d); pose(d);
  }

  function draw(fine) {
    if (!ready||!W||!H) return;
    const t0=now(),still=!live(),sw=still&&soft,tc=touch();
    const q=fine?(sw?.75:1):qMove(),dpr=Math.min(devicePixelRatio||1,tc?1.25:1.5);
    const f=Math.min(1,Math.sqrt(1.1e6/(W*H*(dpr*q)**2)))*dpr*q;
    const w=Math.max(1,Math.round(W*f)),h=Math.max(1,Math.round(H*f));
    if (cv.width!==w) cv.width=w;
    if (cv.height!==h) cv.height=h;
    gl.viewport(0,0,w,h);
    const T=clamp(th.x),[P,L]=PAL,sc=base.x*(1+kick.x)*(1-.1*scr.x);
    const Y=yaw.x+.45*px.x+dragYaw+.9*scr.x+(band?spin:0),X=pit.x+.3*py.x+.35*scr.x;
    const cy=Math.cos(Y),sy=Math.sin(Y),cp=Math.cos(X),sp=Math.sin(X);
    const R=[cy,sp*sy,-cp*sy,0,cp,sp,sy,-sp*cy,cp*cy];
    const o=(i)=>(R[i]*rx.x+R[i+3]*ry.x+R[i+6]*rz.x)/sc;
    const k=still||band?0:.5*ss(.06,.55,scr.x),mm=m<.5?Math.max(m,k):Math.min(m,1-k); // desk scroll melts the form
    const e=mm<.5?A:B,ek=mm>0?Math.abs(2*mm-1)**3:1;
    const u=(n,...v)=>gl['uniform'+v.length+'f'](U[n],...v),u3=(n,v)=>gl.uniform3fv(U[n],v);
    u('uRes',w,h); u('uOff',band?.08*W/H:0,band?0:.04); u('uFov',band?.652:.806);
    u('uTime',time); gl.uniformMatrix3fv(U.uRot,false,R);
    u('uScale',sc); u('uFormA',A); u('uFormB',B); u('uMorph',mm); u('uWob',wob);
    u('uReach',o(0),o(1),o(2),still||tc?0:clamp(ra.x));
    u('uTheme',T); u('uFilm',1.5*scr.x);
    u('uSteps',fine?(sw?72:96):clamp((tc?48:64)+stepAdj,40,64));
    u('uShadow',fine&&!soft&&(still||!tc)?1:0);
    u('uSweep',sweepT>=0?-1.4+3*clamp((now()-sweepT)/700):-9);
    u('uGlow',P.g+(L.g-P.g)*T); u3('uBg',mix(P.b,L.b,T));
    for (let i=0; i<4; i++) u3('uC'+i,mix(P.c[i],L.c[i],T));
    u3('uEmit',mix(P.e[e],L.e[e],T).map((v)=>v*ek));
    gl.drawArrays(gl.TRIANGLES,0,3);
    if (!still&&!band&&tiltEl) {
      const t=[(4*px.x).toFixed(2),(-3*py.x).toFixed(2)]+'';
      if (t!==tilt) {tilt=t; const [a,b]=t.split(','); tiltEl.style.setProperty('--tilt-x',a+'deg'); tiltEl.style.setProperty('--tilt-y',b+'deg');}
    }
    Object.assign(stats,{frames:stats.frames+1,lastFrameMs:now()-t0,backing:[w,h],qMove:qMove()});
  }
  function refresh() {
    if (ready) if (visible&&!doc.hidden) {draw(true); dirty=false;} else dirty=true;
  }

  function settle() {
    SPR.forEach(snap);
    if (tw) {A=B; m=0; tw=null;}
    sweepT=-1; wob=dragV=0;
    if (band) applyBand();
  }
  function halt() {if (raf) cancelAnimationFrame(raf); raf=0; rolling=false;}
  function wake(input=true) {
    if (input) lastIn=now();
    if (!raf&&canRender()) {last=now(); rolling=false; raf=requestAnimationFrame(frame);}
  }
  function step(dt,t) {
    for (const s of SPR) {s.v+=(-s.k*(s.x-s.t)-s.c*s.v)*dt; s.x+=s.v*dt;}
    if (tw) {
      const k=clamp(tw.u0+(t-tw.t0)/tw.dur);
      m=tw.intro?.5+.5*(1-(1-k)**3):k<.5?4*k**3:1-(2-2*k)**3/2;
      if (k>=1) {A=B; m=0; tw=null;}
    }
    if (sweepT>=0&&t-sweepT>=700) sweepT=-1;
    if (wob&&(wob*=Math.exp(-4*dt))<.02) wob=0;
    if (dragV&&!drag?.on) {dragYaw+=dragV*dt; dragV*=Math.exp(-4*dt); if (Math.abs(dragV)<1e-3) dragV=0;}
    energy*=Math.exp(-dt/.16);
    time+=dt*(.3+1.2*energy);
    if (band&&!tw) applyBand();
  }
  const busy=(t)=>tw||sweepT>=0||wob||dragV||drag?.on||SPR.some(moving)||(band&&t-lastScroll<150);
  function adapt(d) {
    ema=ema?ema*.9+d*.1:d;
    slow=ema>22?slow+1:0; fast=ema<12?fast+1:0;
    if (slow<30&&fast<90) return;
    if (!slow) qAdj+=qMove()<.85?.05:0; else if (qMove()>.5) qAdj-=.1; else stepAdj=Math.max(stepAdj-8,-24);
    slow=fast=0;
    try {sessionStorage.setItem('mp-glq',JSON.stringify([qAdj,stepAdj]));} catch {/* optional */}
  }
  function frame(t) {
    raf=0;
    if (!canRender()) return;
    const d=t-last;
    last=t;
    if (rolling) adapt(d);
    step(clamp(d/1000,0,1/30),now());
    if (busy(now())&&now()-lastIn<=900) {draw(false); rolling=true; setState('live'); raf=requestAnimationFrame(frame);}
    else {settle(); draw(true); rolling=false; setState('idle');} // refine, then zero rAF
  }

  // A -> drop -> B; a retarget mirrors through the drop
  function select(id) {
    if (band||id<0) return;
    if (!canRender()) {show(id); refresh(); return;}
    if (id===(tw?B:A)) return;
    let u0=0;
    if (tw) {if (m>=.5) {A=B; m=1-m;} u0=Math.cbrt(m/4);}
    B=id; tw={t0:now(),dur:700,u0};
    setForm(id); pose(id); bump(-.06); sweepT=now(); energy=cap(energy+1);
    wake();
  }

  const box=()=>(rect||=hv.getBoundingClientRect());
  const ui=(e)=>e.target.closest('a,button,.scene-dock');
  function hit(e) {
    const r=box(),x=e.clientX-r.left-r.width*(band?.58:.5),y=e.clientY-r.top-r.height*(band?.5:.46);
    return x*x+y*y<(r.height*(band?.378:.306))**2&&!ui(e);
  }
  function onMove(e) {
    if (e.pointerType==='touch'||band) return;
    hv.classList.toggle('is-over-object',hit(e));
    if (!live()||!started) return;
    const r=box(),x=e.clientX-r.left,y=e.clientY-r.top;
    if (drag) {
      if (!drag.on&&Math.abs(e.clientX-drag.x0)>6) {drag.on=true; try {hv.setPointerCapture(drag.id);} catch {/* ignore */}}
      if (drag.on) {
        const dx=e.clientX-drag.x,dts=Math.max(.008,(e.timeStamp-drag.ts)/1000);
        dragYaw+=dx*.008; dragV=clamp((dragV+dx*.008/dts)/2,-8,8);
        drag.x=e.clientX; drag.ts=e.timeStamp;
      }
    }
    px.t=clamp(x/r.width*2-1,-1,1); py.t=clamp(y/r.height*2-1,-1,1);
    // z = .4 plane; no droplet over the UI
    const wx=(x-r.width/2)/r.height*3.063,wy=((r.height/2-y)/r.height-.04)*3.063;
    const dist=Math.hypot(wx,wy),s=Math.min(dist,1.1)/Math.max(dist,1e-4);
    rx.t=wx*s; ry.t=wy*s; ra.t=ui(e)?0:ss(1.6,.95,dist);
    energy=cap(energy+.25);
    wake();
  }
  const onLeave=()=>{hv.classList.remove('is-over-object'); px.t=py.t=ra.t=0; if (live()) wake();};
  function onDown(e) {
    suppress=false;
    if (!e.button&&e.pointerType!=='touch'&&!band&&live()&&hit(e)) drag={id:e.pointerId,x0:e.clientX,x:e.clientX,ts:e.timeStamp};
  }
  function onUp(e) {
    if (drag?.on) {suppress=true; if (e.timeStamp-drag.ts>60) dragV=0; wake();}
    drag=null;
  }
  function onClick(e) {
    if (suppress) {suppress=false; return;}
    if (!hit(e)) return;
    if (live()&&started) {wob=1; bump(-.08); energy=cap(energy+1); wake();}
    if (!band) link?.click();
  }

  function measure() {
    rect=null;
    heroH=hero.offsetHeight||1;
    // The scrub ends at the sticky header
    const r=hv.getBoundingClientRect(),top=r.top+scrollY-(doc.querySelector('.site-header')?.offsetHeight||0);
    bandEnd=Math.max(1,top>80?top:r.bottom+scrollY);
  }
  function onScroll() {
    rect=null;
    if (!live()) return;
    if (band) {bandP=clamp(scrollY/bandEnd); lastScroll=now();} else scr.t=clamp(scrollY/heroH);
    energy=cap(energy+.2);
    wake();
  }
  function onTheme() {
    const t=light();
    if (t===th.t) return;
    th.t=t;
    // Theme circle or still: draw now for the new snapshot
    if (canRender()&&!root.classList.contains('theme-vt')) wake(); else {snap(th); refresh();}
  }
  function pickTier() {
    if (tier==='fallback') return;
    const t=canLive&&!RM.matches?'live':'still';
    if (t===tier) return;
    setTier(t);
    if (!started) return;
    halt(); ra.t=0; settle(); refresh();
    setState(live()?'idle':'still');
  }
  function fallback(msg) {
    if (msg) console.warn('HeroGL fallback:',msg);
    halt(); ready=started=false; setTier('fallback'); setState('fallback'); setForm(band?0:selected());
  }

  // Reveal after the first frame (software JIT ~750 ms)
  function afterGPU(cb) {
    const f=gl.fenceSync?.(gl.SYNC_GPU_COMMANDS_COMPLETE,0),t0=now();
    if (!f) return cb();
    gl.flush();
    const poll=()=>(gl.isContextLost()||gl.getSyncParameter(f,gl.SYNC_STATUS)===gl.SIGNALED||now()-t0>3000?cb():setTimeout(poll,16));
    setTimeout(poll,16);
  }
  function setup() {
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER,gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
    for (const n of new Set(FS.match(/\bu[A-Z]\w*/g))) U[n]=gl.getUniformLocation(prog,n);
    gl.uniform1f(U.uGradeT,.85);
    gl.uniform4f(U.uSleep,345,120,105,342.5); // 23:00, 8 h, 07:00, 22:50
    ready=true;
    if (!W) ({width:W,height:H}=stage.getBoundingClientRect());
    measure();
    th.x=th.t=light();
    if (live()) {bandP=clamp(scrollY/bandEnd); scr.x=scr.t=clamp(scrollY/heroH);}
    if (band) applyBand(); else show(selected());
    const intro=live()&&visible&&!doc.hidden&&!band;
    if (intro) {tw={t0:now(),dur:900,intro,u0:0}; m=.5; base.x=.6;}
    draw(!intro);
    afterGPU(()=>{
      if (!ready) return;
      started=true;
      if (tw?.intro) tw.t0=now();
      setState(live()?(intro?'live':'idle'):'still');
      if (intro) wake(); else refresh();
    });
  }
  function compile() {
    const t0=now(),ext=gl.getExtension('KHR_parallel_shader_compile');
    prog=gl.createProgram();
    const add=(type,src)=>{const s=gl.createShader(type); gl.shaderSource(s,src); gl.compileShader(s); gl.attachShader(prog,s); return s;};
    add(gl.VERTEX_SHADER,'attribute vec2 a;void main(){gl_Position=vec4(a,0.,1.);}');
    const fs=add(gl.FRAGMENT_SHADER,FS);
    gl.bindAttribLocation(prog,0,'a');
    gl.linkProgram(prog);
    const check=()=>{ // setTimeout, never rAF
      if (ext&&!gl.getProgramParameter(prog,ext.COMPLETION_STATUS_KHR)) return now()-t0>3000?fallback('Compile timeout'):void setTimeout(check,16);
      if (gl.getProgramParameter(prog,gl.LINK_STATUS)) setup(); else fallback(gl.getShaderInfoLog(fs)||gl.getProgramInfoLog(prog)||'Link failed');
    };
    check();
  }
  const idle=(fn,timeout)=>(window.requestIdleCallback?requestIdleCallback(fn,{timeout}):setTimeout(fn,60));
  function probe() {
    const opts={antialias:false,depth:false,powerPreference:'default'};
    try {gl=cv.getContext('webgl2',opts)||cv.getContext('webgl',opts);} catch {gl=null;}
    if (!gl) return fallback('No WebGL');
    const dbg=gl.getExtension('WEBGL_debug_renderer_info');
    stats.renderer=String(gl.getParameter(dbg?dbg.UNMASKED_RENDERER_WEBGL:gl.RENDERER)||'');
    soft=/SwiftShader|llvmpipe|softpipe|Software|Basic Render|Microsoft Basic/i.test(stats.renderer);
    canLive=flag==='force'||(flag!=='still'&&!soft&&!navigator.connection?.saveData&&(navigator.hardwareConcurrency||8)>2);
    pickTier();
    if (!live()&&soft&&doc.readyState!=='complete') addEventListener('load',()=>idle(compile,1200),{once:true});
    else setTimeout(()=>idle(compile,600),RM.matches?0:1200-now()); // after the load choreography: a cold first draw blocks
  }

  globalThis.HeroGL=Object.freeze({
    get state() {return state;},
    get tier() {return tier;},
    stats,
    render: ()=>{if (ready) {draw(true); dirty=false;}},
  });
  bench?.addEventListener('benchselect',(e)=>select(FORMS.indexOf(e.detail?.name)));
  if (flag==='off'||!cv.getContext||mq('(forced-colors: active)').matches) return fallback();
  setState('compiling');
  const on=(el,type,fn,o={passive:true})=>el.addEventListener(type,fn,o);
  on(cv,'webglcontextlost',(e)=>{e.preventDefault(); fallback();},false);
  on(cv,'webglcontextrestored',()=>{tier=''; pickTier(); setState('compiling'); compile();});
  const vis=()=>{
    if (!started) return;
    if (!visible||doc.hidden) {halt(); settle(); dirty=true; setState(live()?'idle':'still');} else if (live()) wake(); else if (dirty) refresh();
  };
  if (window.IntersectionObserver) new IntersectionObserver(([en])=>{visible=en.isIntersecting; vis();}).observe(hv);
  if (window.ResizeObserver) new ResizeObserver(([en])=>{
    const {width,height}=en.contentRect;
    if (width===W&&height===H) return;
    W=width; H=height;
    clearTimeout(rT); rT=setTimeout(()=>{measure(); refresh();},120);
  }).observe(stage);
  on(doc,'visibilitychange',vis);
  on(window,'pagehide',halt);
  on(window,'pageshow',(e)=>{if (e.persisted&&started) {measure(); refresh();}});
  on(window,'scroll',onScroll);
  on(window,'resize',()=>{rect=null;});
  on(window,'load',measure,{once:true});
  on(hv,'pointermove',onMove); on(hv,'pointerleave',onLeave); on(hv,'pointerdown',onDown);
  on(hv,'pointerup',onUp); on(hv,'pointercancel',onUp); on(hv,'click',onClick,false);
  on(doc,'pointerdown',(e)=>{ // anticipation
    if (live()&&e.target.closest?.('a[href*="sechserrechner"],a[href*="sleepcalculator"]')) {bump(-.05); wake();}
  },{capture:true,passive:true});
  on(doc,'themechange',onTheme);
  new MutationObserver(onTheme).observe(root,{attributes:true,attributeFilter:['data-theme']});
  RM.addEventListener?.('change',pickTier);
  BAND.addEventListener?.('change',()=>{
    band=BAND.matches; halt(); drag=null; px.t=py.t=ra.t=0; settle();
    if (!band) show(selected());
    tilt=''; measure(); refresh();
  });
  th.x=th.t=light();
  idle(probe,200);
})();
