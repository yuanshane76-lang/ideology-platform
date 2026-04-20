// ==================== 思政云伴读 - 前端交互逻辑 ====================

const TB = {
  currentBookId: null,
  currentBlockId: null,
  readerData: null,
  graphData: null,
  chatHistory: [],
};

// ==================== 子视图切换 ====================

function showTextView(view) {
  ['list', 'reader', 'graph'].forEach(v => {
    const el = document.getElementById(`tb-view-${v}`);
    if (el) el.classList.toggle('hidden', v !== view);
    const btn = document.getElementById(`tb-${v}-btn`);
    if (btn) {
      btn.classList.toggle('bg-teal', v === view);
      btn.classList.toggle('text-white', v === view);
      btn.classList.toggle('bg-slate-100', v !== view);
      btn.classList.toggle('text-slate-600', v !== view);
      btn.classList.toggle('hidden', v === 'reader' && !TB.currentBookId);
      btn.classList.toggle('hidden', v === 'graph' && !TB.currentBookId);
    }
  });
}

// ==================== 教材列表 ====================

async function loadBookList() {
  try {
    const resp = await fetch('/api/textbook/books');
    const data = await resp.json();
    renderBookGrid(data.books || []);
  } catch (e) {
    document.getElementById('tb-book-grid').innerHTML = '<p class="text-red-500 text-sm col-span-3">加载失败</p>';
  }
}

function renderBookGrid(books) {
  const grid = document.getElementById('tb-book-grid');
  if (!books.length) {
    grid.innerHTML = '<p class="text-slate-400 text-sm col-span-3">暂无可用教材</p>';
    return;
  }
  grid.innerHTML = books.map(b => `
    <div class="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5">
      <div class="flex items-start justify-between gap-3 mb-3">
        <div class="w-11 h-11 rounded-xl bg-teal-50 text-teal flex items-center justify-center shrink-0">
          <i class="fas fa-book text-lg"></i>
        </div>
        <div class="flex gap-1.5">
          <span class="text-[11px] font-semibold px-2 py-0.5 rounded-full ${b.enabled ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-slate-50 text-slate-500 border border-slate-200'}">${b.enabled ? '已启用' : '未启用'}</span>
          <span class="text-[11px] font-semibold text-teal bg-teal-50 px-2 py-0.5 rounded-full border border-teal-100">${b.ingest_status}</span>
        </div>
      </div>
      <h3 class="text-base font-bold text-slate-800">${b.title}</h3>
      ${b.subtitle ? `<p class="mt-1 text-xs text-slate-500">${b.subtitle}</p>` : ''}
      <p class="mt-2 text-sm text-slate-500 leading-6 line-clamp-2">${b.description || '暂无说明'}</p>
      <div class="mt-3 flex flex-wrap gap-1.5 text-xs">
        ${b.subject ? `<span class="rounded-full bg-orange-50 border border-orange-100 px-2 py-0.5 text-orange-700">${b.subject}</span>` : ''}
        ${b.version ? `<span class="rounded-full bg-slate-50 border border-slate-200 px-2 py-0.5 text-slate-600">${b.version}</span>` : ''}
      </div>
      <div class="mt-4 flex gap-2">
        <button onclick="openReader('${b.book_id}')" class="flex-1 rounded-lg py-2 text-xs font-medium transition-colors ${b.enabled ? 'bg-teal text-white hover:bg-teal-700' : 'bg-slate-100 text-slate-500 border border-slate-200 cursor-not-allowed'}" ${b.enabled ? '' : 'disabled'}>进入阅读器</button>
        <button onclick="openGraph('${b.book_id}')" class="rounded-lg bg-white text-slate-700 px-3 py-2 text-xs font-medium border border-slate-200 hover:border-teal-200 hover:text-teal-700 transition-colors">知识星图</button>
      </div>
    </div>
  `).join('');
}

// ==================== 阅读器 ====================

async function openReader(bookId) {
  TB.currentBookId = bookId;
  TB.chatHistory = [];
  document.getElementById('tb-chat-history').innerHTML = '';
  showTextView('reader');
  try {
    const resp = await fetch(`/api/textbook/reader?book_id=${bookId}`);
    TB.readerData = await resp.json();
    renderReader(TB.readerData);
  } catch (e) {
    document.getElementById('tb-reader-content').innerHTML = '<p class="text-red-500 text-sm">加载失败</p>';
  }
}

