/* ==========================================================================
   UI Utils v3
   - toast / modal viewer
   - spotlight cursor effect
   - tilt hover
   - ripple buttons
   - entrance animation
   - NEW: Sakura falling canvas (interactive wind + toggle)
   ========================================================================== */
(function(){
  const UI = {};
  function qs(sel, root=document){ return root.querySelector(sel); }
  function qsa(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }

  UI.getCookie = function(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  };

  // ---- Toasts ----
  let toastRoot = null;
  function ensureToastRoot(){
    if (toastRoot) return toastRoot;
    toastRoot = document.createElement('div');
    toastRoot.className = 'toasts';
    document.body.appendChild(toastRoot);
    return toastRoot;
  }
  UI.toast = function({title="提示", message="", type="info", timeout=3200} = {}){
    const root = ensureToastRoot();
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.innerHTML = `
      <div class="t-dot"></div>
      <div style="min-width:0">
        <div class="t-title">${escapeHtml(title)}</div>
        <div class="t-msg">${escapeHtml(message)}</div>
      </div>
      <div class="t-actions">
        <button class="button ghost" type="button" aria-label="关闭">✕</button>
      </div>
    `;
    qs('button', el).addEventListener('click', ()=> el.remove());
    root.appendChild(el);
    if (timeout > 0) setTimeout(()=> el.remove(), timeout);
  };

  // ---- Modal viewer ----
  let modalEl = null;
  function ensureModal(){
    if (modalEl) return modalEl;
    modalEl = document.createElement('div');
    modalEl.className = 'modal';
    modalEl.innerHTML = `
      <div class="modal-card" role="dialog" aria-modal="true" aria-label="图片预览">
        <div class="modal-media">
          <img id="modal-img" alt="preview"/>
        </div>
        <div class="modal-side">
          <div style="display:flex; gap:10px; align-items:flex-start;">
            <div style="min-width:0;">
              <div class="modal-title">图片详情</div>
              <div class="subtitle">点击空白处或按 ESC 关闭</div>
            </div>
            <button class="button ghost iconbtn" type="button" id="modal-close" aria-label="关闭">✕</button>
          </div>

          <div class="modal-actions">
            <a class="button primary" id="modal-open" target="_blank" rel="noreferrer">打开原图</a>
            <button class="button" type="button" id="modal-copy">复制链接</button>
            <a class="button secondary" id="modal-download" download>下载</a>
          </div>

          <div class="modal-meta">
            <div class="row">
              <div class="label">URL</div>
              <div class="value" id="modal-url">-</div>
            </div>
            <div class="row">
              <div class="label">匹配度</div>
              <div class="value" id="modal-score">-</div>
            </div>
            <div class="row">
              <div class="label">标签</div>
              <div class="value" id="modal-tags">-</div>
            </div>
          </div>

          <hr class="sep"/>
          <div class="footer">快捷键：<span class="kbd">Esc</span> 关闭 · <span class="kbd">C</span> 复制链接</div>
        </div>
      </div>
    `;
    document.body.appendChild(modalEl);

    modalEl.addEventListener('click', (e)=>{ if (e.target === modalEl) UI.modalClose(); });
    qs('#modal-close', modalEl).addEventListener('click', UI.modalClose);

    document.addEventListener('keydown', (e)=>{
      if (!modalEl.classList.contains('open')) return;
      if (e.key === 'Escape') UI.modalClose();
      if (e.key.toLowerCase() === 'c') qs('#modal-copy', modalEl)?.click();
    });

    qs('#modal-copy', modalEl).addEventListener('click', async ()=>{
      const url = qs('#modal-open', modalEl)?.getAttribute('href') || '';
      if (!url) return;
      try{
        await navigator.clipboard.writeText(url);
        UI.toast({title:"已复制", message:"图片链接已复制到剪贴板", type:"good"});
      }catch{
        UI.toast({title:"复制失败", message:"浏览器不支持或权限不足", type:"warn"});
      }
    });

    return modalEl;
  }

  UI.modalOpen = function({url="", score="", tags=""} = {}){
    const m = ensureModal();
    qs('#modal-img', m).src = url;
    qs('#modal-open', m).href = url;
    qs('#modal-download', m).href = url;
    qs('#modal-url', m).textContent = url || '-';
    qs('#modal-score', m).textContent = (score !== undefined && score !== null && score !== "") ? String(score) : '-';
    qs('#modal-tags', m).textContent = tags || '-';
    m.classList.add('open');
    setTimeout(()=> qs('#modal-close', m).focus(), 50);
  };

  UI.modalClose = function(){
    if (!modalEl) return;
    modalEl.classList.remove('open');
  };

  UI.bindImageGridViewer = function(root=document){
    const items = qsa('.item', root);
    items.forEach((it)=>{
      const img = qs('img', it);
      if (!img) return;
      if (it.dataset.viewerBound) return;
      it.dataset.viewerBound = '1';

      it.addEventListener('click', (e)=>{
        const t = e.target;
        if (t && (t.tagName === 'BUTTON' || t.tagName === 'A' || t.tagName === 'INPUT' || t.closest('button,a,input'))) return;
        const url = it.getAttribute('data-url') || img.getAttribute('src') || '';
        const score = it.getAttribute('data-score') || qs('.score', it)?.textContent || '';
        const tags = it.getAttribute('data-tags') || qs('.url', it)?.textContent || '';
        if (url) UI.modalOpen({url, score, tags});
      });
    });
  };

  // ---- Theme ----
  UI.initTheme = function(){
    const saved = localStorage.getItem('theme');
    const theme = saved || (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    document.body.setAttribute('data-theme', theme);
  };
  UI.toggleTheme = function(){
    const cur = document.body.getAttribute('data-theme') || 'light';
    const next = cur === 'light' ? 'dark' : 'light';
    document.body.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
  };

  // ---- Fancy: Spotlight ----
  UI.initSpotlight = function(){
    if (prefersReduced()) return;
    if (document.querySelector('.spotlight')) return;
    const el = document.createElement('div');
    el.className = 'spotlight';
    document.body.appendChild(el);
    window.addEventListener('pointermove', (e)=>{
      const x = (e.clientX / window.innerWidth) * 100;
      const y = (e.clientY / window.innerHeight) * 100;
      el.style.setProperty('--x', x + '%');
      el.style.setProperty('--y', y + '%');
    }, {passive:true});
  };

  // ---- Fancy: Tilt hover ----
  UI.bindTilt = function(selector='.item, .card'){
    if (prefersReduced()) return;
    qsa(selector).forEach((el)=>{
      if (el.dataset.tiltBound) return;
      el.dataset.tiltBound = '1';
      el.addEventListener('mousemove', (e)=>{
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        const rx = (py - 0.5) * -6;
        const ry = (px - 0.5) * 8;
        el.style.transform = `translateY(-2px) rotateX(${rx}deg) rotateY(${ry}deg)`;
      });
      el.addEventListener('mouseleave', ()=>{ el.style.transform = ''; });
    });
  };

  // ---- Fancy: Ripple buttons ----
  UI.bindRipple = function(){
    document.addEventListener('click', (e)=>{
      const btn = e.target.closest?.('.button');
      if (!btn) return;
      const r = btn.getBoundingClientRect();
      const s = document.createElement('span');
      s.className = 'ripple';
      s.style.left = (e.clientX - r.left) + 'px';
      s.style.top = (e.clientY - r.top) + 'px';
      btn.appendChild(s);
      setTimeout(()=> s.remove(), 560);
    }, true);
  };

  // ---- Entrance animation ----
  UI.bindEntrance = function(){
    const els = qsa('[data-animate]');
    if (!els.length) return;
    const io = new IntersectionObserver((entries)=>{
      entries.forEach(ent=>{
        if (ent.isIntersecting){
          ent.target.classList.add('in');
          io.unobserve(ent.target);
        }
      });
    }, {threshold: 0.12});
    els.forEach(el=> io.observe(el));
  };

  // ======================================================================
  // NEW: Sakura Engine
  // ======================================================================
  const Sakura = {
    enabled: true,
    running: false,
    canvas: null,
    ctx: null,
    petals: [],
    dpr: 1,
    w: 0,
    h: 0,
    raf: 0,
    cfg: {
      density: 42,     // base count
      minSize: 6,
      maxSize: 14,
      fallSpeed: [0.55, 1.35],
      drift: [0.25, 1.2],
      rotSpeed: [0.006, 0.022],
      sway: [0.8, 2.4],      // wobble amplitude
      alpha: [0.35, 0.85],
      spawnPadding: 40
    },
    wind: {
      x: 0,      // current wind
      tx: 0,     // target wind (mouse driven)
      vx: 0,
      lastX: null,
      lastT: 0
    }
  };

  function prefersReduced(){
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function clamp(n, a, b){ return Math.max(a, Math.min(b, n)); }
  function rand(a, b){ return a + Math.random() * (b - a); }
  function pick(arr){ return arr[Math.floor(Math.random()*arr.length)]; }

  function setCanvasSize(){
    const c = Sakura.canvas;
    if (!c) return;
    Sakura.dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    Sakura.w = Math.floor(window.innerWidth);
    Sakura.h = Math.floor(window.innerHeight);
    c.width = Math.floor(Sakura.w * Sakura.dpr);
    c.height = Math.floor(Sakura.h * Sakura.dpr);
    c.style.width = Sakura.w + 'px';
    c.style.height = Sakura.h + 'px';
    Sakura.ctx.setTransform(Sakura.dpr, 0, 0, Sakura.dpr, 0, 0);
  }

  function petalFactory(spawnTop=true){
    const pad = Sakura.cfg.spawnPadding;
    const x = rand(-pad, Sakura.w + pad);
    const y = spawnTop ? rand(-Sakura.h * 0.2 - pad, -pad) : rand(-pad, Sakura.h + pad);
    const size = rand(Sakura.cfg.minSize, Sakura.cfg.maxSize);
    const speed = rand(Sakura.cfg.fallSpeed[0], Sakura.cfg.fallSpeed[1]);
    const drift = rand(Sakura.cfg.drift[0], Sakura.cfg.drift[1]) * (Math.random() < 0.5 ? -1 : 1);
    const rot = rand(0, Math.PI * 2);
    const rotSpeed = rand(Sakura.cfg.rotSpeed[0], Sakura.cfg.rotSpeed[1]) * (Math.random() < 0.5 ? -1 : 1);
    const sway = rand(Sakura.cfg.sway[0], Sakura.cfg.sway[1]);
    const alpha = rand(Sakura.cfg.alpha[0], Sakura.cfg.alpha[1]);

    // color palette (slightly different petals)
    const palette = [
      {a:'#ffd7e6', b:'#ff9fc2', hi:'rgba(255,255,255,.55)'},
      {a:'#ffe0ef', b:'#ffb5d3', hi:'rgba(255,255,255,.50)'},
      {a:'#ffdbe9', b:'#ffa6ca', hi:'rgba(255,255,255,.52)'}
    ];
    const col = pick(palette);

    return {
      x, y, size,
      vy: speed,
      vx: drift,
      rot, rotSpeed,
      sway, swayT: rand(0, Math.PI*2),
      alpha,
      col
    };
  }

  function drawPetal(p){
    const ctx = Sakura.ctx;
    const s = p.size;
    ctx.save();
    ctx.globalAlpha = p.alpha;

    ctx.translate(p.x, p.y);
    ctx.rotate(p.rot);

    // petal shape via ellipse + notch (simple but nice)
    const grd = ctx.createRadialGradient(-s*0.2, -s*0.2, 1, 0, 0, s*1.4);
    grd.addColorStop(0, p.col.a);
    grd.addColorStop(1, p.col.b);

    ctx.fillStyle = grd;
    ctx.beginPath();
    // ellipse-ish
    ctx.ellipse(0, 0, s*0.78, s*1.05, Math.PI/8, 0, Math.PI*2);
    ctx.fill();

    // small notch to look like sakura petal
    ctx.globalAlpha = p.alpha * 0.85;
    ctx.fillStyle = 'rgba(255, 140, 190, .22)';
    ctx.beginPath();
    ctx.moveTo(0, s*0.22);
    ctx.quadraticCurveTo(-s*0.16, s*0.55, 0, s*0.72);
    ctx.quadraticCurveTo(s*0.16, s*0.55, 0, s*0.22);
    ctx.fill();

    // highlight
    ctx.globalAlpha = p.alpha * 0.65;
    ctx.fillStyle = p.col.hi;
    ctx.beginPath();
    ctx.ellipse(-s*0.16, -s*0.18, s*0.18, s*0.35, -Math.PI/8, 0, Math.PI*2);
    ctx.fill();

    ctx.restore();
  }

  function step(){
    const ctx = Sakura.ctx;
    if (!ctx) return;
    ctx.clearRect(0, 0, Sakura.w, Sakura.h);

    // smooth wind towards target wind
    Sakura.wind.x += (Sakura.wind.tx - Sakura.wind.x) * 0.06;

    for (let i=0;i<Sakura.petals.length;i++){
      const p = Sakura.petals[i];
      p.swayT += 0.03;

      const wind = Sakura.wind.x;
      const swayX = Math.sin(p.swayT) * p.sway;
      p.x += p.vx + wind + swayX*0.12;
      p.y += p.vy;

      p.rot += p.rotSpeed;

      // wrap / respawn
      if (p.y > Sakura.h + 60 || p.x < -80 || p.x > Sakura.w + 80){
        Sakura.petals[i] = petalFactory(true);
        Sakura.petals[i].x = clamp(Sakura.petals[i].x, -40, Sakura.w+40);
      }

      drawPetal(p);
    }

    Sakura.raf = requestAnimationFrame(step);
  }

  function computeCount(){
    // density scaled by screen area (capped)
    const base = Sakura.cfg.density;
    const area = (window.innerWidth * window.innerHeight) / (1280*720);
    const n = Math.round(base * clamp(area, 0.75, 1.65));
    return clamp(n, 18, 90);
  }

  function attachWind(){
    // wind based on pointer velocity
    Sakura.wind.lastX = null;
    Sakura.wind.lastT = 0;

    window.addEventListener('pointermove', (e)=>{
      if (!Sakura.running) return;
      const now = performance.now();
      if (Sakura.wind.lastX == null){
        Sakura.wind.lastX = e.clientX;
        Sakura.wind.lastT = now;
        return;
      }
      const dx = e.clientX - Sakura.wind.lastX;
      const dt = Math.max(16, now - Sakura.wind.lastT);

      Sakura.wind.lastX = e.clientX;
      Sakura.wind.lastT = now;

      // target wind in px per frame-ish (clamped)
      const v = dx / dt; // px/ms
      Sakura.wind.tx = clamp(v * 18, -1.9, 1.9);
    }, {passive:true});

    // slowly calm down wind when idle
    window.addEventListener('pointerleave', ()=>{
      Sakura.wind.tx = 0;
    });
  }

  function startSakura(){
    if (Sakura.running) return;
    if (!Sakura.enabled) return;
    if (prefersReduced()) return;

    if (!Sakura.canvas || !Sakura.ctx) return;
    setCanvasSize();

    const count = computeCount();
    Sakura.petals = Array.from({length: count}, ()=> petalFactory(true));
    Sakura.running = true;

    // run loop
    cancelAnimationFrame(Sakura.raf);
    Sakura.raf = requestAnimationFrame(step);
  }

  function stopSakura(){
    Sakura.running = false;
    cancelAnimationFrame(Sakura.raf);
    if (Sakura.ctx) Sakura.ctx.clearRect(0,0,Sakura.w,Sakura.h);
  }

  UI.initSakura = function({canvasId='sakura-canvas'} = {}){
    const saved = localStorage.getItem('sakura');
    Sakura.enabled = saved == null ? true : (saved === 'on');

    Sakura.canvas = document.getElementById(canvasId);
    if (!Sakura.canvas) return;
    Sakura.ctx = Sakura.canvas.getContext('2d');

    // hide canvas if disabled
    Sakura.canvas.style.display = Sakura.enabled ? 'block' : 'none';

    // responsive
    window.addEventListener('resize', ()=>{
      if (!Sakura.canvas) return;
      setCanvasSize();
      if (Sakura.running){
        // rebuild petals to fit new size
        const count = computeCount();
        Sakura.petals = Array.from({length: count}, ()=> petalFactory(true));
      }
    }, {passive:true});

    attachWind();

    if (Sakura.enabled && !prefersReduced()){
      startSakura();
      UI.toast({title:"樱花特效", message:"已开启（鼠标移动有风）", type:"info", timeout:1800});
    }
  };

  UI.toggleSakura = function(){
    Sakura.enabled = !Sakura.enabled;
    localStorage.setItem('sakura', Sakura.enabled ? 'on' : 'off');

    if (Sakura.canvas){
      Sakura.canvas.style.display = Sakura.enabled ? 'block' : 'none';
    }
    if (Sakura.enabled){
      startSakura();
      UI.toast({title:"樱花已开启", message:"🌸 鼠标移动可吹动花瓣", type:"good", timeout:2000});
    }else{
      stopSakura();
      UI.toast({title:"樱花已关闭", message:"已关闭特效（性能更优）", type:"warn", timeout:2000});
    }
  };

  // ---- helpers ----
  function prefersReduced(){
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  function escapeHtml(str){
    return String(str)
      .replaceAll('&','&amp;')
      .replaceAll('<','&lt;')
      .replaceAll('>','&gt;')
      .replaceAll('"','&quot;')
      .replaceAll("'","&#39;");
  }

  window.UI = UI;
})();
