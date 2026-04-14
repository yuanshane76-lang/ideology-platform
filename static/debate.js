let sessionId = null;
let currentRound = 0;
let maxRounds = 10;
let isGenerating = false;
let abortController = null;
let currentCardBody = null;
let currentContent = '';

const statusEl = document.getElementById('debate-status');
const titleInput = document.getElementById('topic-title');
const descInput = document.getElementById('topic-description');
const roundsSelect = document.getElementById('rounds');
const topicsList = document.getElementById('topics-list');
const startBtn = document.getElementById('start-btn');
const nextBtn = document.getElementById('next-btn');
const judgeBtn = document.getElementById('judge-btn');
const stopBtn = document.getElementById('stop-btn');
const resetBtn = document.getElementById('reset-btn');
const placeholder = document.getElementById('placeholder');
const timeline = document.getElementById('timeline');
const notice = document.getElementById('notice');

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = `text-xs px-3 py-1 rounded-full ${cls}`;
}

function setNotice(text, type = 'info') {
  if (!text) {
    notice.className = 'hidden mb-3 text-sm px-3 py-2 rounded-xl';
    notice.textContent = '';
    return;
  }

  const clsMap = {
    info: 'mb-3 text-sm px-3 py-2 rounded-xl bg-slate-100 text-slate-700',
    success: 'mb-3 text-sm px-3 py-2 rounded-xl bg-emerald-100 text-emerald-700',
    warning: 'mb-3 text-sm px-3 py-2 rounded-xl bg-amber-100 text-amber-700',
    error: 'mb-3 text-sm px-3 py-2 rounded-xl bg-rose-100 text-rose-700',
  };

  notice.className = clsMap[type] || clsMap.info;
  notice.textContent = text;
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

function resetDebateView() {
  if (abortController) abortController.abort();
  sessionId = null;
  currentRound = 0;
  isGenerating = false;
  currentCardBody = null;
  currentContent = '';
  setStatus('待开始', 'bg-slate-100 text-slate-600');
  setNotice('', 'info');
  startBtn.disabled = false;
  startBtn.classList.remove('hidden');
  nextBtn.classList.add('hidden');
  judgeBtn.classList.add('hidden');
  stopBtn.classList.add('hidden');
  timeline.innerHTML = '';
  timeline.classList.add('hidden');
  placeholder.classList.remove('hidden');
}

function createRoundDivider(round) {
  const div = document.createElement('div');
  div.className = 'text-center text-xs text-slate-500 my-1';
  div.innerHTML = `<span class="px-3 py-1 rounded-full bg-slate-100">第 ${round} 轮</span>`;
  timeline.appendChild(div);
}

function createMessageCard(role, round = null) {
  const map = {
    protagonist: { title: '红芯正方', color: 'border-rose-300 bg-rose-50', icon: '🔴' },
    antagonist: { title: '红芯反方', color: 'border-sky-300 bg-sky-50', icon: '🔵' },
    judge: { title: '红芯裁判', color: 'border-emerald-300 bg-emerald-50', icon: '⚖️' },
  };

  const cfg = map[role];
  const card = document.createElement('div');
  card.className = `rounded-xl border ${cfg.color} bg-white p-3`;
  card.innerHTML = `
    <div class="text-sm font-semibold mb-2">${cfg.icon} ${cfg.title}${round ? ` · 第${round}轮` : ''}</div>
    <div class="prose prose-sm max-w-none text-slate-700"></div>
  `;

  timeline.appendChild(card);
  timeline.scrollTop = timeline.scrollHeight;
  return card.querySelector('.prose');
}

function appendChunk(chunk) {
  if (!currentCardBody) return;
  currentContent += chunk;
  currentCardBody.innerHTML = marked.parse(currentContent) + '<span style="opacity:.5">▍</span>';
  timeline.scrollTop = timeline.scrollHeight;
}

function finalizeCard() {
  if (!currentCardBody) return;
  currentCardBody.innerHTML = marked.parse(currentContent);
  currentCardBody = null;
  currentContent = '';
}

function prepareRunningUI() {
  placeholder.classList.add('hidden');
  timeline.classList.remove('hidden');
  timeline.innerHTML = '';
  startBtn.classList.add('hidden');
  nextBtn.classList.add('hidden');
  judgeBtn.classList.add('hidden');
  stopBtn.classList.remove('hidden');
  setStatus('正在交锋', 'bg-orange-100 text-orange-700');
}

function finishRoundUI(canContinue, isMaxRounds) {
  isGenerating = false;
  stopBtn.classList.add('hidden');

  if (isMaxRounds) {
    setStatus(`已达最大轮次 (${currentRound}/${maxRounds})`, 'bg-amber-100 text-amber-700');
    setNotice('已达最大轮次，可以请求裁判总结。', 'warning');
    judgeBtn.classList.remove('hidden');
    judgeBtn.disabled = false;
  } else if (canContinue) {
    setStatus(`第 ${currentRound} 轮完成`, 'bg-emerald-100 text-emerald-700');
    setNotice(`第 ${currentRound} 轮交锋完成，点击"下一轮"继续，或点击"请求裁判"结束辩论。`, 'success');
    nextBtn.classList.remove('hidden');
    nextBtn.disabled = false;
    judgeBtn.classList.remove('hidden');
    judgeBtn.disabled = false;
  }
}

function finishJudgeUI() {
  isGenerating = false;
  stopBtn.classList.add('hidden');
  nextBtn.classList.add('hidden');
  judgeBtn.classList.add('hidden');
  setStatus('辩论结束', 'bg-emerald-100 text-emerald-700');
  setNotice('辩论已完成，可更换议题开始新的辩论。', 'success');
}

async function loadTopics() {
  try {
    const topicsResp = await fetch('/api/debate/topics');

    if (!topicsResp.ok) {
      throw new Error('加载配置失败');
    }

    const topics = await topicsResp.json();

    topicsList.innerHTML = topics.map(topic => `
      <button class="w-full text-left p-3 rounded-xl border border-slate-200 hover:border-rose-300 hover:bg-rose-50 transition"
        data-title="${escapeHtml(topic.title)}"
        data-description="${escapeHtml(topic.description)}">
        <div class="text-sm font-medium text-slate-800">${escapeHtml(topic.title)}</div>
        <div class="text-xs text-slate-500 mt-1">${escapeHtml(topic.tags.join(' · '))}</div>
      </button>
    `).join('');

    topicsList.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        titleInput.value = btn.dataset.title;
        descInput.value = btn.dataset.description;
      });
    });
  } catch (e) {
    setNotice(`加载热门议题失败：${e.message}`, 'error');
  }
}