function renderReader(data) {
  document.getElementById('tb-reader-booktitle').textContent = data.book?.title || '--';

  // 存储当前 reader 数据供目录跳转使用
  TB.readerData = data;

  // 移动端书名
  const mobileTitle = document.getElementById('tb-reader-booktitle-mobile');
  if (mobileTitle) mobileTitle.textContent = data.book?.title || '--';

  // 目录
  const tocEl = document.getElementById('tb-toc-list');
  if (data.toc && data.toc.length) {
    tocEl.innerHTML = data.toc.map(ch => `
      <div class="mb-2">
        <div class="px-2 py-1.5 text-xs font-semibold text-slate-700 rounded-lg ${ch.active ? 'bg-teal-50 text-teal-700' : 'hover:bg-slate-50'} cursor-pointer" onclick="navigateToChapter('${data.book_id}', '${ch.id}')">
          ${ch.title}
        </div>
        <div class="ml-2 space-y-0.5">
          ${(ch.sections || []).map(s => `
            <div class="block px-2 py-1 text-xs text-slate-500 rounded hover:bg-slate-50 hover:text-teal-700 truncate cursor-pointer" onclick="navigateToSection('${data.book_id}', '${ch.id}', '${escAttr(s.anchor)}')">${s.title}</div>
          `).join('')}
        </div>
      </div>
    `).join('');
  } else {
    tocEl.innerHTML = '<div class="text-xs text-slate-400 text-center py-4">暂无目录</div>';
  }

  // 同步移动端 TOC
  const mobileToc = document.getElementById('tb-toc-mobile');
  if (mobileToc) mobileToc.innerHTML = tocEl.innerHTML;

  // 正文
  const contentEl = document.getElementById('tb-reader-content');
  if (!data.has_structured_content) {
    contentEl.innerHTML = `<div class="text-center py-16"><i class="fas fa-file-warning text-3xl text-slate-300 mb-3"></i><p class="text-slate-500 text-sm">${data.empty_state?.description || '暂无内容'}</p></div>`;
    return;
  }

  let html = `<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 mb-4">
    <div class="text-xs font-semibold text-teal mb-2">当前阅读章节</div>
    <h1 class="text-xl font-bold text-slate-800">${data.chapter?.title || ''}</h1>
    <p class="mt-2 text-sm text-slate-500">${data.chapter?.summary || ''}</p>
  </div>`;

  (data.section_groups || []).forEach(section => {
    const safeAnchor = safeId(section.anchor);
    html += `<section id="${safeAnchor}" data-raw-anchor="${escAttr(section.anchor)}" class="mb-4">
      <div class="bg-white rounded-xl p-4 border border-teal-100 mb-3">
        <div class="flex items-center gap-2 text-teal text-xs font-semibold"><i class="fas fa-pilcrow"></i>小节</div>
        <h2 class="mt-2 text-lg font-bold text-slate-800">${section.title}</h2>
        <p class="mt-1 text-xs text-slate-500">${section.summary || ''}</p>
      </div>`;
    (section.blocks || []).forEach(block => {
      const safeBlockAnchor = safeId(block.anchor);
      html += `<article id="${safeBlockAnchor}" data-raw-anchor="${escAttr(block.anchor)}" class="bg-white rounded-xl p-5 shadow-sm border border-slate-100 mb-3 cursor-pointer hover:border-teal-200 transition-colors" data-block-id="${block.id}" data-book-id="${data.book_id}" onclick="selectBlock(this)">
        <div class="flex flex-wrap items-center gap-1.5 mb-3">
          <span class="text-[11px] px-2 py-0.5 rounded-full bg-teal-50 border border-teal-100 text-teal-700 font-medium">${block.sectionTitle || ''}</span>
          ${(block.relatedConcepts || []).slice(0, 3).map(c => `<span class="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 border border-orange-100 text-orange-700">${c.name}</span>`).join('')}
        </div>
        <div class="text-sm text-slate-700 leading-7">${block.text || ''}</div>
      </article>`;
    });
    html += `</section>`;
  });

  contentEl.innerHTML = html;

  // 初始化伴读区
  if (data.companion_initial) {
    updateCompanionPanel(data.companion_initial);
  }
}

