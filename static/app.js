// static/app.js

let currentConversationId = null;
let abortController = null;
let isGenerating = false;
let currentAiMessageElement = null;
let _allReferencesData = []; // 用于存储当前回答的全部引用数据
let _referencesMap = {}; // 用于快速查找引用：ref_index -> ref 对象

// 清理 theory source 字段的冗余后缀
function cleanTheorySource(source) {
    if (!source) return source;
    return source
        .replace(/思想道德与法治.*/, '思想道德与法治')
        .replace(/毛泽东思想和中国特色社会主义理论体系概论.*/, '毛泽东思想和中国特色社会主义理论体系概论')
        .replace(/新时代中国特色社会主义思想概论.*/, '新时代中国特色社会主义思想概论');
}

// 更新引用高亮信息（阶段二完成后调用）
function updateReferencesHighlight(highlightsData) {
    // highlightsData = [{ref_index: 0, highlights: [...]}, ...]
    for (const item of highlightsData) {
        const idx = item.ref_index;
        if (_allReferencesData[idx]) {
            _allReferencesData[idx].highlights = item.highlights;
            // 同时更新卡片中的高亮显示
            const cardId = `ref_card_${idx}`;
            const card = document.getElementById(cardId);
            if (card) {
                // 重新渲染该卡片的高亮内容
                const ref = _allReferencesData[idx];
                const highlightedHtml = buildHighlightedContent(ref.full_content || ref.content || '', ref.highlights);
                const contentDiv = card.querySelector('.ref-content-preview');
                if (contentDiv) {
                    contentDiv.innerHTML = highlightedHtml;
                }
            }
        }
    }
    // 显示"黄色为对话引用处"提示
    const highlightTip = document.getElementById('highlight-tip');
    if (highlightTip) {
        highlightTip.classList.remove('hidden');
    }
}

lucide.createIcons();

const textarea = document.getElementById('user-input');
const chatContainer = document.getElementById('chat-container');
const messageList = document.getElementById('message-list');
const welcomeScreen = document.getElementById('welcome-screen');
const loadingIndicator = document.getElementById('loading-indicator');
const loadingText = loadingIndicator.querySelector('span');
const bottomAnchor = document.getElementById('bottom-anchor');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');

// 监听回车发送
textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSendClick();
    }
});

// 点击发送按钮
function handleSendClick() {
    const text = textarea.value.trim();
    if (!text) return;
    
    sendQuery(text);
    textarea.value = '';
    textarea.style.height = 'auto'; // 重置高度
}

// 更新停止按钮状态
function updateStopButton(show) {
    if (show && isGenerating) {
        sendBtn.classList.add('hidden');
        stopBtn.classList.remove('hidden');
    } else {
        sendBtn.classList.remove('hidden');
        stopBtn.classList.add('hidden');
    }
}

// 停止生成
function stopGeneration() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    isGenerating = false;
    updateStopButton(false);
    loadingIndicator.classList.add('hidden');
    
    if (currentAiMessageElement) {
        const messageWrapper = currentAiMessageElement.closest('.flex-col');
        if (messageWrapper) {
            messageWrapper.remove();
        }
        currentAiMessageElement = null;
    }
}

