const appState = {
    stage: 'welcome', // welcome | outline_generating | outline_ready | preview_generating | preview_ready | exporting | result
    currentPPTData: null,
    currentOutline: null,
    currentQuery: null,
    abortController: null,
    isGenerating: false,
    selectedTheme: 'party_red',
    currentSessionId: null,
    currentSlideIndex: 0,
    totalSlides: 0,
    isExporting: false,
};

let resizeHandler = null;

const textarea = document.getElementById('user-input');
const welcomeScreen = document.getElementById('welcome-screen');
const progressSection = document.getElementById('progress-section');
const outlineSection = document.getElementById('outline-section');
const resultSection = document.getElementById('result-section');
const generateBtn = document.getElementById('generate-btn');


function setStage(stage) {
    appState.stage = stage;
}

function setGeneratingButtonState(loading, text = '生成PPT') {
    if (!generateBtn) return;

    generateBtn.disabled = loading;
    if (loading) {
        generateBtn.classList.add('opacity-60', 'cursor-not-allowed');
        generateBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>';
    } else {
        generateBtn.classList.remove('opacity-60', 'cursor-not-allowed');
        generateBtn.innerHTML = '<i data-lucide="sparkles" class="w-5 h-5"></i>';
    }
    lucide.createIcons();
}

function setStartPreviewButtonState(loading) {
    const startPreviewBtn = document.getElementById('start-preview-btn');
    if (!startPreviewBtn) return;

    startPreviewBtn.disabled = loading;
    if (loading) {
        startPreviewBtn.innerHTML = '<i data-lucide="loader-2" class="w-5 h-5 animate-spin"></i>正在生成...';
        startPreviewBtn.classList.add('opacity-50', 'cursor-not-allowed');
    } else {
        startPreviewBtn.innerHTML = '<i data-lucide="play" class="w-5 h-5"></i>开始生成预览';
        startPreviewBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    }
    lucide.createIcons();
}

function setExportButtonState(disabled, text = '下载PPT') {
    const exportBtn = document.getElementById('export-ppt-btn');
    if (!exportBtn) return;

    exportBtn.disabled = disabled;

    if (disabled) {
        exportBtn.classList.add('opacity-50', 'cursor-not-allowed');
        exportBtn.innerHTML = `<i data-lucide="download" class="w-5 h-5"></i>${text}`;
    } else {
        exportBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        exportBtn.innerHTML = '<i data-lucide="download" class="w-5 h-5"></i>下载PPT';
    }
    lucide.createIcons();
}

textarea.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleGenerate();
    }
});

function quickStart(query) {
    textarea.value = query;
    textarea.focus();
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
}

function handleGenerate() {
    const text = textarea.value.trim();
    if (!text || appState.isGenerating) return;

    appState.currentQuery = text;
    appState.isGenerating = true;
    setStage('outline_generating');
    setGeneratingButtonState(true);

    generateOutlineStream(text);
    textarea.value = '';
    textarea.style.height = 'auto';
}

function updateSteps(currentStep) {
    const step1 = document.getElementById('step-1');
    const step2 = document.getElementById('step-2');
    const progressBar = document.getElementById('progress-bar');
    const text1 = document.getElementById('step-text-1');
    const text2 = document.getElementById('step-text-2');
    const guideText = document.getElementById('guide-text');
    const guideHint = document.getElementById('guide-hint');
    
    if (currentStep === 1) {
        // 生成大纲阶段
        if (step1) {
            step1.classList.add('active', 'bg-rose-500', 'text-white');
            step1.classList.remove('bg-slate-200', 'text-slate-500');
        }
        if (step2) {
            step2.classList.remove('active', 'bg-rose-500', 'text-white');
            step2.classList.add('bg-slate-200', 'text-slate-500');
        }
        if (progressBar) progressBar.style.width = '0%';
        if (text1) text1.classList.add('text-rose-600', 'font-medium');
        if (text2) text2.classList.remove('text-rose-600', 'font-medium');
        // 更新引导文字
        if (guideText) guideText.textContent = 'AI正在分析您的需求并生成大纲，请稍候...';
        if (guideHint) guideHint.classList.remove('hidden');
    } else if (currentStep === 2) {
        // 预览下载阶段
        if (step1) {
            step1.classList.remove('active', 'bg-rose-500', 'text-white');
            step1.classList.add('bg-green-500', 'text-white');
        }
        if (step2) {
            step2.classList.add('active', 'bg-rose-500', 'text-white');
            step2.classList.remove('bg-slate-200', 'text-slate-500');
        }
        if (progressBar) progressBar.style.width = '100%';
        if (text1) text1.classList.remove('text-rose-600', 'font-medium');
        if (text2) text2.classList.add('text-rose-600', 'font-medium');
        // 更新引导文字
        if (guideText) guideText.textContent = '大纲已生成！您可以编辑大纲后点击"生成预览"查看效果';
        if (guideHint) guideHint.classList.remove('hidden');
    }
}

