/* ==========================================================================
   Home page: drag&drop / paste upload + progress (Hardened)
   - Always asks backend for JSON (so we can reliably get redirect + error)
   - Uses XHR upload progress; does NOT rely on xhr.responseURL heuristics
   ========================================================================== */
(function(){
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('file-input');
  const chooseBtn = document.getElementById('choose-btn');
  const submitBtn = document.getElementById('submit-btn');
  const fileName = document.getElementById('file-name');
  const form = document.getElementById('search-form');
  const progressWrap = document.getElementById('upload-progress');
  const progressBar = document.getElementById('upload-bar');
  const infoWrap = document.getElementById('upload-info');
  const pctEl = document.getElementById('upload-pct');
  const spinner = document.getElementById('upload-spinner');

  function getCookie(name){
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  function setFile(f){
    if (!fileInput) return;
    const dt = new DataTransfer();
    dt.items.add(f);
    fileInput.files = dt.files;
    fileName.textContent = f ? `已选择：${f.name}（${Math.round(f.size/1024)}KB）` : '';
  }

  function onFiles(files){
    const f = files && files[0];
    if (!f) return;
    if (!/^image\//.test(f.type)){
      window.UI?.toast({title:"格式不支持", message:"请上传图片文件", type:"warn"});
      return;
    }
    setFile(f);
    window.UI?.toast({title:"已就绪", message:"点击「开始搜索」即可", type:"good", timeout:2000});
  }

  function bindDnD(){
    if (!dropzone) return;
    ['dragenter','dragover'].forEach(ev=>{
      dropzone.addEventListener(ev, (e)=>{
        e.preventDefault(); e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });
    ['dragleave','drop'].forEach(ev=>{
      dropzone.addEventListener(ev, (e)=>{
        e.preventDefault(); e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });
    dropzone.addEventListener('drop', (e)=>{
      const files = e.dataTransfer?.files;
      if (files && files.length) onFiles(files);
    });

    // Clicking inside dropzone should NOT always open file dialog.
    // Otherwise clicking "选择文件" / "开始搜索" will also bubble here and re-open the dialog,
    // preventing a normal submit and causing repeated popups.
    dropzone.addEventListener('click', (e)=>{
      const target = e.target;
      if (!(target instanceof Element)) {
        fileInput?.click();
        return;
      }

      // If user clicked an interactive element inside, do nothing.
      if (target.closest('button, a, input, select, textarea, label')) return;

      fileInput?.click();
    });
  }

  function bindPaste(){
    document.addEventListener('paste', (e)=>{
      const items = e.clipboardData?.items || [];
      for (const it of items){
        if (it.type && it.type.startsWith('image/')){
          const file = it.getAsFile();
          if (file){ onFiles([file]); return; }
        }
      }
    });
  }

  function setProgress(p){
    if (!progressWrap || !progressBar || !pctEl || !infoWrap) return;
    progressWrap.style.display = 'block';
    infoWrap.style.display = 'flex';
    progressBar.style.width = `${p}%`;
    pctEl.textContent = `${p}%`;
    if (spinner) spinner.style.display = p >= 100 ? 'none' : 'inline-block';
  }

  function xhrSubmit(){
    if (!form) return false;
    const hasFile = fileInput && fileInput.files && fileInput.files.length;
    if (!hasFile){
      window.UI?.toast({title:"还没选图", message:"请先拖拽/选择/粘贴图片", type:"warn"});
      return true;
    }

    try{
      const xhr = new XMLHttpRequest();
      xhr.open(form.method || 'POST', form.action || window.location.href);

      // 强制后端走 JSON 分支（我们就能拿到 redirect / error）
      xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
      xhr.setRequestHeader('Accept', 'application/json');

      xhr.upload.onprogress = (e)=>{
        if (!e.lengthComputable) return;
        const pct = Math.max(1, Math.min(99, Math.round((e.loaded / e.total) * 100)));
        setProgress(pct);
      };

      xhr.onload = ()=>{
        setProgress(100);
        submitBtn && (submitBtn.disabled = false);

        let data = null;
        try{ data = JSON.parse(xhr.responseText); }catch{}

        if (!data || data.ok !== true){
          const msg = data?.error || `请求失败（HTTP ${xhr.status}）`;
          window.UI?.toast({title:"上传失败", message: msg, type:"bad", timeout:5200});
          return;
        }

        // 后端返回 redirect
        const url = data.redirect || `/results/?hid=${encodeURIComponent(data.hid || '')}`;
        window.location.href = url;
      };

      xhr.onerror = ()=>{
        submitBtn && (submitBtn.disabled = false);
        window.UI?.toast({title:"上传失败", message:"网络异常或服务不可用", type:"bad"});
      };

      const fd = new FormData(form);
      // 某些情况下 Django CSRF 校验依赖 cookie/header：这里补一份 header 更稳
      const csrftoken = getCookie('csrftoken');
      if (csrftoken) xhr.setRequestHeader('X-CSRFToken', csrftoken);

      setProgress(1);
      submitBtn && (submitBtn.disabled = true);
      xhr.send(fd);
      return true;
    }catch{
      return false;
    }
  }

  function bindForm(){
    if (!form) return;
    form.addEventListener('submit', (e)=>{
      const prevented = xhrSubmit();
      if (prevented){
        e.preventDefault();
        e.stopPropagation();
      }
    });
  }

  chooseBtn?.addEventListener('click', (e)=>{ e.stopPropagation(); fileInput?.click(); });
  submitBtn?.addEventListener('click', (e)=>{ e.stopPropagation(); });
  fileInput?.addEventListener('change', ()=> onFiles(fileInput.files));

  bindDnD();
  bindPaste();
  bindForm();

  document.addEventListener('keydown', (e)=>{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'o'){
      e.preventDefault();
      fileInput?.click();
    }
  });
})();