// 核心发送函数
async function sendQuery(text) {
    // UI 状态更新
    welcomeScreen.classList.add('hidden');
    messageList.classList.remove('hidden');

    appendMessage('user', text);
    scrollToBottom(true);

    const aiContentDiv = appendMessage('assistant', '');
    currentAiMessageElement = aiContentDiv;
    
    loadingIndicator.classList.remove('hidden');
    loadingText.innerText = "AI正在分析问题...";
    scrollToBottom(true);

    abortController = new AbortController();
    isGenerating = true;
    updateStopButton(true);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                query: text,
                conversation_id: currentConversationId 
            }),
            signal: abortController.signal  // 添加中止信号
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = ""; 

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.replace('data: ', '');
                    if (jsonStr.trim() === '') continue;

                    try {
                        const data = JSON.parse(jsonStr);

                        // 【核心修改】在更新内容前，先判断用户当前是否在底部
                        // 阈值设为 100px：如果距离底部小于 100px，就认为是"正在跟随"
                        // chatContainer 是我们在 index.html 定义的滚动区域
                        const isUserAtBottom = (chatContainer.scrollHeight - chatContainer.scrollTop - chatContainer.clientHeight) < 150;

                        if (data.type === 'token' || data.type === 'content') {
                            loadingIndicator.classList.add('hidden');
                            const newContent = data.content || data.chunk || "";
                            fullText += newContent;
                            
                            // 兼容新旧版本 marked：新版 marked.parse()，旧版直接 marked()
                            if (typeof marked !== 'undefined' && marked.parse) {
                                aiContentDiv.innerHTML = marked.parse(fullText);
                            } else if (typeof marked === 'function') {
                                aiContentDiv.innerHTML = marked(fullText);
                            } else {
                                aiContentDiv.innerHTML = fullText.replace(/\n/g, '<br>');
                            }
                            
                            // 【核心修改】只有当用户原本就在底部时，才自动滚动
                            if (isUserAtBottom) {
                                scrollToBottom(false); // false 表示流式输出时不强制 smooth，避免抖动
                            }
                        }
                        else if (data.type === 'clear') {
                            fullText = ""; 
                            aiContentDiv.innerHTML = ""; 
                            loadingIndicator.classList.remove('hidden');
                            loadingText.innerText = "正在修正回复...";
                            // 修正回复时通常希望用户看到，可以强制滚一下
                            scrollToBottom(true);
                        }
                        else if (data.type === 'thinking') {
                            loadingText.innerText = data.content;
                            if (isUserAtBottom) scrollToBottom(false);
                        }
                        else if (data.type === 'meta') {
                            currentConversationId = data.conversation_id;
                            loadHistory(); 
                        }
                        else if (data.type === 'references') {
                            renderReferences(aiContentDiv, data.data);
                            if (isUserAtBottom) scrollToBottom(true);
                        }
                        else if (data.type === 'references_highlight') {
                            // 阶段二：更新高亮信息（后台异步完成）
                            updateReferencesHighlight(data.data);
                            if (isUserAtBottom) scrollToBottom(false);
                        }
                        else if (data.type === 'done') {
                            loadingIndicator.classList.add('hidden');
                            // 用最终答案重新渲染，确保 validator 修正版本也能正确显示
                            if (data.final_answer) {
                                if (typeof marked !== 'undefined' && marked.parse) {
                                    aiContentDiv.innerHTML = marked.parse(data.final_answer);
                                } else {
                                    aiContentDiv.innerHTML = data.final_answer.replace(/\n/g, '<br>');
                                }
                            }
                            isGenerating = false;
                            updateStopButton(false);
                            currentAiMessageElement = null;
                            loadHistory(); 
                            if (data.chips && data.chips.length > 0) {
                                renderChips(aiContentDiv, data.chips);
                                if (isUserAtBottom) scrollToBottom(true);
                            }
                        }
                        else if (data.type === 'error') {
                            aiContentDiv.innerHTML += `<br><span class="text-red-500">错误: ${data.content}</span>`;
                            isGenerating = false;
                            updateStopButton(false);
                            currentAiMessageElement = null;
                        }

                    } catch (e) {
                        console.error("JSON Parse Error", e, jsonStr);
                    }
                }
            }
        }

    } catch (error) {
        loadingIndicator.classList.add('hidden');
        isGenerating = false;
        updateStopButton(false);
        
        if (error.name === 'AbortError') {
            // 用户主动中止，不显示错误
            console.log('Generation aborted by user');
        } else {
            aiContentDiv.innerHTML += `<br><span class="text-red-500">网络连接异常: ${error.message}</span>`;
            console.error(error);
        }
    }
}

// 渲染推荐追问 Chips
function renderChips(aiContentDiv, chips) {
    const chipsHtml = `
    <div class="mt-3 flex flex-wrap gap-2 animate-fade-in">
        ${chips.map(chip => `
            <button onclick="sendQuery('${chip}')" class="text-xs md:text-sm px-3 py-1.5 bg-rose-50 text-rose-700 rounded-full border border-rose-100 hover:bg-rose-100 cursor-pointer transition-colors">
                ${chip}
            </button>
        `).join('')}
    </div>`;
    const bubbleContainer = aiContentDiv.closest('.flex-col');
    if (bubbleContainer) {
        bubbleContainer.insertAdjacentHTML('beforeend', chipsHtml);
    }
}