async function startDebate() {
  const title = titleInput.value.trim();
  if (!title) {
    setNotice('请先填写交锋议题。', 'warning');
    return;
  }

  try {
    maxRounds = parseInt(roundsSelect.value) || 10;
  } catch {
    maxRounds = 10;
  }
  maxRounds = Math.max(1, Math.min(10, maxRounds));

  isGenerating = true;
  abortController = new AbortController();
  prepareRunningUI();

  try {
    const startResp = await fetch('/api/debate/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title,
        description: descInput.value.trim(),
        max_rounds: maxRounds,
      }),
    });

    if (!startResp.ok) {
      throw new Error(`启动失败: ${startResp.status}`);
    }

    const startData = await startResp.json();
    sessionId = startData.session_id;
    currentRound = 0;

    setNotice('辩论会话已创建，开始第一轮交锋...', 'info');

    await runNextRound();

  } catch (e) {
    if (e.name === 'AbortError') {
      setNotice('已停止生成。', 'warning');
    } else {
      setNotice(`启动失败：${e.message}`, 'error');
    }
    isGenerating = false;
    stopBtn.classList.add('hidden');
    startBtn.classList.remove('hidden');
    startBtn.disabled = false;
  }
}

async function runNextRound() {
  if (!sessionId) {
    setNotice('会话不存在，请重新开始。', 'error');
    return;
  }

  isGenerating = true;
  abortController = new AbortController();
  stopBtn.classList.remove('hidden');
  nextBtn.disabled = true;
  judgeBtn.disabled = true;

  try {
    const resp = await fetch('/api/debate/next', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: abortController.signal,
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const block of parts) {
        const line = block.trim();
        if (!line.startsWith('data: ')) continue;

        let data;
        try {
          data = JSON.parse(line.slice(6));
        } catch {
          continue;
        }

        switch (data.type) {
          case 'round_start':
            currentRound = data.round;
            createRoundDivider(currentRound);
            break;
          case 'protagonist_start':
            currentCardBody = createMessageCard('protagonist', currentRound);
            break;
          case 'antagonist_start':
            currentCardBody = createMessageCard('antagonist', currentRound);
            break;
          case 'protagonist_chunk':
          case 'antagonist_chunk':
            appendChunk(data.content || '');
            break;
          case 'protagonist_end':
          case 'antagonist_end':
            finalizeCard();
            break;
          case 'round_complete':
            finalizeCard();
            finishRoundUI(data.can_continue, false);
            break;
          case 'max_rounds_reached':
            finalizeCard();
            finishRoundUI(false, true);
            break;
          case 'error':
            finalizeCard();
            if (data.error_type === 'content_moderation') {
              setNotice(data.message || '内容审核拦截，请调整议题措辞后重试。', 'warning');
            } else {
              setNotice(data.message || '交锋发生错误，请稍后重试。', 'error');
            }
            isGenerating = false;
            stopBtn.classList.add('hidden');
            break;
          default:
            break;
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      setNotice('已停止生成。', 'warning');
    } else {
      setNotice(`请求失败：${e.message}`, 'error');
    }
    isGenerating = false;
    stopBtn.classList.add('hidden');
    nextBtn.disabled = false;
    judgeBtn.disabled = false;
  }
}

async function runJudge() {
  if (!sessionId) {
    setNotice('会话不存在，请重新开始。', 'error');
    return;
  }

  isGenerating = true;
  abortController = new AbortController();
  stopBtn.classList.remove('hidden');
  nextBtn.disabled = true;
  judgeBtn.disabled = true;

  try {
    const resp = await fetch('/api/debate/judge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: abortController.signal,
      body: JSON.stringify({ session_id: sessionId }),
    });

    if (!resp.ok || !resp.body) {
      throw new Error(`HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const block of parts) {
        const line = block.trim();
        if (!line.startsWith('data: ')) continue;

        let data;
        try {
          data = JSON.parse(line.slice(6));
        } catch {
          continue;
        }

        switch (data.type) {
          case 'judge_start':
            currentCardBody = createMessageCard('judge');
            break;
          case 'judge_chunk':
            appendChunk(data.content || '');
            break;
          case 'judge_end':
            finalizeCard();
            break;
          case 'complete':
            finalizeCard();
            finishJudgeUI();
            break;
          case 'error':
            finalizeCard();
            setNotice(data.message || '裁判总结失败。', 'error');
            isGenerating = false;
            stopBtn.classList.add('hidden');
            break;
          default:
            break;
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') {
      setNotice('已停止生成。', 'warning');
    } else {
      setNotice(`请求失败：${e.message}`, 'error');
    }
    isGenerating = false;
    stopBtn.classList.add('hidden');
    judgeBtn.disabled = false;
  }
}

function stopDebate() {
  if (abortController) abortController.abort();
}

startBtn.addEventListener('click', startDebate);
nextBtn.addEventListener('click', runNextRound);
judgeBtn.addEventListener('click', runJudge);
stopBtn.addEventListener('click', stopDebate);
resetBtn.addEventListener('click', resetDebateView);

loadTopics();
lucide.createIcons();