// ==================== 目录跳转 ====================

async function navigateToChapter(bookId, chapterId, scrollTarget) {
  try {
    const resp = await fetch(`/api/textbook/reader?book_id=${bookId}&chapter_id=${chapterId}`);
    TB.readerData = await resp.json();
    renderReader(TB.readerData);
    // 滚动到正文顶部 或 指定 section
    if (scrollTarget) {
      setTimeout(() => scrollToSection(scrollTarget), 150);
    } else {
      const contentEl = document.getElementById('tb-reader-content');
      if (contentEl) contentEl.scrollTop = 0;
    }
  } catch (e) {
    console.error('navigateToChapter error:', e);
  }
}

function navigateToSection(bookId, chapterId, anchor) {
  // 确保切换到阅读器视图
  const readerView = document.getElementById('tb-view-reader');
  if (readerView && readerView.classList.contains('hidden')) {
    showTextView('reader');
  }

  // 判断目标 section 是否在当前已渲染的 DOM 中
  let el = document.getElementById(safeId(anchor));
  if (!el) el = document.querySelector(`[data-raw-anchor="${CSS.escape(anchor)}"]`);
  if (el) {
    // 当前章节内，直接滚动
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.style.transition = 'background 0.3s';
    el.style.background = 'rgba(13,148,136,0.08)';
    setTimeout(() => { el.style.background = ''; }, 1500);
  } else {
    // 跨章节，先加载目标章节再滚动
    navigateToChapter(bookId, chapterId, anchor);
  }
}

function selectBlock(el) {
  // 清除之前选中状态
  document.querySelectorAll('#tb-reader-content .ring-2').forEach(e => e.classList.remove('ring-2', 'ring-teal-300'));
  el.classList.add('ring-2', 'ring-teal-300');
  TB.currentBlockId = el.dataset.blockId;

  const bookId = el.dataset.bookId;
  const blockText = el.querySelector('.text-sm.text-slate-700')?.textContent || '';
  document.getElementById('tb-block-preview').textContent = blockText.slice(0, 200);

  // 更新上下文
  const chapterTitle = document.getElementById('tb-reader-booktitle')?.textContent || '';
  const sectionEl = el.closest('section');
  const sectionTitle = sectionEl?.querySelector('h2')?.textContent || '';
  document.getElementById('tb-chapter-title').textContent = chapterTitle;
  document.getElementById('tb-section-title').textContent = sectionTitle;

  // 重置结果区
  document.getElementById('tb-result-empty').textContent = '请选择伴读动作';
  document.getElementById('tb-result-empty').classList.remove('hidden');
  document.getElementById('tb-result-text').classList.add('hidden');
  document.getElementById('tb-result-items').classList.add('hidden');

  // 更新概念标签
  const concepts = el.querySelectorAll('.bg-orange-50');
  const conceptEl = document.getElementById('tb-concepts');
  if (concepts.length) {
    conceptEl.innerHTML = Array.from(concepts).map(c => `<span class="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 border border-orange-100 text-orange-700">${c.textContent}</span>`).join('');
  } else {
    conceptEl.innerHTML = '<span class="text-xs text-slate-400">--</span>';
  }

  // 重置追问历史
  TB.chatHistory = [];
  document.getElementById('tb-chat-history').innerHTML = '';
}

// ==================== 伴读动作 ====================

