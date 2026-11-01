/* Trusted same-site chart documents retain their own interactive controls. */
(() => {
  'use strict';
  const chinese = /^zh(?:-|$)/i.test(document.documentElement.lang);
  const words = chinese ? {
    expand: '展開圖表', close: '關閉',
    loading: '正在載入圖表文件…', failed: '無法載入圖表文件。請重試，或開啟原始圖表查看。',
    retry: '重試', source: '開啟原始圖表', unavailable: '這個瀏覽器無法開啟浮動檢視，請使用原始圖表連結。'
  } : {
    expand: 'Expand chart', close: 'Close',
    loading: 'Loading chart document…', failed: 'Could not load the chart document. Retry or open the source chart.',
    retry: 'Retry', source: 'Open source chart', unavailable: 'This browser cannot open a floating viewer. Use the source chart link.'
  };
  let dialog, title, stage, status, source, closeControl, current;

  function button(text, action, className) {
    const control = document.createElement('button');
    control.type = 'button'; control.textContent = text;
    if (className) control.className = className;
    control.addEventListener('click', action);
    return control;
  }
  function statusRegion() {
    const region = document.createElement('p');
    region.className = 'askr-chart-status';
    region.setAttribute('role', 'status');
    region.hidden = true;
    return region;
  }
  function showStatus(region, message, retry) {
    region.replaceChildren(document.createTextNode(message));
    if (retry) region.append(button(words.retry, retry));
    region.hidden = false;
  }
  function escapeViewer(event) {
    event.preventDefault();
    closeViewer();
  }
  function watchFrame(frame, region, url, retry, alive) {
    let disposed = false, verified = null, documentLoaded = false, hookedDocument;
    const abort = new AbortController();
    function active() { return !disposed && frame.isConnected && (!alive || alive()); }
    function frameEscape(event) {
      if (event.key === 'Escape' && current && current.frame === frame) escapeViewer(event);
    }
    function loaded() {
      if (!active()) return;
      documentLoaded = true;
      if (verified !== true) return;
      // A blocked or cross-origin frame is not a usable same-site chart.
      let chartDocument;
      try { chartDocument = frame.contentDocument; } catch (_) { failed(); return; }
      if (!chartDocument) { failed(); return; }
      frame.hidden = false;
      region.hidden = true;
      // Same-origin only: Escape inside the document returns to the outer shell.
      if (hookedDocument !== chartDocument) {
        hookedDocument = chartDocument;
        hookedDocument.addEventListener('keydown', frameEscape);
      }
    }
    function failed() {
      if (!active()) return;
      verified = false; frame.hidden = true;
      showStatus(region, words.failed, retry);
    }
    frame.addEventListener('load', loaded);
    frame.addEventListener('error', failed);
    showStatus(region, words.loading);
    // An iframe can fire load for a 404. Check the static document's HTTP status.
    fetch(url, {credentials: 'same-origin', signal: abort.signal}).then(response => {
      if (!active()) return;
      if (!response.ok || new URL(response.url).origin !== location.origin) { failed(); return; }
      verified = true;
      if (documentLoaded || (frame.contentDocument && frame.contentDocument.readyState === 'complete' && frame.contentWindow.location.href !== 'about:blank')) loaded();
    }).catch(error => { if (error.name !== 'AbortError') failed(); });
    return () => {
      disposed = true; abort.abort();
      frame.removeEventListener('load', loaded);
      frame.removeEventListener('error', failed);
      if (hookedDocument) hookedDocument.removeEventListener('keydown', frameEscape);
    };
  }
  function makeFrame(url, label) {
    const frame = document.createElement('iframe');
    frame.className = 'askr-chart-frame'; frame.title = label; frame.src = url;
    return frame;
  }
  function ensureDialog() {
    if (dialog) return true;
    if (!window.HTMLDialogElement || !HTMLDialogElement.prototype.showModal) return false;
    dialog = document.createElement('dialog');
    dialog.className = 'askr-chart-dialog';
    dialog.setAttribute('aria-labelledby', 'askr-chart-dialog-title');
    const toolbar = document.createElement('div'); toolbar.className = 'askr-chart-toolbar';
    title = document.createElement('h2'); title.id = 'askr-chart-dialog-title'; title.className = 'askr-chart-dialog-title';
    source = document.createElement('a'); source.className = 'askr-chart-source'; source.textContent = words.source;
    toolbar.append(title, source);
    closeControl = button(words.close, closeViewer);
    toolbar.append(closeControl);
    status = statusRegion(); stage = document.createElement('div'); stage.className = 'askr-chart-frame-wrap';
    dialog.append(toolbar, status, stage); document.body.append(dialog);
    dialog.addEventListener('cancel', escapeViewer);
    dialog.addEventListener('close', () => { if (!dialog.open) cleanup(); });
    let backdropStart = false;
    function backdrop(event) {
      const bounds = dialog.getBoundingClientRect();
      return event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom);
    }
    dialog.addEventListener('pointerdown', event => { backdropStart = backdrop(event); });
    dialog.addEventListener('pointerup', event => {
      if (backdropStart && backdrop(event)) closeViewer();
      backdropStart = false;
    });
    return true;
  }
  function cleanup() {
    if (!current) return;
    const old = current; current = null;
    if (old.dispose) old.dispose();
    stage.replaceChildren();
    document.body.style.overflow = old.overflow;
    document.body.style.paddingRight = old.paddingRight;
    window.scrollTo({left: old.x, top: old.y, behavior: 'instant'});
    if (old.trigger.isConnected) old.trigger.focus({preventScroll: true});
  }
  function closeViewer() {
    if (!dialog || !dialog.open) return;
    dialog.close();
    cleanup();
  }
  function loadModal(entry) {
    if (entry.dispose) entry.dispose();
    const frame = makeFrame(entry.url, entry.label); entry.frame = frame;
    stage.replaceChildren(frame);
    entry.dispose = watchFrame(frame, status, entry.url, () => loadModal(entry), () => current === entry && entry.frame === frame);
  }
  function openViewer(url, label, trigger) {
    if (!ensureDialog()) { location.assign(url); return; }
    if (dialog.open) return;
    const entry = {
      url, label, trigger, x: scrollX, y: scrollY,
      overflow: document.body.style.overflow, paddingRight: document.body.style.paddingRight
    };
    const scrollbar = innerWidth - document.documentElement.clientWidth;
    current = entry;
    title.textContent = label; source.href = url;
    document.body.style.overflow = 'hidden';
    if (scrollbar) document.body.style.paddingRight = `${parseFloat(getComputedStyle(document.body).paddingRight) + scrollbar}px`;
    dialog.showModal(); loadModal(entry); closeControl.focus({preventScroll: true});
  }
  function mount() {
    document.querySelectorAll('.askr-chart-view').forEach(root => {
      if (root.dataset.askrChartBound) return;
      root.dataset.askrChartBound = 'true';
      const link = root.querySelector('.askr-chart-open');
      if (!link) return;
      const url = new URL(link.href, location.href);
      if (url.origin !== location.origin || !['http:', 'https:'].includes(url.protocol)) return;
      const label = root.dataset.askrChartTitle || link.textContent;
      if (!window.HTMLDialogElement || !HTMLDialogElement.prototype.showModal) return;
      const trigger = button(root.dataset.askrChartMode === 'inline' ? words.expand : link.textContent,
        () => openViewer(url.href, label, trigger), 'askr-chart-open-button');
      link.replaceWith(trigger);
      if (root.dataset.askrChartMode === 'inline') {
        const wrap = root.querySelector('.askr-chart-frame-wrap');
        const region = statusRegion(); wrap.before(region);
        let dispose;
        function bind(frame) { dispose = watchFrame(frame, region, url.href, retry); }
        function retry() {
          if (dispose) dispose();
          const frame = makeFrame(url.href, label); wrap.replaceChildren(frame); bind(frame);
        }
        const frame = wrap.querySelector('iframe'); if (frame) bind(frame);
      }
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