// 渲染引用文献区域
function renderReferences(aiContentDiv, references) {
    if (!references || references.length === 0) return;
    
    const bubbleContainer = aiContentDiv.closest('.flex-col');
    if (!bubbleContainer) return;
    
    // 存储到全局变量，供"查看全部"按钮使用
    _allReferencesData = references;
    _referencesMap = {};
    
    const html = `
    <div class="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-fade-in">
        <div class="flex items-center gap-2 mb-3">
            <i data-lucide="book-open" class="w-5 h-5 text-rose-500"></i>
            <span class="font-semibold text-slate-700">参考资料 (${references.length})</span>
        </div>
        <div id="highlight-tip" class="hidden text-xs text-yellow-600 mb-2 px-2 py-1 bg-yellow-50 rounded">
            💡 黄色为对话引用处
        </div>
        <div class="space-y-2">
            ${references.slice(0, 2).map((ref, idx) => renderReferenceCard(ref, idx)).join('')}
            ${references.length > 2 ? `
                <button onclick="showAllReferences()" class="w-full text-center py-2 text-sm text-rose-600 hover:bg-rose-50 rounded-lg transition-colors">
                    查看全部 ${references.length} 条
                </button>
            ` : ''}
        </div>
    </div>
    `;
    bubbleContainer.insertAdjacentHTML('beforeend', html);
    lucide.createIcons();
}

// 渲染单条引用卡片
function renderReferenceCard(ref, idx) {
    const refId = `ref_${Date.now()}_${idx}`;
    window[refId] = ref;
    const mergeTag = ref.chunk_count > 1 ? ` <span class="text-xs text-slate-400">合并${ref.chunk_count}片段</span>` : '';
    
    if (ref.type === 'moment') {
        return `
            <div id="ref_card_${idx}" class="p-3 bg-white rounded-lg border border-slate-100 hover:border-rose-200 transition-colors cursor-pointer"
                 onclick="showReferenceDetail(window['${refId}'])">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xs bg-blue-100 text-blue-600 px-2 py-0.5 rounded font-medium">📰 时政</span>
                            <div class="text-sm font-medium text-slate-800 line-clamp-1">${ref.title}</div>
                            ${mergeTag}
                        </div>
                        <div class="text-xs text-slate-500 mt-0.5">${ref.source} · ${ref.date}</div>
                        <div class="text-xs text-slate-400 mt-1 line-clamp-2 ref-content-preview">"${ref.content.substring(0, 60)}..."</div>
                    </div>
                    <div class="text-xs text-rose-500 font-medium ml-2 flex-shrink-0">${ref.score}%</div>
                </div>
            </div>
        `;
    } else {
        const displaySource = cleanTheorySource(ref.source);
        return `
            <div id="ref_card_${idx}" class="p-3 bg-white rounded-lg border border-slate-100 hover:border-rose-200 transition-colors cursor-pointer"
                 onclick="showReferenceDetail(window['${refId}'])">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 flex-wrap">
                            <span class="text-xs bg-rose-100 text-rose-600 px-2 py-0.5 rounded font-medium">📖 理论</span>
                            <div class="text-sm font-medium text-slate-800 line-clamp-1">${displaySource}</div>
                            ${mergeTag}
                        </div>
                        <div class="text-xs text-slate-500 mt-0.5">${ref.chapter}${ref.section ? ' · ' + ref.section : ''}</div>
                        <div class="text-xs text-slate-400 mt-1 line-clamp-2 ref-content-preview">"${ref.content.substring(0, 60)}..."</div>
                    </div>
                    <div class="text-xs text-rose-500 font-medium ml-2 flex-shrink-0">${ref.score}%</div>
                </div>
            </div>
        `;
    }
}
    