function dismissGuide() {
    const guideHint = document.getElementById('guide-hint');
    if (guideHint) {
        guideHint.classList.add('hidden');
    }
}

async function generateOutlineStream(query) {
    welcomeScreen.classList.add('hidden');
    progressSection.classList.remove('hidden');
    outlineSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    
    updateSteps(1);
    updateProgress(10, '正在生成大纲，预计还需要 15 秒...');
    
    const chapters = [];
    let chapterCount = 0;
    
    appState.abortController = new AbortController();
    appState.isGenerating = true;
    
    try {
        const response = await fetch('/api/ppt/outline/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query }),
            signal: appState.abortController.signal
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const event = JSON.parse(line.slice(6));
                        
                        if (event.type === 'start') {
                            updateProgress(10, `开始生成: ${event.topic}`);
                        } else if (event.type === 'chapter_start') {
                            chapterCount++;
                            const progress = 10 + (chapterCount - 1) * 15;
                            updateProgress(progress, `正在生成第 ${event.chapter_index} 章: ${event.chapter_title}`);
                        } else if (event.type === 'chapter_done') {
                            chapters.push(event.chapter);
                            const progress = 10 + chapterCount * 15;
                            updateProgress(progress, `第 ${event.chapter.chapter_index} 章完成`);
                        } else if (event.type === 'done') {
                            appState.currentOutline = event.outline;
                            appState.isGenerating = false;
                            setGeneratingButtonState(false);
                            setStage('outline_ready');
                            updateProgress(100, '大纲生成完成！');
                            
                            setTimeout(() => {
                                progressSection.classList.add('hidden');
                                showOutlineEditor(appState.currentOutline);
                            }, 500);
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        appState.isGenerating = false;
        setGeneratingButtonState(false);
        if (error.name === 'AbortError') {
            console.log('Generation cancelled');
            resetPage();
        } else {
            progressSection.classList.add('hidden');
            showError(error.message);
        }
    }
}

function cancelGeneration() {
    if (appState.abortController) {
        appState.abortController.abort();
        appState.abortController = null;
    }
    appState.isGenerating = false;
    setGeneratingButtonState(false);
    setStage('welcome');
    resetPage();
}

function updateProgress(percent, text) {
    const progressLine = document.getElementById('progress-bar-line');
    const progressText = document.getElementById('progress-text');
    const progressPercent = document.getElementById('progress-percent');
    const node1 = document.getElementById('progress-node-1');
    const node2 = document.getElementById('progress-node-2');
    const node3 = document.getElementById('progress-node-3');
    
    if (progressText) progressText.textContent = text;
    if (progressPercent) progressPercent.textContent = `${Math.round(percent)}%`;

    // 使用完整进度条，避免 0-50% 的映射混乱
    const linePercent = Math.min(Math.max(percent, 0), 100);
    if (progressLine) progressLine.style.width = `${linePercent}%`;
    
    if (percent >= 0) {
        if (node1) {
            node1.classList.remove('bg-slate-300');
            node1.classList.add('bg-rose-500');
        }
    }
    if (percent >= 50) {
        if (node2) {
            node2.classList.remove('bg-slate-300');
            node2.classList.add('bg-rose-500');
        }
    }
    if (percent >= 100) {
        if (node3) {
            node3.classList.remove('bg-slate-300', 'bg-slate-400');
            node3.classList.add('bg-rose-500');
        }
    }
}

function showOutlineEditor(outline) {
    const modal = document.getElementById('outline-modal');
    const editor = document.getElementById('outline-editor');
    
    editor.innerHTML = `
        <div class="mb-4 p-4 bg-gradient-to-r from-rose-50 to-orange-50 rounded-xl border border-rose-100">
            <div class="flex items-center gap-2 mb-3">
                <i data-lucide="message-circle" class="w-5 h-5 text-rose-500"></i>
                <span class="font-semibold text-slate-700">对大纲不满意？在这里提出修改需求</span>
            </div>
            <textarea id="outline-feedback" rows="2" 
                placeholder="例如：增加一个关于XX的章节、删除第三章、把第二章的内容合并到第一章..."
                class="w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:border-rose-500 focus:outline-none focus:ring-2 focus:ring-rose-200 resize-none"></textarea>
            <button onclick="regenerateOutline()" class="mt-3 w-full py-2.5 px-4 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-xl font-medium hover:shadow-lg transition-all flex items-center justify-center gap-2">
                <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                按需求重新生成大纲
            </button>
        </div>
        
        <div class="flex items-center justify-between mb-3">
            <span class="font-semibold text-slate-700">当前大纲结构</span>
            <button onclick="addNewChapter()" class="text-sm text-rose-600 hover:text-rose-700 flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-rose-50 transition-colors font-medium">
                <i data-lucide="plus" class="w-4 h-4"></i>
                添加章节
            </button>
        </div>
        
        <div id="chapters-container">
            ${outline.chapters.map((chapter, cIdx) => `
                <div class="chapter-block border border-slate-200 rounded-xl p-4 mb-4 bg-slate-50/50" data-chapter-idx="${cIdx}">
                    <div class="flex items-center gap-2 mb-3">
                        <span class="text-sm font-semibold text-rose-600 bg-rose-100 px-3 py-1 rounded-lg">第 ${chapter.chapter_index} 章</span>
                        <input type="text" value="${chapter.chapter_title}" 
                            class="flex-1 text-lg font-bold border-b-2 border-transparent hover:border-slate-300 focus:border-rose-500 focus:outline-none px-2 py-1 bg-transparent chapter-title" 
                            data-chapter="${cIdx}" data-field="title"
                            placeholder="章节标题">
                        <button onclick="deleteChapter(${cIdx})" class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="删除此章节">
                            <i data-lucide="trash-2" class="w-4 h-4"></i>
                        </button>
                    </div>
                    
                    <div class="slides-container space-y-2">
                        ${chapter.slides.map((slide, sIdx) => `
                            <div class="slide-block bg-white rounded-lg p-3 border border-slate-100" data-slide-idx="${sIdx}">
                                <div class="flex items-start gap-2">
                                    <div class="flex-1">
                                        <input type="text" value="${slide.title}" 
                                            class="w-full text-sm font-medium border-none bg-transparent focus:ring-0 mb-2 focus:outline-none text-slate-700 slide-title"
                                            data-chapter="${cIdx}" data-slide="${sIdx}" data-field="slide-title"
                                            placeholder="幻灯片标题">
                                        
                                        <div class="bullets-container space-y-1.5">
                                            ${slide.bullets.map((bullet, bIdx) => `
                                                <div class="bullet-row flex items-center gap-2">
                                                    <span class="text-slate-400 text-xs">•</span>
                                                    <input type="text" value="${bullet}" 
                                                        class="flex-1 text-xs border border-slate-200 rounded-lg px-3 py-1.5 focus:border-rose-500 focus:outline-none focus:ring-1 focus:ring-rose-200 bullet-input"
                                                        data-chapter="${cIdx}" data-slide="${sIdx}" data-bullet="${bIdx}"
                                                        placeholder="要点内容">
                                                    <button onclick="deleteBullet(${cIdx}, ${sIdx}, ${bIdx})" class="p-1 text-slate-300 hover:text-red-500 rounded transition-colors">
                                                        <i data-lucide="x" class="w-3 h-3"></i>
                                                    </button>
                                                </div>
                                            `).join('')}
                                        </div>
                                        <button onclick="addBullet(${cIdx}, ${sIdx})" class="mt-2 text-xs text-slate-400 hover:text-rose-500 flex items-center gap-1 transition-colors">
                                            <i data-lucide="plus" class="w-3 h-3"></i>
                                            添加要点
                                        </button>
                                    </div>
                                    <button onclick="deleteSlide(${cIdx}, ${sIdx})" class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors flex-shrink-0" title="删除此幻灯片">
                                        <i data-lucide="trash-2" class="w-4 h-4"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                    <button onclick="addSlide(${cIdx})" class="mt-3 text-sm text-slate-500 hover:text-rose-600 flex items-center gap-1.5 px-3 py-2 rounded-lg hover:bg-rose-50 transition-colors border border-dashed border-slate-300 hover:border-rose-300 w-full justify-center">
                        <i data-lucide="plus" class="w-4 h-4"></i>
                        添加幻灯片
                    </button>
                </div>
            `).join('')}
        </div>
    `;
    
    modal.classList.remove('hidden');
    lucide.createIcons();
}

function showOutline(outline) {
    if (!outline || !outline.chapters) return;
    
    appState.currentOutline = outline;
    outlineSection.classList.remove('hidden');
    
    const outlineContent = document.getElementById('outline-content');
    outlineContent.innerHTML = outline.chapters.map((chapter, idx) => `
        <div class="border-l-4 border-rose-300 pl-4 py-2 bg-slate-50 rounded-r-lg">
            <div class="font-semibold text-slate-800 flex items-center gap-2">
                <span class="w-6 h-6 rounded-full bg-rose-100 text-rose-600 text-xs flex items-center justify-center font-bold">${chapter.chapter_index || idx + 1}</span>
                ${chapter.chapter_title}
            </div>
            ${chapter.slides ? chapter.slides.map(sub => `
                <div class="ml-8 text-sm text-slate-600 mt-2 flex items-start gap-2">
                    <i data-lucide="chevron-right" class="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5"></i>
                    <span>${sub.title}</span>
                </div>
            `).join('') : ''}
        </div>
    `).join('');
    
    lucide.createIcons();
}

function closeOutlineModal() {
    const modal = document.getElementById('outline-modal');
    modal.classList.add('hidden');
}

async function confirmOutline() {
    const editedOutline = collectOutlineData();
    appState.currentOutline = editedOutline;
    
    closeOutlineModal();
    
    outlineSection.classList.remove('hidden');
    
    const outlineContent = document.getElementById('outline-content');
    outlineContent.innerHTML = appState.currentOutline.chapters.map((chapter, idx) => `
        <div class="border-l-4 border-rose-300 pl-4 py-2 bg-slate-50 rounded-r-lg">
            <div class="font-semibold text-slate-800 flex items-center gap-2">
                <span class="w-6 h-6 rounded-full bg-rose-100 text-rose-600 text-xs flex items-center justify-center font-bold">${chapter.chapter_index || idx + 1}</span>
                ${chapter.chapter_title}
            </div>
            ${chapter.slides ? chapter.slides.map(sub => `
                <div class="ml-8 text-sm text-slate-600 mt-2 flex items-start gap-2">
                    <i data-lucide="chevron-right" class="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5"></i>
                    <span>${sub.title}</span>
                </div>
            `).join('') : ''}
        </div>
    `).join('');
    
    lucide.createIcons();
    updateSteps(1);
}

function collectOutlineData() {
    const chapters = [];
    const chapterElements = document.querySelectorAll('[data-chapter]');
    
    const chapterMap = new Map();
    
    chapterElements.forEach(el => {
        const cIdx = parseInt(el.dataset.chapter);
        const sIdx = el.dataset.slide !== undefined ? parseInt(el.dataset.slide) : null;
        const bIdx = el.dataset.bullet !== undefined ? parseInt(el.dataset.bullet) : null;
        const field = el.dataset.field;
        
        if (!chapterMap.has(cIdx)) {
            chapterMap.set(cIdx, { 
                chapter_index: cIdx + 1, 
                chapter_title: '', 
                slides: [] 
            });
        }
        
        const chapter = chapterMap.get(cIdx);
        
        if (field === 'title') {
            chapter.chapter_title = el.value;
        } else if (field === 'slide-title') {
            while (chapter.slides.length <= sIdx) {
                chapter.slides.push({ title: '', bullets: [] });
            }
            chapter.slides[sIdx].title = el.value;
        } else if (bIdx !== null) {
            while (chapter.slides.length <= sIdx) {
                chapter.slides.push({ title: '', bullets: [] });
            }
            while (chapter.slides[sIdx].bullets.length <= bIdx) {
                chapter.slides[sIdx].bullets.push('');
            }
            chapter.slides[sIdx].bullets[bIdx] = el.value;
        }
    });
    
    chapterMap.forEach(chapter => chapters.push(chapter));
    
    return {
        title: appState.currentOutline?.title || appState.currentQuery,
        chapters: chapters
    };
}

function showResult(result) {
    resultSection.classList.remove('hidden');
    
    const title = result.title || appState.currentOutline?.title || 'PPT';
    const pptId = result.ppt_id;
    const downloadUrl = result.download_url;
    
    appState.currentPPTData = result;
    
    const resultInfo = document.getElementById('result-info');
    resultInfo.innerHTML = `
        <div class="flex items-center gap-4 mb-5">
            <div class="w-14 h-14 rounded-2xl gradient-bg flex items-center justify-center shadow-lg shadow-rose-500/20">
                <i data-lucide="presentation" class="w-7 h-7 text-white"></i>
            </div>
            <div class="flex-1">
                <div class="font-bold text-slate-800 text-lg">${title}</div>
                <div class="text-sm text-slate-500 mt-1">PPT 已生成完成，点击下载或预览</div>
            </div>
        </div>
        
        <div class="flex gap-3">
            <button onclick="previewPPT('${pptId}')" class="flex-1 py-3 px-4 bg-gradient-to-r from-blue-500 to-cyan-500 text-white rounded-xl font-medium text-center hover:shadow-lg transition-all flex items-center justify-center gap-2">
                <i data-lucide="play-circle" class="w-5 h-5"></i>
                在线预览
            </button>
            <a href="${downloadUrl}" class="flex-1 py-3 px-4 bg-gradient-to-r from-rose-500 to-orange-500 text-white rounded-xl font-medium text-center hover:shadow-lg transition-all flex items-center justify-center gap-2">
                <i data-lucide="download" class="w-5 h-5"></i>
                下载 PPT
            </a>
        </div>
        <div class="mt-4">
            <button onclick="resetPage()" class="w-full py-2.5 px-4 border border-slate-300 text-slate-700 rounded-xl hover:bg-slate-50 transition-colors flex items-center justify-center gap-2 font-medium">
                <i data-lucide="refresh-cw" class="w-4 h-4"></i>
                重新开始
            </button>
        </div>
    `;
    
    lucide.createIcons();
}

function previewPPT(pptId) {
    if (!pptId) {
        alert('无法预览：缺少 PPT ID');
        return;
    }
    
    if (appState.currentOutline) {
        localStorage.setItem('ppt_outline_' + pptId, JSON.stringify(appState.currentOutline));
    }
    
    window.open(`/ppt/preview?ppt_id=${pptId}`, '_blank');
}

function showError(message) {
    resultSection.classList.remove('hidden');
    
    const resultInfo = document.getElementById('result-info');
    resultInfo.innerHTML = `
        <div class="flex items-center gap-3 text-red-600 mb-4">
            <div class="w-10 h-10 rounded-xl bg-red-100 flex items-center justify-center">
                <i data-lucide="alert-circle" class="w-5 h-5"></i>
            </div>
            <div>
                <div class="font-semibold">生成失败</div>
                <div class="text-sm text-slate-600 mt-1">${message}</div>
            </div>
        </div>
        <button onclick="resetPage()" class="w-full py-2.5 px-4 bg-rose-500 text-white rounded-xl hover:bg-rose-600 transition-colors font-medium flex items-center justify-center gap-2">
            <i data-lucide="refresh-cw" class="w-4 h-4"></i>
            重新开始
        </button>
    `;
    
    lucide.createIcons();
}

function resetPage() {
    welcomeScreen.classList.remove('hidden');
    progressSection.classList.add('hidden');
    outlineSection.classList.add('hidden');
    resultSection.classList.add('hidden');
    const htmlPreviewSection = document.getElementById('html-preview-section');
    if (htmlPreviewSection) htmlPreviewSection.classList.add('hidden');
    appState.currentPPTData = null;
    appState.currentOutline = null;
    appState.currentQuery = null;
    appState.isGenerating = false;
    appState.currentSessionId = null;
    appState.currentSlideIndex = 0;
    appState.totalSlides = 0;
    setGeneratingButtonState(false);
    setStartPreviewButtonState(false);
    setExportButtonState(true, '请先生成预览');
    updateSteps(1);
}

function selectTheme(themeName) {
    appState.selectedTheme = themeName;
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.classList.remove('border-rose-500', 'bg-rose-50');
        btn.classList.add('border-slate-200');
    });
    const selected = document.querySelector(`.theme-btn[data-theme="${themeName}"]`);
    if (selected) {
        selected.classList.remove('border-slate-200');
        selected.classList.add('border-rose-500', 'bg-rose-50');
    }
}

// 显示预览页面（从大纲页点击"生成预览"后调用）
function generatePreview() {
    if (!appState.currentOutline) {
        alert('大纲数据丢失，请重新生成');
        return;
    }
    
    const previewSection = document.getElementById('preview-section');
    const outlineSection = document.getElementById('outline-section');
    const previewContentArea = document.getElementById('preview-content-area');
    
    setStage('preview_ready');
    outlineSection.classList.add('hidden');
    previewSection.classList.remove('hidden');
    updateSteps(2);
    
    // 重置预览状态
    window.slidesData = {};
    appState.currentSlideIndex = 0;
    appState.totalSlides = 0;
    appState.currentSessionId = null;
    
    // 隐藏预览内容区域，显示开始生成按钮
    if (previewContentArea) previewContentArea.classList.add('hidden');
    setStartPreviewButtonState(false);
    setExportButtonState(true, '请先生成预览');
    
    lucide.createIcons();
}

// 实际开始生成预览（用户选择主题后点击"开始生成预览"调用）
async function startPreviewGeneration() {
    const previewContentArea = document.getElementById('preview-content-area');
    const startPreviewBtn = document.getElementById('start-preview-btn');
    
    setStage('preview_generating');
    setStartPreviewButtonState(true);
    setExportButtonState(true, '预览生成中...');
    
    // 显示预览内容区域
    if (previewContentArea) previewContentArea.classList.remove('hidden');
    
    document.getElementById('slides-list').innerHTML = '<div class="text-sm text-slate-500 p-2">正在生成预览...</div>';
    document.getElementById('preview-container').innerHTML = '<div class="w-full h-full flex items-center justify-center text-slate-400" style="min-height: 300px;"><i data-lucide="loader-2" class="w-8 h-8 animate-spin"></i><span class="ml-2">正在生成...</span></div>';
    lucide.createIcons();
    
    try {
        const response = await fetch('/api/ppt/html/generate/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                outline: appState.currentOutline,
                theme: appState.selectedTheme
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (value) {
                buffer += decoder.decode(value, { stream: true });
            }
            
            // 处理缓冲区的数据
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('event: slide_ready')) {
                    const dataLine = line.split('\n').find(l => l.startsWith('data:'));
                    if (dataLine) {
                        const slide = JSON.parse(dataLine.substring(5));
                        onSlideReady(slide);
                    }
                } else if (line.startsWith('event: slide_error')) {
                    const dataLine = line.split('\n').find(l => l.startsWith('data:'));
                    if (dataLine) {
                        const error = JSON.parse(dataLine.substring(5));
                        console.error('Slide generation error:', error);
                    }
                } else if (line.startsWith('event: done')) {
                    const dataLine = line.split('\n').find(l => l.startsWith('data:'));
                    if (dataLine) {
                        const result = JSON.parse(dataLine.substring(5));
                        console.log('Received done event with result:', result);
                        onGenerateDone(result);
                    }
                }
            }
            
            if (done) {
                // 流结束，处理剩余的buffer
                if (buffer.trim()) {
                    console.log('Stream ended, processing remaining buffer:', buffer);
                    const remainingLines = buffer.split('\n\n');
                    for (const line of remainingLines) {
                        if (line.startsWith('event: done')) {
                            const dataLine = line.split('\n').find(l => l.startsWith('data:'));
                            if (dataLine) {
                                const result = JSON.parse(dataLine.substring(5));
                                console.log('Received done event from remaining buffer:', result);
                                onGenerateDone(result);
                            }
                        }
                    }
                }
                break;
            }
        }
        
    } catch (error) {
        alert('预览生成失败: ' + error.message);
        setStartPreviewButtonState(false);
        setExportButtonState(true, '请先生成预览');
    }
}

function onSlideReady(slide) {
    console.log('onSlideReady called for slide:', slide.index);
    window.slidesData[slide.index] = slide.html;
    appState.totalSlides = slide.index + 1;
    
    const list = document.getElementById('slides-list');
    if (slide.index === 0) {
        list.innerHTML = '';
    }
    
    const item = document.createElement('div');
    item.className = 'slide-item p-2 rounded-lg cursor-pointer transition-all bg-white border border-slate-200 hover:border-rose-300';
    item.setAttribute('data-slide-idx', slide.index);
    item.onclick = () => loadSlide(slide.index);
    item.innerHTML = `<div class="text-xs font-medium text-slate-700 truncate">
        <span class="text-rose-500">${slide.index + 1}.</span> ${slide.title}
    </div>`;
    list.appendChild(item);
    
    document.getElementById('slide-counter').textContent = `1 / ${appState.totalSlides}`;
    document.getElementById('prev-slide-btn').disabled = true;
    document.getElementById('next-slide-btn').disabled = appState.totalSlides <= 1;
    
    if (slide.index === 0) {
        loadSlide(0);
    }
    
    document.getElementById('preview-container').innerHTML = `<div class="w-full h-full flex items-center justify-center text-green-500"><i data-lucide="check-circle" class="w-5 h-5"></i><span class="ml-2">已生成 ${slide.index + 1}/${appState.totalSlides} 页</span></div>`;
    lucide.createIcons();
}

function onGenerateDone(result) {
    console.log('onGenerateDone called with:', result);
    
    if (!result || !result.session_id) {
        console.error('Invalid result received:', result);
        alert('生成完成但会话数据无效，请重试');
        return;
    }
    
    appState.currentSessionId = result.session_id;
    appState.totalSlides = result.total;
    setStage('preview_ready');
    setStartPreviewButtonState(false);
    setExportButtonState(false);
    console.log('Session ID set to:', appState.currentSessionId);
    
    document.getElementById('slide-counter').textContent = `1 / ${appState.totalSlides}`;
    document.getElementById('next-slide-btn').disabled = appState.totalSlides <= 1;
    
    document.getElementById('slides-list').innerHTML = '';
    for (let i = 0; i < appState.totalSlides; i++) {
        const title = window.slidesData[i] ? `幻灯片 ${i+1}` : '加载中...';
        const item = document.createElement('div');
        item.className = 'slide-item p-2 rounded-lg cursor-pointer transition-all bg-white border border-slate-200 hover:border-rose-300';
        item.setAttribute('data-slide-idx', i);
        item.onclick = () => loadSlide(i);
        item.innerHTML = `<div class="text-xs font-medium text-slate-700 truncate">
            <span class="text-rose-500">${i + 1}.</span> ${title}
        </div>`;
        document.getElementById('slides-list').appendChild(item);
    }
    
    if (appState.totalSlides > 0) {
        loadSlide(0);
    }
}

function renderSlidesList(slides) {
    const container = document.getElementById('slides-list');
    container.innerHTML = slides.map((slide, idx) => `
        <div class="slide-item p-2 rounded-lg cursor-pointer transition-all ${idx === 0 ? 'bg-rose-100 border-rose-500 border' : 'bg-white border border-slate-200 hover:border-rose-300'}"
             onclick="loadSlide(${idx})" data-slide-idx="${idx}">
            <div class="text-xs font-medium text-slate-700 truncate">
                <span class="text-rose-500">${idx + 1}.</span> ${slide.title}
            </div>
        </div>
    `).join('');
}

async function loadSlide(index) {
    appState.currentSlideIndex = index;
    
    document.querySelectorAll('.slide-item').forEach((el, idx) => {
        if (idx === index) {
            el.classList.remove('bg-white', 'border-slate-200');
            el.classList.add('bg-rose-100', 'border-rose-500');
        } else {
            el.classList.remove('bg-rose-100', 'border-rose-500');
            el.classList.add('bg-white', 'border-slate-200');
        }
    });
    
    document.getElementById('slide-counter').textContent = `${index + 1} / ${appState.totalSlides}`;
    document.getElementById('prev-slide-btn').disabled = index === 0;
    document.getElementById('next-slide-btn').disabled = index === appState.totalSlides - 1;
    
    const container = document.getElementById('preview-container');
    const previewArea = document.getElementById('preview-area');
    
    // 清除之前的resize监听器
    if (resizeHandler) {
        window.removeEventListener('resize', resizeHandler);
        resizeHandler = null;
    }
    
    // 渲染幻灯片到容器
    const renderSlide = (html) => {
        const escapedHTML = html.replace(/"/g, '&quot;').replace(/'/g, '&#39;');

        // 获取预览区域的可用宽度
        const previewArea = document.getElementById('preview-area');
        const availableWidth = previewArea ? previewArea.clientWidth - 40 : 800; // 减去padding

        // 计算缩放比例：基于宽度，保持16:9比例
        // 确保在任何窗口大小下都能完整显示1920x1080内容
        const scale = availableWidth / 1920;
        const targetHeight = 1080 * scale;

        // 创建固定尺寸的容器 - 使用自适应缩放确保完整显示
        container.innerHTML = `
            <div class="slide-wrapper" style="width: ${availableWidth}px; height: ${targetHeight}px; position: relative; overflow: hidden; background: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border-radius: 8px;">
                <iframe srcdoc="${escapedHTML}"
                    style="position: absolute; top: 0; left: 0; width: 1920px; height: 1080px; border: none; transform: scale(${scale}); transform-origin: top left;"
                    id="preview-iframe-${index}">
                </iframe>
            </div>
        `;

        // 存储当前HTML用于resize时重新渲染
        container.dataset.currentHtml = html;
        container.dataset.currentScale = scale;
    };

    // 设置resize监听器以自适应窗口大小变化
    resizeHandler = () => {
        const currentHtml = container.dataset.currentHtml;
        if (currentHtml) {
            renderSlide(currentHtml);
        }
    };
    window.addEventListener('resize', resizeHandler);
    
    if (window.slidesData && window.slidesData[index]) {
        renderSlide(window.slidesData[index]);
    } else {
        container.innerHTML = '<div class="w-full h-full flex items-center justify-center text-slate-400" style="min-height: 300px;"><i data-lucide="loader-2" class="w-8 h-8 animate-spin"></i></div>';
        lucide.createIcons();
        
        try {
            const response = await fetch(`/api/ppt/html/slide/${appState.currentSessionId}/${index}`);
            const result = await response.json();
            
            if (result.success) {
                window.slidesData[index] = result.html;
                renderSlide(result.html);
            } else {
                container.innerHTML = `<div class="w-full h-full flex items-center justify-center text-red-500" style="min-height: 300px;">${result.error}</div>`;
            }
        } catch (error) {
            container.innerHTML = `<div class="w-full h-full flex items-center justify-center text-red-500" style="min-height: 300px;">加载失败</div>`;
        }
    }
}

function prevSlide() {
    if (appState.currentSlideIndex > 0) {
        loadSlide(appState.currentSlideIndex - 1);
    }
}

function nextSlide() {
    if (appState.currentSlideIndex < appState.totalSlides - 1) {
        loadSlide(appState.currentSlideIndex + 1);
    }
}

async function confirmAndExportPPT() {
    console.log('confirmAndExportPPT called, appState.currentSessionId:', appState.currentSessionId);
    if (!appState.currentSessionId) {
        alert('会话数据丢失，请重新生成');
        return;
    }
    if (appState.isExporting) {
        return;
    }
    
    const previewSection = document.getElementById('preview-section');
    appState.isExporting = true;
    setExportButtonState(true, '正在导出...');
    setStage('exporting');
    previewSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    updateProgress(30, '正在生成PPT，预计还需要 10 秒...');
    
    try {
        const response = await fetch(`/api/ppt/html/convert/${appState.currentSessionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updateProgress(100, 'PPT生成成功！');
            appState.isExporting = false;
            setStage('result');
            
            setTimeout(() => {
                progressSection.classList.add('hidden');
                resultSection.classList.remove('hidden');
                showResult(result);
            }, 500);
            
        } else {
            appState.isExporting = false;
            progressSection.classList.add('hidden');
            previewSection.classList.remove('hidden');
            setExportButtonState(false);
            alert('PPT生成失败: ' + (result.error || '未知错误'));
        }
        
    } catch (error) {
        appState.isExporting = false;
        progressSection.classList.add('hidden');
        previewSection.classList.remove('hidden');
        setExportButtonState(false);
        alert('网络错误: ' + error.message);
    }
}

// 重新生成预览（回到主题选择状态）
function regeneratePreview() {
    const previewContentArea = document.getElementById('preview-content-area');
    
    // 重置状态
    window.slidesData = {};
    appState.currentSlideIndex = 0;
    appState.totalSlides = 0;
    appState.currentSessionId = null;
    setStage('preview_ready');
    
    // 隐藏预览内容，显示开始按钮
    if (previewContentArea) previewContentArea.classList.add('hidden');
    setStartPreviewButtonState(false);
    
    // 清空幻灯片列表和预览容器
    document.getElementById('slides-list').innerHTML = '';
    document.getElementById('preview-container').innerHTML = '';
    setExportButtonState(true, '请先生成预览');
    
    lucide.createIcons();
}

// 返回大纲编辑页面
function backToOutline() {
    document.getElementById('preview-section').classList.add('hidden');
    document.getElementById('outline-section').classList.remove('hidden');
    appState.currentSessionId = null;
    setExportButtonState(true, '请先生成预览');
    setStage('outline_ready');
}

lucide.createIcons();