async function tbDoAction(action) {
  if (!TB.currentBookId || !TB.currentBlockId) {
    showToast('请先点击左侧正文段落');
    return;
  }

  const actionNames = { explain: '解释这段', ask: '基于这段提问', note: '生成笔记' };
  document.getElementById('tb-action-label').textContent = actionNames[action] || action;

  // 显示加载
  document.getElementById('tb-result-loading').classList.remove('hidden');
  document.getElementById('tb-result-empty').classList.add('hidden');
  document.getElementById('tb-result-text').classList.add('hidden');
  document.getElementById('tb-result-items').classList.add('hidden');
  document.getElementById('tb-result-error').classList.add('hidden');

  try {
    const resp = await fetch('/api/textbook/companion/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: TB.currentBookId,
        block_id: TB.currentBlockId,
        action: action,
      }),
    });
    const data = await resp.json();
    document.getElementById('tb-result-loading').classList.add('hidden');

    if (data.error) {
      document.getElementById('tb-result-error').textContent = data.error;
      document.getElementById('tb-result-error').classList.remove('hidden');
      return;
    }

    if (data.resultType === 'questions' && data.resultItems?.length) {
      const list = document.getElementById('tb-result-items');
      list.innerHTML = data.resultItems.map(q => `<li class="p-2 bg-white rounded-lg border border-slate-100 cursor-pointer hover:border-teal-200" onclick="tbAskFollowup('${q.replace(/'/g, "\\'")}')">${q}</li>`).join('');
      list.classList.remove('hidden');
    } else if (data.resultText) {
      document.getElementById('tb-result-text').textContent = data.resultText;
      document.getElementById('tb-result-text').classList.remove('hidden');
    } else {
      document.getElementById('tb-result-empty').textContent = data.resultText || '无结果';
      document.getElementById('tb-result-empty').classList.remove('hidden');
    }

    // 更新概念
    if (data.relatedConcepts?.length) {
      document.getElementById('tb-concepts').innerHTML = data.relatedConcepts.map(c => `<span class="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 border border-orange-100 text-orange-700">${c.name}</span>`).join('');
    }
  } catch (e) {
    document.getElementById('tb-result-loading').classList.add('hidden');
    document.getElementById('tb-result-error').textContent = '请求失败: ' + e.message;
    document.getElementById('tb-result-error').classList.remove('hidden');
  }
}

function updateCompanionPanel(companion) {
  document.getElementById('tb-chapter-title').textContent = companion.chapterTitle || '--';
  document.getElementById('tb-section-title').textContent = companion.sectionTitle || '--';
  if (companion.relatedConcepts?.length) {
    document.getElementById('tb-concepts').innerHTML = companion.relatedConcepts.map(c => `<span class="text-[11px] px-2 py-0.5 rounded-full bg-orange-50 border border-orange-100 text-orange-700">${c.name}</span>`).join('');
  }
}

// ==================== 追问对话 ====================

async function tbSendChat() {
  const input = document.getElementById('tb-chat-input');
  const question = input.value.trim();
  if (!question || !TB.currentBookId || !TB.currentBlockId) return;
  input.value = '';

  // 添加用户消息到历史
  TB.chatHistory.push({ role: 'user', content: question });
  renderChatHistory();

  try {
    const resp = await fetch('/api/textbook/companion/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        book_id: TB.currentBookId,
        block_id: TB.currentBlockId,
        question: question,
        history: TB.chatHistory.slice(-6),
      }),
    });
    const data = await resp.json();

    if (data.error) {
      TB.chatHistory.push({ role: 'assistant', content: '出错了: ' + data.error });
    } else {
      TB.chatHistory.push({ role: 'assistant', content: data.reply || data.answer || '无回复' });
    }
  } catch (e) {
    TB.chatHistory.push({ role: 'assistant', content: '请求失败' });
  }
  renderChatHistory();
}

function tbAskFollowup(question) {
  document.getElementById('tb-chat-input').value = question;
  tbSendChat();
}

function renderChatHistory() {
  const el = document.getElementById('tb-chat-history');
  el.innerHTML = TB.chatHistory.map(m => `
    <div class="${m.role === 'user' ? 'text-right' : 'text-left'}">
      <span class="inline-block text-xs px-2.5 py-1.5 rounded-lg max-w-[85%] ${m.role === 'user' ? 'bg-teal text-white' : 'bg-white border border-slate-100 text-slate-700'}">${m.content}</span>
    </div>
  `).join('');
  el.scrollTop = el.scrollHeight;
}

// ==================== 知识星图 ====================

async function openGraph(bookId) {
  TB.currentBookId = bookId;
  showTextView('graph');
  try {
    const resp = await fetch(`/api/textbook/knowledge-structure?book_id=${bookId}`);
    TB.graphData = await resp.json();
    renderGraph(TB.graphData);
  } catch (e) {
    document.getElementById('tb-graph-stats').innerHTML = '<p class="text-red-500 text-sm col-span-4">加载失败</p>';
  }
}