// 高亮辅助函数：在原文中高亮引用片段，格式为 ……前文（高亮）后文……
function buildHighlightedContent(fullContent, highlights) {
    if (!highlights || highlights.length === 0) {
        return `<span>${escapeHtml(fullContent)}</span>`;
    }

    // 找出所有高亮片段在原文中的位置，构建带省略号的展示
    let result = fullContent;
    let markedResult = escapeHtml(fullContent);

    highlights.forEach(h => {
        if (!h || h.length < 4) return;
        const escapedH = escapeHtml(h);
        if (markedResult.includes(escapedH)) {
            markedResult = markedResult.replace(
                escapedH,
                `<mark class="bg-yellow-200 text-yellow-900 rounded px-0.5">${escapedH}</mark>`
            );
        }
    });

    return markedResult;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// 下载原文（修复：将 a 元素插入 DOM 再触发）
function downloadReference(refId) {
    const ref = window[refId];
    if (!ref) return;
    
    // 显示加载提示
    const btn = event.target.closest('button');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ 正在生成...';
    btn.disabled = true;
    
    fetch('/api/reference/download', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(ref)
    }).then(r => {
        if (!r.ok) throw new Error('下载请求失败');
        return r.blob();
    }).then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = ref.type === 'moment'
            ? `${ref.title.substring(0, 20)}.docx`
            : `${cleanTheorySource(ref.source).substring(0, 15)}.docx`;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 200);
    }).catch(e => {
        console.error('下载失败', e);
        alert('下载失败，请重试');
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

// 显示引用详情模态框
function showReferenceDetail(ref) {
    const modal = document.getElementById('reference-modal');
    const content = document.getElementById('reference-modal-content');
    
    // 为下载按钮生成唯一 ID
    const dlId = `dl_${Date.now()}`;
    window[dlId] = ref;

    // 渲染高亮原文
    const fullText = ref.full_content || ref.content || '';
    const highlightedHtml = buildHighlightedContent(fullText, ref.highlights || []);
    const hasHighlights = ref.highlights && ref.highlights.length > 0;

    const downloadBtn = `
        <button onclick="downloadReference('${dlId}')" class="flex items-center gap-1 text-xs text-rose-600 hover:text-rose-700 border border-rose-200 hover:bg-rose-50 px-3 py-1.5 rounded-lg transition-colors">
            ⬇ 下载原文
        </button>`;

    let html = '';
    if (ref.type === 'moment') {
        html = `
            <div class="space-y-4">
                <div class="flex items-start justify-between">
                    <div>
                        <h4 class="text-sm font-semibold text-slate-600 mb-1">📰 新闻标题</h4>
                        <p class="text-base font-medium text-slate-800">${ref.title}</p>
                    </div>
                    ${downloadBtn}
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div><p class="text-xs text-slate-500 mb-1">发布日期</p><p class="text-sm font-medium text-slate-700">${ref.date}</p></div>
                    <div><p class="text-xs text-slate-500 mb-1">新闻来源</p><p class="text-sm font-medium text-slate-700">${ref.source}</p></div>
                </div>
                ${ref.keywords && ref.keywords.length > 0 ? `
                    <div>
                        <p class="text-xs text-slate-500 mb-2">🏷️ 关键词</p>
                        <div class="flex flex-wrap gap-2">${ref.keywords.map(kw => `<span class="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded">${kw}</span>`).join('')}</div>
                    </div>` : ''}
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-xs text-slate-500">📝 新闻片段${hasHighlights ? ' <span class="text-yellow-600">（黄色为对话引用处）</span>' : ''}</p>
                    </div>
                    <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 max-h-64 overflow-y-auto text-sm text-slate-700 leading-relaxed">${highlightedHtml}</div>
                </div>
                <div class="pt-2 border-t border-slate-200">
                    <p class="text-xs text-slate-500">📊 相关度：<span class="font-semibold text-rose-500">${ref.score}%</span>${ref.chunk_count > 1 ? ` · 合并了 ${ref.chunk_count} 个相关片段` : ''}</p>
                </div>
            </div>`;
    } else {
        const displaySource = cleanTheorySource(ref.source);
        const location = [ref.chapter, ref.section, ref.subsection, ref.subsubsection].filter(Boolean).join(' / ');
        html = `
            <div class="space-y-4">
                <div class="flex items-start justify-between">
                    <div>
                        <h4 class="text-sm font-semibold text-slate-600 mb-1">📚 文献来源</h4>
                        <p class="text-base font-medium text-slate-800">《${displaySource}》</p>
                    </div>
                    ${downloadBtn}
                </div>
                <div>
                    <p class="text-xs text-slate-500 mb-2">📍 章节定位</p>
                    <div class="text-sm text-slate-700 space-y-1">
                        ${ref.chapter ? `<div>• ${ref.chapter}</div>` : ''}
                        ${ref.section ? `<div class="ml-4">└─ ${ref.section}</div>` : ''}
                        ${ref.subsection ? `<div class="ml-8">└─ ${ref.subsection}</div>` : ''}
                        ${ref.subsubsection ? `<div class="ml-12">└─ ${ref.subsubsection}</div>` : ''}
                    </div>
                </div>
                ${ref.keywords && ref.keywords.length > 0 ? `
                    <div>
                        <p class="text-xs text-slate-500 mb-2">🏷️ 关键词</p>
                        <div class="flex flex-wrap gap-2">${ref.keywords.map(kw => `<span class="text-xs bg-rose-50 text-rose-600 px-2 py-1 rounded">${kw}</span>`).join('')}</div>
                    </div>` : ''}
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <p class="text-xs text-slate-500">📝 引用片段${hasHighlights ? ' <span class="text-yellow-600">（黄色为对话引用处）</span>' : ''}</p>
                    </div>
                    <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 max-h-64 overflow-y-auto text-sm text-slate-700 leading-relaxed">${highlightedHtml}</div>
                </div>
                <div class="pt-2 border-t border-slate-200">
                    <p class="text-xs text-slate-500">📊 相关度：<span class="font-semibold text-rose-500">${ref.score}%</span>${ref.chunk_count > 1 ? ` · 合并了 ${ref.chunk_count} 个相关片段` : ''}</p>
                </div>
            </div>`;
    }
    
    content.innerHTML = html;
    modal.classList.remove('hidden');
    lucide.createIcons();
}

// 关闭引用详情模态框
function closeReferenceModal() {
    const modal = document.getElementById('reference-modal');
    modal.classList.add('hidden');
}

// 点击模态框外部关闭
document.addEventListener('DOMContentLoaded', function() {
    const modal = document.getElementById('reference-modal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                closeReferenceModal();
            }
        });
    }
});

