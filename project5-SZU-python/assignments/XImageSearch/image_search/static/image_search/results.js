/* ==========================================================================
   Results page (Hardened)
   - Applies threshold styling/filtering
   - Polls /api/results/?hid=... until ready
   - Shows backend error explicitly
   - Supports add favorite + copy url
   ========================================================================== */
(function(){
  const grid = document.getElementById('results-grid');
  const statusEl = document.getElementById('status');

  const thrEl = document.getElementById('thr');
  const thrValEl = document.getElementById('thr-val');
  const bStrongEl = document.getElementById('b-strong');
  const bMediumEl = document.getElementById('b-medium');
  const onlyPassEl = document.getElementById('only-pass');
  const hidePoorEl = document.getElementById('hide-poor');
  const groupModeEl = document.getElementById('group-mode');
  const showStrongEl = document.getElementById('show-strong');
  const showMediumEl = document.getElementById('show-medium');
  const showWeakEl = document.getElementById('show-weak');
  const showPoorEl = document.getElementById('show-poor');
  const cntStrongEl = document.getElementById('cnt-strong');
  const cntMediumEl = document.getElementById('cnt-medium');
  const cntWeakEl = document.getElementById('cnt-weak');
  const cntPoorEl = document.getElementById('cnt-poor');
  const sortEl = document.getElementById('sort');

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function setStatus(text, type){
    if (!statusEl) return;
    statusEl.textContent = text;
    statusEl.style.color = type === 'bad' ? 'var(--bad)'
                     : type === 'warn' ? 'var(--warn)'
                     : '';
    statusEl.style.fontWeight = type ? '900' : '';
  }

  function num(x, d=0){
    const v = Number(x);
    return Number.isFinite(v) ? v : d;
  }

  function clamp01(x){
    return Math.max(0, Math.min(1, x));
  }

  function percentile(sortedAsc, p){
    if (!sortedAsc || !sortedAsc.length) return 0;
    const pp = Math.max(0, Math.min(1, p));
    const idx = (sortedAsc.length - 1) * pp;
    const lo = Math.floor(idx);
    const hi = Math.ceil(idx);
    if (lo === hi) return sortedAsc[lo];
    const w = idx - lo;
    return sortedAsc[lo] * (1 - w) + sortedAsc[hi] * w;
  }

  function computeBoundaries(scores, thr){
    const t = clamp01(thr);
    const pass = scores.filter(s => Number.isFinite(s) && s >= t).sort((a,b)=>a-b);

    // 如果有效数据太少，就使用保守的固定偏移边界（仍保证 >=thr）
    if (pass.length < 6){
      const m = clamp01(Math.max(t, t + 0.05));
      const s = clamp01(Math.max(m, t + 0.10));
      return {thr: t, medium: m, strong: s};
    }

    // 按“实际分布”划分：通过分位数确定中/强边界
    // - weak: [thr, medium)
    // - medium: [medium, strong)
    // - strong: [strong, +inf)
    const med = clamp01(Math.max(t, percentile(pass, 0.55)));
    const strong = clamp01(Math.max(med, percentile(pass, 0.85)));

    // 避免边界过近导致显示不稳定
    const mediumFinal = clamp01(Math.max(t, Math.min(med, strong - 0.01)));
    const strongFinal = clamp01(Math.max(mediumFinal + 0.01, strong));
    return {thr: t, medium: mediumFinal, strong: strongFinal};
  }

  function grade(score, b){
    if (!Number.isFinite(score)) return 'poor';
    if (score < b.thr) return 'poor';
    if (score >= b.strong) return 'strong';
    if (score >= b.medium) return 'medium';
    return 'weak';
  }

  function gradeText(g){
    if (g === 'strong') return '强';
    if (g === 'medium') return '中';
    if (g === 'weak') return '弱';
    return '差';
  }

  function updateCounts(counts){
    if (cntStrongEl) cntStrongEl.textContent = String(counts.strong || 0);
    if (cntMediumEl) cntMediumEl.textContent = String(counts.medium || 0);
    if (cntWeakEl) cntWeakEl.textContent = String(counts.weak || 0);
    if (cntPoorEl) cntPoorEl.textContent = String(counts.poor || 0);
  }

  function removeGroupHeaders(){
    if (!grid) return;
    Array.from(grid.querySelectorAll('.group-header')).forEach(el => el.remove());
  }

  function buildGroupHeader(title, count, boundaryText){
    const h = document.createElement('div');
    h.className = 'card pad group-header';
    h.style.gridColumn = '1 / -1';
    h.style.padding = '10px 12px';
    h.style.display = 'flex';
    h.style.alignItems = 'center';
    h.style.justifyContent = 'space-between';
    h.style.gap = '12px';
    h.innerHTML = `
      <div style="font-weight:950;">${title} <span class="pill" style="margin-left:10px;">${count}</span></div>
      <div class="footer" style="margin-top:0;">${boundaryText || ''}</div>
    `;
    return h;
  }

  function applyStyles(){
    if (!grid) return;

    const thr = num(thrEl?.value ?? 0.75, 0.75);
    if (thrValEl) thrValEl.textContent = thr.toFixed(2);

    const items = Array.from(grid.querySelectorAll('.item[data-score]'));
    const scores = items.map(it => num(it.getAttribute('data-score'), NaN)).filter(Number.isFinite);
    const b = computeBoundaries(scores, thr);

    if (bStrongEl) bStrongEl.textContent = b.strong.toFixed(2);
    if (bMediumEl) bMediumEl.textContent = b.medium.toFixed(2);

    const onlyPass = !!onlyPassEl?.checked;
    const hidePoor = !!hidePoorEl?.checked;

    const showStrong = showStrongEl ? !!showStrongEl.checked : true;
    const showMedium = showMediumEl ? !!showMediumEl.checked : true;
    const showWeak = showWeakEl ? !!showWeakEl.checked : true;
    const showPoor = showPoorEl ? !!showPoorEl.checked : true;

    const counts = {strong:0, medium:0, weak:0, poor:0};

    // 先打标签 + 计数（计数不受 UI 过滤影响）
    for (const it of items){
      const sc = num(it.getAttribute('data-score'), 0);
      const g = grade(sc, b);
      counts[g] += 1;
      it.dataset.grade = g;
    }
    updateCounts(counts);

    // 再做展示过滤
    for (const it of items){
      it.classList.remove('is-strong','is-medium','is-weak','is-poor');

      const sc = num(it.getAttribute('data-score'), 0);
      const pass = sc >= b.thr;
      const g = it.dataset.grade || grade(sc, b);
      it.classList.add(`is-${g}`);

      // 更新徽标文字
      const mText = it.querySelector('.m-text');
      if (mText) mText.textContent = gradeText(g);

      if (hidePoor && g === 'poor'){
        it.style.display = 'none';
        continue;
      }
      if (onlyPass && !pass){
        it.style.display = 'none';
        continue;
      }

      if (g === 'strong' && !showStrong){ it.style.display = 'none'; continue; }
      if (g === 'medium' && !showMedium){ it.style.display = 'none'; continue; }
      if (g === 'weak' && !showWeak){ it.style.display = 'none'; continue; }
      if (g === 'poor' && !showPoor){ it.style.display = 'none'; continue; }

      it.style.display = '';
    }

    // 分组显示：把可见项按等级重排，并插入分组头
    const groupMode = !!groupModeEl?.checked;
    if (groupMode){
      removeGroupHeaders();

      const mode = sortEl?.value || 'score_desc';
      const visibleItems = items.filter(it => it.style.display !== 'none');

      const by = {strong:[], medium:[], weak:[], poor:[]};
      for (const it of visibleItems){
        const g = it.dataset.grade || 'poor';
        if (!by[g]) by[g] = [];
        by[g].push(it);
      }

      const cmp = (a,b)=>{
        const sa = num(a.getAttribute('data-score'), 0);
        const sb = num(b.getAttribute('data-score'), 0);
        return mode === 'score_asc' ? (sa - sb) : (sb - sa);
      };
      (by.strong || []).sort(cmp);
      (by.medium || []).sort(cmp);
      (by.weak || []).sort(cmp);
      (by.poor || []).sort(cmp);

      const groups = [
        {k:'strong', title:'强匹配', boundary:`score ≥ ${b.strong.toFixed(2)}`},
        {k:'medium', title:'中匹配', boundary:`${b.medium.toFixed(2)} ≤ score < ${b.strong.toFixed(2)}`},
        {k:'weak', title:'弱匹配', boundary:`${b.thr.toFixed(2)} ≤ score < ${b.medium.toFixed(2)}`},
        {k:'poor', title:'差匹配', boundary:`score < ${b.thr.toFixed(2)}`},
      ];

      for (const g of groups){
        const arr = by[g.k] || [];
        if (!arr.length) continue;
        grid.appendChild(buildGroupHeader(g.title, arr.length, g.boundary));
        for (const it of arr) grid.appendChild(it);
      }
    }else{
      // 非分组：确保没有残留头
      removeGroupHeaders();
    }
  }

  function sortItems(){
    if (!grid) return;
    if (groupModeEl?.checked) return; // 分组模式下由 applyStyles 统一排序/重排
    const mode = sortEl?.value || 'score_desc';
    const items = Array.from(grid.querySelectorAll('.item[data-score]'));

    items.sort((a,b)=>{
      const sa = num(a.getAttribute('data-score'), 0);
      const sb = num(b.getAttribute('data-score'), 0);
      return mode === 'score_asc' ? (sa - sb) : (sb - sa);
    });

    for (const it of items) grid.appendChild(it);
  }

  function bindControls(){
    thrEl?.addEventListener('input', ()=>{ sortItems(); applyStyles(); });
    onlyPassEl?.addEventListener('change', ()=> applyStyles());
    hidePoorEl?.addEventListener('change', ()=> applyStyles());
    groupModeEl?.addEventListener('change', ()=> applyStyles());
    showStrongEl?.addEventListener('change', ()=> applyStyles());
    showMediumEl?.addEventListener('change', ()=> applyStyles());
    showWeakEl?.addEventListener('change', ()=> applyStyles());
    showPoorEl?.addEventListener('change', ()=> applyStyles());
    sortEl?.addEventListener('change', ()=>{ sortItems(); applyStyles(); });
  }

  async function copyText(text){
    try{
      await navigator.clipboard.writeText(text);
      UI?.toast({title:"已复制", message:"链接已复制到剪贴板", type:"good"});
    }catch{
      UI?.toast({title:"复制失败", message:"浏览器权限不足", type:"warn"});
    }
  }

  async function addFavorite(url, score){
    const tags = (prompt('请输入收藏标签（必填，可用逗号分隔多个）') || '').trim();
    if (!tags){
      UI?.toast({title:"未收藏", message:"标签为必填项", type:"warn", timeout:2200});
      return;
    }

    const fd = new FormData();
    fd.append('url', url);
    fd.append('score', String(score ?? 0));
    fd.append('tags', tags);

    const csrftoken = getCookie('csrftoken');
    const resp = await fetch('/api/favorite/add/', {
      method: 'POST',
      body: fd,
      headers: csrftoken ? {'X-CSRFToken': csrftoken} : {},
    });

    if (resp.ok){
      UI?.toast({title:"已收藏", message:"已加入收藏夹", type:"good"});
    }else{
      UI?.toast({title:"收藏失败", message:`HTTP ${resp.status}`, type:"bad"});
    }
  }

  function bindItemActions(){
    if (!grid) return;

    grid.addEventListener('click', async (e)=>{
      const btn = e.target;
      if (!(btn instanceof HTMLElement)) return;

      const item = btn.closest('.item');
      if (!item) return;

      const url = item.getAttribute('data-url') || item.querySelector('img.thumb')?.getAttribute('src') || '';
      const score = num(item.getAttribute('data-score'), 0);

      if (btn.classList.contains('copy-url')){
        await copyText(url);
      }

      if (btn.classList.contains('fav-add')){
        await addFavorite(url, score);
      }
    });
  }

  function renderResults(results){
    if (!grid) return;
    // 清空“暂无结果”占位卡（非 .item）
    Array.from(grid.children).forEach(ch=>{
      if (!ch.classList.contains('item')) ch.remove();
    });

    for (const r of results){
      const url = r.url;
      const score = num(r.score, 0);

      const div = document.createElement('div');
      div.className = 'item';
      div.setAttribute('data-url', url);
      div.setAttribute('data-score', String(score));

      div.innerHTML = `
        <div class="match"><i></i><span class="m-text">Match</span></div>
        <img class="thumb" src="${url}" alt="result">
        <div class="meta">
          <div class="url"></div>
          <div class="score">${score.toFixed(3)}</div>
        </div>
        <div style="padding: 0 10px 12px; display:flex; gap:10px; align-items:center;">
          <button class="button secondary fav-add" type="button">收藏</button>
          <button class="button ghost copy-url" type="button">复制链接</button>
        </div>
      `;
      div.querySelector('.url').textContent = url;

      grid.appendChild(div);
    }

    UI?.bindImageGridViewer(document);
    sortItems();
    applyStyles();
  }

  async function pollIfNeeded(){
    if (!grid) return;
    const hid = grid.getAttribute('data-hid') || new URLSearchParams(location.search).get('hid');
    if (!hid) return;

    const hasAnyItem = grid.querySelector('.item[data-score]');
    // 如果已经有结果就不轮询
    if (hasAnyItem) return;

    let tries = 0;
    // 更快首屏：前几秒更密集轮询，随后退避，整体上限仍约 2 分钟
    const maxTries = 260;

    function nextDelayMs(t){
      // 0~2s：200ms，2~10s：400ms，之后：750ms
      if (t <= 10) return 200;
      if (t <= 40) return 400;
      return 750;
    }

    async function tick(){
      tries += 1;
      try{
        const resp = await fetch(`/api/results/?hid=${encodeURIComponent(hid)}`, {
          headers: {'Accept': 'application/json'}
        });
        const j = await resp.json();

        if (!j.ok){
          setStatus(`请求失败：${j.error || 'unknown'}`, 'bad');
          return;
        }

        if (j.error){
          setStatus(`后端异常：${j.error}`, 'bad');
          UI?.toast({title:"检索失败", message:j.error, type:"bad", timeout:8000});
          return;
        }

        if (j.pending){
          setStatus('后端检索中...（自动刷新）');
          if (tries < maxTries) return setTimeout(tick, nextDelayMs(tries));
          setStatus('等待超时：请刷新页面或检查后端配置/日志', 'warn');
          return;
        }

        // done
        if (Array.isArray(j.results) && j.results.length){
          setStatus(`已加载 ${j.results.length} 条结果`);
          renderResults(j.results);
        }else{
          setStatus('检索完成，但没有结果（可能 gallery 未加载或被过滤）', 'warn');
        }
      }catch(e){
        setStatus(`轮询异常：${String(e)}`, 'warn');
        if (tries < maxTries) setTimeout(tick, 1200);
      }
    }

    setStatus('正在等待后端返回结果...');
    tick();
  }

  bindControls();
  bindItemActions();

  sortItems();
  applyStyles();
  pollIfNeeded();
})();