function renderGraph(data) {
  // 统计卡片
  const statsEl = document.getElementById('tb-graph-stats');
  const cards = data.focus_cards || [];
  statsEl.innerHTML = cards.map(c => `
    <div class="bg-slate-50 rounded-lg p-3 border border-slate-100 text-center">
      <div class="text-xs text-slate-500 uppercase tracking-wider">${c.label}</div>
      <div class="mt-1 text-2xl font-bold text-slate-800">${c.value}</div>
      <div class="mt-1 text-[11px] text-slate-400">${c.description}</div>
    </div>
  `).join('');

  // 图例
  const legendEl = document.getElementById('tb-graph-legend');
  const legend = data.legend || [];
  legendEl.innerHTML = legend.map(l => `
    <span class="text-[11px] px-2 py-0.5 rounded-full border border-slate-200 bg-white text-slate-600">${l.label}</span>
  `).join('');

  // 渲染 SVG 图谱
  renderGraphSVG(data);
}

function renderGraphSVG(data) {
  const svg = document.getElementById('tb-graph-svg');
  const graph = data.graph || {};
  const nodes = graph.nodes || [];
  const edges = graph.edges || [];
  const detailIndex = data.detail_index || {};

  if (!nodes.length) {
    svg.innerHTML = '<text x="600" y="450" text-anchor="middle" fill="#94a3b8" font-size="16">暂无图谱数据</text>';
    return;
  }

  const W = 1200, H = 900, cx = W / 2, cy = H / 2;
  const orbitRadius = { 0: 0, 1: 248, 2: 366, 3: 486 };
  const typeRadius = { book: 52, chapter: 26, section: 16, concept: 11 };
  const typeColors = { book: '#0D9488', chapter: '#F97316', section: '#3B82F6', concept: '#8B5CF6' };

  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = '';

  // --- Defs: 渐变 ---
  const ns = 'http://www.w3.org/2000/svg';
  const defs = document.createElementNS(ns, 'defs');

  const gradients = {
    nodeGradientBook: [['0%','#fff7d1',1],['55%','#ffcf72',.95],['100%','#a46f21',.88]],
    nodeGradientChapter: [['0%','#dffcff',1],['55%','#70d8ff',.98],['100%','#1e607f',.86]],
    nodeGradientSection: [['0%','#f0eaff',1],['55%','#b19eff',.96],['100%','#4e3ea8',.84]],
    nodeGradientConcept: [['0%','#ffeaf4',1],['55%','#ff9dbf',.96],['100%','#7b3657',.82]],
  };
  Object.entries(gradients).forEach(([id, stops]) => {
    const g = document.createElementNS(ns, 'radialGradient');
    g.setAttribute('id', id); g.setAttribute('cx','35%'); g.setAttribute('cy','35%'); g.setAttribute('r','75%');
    stops.forEach(([offset, color, opacity]) => {
      const s = document.createElementNS(ns, 'stop');
      s.setAttribute('offset', offset); s.setAttribute('stop-color', color); s.setAttribute('stop-opacity', opacity);
      g.appendChild(s);
    });
    defs.appendChild(g);
  });
  svg.appendChild(defs);

  // --- Layers ---
  const viewport = document.createElementNS(ns, 'g'); viewport.setAttribute('class','graph-viewport');
  const orbitLayer = document.createElementNS(ns, 'g'); orbitLayer.setAttribute('class','graph-orbits');
  const edgeLayer = document.createElementNS(ns, 'g'); edgeLayer.setAttribute('class','graph-edges');
  const nodeLayer = document.createElementNS(ns, 'g'); nodeLayer.setAttribute('class','graph-nodes');

  [1,2,3].forEach(lv => {
    const c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', cx); c.setAttribute('cy', cy); c.setAttribute('r', orbitRadius[lv]);
    c.setAttribute('fill','none'); c.setAttribute('stroke','rgba(13,148,136,.08)');
    c.setAttribute('stroke-width','1.1'); c.setAttribute('stroke-dasharray','6 10');
    orbitLayer.appendChild(c);
  });
  viewport.appendChild(orbitLayer);
  viewport.appendChild(edgeLayer);
  viewport.appendChild(nodeLayer);
  svg.appendChild(viewport);

  // --- Build positions using precomputed angles ---
  const positions = buildGraphPositions(nodes, cx, cy, orbitRadius);

  // --- Adjacency ---
  const adjacency = new Map(nodes.map(n => [n.id, new Set()]));
  const nodeElMap = new Map();
  const edgeElMap = new Map();

  // --- Render edges ---
  edges.forEach((edge, idx) => {
    const sp = positions.get(edge.source), tp = positions.get(edge.target);
    if (!sp || !tp) return;
    adjacency.get(edge.source)?.add(edge.target);
    adjacency.get(edge.target)?.add(edge.source);
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', curvePath(sp.x, sp.y, tp.x, tp.y, edge.type));
    path.setAttribute('stroke', edge.type === 'contains' ? 'rgba(13,148,136,.5)' : edge.type === 'explains' ? 'rgba(249,115,22,.42)' : 'rgba(139,92,246,.34)');
    path.setAttribute('stroke-width', edge.type === 'contains' ? '1.4' : '1.15');
    path.setAttribute('fill','none'); path.setAttribute('stroke-linecap','round');
    path.setAttribute('opacity','0.72');
    path.setAttribute('data-edge-id', `${edge.source}->${edge.target}:${idx}`);
    edgeLayer.appendChild(path);
    edgeElMap.set(`${edge.source}->${edge.target}:${idx}`, path);
  });

  // --- Render nodes ---
  const gradientMap = { book:'url(#nodeGradientBook)', chapter:'url(#nodeGradientChapter)', section:'url(#nodeGradientSection)', concept:'url(#nodeGradientConcept)' };

  nodes.forEach(node => {
    const pos = positions.get(node.id);
    if (!pos) return;
    const r = typeRadius[node.type] || 12;
    const g = document.createElementNS(ns, 'g');
    g.setAttribute('transform', `translate(${pos.x} ${pos.y})`);
    g.setAttribute('data-node-id', node.id);
    g.setAttribute('cursor','pointer');

    const glow = document.createElementNS(ns, 'circle');
    glow.setAttribute('r', r * 1.9); glow.setAttribute('fill', typeColors[node.type] || '#94a3b8');
    glow.setAttribute('opacity','0.22'); glow.setAttribute('class','graph-node-glow');

    const core = document.createElementNS(ns, 'circle');
    core.setAttribute('r', r); core.setAttribute('fill', gradientMap[node.type] || gradientMap.concept);
    core.setAttribute('stroke','rgba(255,255,255,.92)'); core.setAttribute('stroke-width','2');
    core.setAttribute('class','graph-node-core');

    const label = document.createElementNS(ns, 'text');
    label.setAttribute('y', r + 18); label.setAttribute('text-anchor','middle');
    label.setAttribute('fill','#475569'); label.setAttribute('font-size', node.type==='book'?'13':node.type==='chapter'?'11':'9');
    label.setAttribute('font-weight','600');
    label.setAttribute('stroke','rgba(255,255,255,.9)'); label.setAttribute('stroke-width','3');
    label.setAttribute('paint-order','stroke'); label.setAttribute('stroke-linejoin','round');
    label.textContent = (node.label || '').slice(0, 10);

    g.appendChild(glow); g.appendChild(core); g.appendChild(label);
    nodeLayer.appendChild(g);
    nodeElMap.set(node.id, g);

    g.addEventListener('click', () => {
      setActiveGraphNode(node.id, { nodeElMap, edgeElMap, adjacency, detailIndex });
      if (node.type === 'chapter' || node.type === 'section') {
        const ref = detailIndex[node.id]?.ref;
        if (ref && ref.chapter_id) {
          // 跳转回阅读器对应位置（navigateToSection 内部会处理视图切换）
          navigateToSection(ref.book_id || TB.currentBookId, ref.chapter_id, ref.anchor);
        }
      }
    });
  });

  // --- Interactions ---
  initGraphInteractionV2(svg, viewport);

  // --- Init default node ---
  const defaultId = data.default_node_id || 'book-core';
  if (nodeElMap.has(defaultId)) {
    setActiveGraphNode(defaultId, { nodeElMap, edgeElMap, adjacency, detailIndex });
  }
}