// 显示全部引用（使用全局变量，避免 onclick 内嵌 JSON）
function showAllReferences() {
    const references = _allReferencesData;
    if (!references || references.length === 0) return;
    
    const modal = document.getElementById('reference-modal');
    const content = document.getElementById('reference-modal-content');
    
    const items = references.map((ref, idx) => {
        const refId = `refAll_${Date.now()}_${idx}`;
        window[refId] = ref;
        const label = ref.type === 'moment' ? '📰 时政' : '📖 理论';
        const labelClass = ref.type === 'moment' ? 'bg-blue-100 text-blue-600' : 'bg-rose-100 text-rose-600';
        const title = ref.type === 'moment' ? ref.title : cleanTheorySource(ref.source);
        const sub = ref.type === 'moment'
            ? `${ref.source} · ${ref.date}`
            : `${ref.chapter}${ref.section ? ' · ' + ref.section : ''}`;
        return `
            <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 cursor-pointer hover:border-rose-200 transition-colors"
                 onclick="showReferenceDetail(window['${refId}'])">
                <div class="flex items-start justify-between">
                    <div class="flex-1">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-medium ${labelClass} px-2 py-0.5 rounded">${label}</span>
                            <span class="text-sm font-medium text-slate-800">${title}</span>
                        </div>
                        <p class="text-xs text-slate-500 mt-1">${sub}</p>
                    </div>
                    <span class="text-xs text-rose-500 font-medium ml-2">${ref.score}%</span>
                </div>
            </div>
        `;
    }).join('');
    
    content.innerHTML = `
        <div class="space-y-3">
            <h4 class="font-semibold text-slate-800 mb-4">全部参考资料 (${references.length})</h4>
            ${items}
        </div>
    `;
    modal.classList.remove('hidden');
    lucide.createIcons();
}

// 渲染消息气泡
function appendMessage(role, content) {
    const isUser = role === 'user';
    const alignClass = isUser ? 'justify-end' : 'justify-start';
    
    const bubbleClass = isUser 
        ? 'gradient-bg text-white rounded-tr-none shadow-orange-500/20' 
        : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none prose max-w-none assistant-bubble';
    
    let initialHtml = content;
    if (!isUser && content) {
        if (typeof marked !== 'undefined' && marked.parse) {
            initialHtml = marked.parse(content);
        } else if (typeof marked === 'function') {
            initialHtml = marked(content);
        }
    }

    const html = `
    <div class="flex w-full ${alignClass} animate-fade-in-up mb-6">
        <div class="flex flex-col max-w-[85%] md:max-w-[75%] ${isUser ? 'items-end' : 'items-start'}">
            <div class="p-4 md:p-5 text-base leading-relaxed shadow-sm rounded-2xl ${bubbleClass}">
                ${initialHtml}
            </div>
            <div class="text-xs text-slate-400 mt-1 px-1">
                ${isUser ? '我' : '思政云伴侣'} • ${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
            </div>
        </div>
    </div>
    `;

    messageList.insertAdjacentHTML('beforeend', html);
    lucide.createIcons();
    
    const lastMessage = messageList.lastElementChild;
    if (isUser) {
        return lastMessage.querySelector('.gradient-bg');
    } else {
        return lastMessage.querySelector('.assistant-bubble');
    }
}

