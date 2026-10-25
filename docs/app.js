(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  let catalog = [];
  let active = null;
  let selected = null;
  let reviewGeneration = 0;
  const query = new URLSearchParams(location.search);
  const reviewMode = query.get('review') === '1';

  const command = (source, route) => `python scripts/convert.py --input "${source.sample}" --format ${route.target}${route.flags ? ' ' + route.flags : ''}`;
  function closeDetail() {
    selected = null;
    $('#route-detail').hidden = true;
    $('#copy-status').textContent = '';
    document.querySelectorAll('.target-button').forEach((button) => button.setAttribute('aria-expanded', 'false'));
  }
  function showRoute(source, route, focus = false) {
    selected = route;
    $('#route-detail').hidden = false;
    $('#detail-title').textContent = `${source.extension} → ${route.label}`;
    $('#detail-note').textContent = route.note;
    $('#detail-dependency').textContent = route.dependency;
    $('#command-text').textContent = command(source, route);
    $('#copy-status').textContent = '';
    document.querySelectorAll('.target-button').forEach((button) => button.setAttribute('aria-expanded', String(button.dataset.target === route.target)));
    if (focus) $('#route-detail').scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  function showSource(source) {
    active = source;
    closeDetail();
    document.querySelectorAll('.source-button').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.source === source?.id)));
    $('#target-list').replaceChildren();
    $('#source-title').textContent = source?.label || '未找到源格式';
    $('#source-description').textContent = source?.description || '换一个格式名称，或清空搜索重新查看。';
    $('#source-extension').textContent = source ? '.' + source.extension.toLowerCase() : '—';
    $('#target-count').textContent = source ? `${source.routes.length} 条路线` : '0 条路线';
    if (!source) return;
    source.routes.forEach((route) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'target-button' + (route.status === 'unverified' ? ' unverified' : '');
      button.dataset.target = route.target;
      button.setAttribute('aria-expanded', 'false');
      button.setAttribute('aria-controls', 'route-detail');
      const content = document.createElement('span');
      const label = document.createElement('span');
      label.className = 'target-label';
      label.textContent = route.label;
      const subtitle = document.createElement('span');
      subtitle.className = 'target-subtitle';
      subtitle.textContent = route.status === 'unverified' ? '需外部引擎 · 尚未实测' : route.dependency;
      content.append(label, subtitle);
      const arrow = document.createElement('span');
      arrow.textContent = '↗';
      arrow.setAttribute('aria-hidden', 'true');
      button.append(content, arrow);
      button.addEventListener('click', () => selected === route ? closeDetail() : showRoute(source, route, true));
      $('#target-list').append(button);
    });
  }
  function filterSources() {
    const keyword = $('#format-search').value.trim().toLowerCase().replace(/^\./, '');
    const filtered = catalog.filter((source) => `${source.label} ${source.extension} ${source.aliases}`.toLowerCase().includes(keyword));
    $('#source-list').replaceChildren();
    filtered.forEach((source) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'source-button';
      button.dataset.source = source.id;
      button.setAttribute('aria-pressed', String(active?.id === source.id));
      const code = document.createElement('span');
      code.className = 'source-code';
      code.textContent = source.extension;
      const label = document.createElement('span');
      label.textContent = source.label;
      button.append(code, label);
      button.addEventListener('click', () => showSource(source));
      $('#source-list').append(button);
    });
    $('#source-count').textContent = keyword ? `${filtered.length} 种匹配的源格式` : `${catalog.length} 类源文件 · 按需配置引擎`;
    if (!filtered.length) {
      const empty = document.createElement('p');
      empty.className = 'empty-state';
      empty.textContent = '没有匹配格式。清空搜索，或换一个名称。';
      $('#source-list').append(empty);
      showSource(null);
    } else if (!filtered.some((source) => source.id === active?.id)) showSource(filtered[0]);
  }
  function jump(sourceId, targetId, scroll = true) {
    const source = catalog.find((item) => item.id === sourceId) || catalog[0];
    $('#format-search').value = '';
    active = source;
    filterSources();
    showSource(source);
    if (targetId) {
      const route = source.routes.find((item) => item.target === targetId);
      if (route) showRoute(source, route);
    }
    if (scroll) $('#formats').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
  async function copyCommand() {
    const text = $('#command-text').textContent;
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.cssText = 'position:fixed;top:-9999px';
        document.body.append(textArea);
        textArea.select();
        const copied = document.execCommand('copy');
        textArea.remove();
        $('#copy-command').focus();
        if (!copied) throw new Error('copy unavailable');
      }
      $('#copy-status').textContent = '命令已复制';
    } catch {
      $('#copy-status').textContent = '复制不可用，请选中上方命令手动复制。';
    }
  }
  function applyReview(step, generation) {
    reviewGeneration = generation;
    const focus = step === 0 ? 'hero' : step === 1 ? 'catalog' : 'start';
    document.querySelectorAll('[data-focus]').forEach((element) => element.classList.toggle('review-muted', element.dataset.focus !== focus));
    if (step === 1) jump('glb', 'fbx', false);
    else jump('pdf', null, false);
    const target = step === 0 ? document.body : step === 1 ? $('#formats') : $('#start');
    const top = step === 0 ? 0 : target.getBoundingClientRect().top + scrollY - 24;
    window.scrollTo({ top, behavior: 'instant' });
    window.parent.postMessage({ type: 'converter-review-ready', generation }, location.origin);
  }
  $('#format-search').addEventListener('input', filterSources);
  $('#close-detail').addEventListener('click', closeDetail);
  $('#copy-command').addEventListener('click', copyCommand);
  document.querySelectorAll('.quick-route').forEach((button) => button.addEventListener('click', () => jump(button.dataset.source, button.dataset.target)));
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) {
      event.preventDefault();
      $('#format-search').focus();
    }
    if (event.key === 'Escape') closeDetail();
  });
  if (reviewMode) {
    window.addEventListener('message', (event) => {
      if (event.origin !== location.origin || event.source !== window.parent) return;
      if (event.data?.type === 'converter-review-step' && catalog.length) applyReview(event.data.step, event.data.generation);
    });
    let scrollFrame;
    window.addEventListener('scroll', () => {
      cancelAnimationFrame(scrollFrame);
      scrollFrame = requestAnimationFrame(() => window.parent.postMessage({ type: 'converter-review-scroll', top: scrollY, generation: reviewGeneration }, location.origin));
    }, { passive: true });
  }
  fetch('./routes.json').then((response) => {
    if (!response.ok) throw new Error('catalog unavailable');
    return response.json();
  }).then((data) => {
    catalog = data.sources;
    jump(query.get('source') || 'pdf', query.get('to'), false);
    document.documentElement.dataset.ready = 'true';
    if (reviewMode) window.parent.postMessage({ type: 'converter-review-loaded' }, location.origin);
  }).catch(() => {
    $('#source-list').textContent = '格式目录读取失败。请刷新页面，或查看 GitHub 中的转换说明。';
    $('#source-list').className = 'source-list empty-state';
    $('#source-description').textContent = '当前无法读取静态格式目录。下载与 GitHub 链接仍可使用。';
    document.documentElement.dataset.ready = 'error';
  });
})();