function buildGraphPositions(nodes, cx, cy, orbitRadius) {
  const posMap = new Map();
  // 按 type:orbit 分组
  const grouped = new Map();
  nodes.forEach(n => {
    const orbit = n.type === 'book' ? 0 : Number(n.orbit || n.depth || 1);
    const key = `${n.type || 'node'}:${orbit}`;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key).push(n);
  });

  // 节点半径映射
  const typeR = { book: 52, chapter: 26, section: 16, concept: 11 };

  grouped.forEach((items, key) => {
    const [nodeType, orbitRaw] = key.split(':');
    const orbit = Number(orbitRaw || 0);

    if (orbit === 0) {
      items.forEach(n => posMap.set(n.id, { x: cx, y: cy }));
      return;
    }

    const total = items.length;
    if (total === 0) return;

    // 根据节点数量动态调整轨道半径，避免拥挤
    // 最小间距 = 节点直径 + 标签偏移 + 间距缓冲
    const nodeR = typeR[nodeType] || 12;
    const minArcGap = (nodeR * 2) + 22;  // 节点直径 + 间距缓冲
    const minCircumference = minArcGap * total;
    const minRadius = minCircumference / (2 * Math.PI);
    const baseRadius = orbitRadius[orbit] || 240;
    // 取基础半径和最小半径中的较大值，给一点额外余量
    const adjustedRadius = Math.max(baseRadius, minRadius + 20);

    // 按后端 angle 排序，但重新均匀分配角度避免重叠
    const sorted = [...items].sort((a, b) => {
      const aa = Number(a.angle) || 0, ba = Number(b.angle) || 0;
      return aa - ba;
    });

    // 均匀分布角度：chapter 从 -90° 开始
    const startAngle = nodeType === 'chapter' ? -90 : 0;
    const step = 360 / total;

    sorted.forEach((n, i) => {
      // 统一使用均匀分布角度，不再信任后端的 angle 序号
      const angle = startAngle + step * i;
      const rad = ((angle - 90) * Math.PI) / 180;
      // chapter 节点交错偏移，避免与 section 对齐
      const radialJitter = nodeType === 'chapter' ? ((i % 2 === 0 ? 1 : -1) * 10) : 0;
      const r = adjustedRadius + radialJitter;
      posMap.set(n.id, { x: cx + Math.cos(rad) * r, y: cy + Math.sin(rad) * r });
    });
  });

  return posMap;
}