// 滚动到底部 (优化版)
function scrollToBottom(forceSmooth = true) {
    // forceSmooth: true 表示使用平滑滚动（适合用户点击发送时）
    // forceSmooth: false 表示瞬间跳转（适合流式输出时，防止画面抖动）
    if (forceSmooth) {
        bottomAnchor.scrollIntoView({ behavior: 'smooth' });
    } else {
        // 在流式输出高频触发时，直接设置 scrollTop 性能更好且不抖动
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

// 重置对话
function resetChat() {
    // 如果正在生成，先停止
    if (isGenerating) {
        stopGeneration();
    }
    currentConversationId = null;
    messageList.innerHTML = '';
    messageList.classList.add('hidden');
    welcomeScreen.classList.remove('hidden');
    loadingIndicator.classList.add('hidden');
    loadHistory(); 
}

// 加载历史列表
// 加载历史列表 (含 Gemini 同款悬停动画)
async function loadHistory() {
    try {
        // 强制拉取最新数据
        const res = await fetch(`/api/history?t=${new Date().getTime()}`);
        const list = await res.json();
        const container = document.getElementById('history-list');
        
        let html = '<div class="text-xs font-semibold text-slate-400 px-2 mb-2 uppercase tracking-wider">历史对话</div>';
        
        if (list.length === 0) {
            html += '<div class="p-4 text-xs text-slate-300 text-center">暂无历史记录</div>';
        }

        list.forEach(item => {
            const isActive = item.id === currentConversationId;
            
            const activeClass = 'bg-rose-50 text-rose-700 shadow-sm ring-1 ring-rose-100';
            const inactiveClass = 'text-slate-600 hover:bg-slate-200 hover:text-slate-900 transition-all duration-200';
            
            const bgClass = isActive ? activeClass : inactiveClass;
            const iconClass = isActive ? 'text-rose-500' : 'text-slate-400 group-hover:text-slate-600 transition-colors';
            
            const displayTitle = item.title.length > 12 ? item.title.substring(0, 12) + '...' : item.title;

            html += `
                <div class="group/item w-full flex items-center gap-1 mb-1">
                    <button onclick="switchConversation('${item.id}')" class="group flex-1 text-left p-3 rounded-xl text-sm font-medium flex items-center gap-3 ${bgClass}">
                        <i data-lucide="message-square" class="w-4 h-4 ${iconClass}"></i>
                        <div class="flex-1 min-w-0">
                            <div class="truncate">${displayTitle}</div>
                            <div class="text-[10px] opacity-60 font-normal mt-0.5">${item.date}</div>
                        </div>
                    </button>
                    <button onclick="event.stopPropagation(); deleteConversation('${item.id}')" class="opacity-0 group-hover/item:opacity-100 p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-all" title="删除对话">
                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                    </button>
                </div>
            `;
        });
        
        container.innerHTML = html;
        lucide.createIcons();
    } catch(e) {
        console.error("History load failed", e);
    }
}

// 切换会话
async function switchConversation(id) {
    // 如果正在生成，先停止
    if (isGenerating) {
        stopGeneration();
    }
    
    currentConversationId = id;
    loadHistory(); 
    
    messageList.innerHTML = '';
    welcomeScreen.classList.add('hidden');
    messageList.classList.remove('hidden');
    loadingIndicator.classList.add('hidden');
    
    try {
        const res = await fetch(`/api/history/${id}`);
        if (!res.ok) throw new Error("加载详情失败");
        
        const messages = await res.json();
        
        messages.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });
        
        scrollToBottom(true);
        
    } catch (e) {
        console.error("加载历史消息失败:", e);
        messageList.innerHTML = '<div class="p-4 text-center text-red-400 text-sm">加载历史记录失败，请刷新重试</div>';
    }
}

async function deleteConversation(id) {
    if (!confirm('确定要删除这条对话记录吗？')) {
        return;
    }
    
    try {
        const res = await fetch(`/api/history/${id}`, {
            method: 'DELETE'
        });
        
        if (!res.ok) {
            throw new Error('删除失败');
        }
        
        if (currentConversationId === id) {
            resetChat();
        } else {
            loadHistory();
        }
        
    } catch (e) {
        console.error('删除对话失败:', e);
        alert('删除失败，请重试');
    }
}

loadHistory();
