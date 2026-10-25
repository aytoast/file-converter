(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const sentences = [
    '此前没有网站，现在提供格式查询与 Skill 下载入口。',
    '此前没有格式目录，现在可查询转换目标、依赖与使用命令。',
    '此前没有使用说明，现在可查看下载步骤、验证记录和当前边界。'
  ];
  let step = Math.max(0, Math.min(2, Number(new URLSearchParams(location.search).get('step') || 1) - 1));
  let generation = 0;
  let mode = 'new';
  let ready = false;
  let position = 50;
  let pointer = null;
  const current = $('#current-frame');
  const proposed = $('#new-frame');
  function syncHeight() {
    if (current.contentDocument?.body && proposed.contentDocument?.body) {
      current.contentDocument.body.style.height = proposed.contentDocument.documentElement.scrollHeight + 'px';
    }
  }
  function showMode(value) {
    mode = value;
    $('#show-current').setAttribute('aria-pressed', String(mode === 'current'));
    $('#show-new').setAttribute('aria-pressed', String(mode === 'new'));
    $('#show-comparison').setAttribute('aria-pressed', String(mode === 'comparison'));
    $('#divider').hidden = mode !== 'comparison';
    $('#current-layer').style.clipPath = `inset(0 ${mode === 'current' ? 0 : mode === 'new' ? 100 : 100 - position}% 0 0)`;
    $('#current-layer').style.pointerEvents = mode === 'new' ? 'none' : 'auto';
    current.inert = mode === 'new';
    proposed.inert = mode === 'current';
  }
  function setPosition(value) {
    position = Math.max(0, Math.min(100, value));
    $('#divider').style.left = position + '%';
    $('#divider').setAttribute('aria-valuenow', String(Math.round(position)));
    if (mode === 'comparison') showMode(mode);
  }
  function prepare() {
    ready = false;
    generation++;
    $('#previous').disabled = $('#next').disabled = $('#replay').disabled = true;
    proposed.contentWindow.postMessage({ type: 'converter-review-step', step, generation }, location.origin);
  }
  window.addEventListener('message', (event) => {
    if (event.origin !== location.origin) return;
    if (event.source === proposed.contentWindow) {
      if (event.data?.type === 'converter-review-loaded') prepare();
      if (event.data?.type === 'converter-review-ready' && event.data.generation === generation) {
        ready = true;
        syncHeight();
        $('#step-number').textContent = `${step + 1} / 3`;
        $('#step-description').textContent = sentences[step];
        $('#previous').disabled = step === 0;
        $('#next').disabled = step === 2;
        $('#replay').disabled = false;
        current.contentWindow.scrollTo({ top: proposed.contentWindow.scrollY, behavior: 'instant' });
        document.documentElement.dataset.ready = 'true';
      }
      if (ready && event.data?.type === 'converter-review-scroll' && event.data.generation === generation) {
        current.contentWindow.scrollTo({ top: event.data.top, behavior: 'instant' });
      }
    } else if (ready && event.source === current.contentWindow && event.data?.type === 'converter-baseline-scroll') {
      proposed.contentWindow.scrollTo({ top: event.data.top, behavior: 'instant' });
    }
  });
  current.addEventListener('load', syncHeight);
  window.addEventListener('resize', syncHeight);
  $('#previous').addEventListener('click', () => { if (ready && step > 0) { step--; prepare(); } });
  $('#next').addEventListener('click', () => { if (ready && step < 2) { step++; prepare(); } });
  $('#replay').addEventListener('click', () => { if (ready) prepare(); });
  $('#show-current').addEventListener('click', () => showMode('current'));
  $('#show-new').addEventListener('click', () => showMode('new'));
  $('#show-comparison').addEventListener('click', () => { setPosition(50); showMode('comparison'); });
  $('#divider').addEventListener('pointerdown', (event) => { pointer = event.pointerId; event.currentTarget.setPointerCapture(pointer); });
  $('#divider').addEventListener('pointermove', (event) => {
    if (pointer !== event.pointerId) return;
    const bounds = $('#review-stage').getBoundingClientRect();
    setPosition((event.clientX - bounds.left) / bounds.width * 100);
  });
  $('#divider').addEventListener('pointerup', () => { pointer = null; });
  $('#divider').addEventListener('pointercancel', () => { pointer = null; });
  $('#divider').addEventListener('keydown', (event) => {
    const next = { ArrowLeft: position - 5, ArrowRight: position + 5, Home: 0, End: 100 }[event.key];
    if (next !== undefined) { event.preventDefault(); setPosition(next); }
  });
  showMode('new');
})();