function curvePath(x1, y1, x2, y2, edgeType) {
  const mx = (x1+x2)/2, my = (y1+y2)/2;
  const dx = x2-x1, dy = y2-y1;
  const len = Math.max(Math.sqrt(dx*dx+dy*dy), 1);
  const cf = edgeType === 'contains' ? 0.08 : edgeType === 'explains' ? 0.14 : 0.18;
  const ox = -dy/len*len*cf, oy = dx/len*len*cf;
  return `M ${x1} ${y1} Q ${mx+ox} ${my+oy} ${x2} ${y2}`;
}

function setActiveGraphNode(nodeId, ctx) {
  const { nodeElMap, edgeElMap, adjacency, detailIndex } = ctx;
  const neighbors = adjacency.get(nodeId) || new Set();

  nodeElMap.forEach((el, id) => {
    const active = id === nodeId, linked = neighbors.has(id);
    el.style.opacity = (active || linked) ? '1' : '0.35';
    // Glow pulse for active
    const glow = el.querySelector('.graph-node-glow');
    if (glow) glow.setAttribute('opacity', active ? '0.5' : '0.22');
  });

  edgeElMap.forEach((el, eid) => {
    const [srcTgt] = eid.split(':');
    const [src, tgt] = srcTgt.split('->');
    const hl = src === nodeId || tgt === nodeId;
    el.setAttribute('opacity', hl ? '1' : '0.14');
    if (hl) el.setAttribute('stroke-width', '2');
    else el.setAttribute('stroke-width', '1');
  });

  showGraphNodeDetail(nodeId);
}

function initGraphInteractionV2(svg, viewport) {
  const state = { scale:1, x:0, y:0, dragging:false, sx:0, sy:0 };
  const render = () => viewport.setAttribute('transform', `translate(${state.x} ${state.y}) scale(${state.scale})`);
  const clamp = v => Math.min(2.4, Math.max(0.65, v));

  svg.addEventListener('wheel', e => {
    e.preventDefault();
    state.scale = clamp(state.scale * (e.deltaY < 0 ? 1.08 : 0.92));
    render();
  }, { passive: false });

  svg.addEventListener('pointerdown', e => {
    if (e.target.closest('[data-node-id]')) return;
    state.dragging = true; state.sx = e.clientX - state.x; state.sy = e.clientY - state.y;
    svg.setPointerCapture(e.pointerId);
  });
  svg.addEventListener('pointermove', e => {
    if (!state.dragging) return;
    state.x = e.clientX - state.sx; state.y = e.clientY - state.sy; render();
  });
  const end = e => { state.dragging = false; if (e?.pointerId !== undefined && svg.hasPointerCapture(e.pointerId)) svg.releasePointerCapture(e.pointerId); };
  svg.addEventListener('pointerup', end);
  svg.addEventListener('pointerleave', end);
  svg.addEventListener('dblclick', e => { if (e.target.closest('[data-node-id]')) return; state.scale=1; state.x=0; state.y=0; render(); });
  render();
}

function showGraphNodeDetail(nodeId) {
  if (!TB.graphData?.detail_index) return;
  const detail = TB.graphData.detail_index[nodeId];
  if (!detail) return;

  const typeLabels = { book: '核心星核', chapter: '章节轨道', section: '小节站点', concept: '概念星体' };
  document.getElementById('tb-gd-type').textContent = detail.type || '--';
  document.getElementById('tb-gd-label').textContent = detail.label || '--';
  document.getElementById('tb-gd-desc').textContent = detail.description || detail.summary || '';
  document.getElementById('tb-gd-meta').textContent = detail.chapter ? `所属章节: ${detail.chapter}` : `类型: ${typeLabels[detail.type] || detail.type}`;

  // 关联节点
  const linkedEl = document.getElementById('tb-graph-linked');
  const linked = detail.linked_nodes || [];
  const typeColorMap = { book: '#0D9488', chapter: '#F97316', section: '#3B82F6', concept: '#8B5CF6' };
  if (linked.length) {
    linkedEl.innerHTML = linked.map(n => `
      <div class="flex items-center gap-2 p-2 rounded-lg bg-white border border-slate-100 cursor-pointer hover:border-teal-200" onclick="focusGraphNode('${n.id}')">
        <span class="w-2 h-2 rounded-full shrink-0" style="background:${typeColorMap[n.type] || '#94a3b8'}"></span>
        <span class="text-xs text-slate-700 truncate">${escHtml(n.label || '')}</span>
        <span class="text-[10px] text-slate-400 ml-auto shrink-0">${n.type}</span>
      </div>
    `).join('');
  } else {
    linkedEl.innerHTML = '<span class="text-xs text-slate-400">无直接关联节点</span>';
  }
}

function focusGraphNode(nodeId) {
  // Re-render graph and focus node (simplified - just update detail)
  showGraphNodeDetail(nodeId);
}

// ==================== 工具函数 ====================

function escHtml(v) {
  return String(v||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function escAttr(v) {
  return String(v||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function safeId(anchor) {
  if (!anchor) return 'anchor-empty';
  return 'tb-' + anchor.replace(/[^a-zA-Z0-9\u4e00-\u9fff_-]/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '');
}

function scrollToSection(anchor) {
  if (!anchor) return;
  // 先尝试按 safeId 查找
  let el = document.getElementById(safeId(anchor));
  // 再尝试按 data-raw-anchor 属性查找
  if (!el) el = document.querySelector(`[data-raw-anchor="${CSS.escape(anchor)}"]`);
  // 最后尝试原始 id
  if (!el) {
    try { el = document.getElementById(anchor); } catch(e) {}
  }
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.style.transition = 'background 0.3s';
    el.style.background = 'rgba(13,148,136,0.08)';
    setTimeout(() => { el.style.background = ''; }, 1500);
  }
}

function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2500);
}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
  // 当页面切换到 textbook 时加载
  const origShowPage = window.showPage;
  window.showPage = function(page) {
    origShowPage(page);
    if (page === 'textbook') {
      loadBookList();
    }
  };
});
