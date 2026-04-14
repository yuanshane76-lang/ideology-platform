// home-app.js — 思政云伴侣 SPA 前后端集成
// ============================================================
//  工具函数
// ============================================================

function escHtml(s){if(!s)return '';return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}

function showToast(msg,ms){
  const t=document.getElementById('toast');
  t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),ms||2500);
}

function showPage(id){
  document.querySelectorAll('.feature-page').forEach(p=>p.classList.remove('active'));
  const pg=document.getElementById('page-'+id);
  if(pg) pg.classList.add('active');
  document.querySelectorAll('.nav-pill').forEach(n=>n.classList.remove('active'));
  const map={home:0,qa:1,debate:2,ppt:3};
  const pills=document.querySelectorAll('.nav-pill');
  if(pills[map[id]]) pills[map[id]].classList.add('active');
  // 进入辩论页时尝试加载热门议题
  if(id==='debate' && !window._debateTopicsLoaded) loadDebateTopics();
  // 进入问答页时加载历史记录
  if(id==='qa') loadQAHistory();
}

// ============================================================
//  问答模块  —  POST /api/chat  SSE 流
// ============================================================

let qaConversationId = null;
let qaAbort = null;
let qaGenerating = false;

// ========== 历史记录功能 ==========

async function loadQAHistory(){
  try{
    const resp = await fetch('/api/history?t='+Date.now());
    const list = await resp.json();
    const container = document.getElementById('qa-history-list');
    if(!container) return;
    
    if(!list.length){
      container.innerHTML = '<div class="p-3 text-xs text-slate-400 text-center">暂无历史记录</div>';
      return;
    }
    
    let html = '';
    list.forEach(item => {
      const isActive = item.id === qaConversationId;
      const activeCls = isActive ? 'bg-orange-50 border-orange-200 text-brand' : 'bg-white border-slate-100 text-slate-700 hover:border-slate-300';
      const title = item.title.length > 14 ? item.title.substring(0,14)+'...' : item.title;
      html += `<div class="group relative">
        <button onclick="switchQAChat('${item.id}')" class="w-full text-left p-2.5 rounded-xl border ${activeCls} transition-all">
          <div class="text-xs font-medium truncate">${escHtml(title)}</div>
          <div class="text-[10px] text-slate-400 mt-0.5">${item.date}</div>
        </button>
        <button onclick="event.stopPropagation();deleteQAChat('${item.id}')" class="absolute right-1 top-1/2 -translate-y-1/2 p-1.5 rounded-lg text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all" title="删除"><i class="fas fa-times text-xs"></i></button>
      </div>`;
    });
    container.innerHTML = html;
  }catch(e){
    console.error('加载历史失败',e);
  }
}

async function switchQAChat(id){
  if(qaGenerating) return;
  qaConversationId = id;
  loadQAHistory();
  
  const m = document.getElementById('qa-messages');
  m.innerHTML = '<div class="flex items-center justify-center py-20"><i class="fas fa-spinner fa-spin text-slate-400 text-2xl"></i></div>';
  
  try{
    const resp = await fetch('/api/history/'+id);
    if(!resp.ok) throw new Error('加载失败');
    const messages = await resp.json();
    
    m.innerHTML = '';
    messages.forEach(msg => {
      if(msg.role === 'user'){
        appendQAMsg('user', escHtml(msg.content));
      }else{
        // AI 消息用 marked 渲染
        const html = marked ? marked.parse(msg.content) : msg.content.replace(/\n/g,'<br>');
        appendQAMsg('assistant', html);
      }
    });
    scrollQA();
  }catch(e){
    m.innerHTML = '<div class="text-center text-red-500 text-sm py-10">加载失败，请重试</div>';
  }
}

async function deleteQAChat(id){
  if(!confirm('确定删除这条对话？')) return;
  try{
    const resp = await fetch('/api/history/'+id, {method:'DELETE'});
    if(!resp.ok) throw new Error('删除失败');
    if(qaConversationId === id){
      resetQA();
    }else{
      loadQAHistory();
    }
    showToast('已删除');
  }catch(e){
    showToast('删除失败');
  }
}

// ========== 对话功能 ==========

function resetQA(){
  if(qaAbort){qaAbort.abort();qaAbort=null;}
  qaGenerating=false;
  qaConversationId=null;
  const m=document.getElementById('qa-messages');
  // 恢复欢迎卡片
  m.innerHTML = buildQAWelcome();
  loadQAHistory();
}

function newQAChat(){
  resetQA();
}

function buildQAWelcome(){
  return `<div class="bg-white rounded-2xl p-6 shadow-sm border border-slate-200 text-center">
<div class="w-14 h-14 rounded-2xl bg-gradient-to-br from-orange-100 to-red-100 flex items-center justify-center mx-auto mb-4 border border-orange-200">
<i class="fas fa-robot text-brand text-2xl"></i></div>
<h2 class="text-lg font-bold text-slate-800 mb-2">你好，我是思政云问答</h2>
<p class="text-slate-500 text-sm mb-5">思政课程智能助手，支持多轮对话与理论溯源</p>
<div class="grid grid-cols-2 gap-2.5 max-w-md mx-auto">
<button onclick="sendQA('什么是新质生产力？如何理解其核心要义？')" class="text-left p-2.5 rounded-xl bg-orange-50 border border-orange-100 hover:border-orange-300 hover:bg-orange-100/70 transition-all">
<div class="text-xs text-brand font-medium mb-0.5"><i class="fas fa-book-open mr-1"></i>理论概念</div>
<div class="text-sm text-slate-700">什么是新质生产力？</div></button>
<button onclick="sendQA('如何理解中国式现代化的特征？')" class="text-left p-2.5 rounded-xl bg-blue-50 border border-blue-100 hover:border-blue-300 hover:bg-blue-100/70 transition-all">
<div class="text-xs text-blue-600 font-medium mb-0.5"><i class="fas fa-newspaper mr-1"></i>时政分析</div>
<div class="text-sm text-slate-700">中国式现代化的特征</div></button>
<button onclick="sendQA('实践论中如何阐述认识的发展过程？')" class="text-left p-2.5 rounded-xl bg-emerald-50 border border-emerald-100 hover:border-emerald-300 hover:bg-emerald-100/70 transition-all">
<div class="text-xs text-emerald-600 font-medium mb-0.5"><i class="fas fa-scroll mr-1"></i>原著解读</div>
<div class="text-sm text-slate-700">实践论的认识发展过程</div></button>
<button onclick="sendQA('矛盾论中主要矛盾和次要矛盾的关系是什么？')" class="text-left p-2.5 rounded-xl bg-violet-50 border border-violet-100 hover:border-violet-300 hover:bg-violet-100/70 transition-all">
<div class="text-xs text-violet-600 font-medium mb-0.5"><i class="fas fa-puzzle-piece mr-1"></i>方法论</div>
<div class="text-sm text-slate-700">主要矛盾与次要矛盾</div></button>
</div></div>`;
}

function appendQAMsg(role, html){
  const box=document.getElementById('qa-messages');
  const isUser = role==='user';
  const align = isUser?'justify-end':'justify-start';
  const bubble = isUser
    ? 'gradient-brand text-white rounded-tr-none shadow-md'
    : 'bg-white text-slate-800 border border-slate-100 rounded-tl-none shadow-sm';
  const wrapper = document.createElement('div');
  wrapper.className = `flex w-full ${align} mb-5`;
  wrapper.innerHTML = `<div class="flex flex-col max-w-[80%] ${isUser?'items-end':'items-start'}">
    <div class="p-4 text-sm leading-relaxed rounded-2xl ${bubble} qa-bubble">${html}</div>
    <div class="text-[11px] text-slate-400 mt-1 px-1">${isUser?'我':'思政云问答'} · ${new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</div>
  </div>`;
  box.appendChild(wrapper);
  return wrapper.querySelector('.qa-bubble');
}

async function sendQA(text){
  if(!text){
    const inp=document.getElementById('qa-input');
    text=inp.value.trim();
    if(!text) return;
    inp.value='';
  }
  if(qaGenerating) return;

  const box=document.getElementById('qa-messages');
  // 首次发送移除欢迎卡片
  const welcome=box.querySelector('.bg-white.rounded-2xl.p-8');
  if(welcome) welcome.remove();

  appendQAMsg('user', escHtml(text));
  const aiBubble = appendQAMsg('assistant','<div class="flex gap-1.5 items-center py-1"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>');
  scrollQA();

  qaAbort = new AbortController();
  qaGenerating = true;
  let fullText = '';
  let refsData = [];

  try{
    const resp = await fetch('/api/chat',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:text, conversation_id:qaConversationId}),
      signal:qaAbort.signal
    });
    if(!resp.ok) throw new Error('HTTP '+resp.status);

    const reader=resp.body.getReader();
    const dec=new TextDecoder();

    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      const chunk=dec.decode(value,{stream:true});
      const lines=chunk.split('\n\n');
      for(const line of lines){
        if(!line.startsWith('data: ')) continue;
        const json=line.slice(6).trim();
        if(!json) continue;
        let d;try{d=JSON.parse(json);}catch{continue;}

        if(d.type==='token'||d.type==='content'){
          fullText += d.content||d.chunk||'';
          aiBubble.innerHTML = marked.parse(fullText);
          scrollQA();
        } else if(d.type==='thinking'){
          aiBubble.innerHTML = `<span class="text-slate-400 text-xs"><i class="fas fa-spinner fa-spin mr-1"></i>${escHtml(d.content)}</span>`;
        } else if(d.type==='clear'){
          fullText='';
          aiBubble.innerHTML='<span class="text-slate-400 text-xs"><i class="fas fa-spinner fa-spin mr-1"></i>正在修正回复...</span>';
        } else if(d.type==='meta'){
          qaConversationId=d.conversation_id;
        } else if(d.type==='references'){
          refsData=d.data||[];
          renderQARefs(aiBubble, refsData);
          scrollQA();
        } else if(d.type==='references_highlight'){
          // 更新引用高亮（简化处理）
        } else if(d.type==='done'){
          if(d.final_answer){
            fullText=d.final_answer;
            aiBubble.innerHTML=marked.parse(fullText);
          }
          if(d.chips && d.chips.length){
            const cDiv=document.createElement('div');
            cDiv.className='flex flex-wrap gap-2 mt-3';
            d.chips.forEach(c=>{
              const btn=document.createElement('button');
              btn.className='text-xs px-3 py-1.5 bg-orange-50 text-brand rounded-full border border-orange-100 hover:bg-orange-100 transition-colors';
              btn.textContent=c;
              btn.onclick=()=>sendQA(c);
              cDiv.appendChild(btn);
            });
            aiBubble.closest('.flex.flex-col').appendChild(cDiv);
          }
          scrollQA();
          loadQAHistory(); // 刷新历史列表
        } else if(d.type==='error'){
          aiBubble.innerHTML+=`<span class="text-red-500 text-sm block mt-2">错误: ${escHtml(d.content)}</span>`;
        }
      }
    }
  }catch(e){
    if(e.name!=='AbortError'){
      aiBubble.innerHTML+=`<span class="text-red-500 text-sm block mt-2">网络异常: ${escHtml(e.message)}</span>`;
    }
  }finally{
    qaGenerating=false;qaAbort=null;
  }
}

// 全局引用数据存储
let _allQARefs = [];

function renderQARefs(bubble, refs){
  if(!refs||!refs.length) return;
  _allQARefs = refs;
  const container=bubble.closest('.flex.flex-col');
  if(!container) return;
  let html=`<div class="mt-3 p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs">
  <div class="font-semibold text-slate-600 mb-2"><i class="fas fa-book-open text-brand mr-1"></i>参考资料 (${refs.length})</div>
  <div class="space-y-1.5">`;
  refs.slice(0,3).forEach((r,i)=>{
    const label=r.type==='moment'?'📰 时政':'📖 理论';
    const title=r.type==='moment'?r.title:(r.source||'');
    html+=`<div class="p-2 bg-white rounded-lg border border-slate-100 cursor-pointer hover:border-orange-300 transition-colors" onclick="showQARefDetail(${i})">
      <span class="px-1.5 py-0.5 rounded text-[10px] font-medium ${r.type==='moment'?'bg-blue-100 text-blue-600':'bg-orange-100 text-orange-600'}">${label}</span>
      <span class="text-slate-700 ml-1">${escHtml(title)}</span>
      <span class="text-brand ml-1 font-medium">${r.score}%</span>
    </div>`;
  });
  if(refs.length>3) html+=`<button onclick="showAllQARefs()" class="w-full text-center py-1.5 text-xs text-brand hover:bg-orange-50 rounded transition-colors mt-1">查看全部 ${refs.length} 条引用</button>`;
  html+=`</div></div>`;
  container.insertAdjacentHTML('beforeend',html);
}

function showQARefDetail(idx){
  const r = _allQARefs[idx];
  if(!r) return;
  const modal = document.getElementById('qa-ref-modal');
  const content = document.getElementById('qa-ref-modal-content');
  const dlId = 'dl_'+Date.now();
  window[dlId] = r;
  const fullText = r.full_content || r.content || '';
  let html='';
  if(r.type==='moment'){
    html = `<div class="space-y-3">
      <div class="flex items-start justify-between">
        <div><h4 class="text-sm font-semibold text-slate-600 mb-1">📰 新闻标题</h4>
          <p class="text-base font-medium text-slate-800">${escHtml(r.title)}</p></div>
        <button onclick="downloadQARef('${dlId}')" class="text-xs text-brand border border-orange-200 px-3 py-1.5 rounded-lg hover:bg-orange-50 transition-colors">⬇ 下载原文</button>
      </div>
      <div class="grid grid-cols-2 gap-3 text-xs">
        <div><span class="text-slate-500">发布日期</span><p class="text-slate-700 font-medium">${r.date||''}</p></div>
        <div><span class="text-slate-500">新闻来源</span><p class="text-slate-700 font-medium">${r.source||''}</p></div>
      </div>
      <div><span class="text-xs text-slate-500">📝 新闻片段</span>
        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 max-h-48 overflow-y-auto text-sm text-slate-700 mt-1">${escHtml(fullText)}</div>
      </div>
      <div class="pt-2 border-t border-slate-200 text-xs text-slate-500">📊 相关度：<span class="font-semibold text-brand">${r.score}%</span></div>
    </div>`;
  } else {
    const cleanSource = (r.source||'').replace(/思想道德与法治.*/,'思想道德与法治').replace(/毛泽东思想和中国特色社会主义理论体系概论.*/,'毛泽东思想和中国特色社会主义理论体系概论').replace(/新时代中国特色社会主义思想概论.*/,'新时代中国特色社会主义思想概论');
    const loc = [r.chapter, r.section, r.subsection, r.subsubsection].filter(Boolean).join(' / ');
    html = `<div class="space-y-3">
      <div class="flex items-start justify-between">
        <div><h4 class="text-sm font-semibold text-slate-600 mb-1">📚 文献来源</h4>
          <p class="text-base font-medium text-slate-800">《${escHtml(cleanSource)}》</p></div>
        <button onclick="downloadQARef('${dlId}')" class="text-xs text-brand border border-orange-200 px-3 py-1.5 rounded-lg hover:bg-orange-50 transition-colors">⬇ 下载原文</button>
      </div>
      <div><span class="text-xs text-slate-500">📍 章节定位</span>
        <p class="text-sm text-slate-700 mt-1">${escHtml(loc)||'无'}</p>
      </div>
      <div><span class="text-xs text-slate-500">📝 引用片段</span>
        <div class="p-3 bg-slate-50 rounded-lg border border-slate-200 max-h-48 overflow-y-auto text-sm text-slate-700 mt-1">${escHtml(fullText)}</div>
      </div>
      <div class="pt-2 border-t border-slate-200 text-xs text-slate-500">📊 相关度：<span class="font-semibold text-brand">${r.score}%</span></div>
    </div>`;
  }
  content.innerHTML = html;
  modal.classList.remove('hidden');
}

function showAllQARefs(){
  const refs = _allQARefs;
  if(!refs||!refs.length) return;
  const modal = document.getElementById('qa-ref-modal');
  const content = document.getElementById('qa-ref-modal-content');
  let html = `<div class="space-y-2">
    <h4 class="font-semibold text-slate-800 mb-3">全部参考资料 (${refs.length})</h4>`;
  refs.forEach((r,i)=>{
    const label = r.type==='moment'?'📰 时政':'📖 理论';
    const title = r.type==='moment'?r.title:(r.source||'');
    const sub = r.type==='moment'?`${r.source||''} · ${r.date||''}`:`${r.chapter||''}${r.section?' · '+r.section:''}`;
    html += `<div class="p-2 bg-slate-50 rounded-lg border border-slate-200 cursor-pointer hover:border-orange-300 transition-colors" onclick="showQARefDetail(${i})">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="text-[10px] font-medium px-1.5 py-0.5 rounded ${r.type==='moment'?'bg-blue-100 text-blue-600':'bg-orange-100 text-orange-600'}">${label}</span>
          <span class="text-sm font-medium text-slate-700">${escHtml(title)}</span>
        </div>
        <span class="text-xs text-brand font-medium">${r.score}%</span>
      </div>
      <p class="text-[10px] text-slate-500 mt-0.5">${escHtml(sub)}</p>
    </div>`;
  });
  html += '</div>';
  content.innerHTML = html;
  modal.classList.remove('hidden');
}

function closeQARefModal(){
  document.getElementById('qa-ref-modal').classList.add('hidden');
}

async function downloadQARef(refId){
  const ref = window[refId];
  if(!ref) return;
  try{
    const resp = await fetch('/api/reference/download',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(ref)
    });
    if(!resp.ok) throw new Error('下载失败');
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = ref.type==='moment'?`${(ref.title||'时政新闻').substring(0,20)}.docx`:`${(ref.source||'理论文献').substring(0,15)}.docx`;
    document.body.appendChild(a);a.click();
    setTimeout(()=>{document.body.removeChild(a);URL.revokeObjectURL(url);},200);
    showToast('下载成功');
  }catch(e){
    showToast('下载失败: '+e.message);
  }
}

function scrollQA(){
  const c=document.getElementById('qa-chat');
  if(c) c.scrollTop=c.scrollHeight;
}

// ============================================================
//  辩论模块  —  /api/debate/*
// ============================================================

let debateSessionId=null;
let debateRound=0;
let debateAbort=null;
let debateGenerating=false;
let debateCardBody=null;
let debateCardContent='';
window._debateTopicsLoaded=false;

function resetDebate(){
  if(debateAbort){debateAbort.abort();debateAbort=null;}
  debateGenerating=false;debateSessionId=null;debateRound=0;
  debateCardBody=null;debateCardContent='';
  document.getElementById('debate-status').textContent='待开始';
  document.getElementById('debate-status').className='text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-500';
  document.getElementById('debate-start-btn').classList.remove('hidden');
  document.getElementById('debate-start-btn').disabled=false;
  document.getElementById('debate-next-btn').classList.add('hidden');
  document.getElementById('debate-judge-btn').classList.add('hidden');
  document.getElementById('debate-timeline').innerHTML='';
  document.getElementById('debate-timeline').classList.add('hidden');
  document.getElementById('debate-placeholder').classList.remove('hidden');
}

function pickTopic(t){document.getElementById('debate-topic').value=t;}

function debateSetStatus(text,cls){
  const el=document.getElementById('debate-status');
  el.textContent=text;
  el.className='text-xs px-2.5 py-1 rounded-full '+cls;
}

function debateCreateCard(role, round){
  const map={
    protagonist:{title:'思政云正方',color:'border-rose-300 bg-rose-50',icon:'🔴'},
    antagonist:{title:'思政云反方',color:'border-sky-300 bg-sky-50',icon:'🔵'},
    judge:{title:'思政云裁判',color:'border-emerald-300 bg-emerald-50',icon:'⚖️'}
  };
  const cfg=map[role];
  const tl=document.getElementById('debate-timeline');
  const card=document.createElement('div');
  card.className=`rounded-xl border ${cfg.color} bg-white p-4 mb-3`;
  card.innerHTML=`<div class="text-sm font-semibold mb-2">${cfg.icon} ${cfg.title}${round?' · 第'+round+'轮':''}</div>
    <div class="prose prose-sm max-w-none text-slate-700 debate-body"></div>`;
  tl.appendChild(card);
  tl.scrollTop=tl.scrollHeight;
  return card.querySelector('.debate-body');
}

function debateAppendChunk(chunk){
  if(!debateCardBody) return;
  debateCardContent+=chunk;
  debateCardBody.innerHTML=marked.parse(debateCardContent)+'<span style="opacity:.5">▍</span>';
  document.getElementById('debate-main').scrollTop=document.getElementById('debate-main').scrollHeight;
}

function debateFinalizeCard(){
  if(!debateCardBody) return;
  debateCardBody.innerHTML=marked.parse(debateCardContent);
  debateCardBody=null;debateCardContent='';
}

async function startDebate(){
  const topic=document.getElementById('debate-topic').value.trim();
  if(!topic){showToast('请先填写交锋议题');return;}
  if(debateGenerating) return;

  debateGenerating=true;
  debateAbort=new AbortController();
  // UI
  document.getElementById('debate-placeholder').classList.add('hidden');
  const tl=document.getElementById('debate-timeline');
  tl.classList.remove('hidden');tl.innerHTML='';
  document.getElementById('debate-start-btn').classList.add('hidden');
  document.getElementById('debate-next-btn').classList.add('hidden');
  document.getElementById('debate-judge-btn').classList.add('hidden');
  debateSetStatus('正在创建会话...','bg-orange-100 text-orange-700');

  try{
    const startResp=await fetch('/api/debate/start',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:topic,description:document.getElementById('debate-desc').value.trim(),max_rounds:10})
    });
    if(!startResp.ok) throw new Error('启动失败: '+startResp.status);
    const startData=await startResp.json();
    debateSessionId=startData.session_id;
    debateRound=0;
    debateSetStatus('正在交锋','bg-orange-100 text-orange-700');
    await debateRunNext();
  }catch(e){
    if(e.name==='AbortError'){showToast('已停止');}
    else{showToast('启动失败: '+e.message);}
    debateGenerating=false;
    document.getElementById('debate-start-btn').classList.remove('hidden');
    document.getElementById('debate-start-btn').disabled=false;
  }
}

async function debateRunNext(){
  debateGenerating=true;debateAbort=new AbortController();
  document.getElementById('debate-next-btn').classList.add('hidden');
  document.getElementById('debate-judge-btn').classList.add('hidden');
  debateSetStatus('正在交锋','bg-orange-100 text-orange-700');

  try{
    const resp=await fetch('/api/debate/next',{
      method:'POST',headers:{'Content-Type':'application/json'},
      signal:debateAbort.signal,
      body:JSON.stringify({session_id:debateSessionId})
    });
    if(!resp.ok) throw new Error('HTTP '+resp.status);

    const reader=resp.body.getReader();
    const dec=new TextDecoder();
    let buf='';

    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\n\n');
      buf=parts.pop()||'';
      for(const block of parts){
        const line=block.trim();
        if(!line.startsWith('data: ')) continue;
        let d;try{d=JSON.parse(line.slice(6));}catch{continue;}
        switch(d.type){
          case 'round_start':
            debateRound=d.round;
            const rdiv=document.createElement('div');
            rdiv.className='text-center text-xs text-slate-500 my-2';
            rdiv.innerHTML=`<span class="px-3 py-1 rounded-full bg-slate-100">第 ${d.round} 轮</span>`;
            document.getElementById('debate-timeline').appendChild(rdiv);
            break;
          case 'protagonist_start':
            debateCardBody=debateCreateCard('protagonist',debateRound);break;
          case 'antagonist_start':
            debateCardBody=debateCreateCard('antagonist',debateRound);break;
          case 'protagonist_chunk':case 'antagonist_chunk':
            debateAppendChunk(d.content||'');break;
          case 'protagonist_end':case 'antagonist_end':
            debateFinalizeCard();break;
          case 'round_complete':
            debateFinalizeCard();
            debateGenerating=false;
            debateSetStatus(`第 ${debateRound} 轮完成`,'bg-emerald-100 text-emerald-700');
            document.getElementById('debate-next-btn').classList.remove('hidden');
            document.getElementById('debate-judge-btn').classList.remove('hidden');
            break;
          case 'max_rounds_reached':
            debateFinalizeCard();
            debateGenerating=false;
            debateSetStatus('已达最大轮次','bg-amber-100 text-amber-700');
            document.getElementById('debate-judge-btn').classList.remove('hidden');
            break;
          case 'error':
            debateFinalizeCard();debateGenerating=false;
            showToast(d.message||'交锋出错');break;
        }
      }
    }
  }catch(e){
    if(e.name==='AbortError') showToast('已停止');
    else showToast('请求失败: '+e.message);
    debateGenerating=false;
    document.getElementById('debate-next-btn').classList.remove('hidden');
    document.getElementById('debate-judge-btn').classList.remove('hidden');
  }
}

function debateNextRound(){if(!debateSessionId){showToast('请先开始辩论');return;} debateRunNext();}

async function debateJudge(){
  if(!debateSessionId){showToast('请先开始辩论');return;}
  if(debateGenerating) return;
  debateGenerating=true;debateAbort=new AbortController();
  document.getElementById('debate-next-btn').classList.add('hidden');
  document.getElementById('debate-judge-btn').classList.add('hidden');
  debateSetStatus('裁判总结中','bg-amber-100 text-amber-700');

  try{
    const resp=await fetch('/api/debate/judge',{
      method:'POST',headers:{'Content-Type':'application/json'},
      signal:debateAbort.signal,
      body:JSON.stringify({session_id:debateSessionId})
    });
    if(!resp.ok) throw new Error('HTTP '+resp.status);
    const reader=resp.body.getReader();
    const dec=new TextDecoder();let buf='';

    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buf+=dec.decode(value,{stream:true});
      const parts=buf.split('\n\n');buf=parts.pop()||'';
      for(const block of parts){
        const line=block.trim();
        if(!line.startsWith('data: ')) continue;
        let d;try{d=JSON.parse(line.slice(6));}catch{continue;}
        switch(d.type){
          case 'judge_start':
            debateCardBody=debateCreateCard('judge');break;
          case 'judge_chunk':
            debateAppendChunk(d.content||'');break;
          case 'judge_end':
            debateFinalizeCard();break;
          case 'complete':
            debateFinalizeCard();debateGenerating=false;
            debateSetStatus('辩论结束','bg-emerald-100 text-emerald-700');
            showToast('辩论已完成');break;
          case 'error':
            debateFinalizeCard();debateGenerating=false;
            showToast(d.message||'裁判总结失败');break;
        }
      }
    }
  }catch(e){
    if(e.name!=='AbortError') showToast('请求失败: '+e.message);
    debateGenerating=false;
  }
}

async function loadDebateTopics(){
  try{
    const resp=await fetch('/api/debate/topics');
    if(!resp.ok) return;
    const topics=await resp.json();
    window._debateTopicsLoaded=true;
    // 如果有数据，更新侧栏热门议题
    if(!topics.length) return;
    const container=document.querySelector('#page-debate aside .border-t .space-y-2');
    if(!container) return;
    container.innerHTML='';
    topics.slice(0,5).forEach(t=>{
      const div=document.createElement('div');
      div.className='p-3 rounded-xl bg-debate-light border border-blue-100 cursor-pointer hover:border-debate/30 transition-colors';
      div.innerHTML=`<div class="text-sm font-medium text-slate-800">${escHtml(t.title)}</div>
        <div class="text-xs text-slate-500 mt-0.5">${escHtml((t.tags||[]).join(' · '))}</div>`;
      div.onclick=()=>pickTopic(t.title);
      container.appendChild(div);
    });
  }catch(e){console.error('加载议题失败',e);}
}

// ============================================================
//  PPT 备课模块  —  /api/ppt/*
// ============================================================

const pptState={
  outline:null, sessionId:null, query:'', selectedTheme:'party_red',
  slides:{}, totalSlides:0, currentSlide:0, generating:false, abort:null
};

function setPPTQuery(q){document.getElementById('ppt-query').value=q;}

function pptSetStep(step){
  const colors={active:'bg-violet-600 text-white',done:'bg-violet-600 text-white',pending:'bg-slate-200 text-slate-500'};
  [1,2,3].forEach(i=>{
    const el=document.getElementById('ps'+i);
    const t=document.getElementById('ps'+i+'t');
    if(i<step){el.className='w-6 h-6 rounded-full bg-emerald-500 text-white text-xs flex items-center justify-center font-bold';el.innerHTML='✓';if(t) t.className='text-xs text-emerald-600 font-medium';}
    else if(i===step){el.className='w-6 h-6 rounded-full bg-violet-600 text-white text-xs flex items-center justify-center font-bold';el.textContent=i;if(t) t.className='text-xs text-violet-600 font-medium';}
    else{el.className='w-6 h-6 rounded-full bg-slate-200 text-slate-500 text-xs flex items-center justify-center font-bold';el.textContent=i;if(t) t.className='text-xs text-slate-400';}
  });
  [1,2].forEach(i=>{
    const ln=document.getElementById('pline'+i);
    if(ln) ln.className='w-6 h-0.5 '+(i<step?'bg-violet-600':'bg-slate-200');
  });
}

function pptShowStep(n){
  ['ppt-step1','ppt-step2','ppt-step3'].forEach((id,i)=>{
    document.getElementById(id).classList.toggle('hidden',i+1!==n);
  });
  pptSetStep(n);
}

async function pptGenOutline(){
  const q=document.getElementById('ppt-query').value.trim();
  if(!q){showToast('请输入备课主题');return;}
  if(pptState.generating) return;

  pptState.query=q;pptState.generating=true;
  pptState.abort=new AbortController();

  // 显示进度
  document.getElementById('ppt-progress').classList.remove('hidden');
  document.getElementById('ppt-gen-btn').disabled=true;
  document.getElementById('ppt-gen-btn').innerHTML='<i class="fas fa-spinner fa-spin mr-2"></i>生成中...';
  pptUpdateProgress(5,'正在分析需求...');

  let chapters=[];let chapterCount=0;

  try{
    const resp=await fetch('/api/ppt/outline/stream',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({query:q}),
      signal:pptState.abort.signal
    });
    if(!resp.ok) throw new Error('HTTP '+resp.status);

    const reader=resp.body.getReader();
    const dec=new TextDecoder();let buf='';

    while(true){
      const {done,value}=await reader.read();
      if(done) break;
      buf+=dec.decode(value,{stream:true});
      const lines=buf.split('\n');buf=lines.pop()||'';
      for(const line of lines){
        if(!line.startsWith('data: ')) continue;
        let ev;try{ev=JSON.parse(line.slice(6));}catch{continue;}
        if(ev.type==='start'){
          pptUpdateProgress(10,'开始生成: '+(ev.topic||''));
        }else if(ev.type==='chapter_start'){
          chapterCount++;
          pptUpdateProgress(10+chapterCount*12,'正在生成第 '+ev.chapter_index+' 章...');
        }else if(ev.type==='chapter_done'){
          chapters.push(ev.chapter);
          pptUpdateProgress(10+chapters.length*13,'第 '+ev.chapter.chapter_index+' 章完成');
        }else if(ev.type==='done'){
          pptState.outline=ev.outline;
          pptUpdateProgress(100,'大纲生成完成！');
          setTimeout(()=>{
            document.getElementById('ppt-progress').classList.add('hidden');
            pptShowOutlineEditor(pptState.outline);
            pptShowStep(2);
          },400);
        }
      }
    }
  }catch(e){
    if(e.name!=='AbortError') showToast('生成失败: '+e.message);
    document.getElementById('ppt-progress').classList.add('hidden');
  }finally{
    pptState.generating=false;
    document.getElementById('ppt-gen-btn').disabled=false;
    document.getElementById('ppt-gen-btn').innerHTML='<i class="fas fa-wand-magic-sparkles mr-2"></i>生成大纲';
  }
}

function pptUpdateProgress(pct, text){
  const bar=document.getElementById('ppt-progress-bar');
  const txt=document.getElementById('ppt-progress-text');
  const p=document.getElementById('ppt-progress-pct');
  if(bar) bar.style.width=pct+'%';
  if(txt) txt.textContent=text;
  if(p) p.textContent=Math.round(pct)+'%';
}

function pptShowOutlineEditor(outline){
  if(!outline||!outline.chapters) return;
  const list=document.getElementById('ppt-outline-list');
  list.innerHTML=outline.chapters.map((ch,ci)=>`
    <div class="border border-slate-200 rounded-xl p-4 bg-slate-50/50" data-ch="${ci}">
      <div class="flex items-center gap-2 mb-3">
        <span class="text-xs font-bold text-violet-600 bg-violet-100 px-2.5 py-1 rounded-lg">第 ${ch.chapter_index} 章</span>
        <input type="text" value="${escHtml(ch.chapter_title)}" class="flex-1 text-base font-bold border-b-2 border-transparent hover:border-slate-300 focus:border-violet-500 focus:outline-none px-2 py-1 bg-transparent ppt-ch-title">
      </div>
      <div class="space-y-2">
        ${(ch.slides||[]).map((s,si)=>`
          <div class="bg-white rounded-lg p-3 border border-slate-100 ppt-slide-block">
            <input type="text" value="${escHtml(s.title)}" class="w-full text-sm font-medium border-none bg-transparent focus:outline-none text-slate-700 mb-1 ppt-slide-title">
            <div class="space-y-1">
              ${(s.bullets||[]).map(b=>`<div class="flex items-center gap-2"><span class="text-slate-400 text-xs">•</span>
                <input type="text" value="${escHtml(b)}" class="flex-1 text-xs border border-slate-200 rounded-lg px-2 py-1 focus:border-violet-400 focus:outline-none ppt-bullet"></div>`).join('')}
            </div>
          </div>`).join('')}
      </div>
    </div>`).join('');
  pptShowStep(2);
}

function pptCollectOutline(){
  const chapters=[];
  document.querySelectorAll('#ppt-outline-list [data-ch]').forEach((chEl,ci)=>{
    const title=chEl.querySelector('.ppt-ch-title').value;
    const slides=[];
    chEl.querySelectorAll('.ppt-slide-block').forEach(sEl=>{
      const st=sEl.querySelector('.ppt-slide-title').value;
      const bullets=[];
      sEl.querySelectorAll('.ppt-bullet').forEach(b=>bullets.push(b.value));
      slides.push({title:st,bullets});
    });
    chapters.push({chapter_index:ci+1,chapter_title:title,slides});
  });
  return {title:pptState.outline?.title||pptState.query, chapters};
}

function pptBackToInput(){
  pptShowStep(1);
  document.getElementById('ppt-progress').classList.add('hidden');
}

function pptGoPreview(){
  // 收集编辑后的大纲
  const edited=pptCollectOutline();
  if(edited.chapters.length===0){showToast('大纲为空');return;}
  pptState.outline=edited;
  pptShowStep(3);
  // 重置预览区
  document.getElementById('ppt-preview-area').classList.add('hidden');
  document.getElementById('ppt-dl-btn').disabled=true;
  pptState.slides={};pptState.totalSlides=0;pptState.currentSlide=0;pptState.sessionId=null;
}

function pptSelectTheme(th){
  pptState.selectedTheme=th;
  document.querySelectorAll('.ppt-th-btn').forEach(b=>{
    if(b.dataset.th===th){b.className='ppt-th-btn p-2 rounded-lg border-2 border-violet-500 bg-violet-50 transition-all';}
    else{b.className='ppt-th-btn p-2 rounded-lg border-2 border-slate-200 hover:border-slate-400 transition-all';}
  });
}

async function pptStartPreview(){
  if(pptState.generating) return;
  pptState.generating=true;
  const btn=document.getElementById('ppt-preview-btn');
  btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin mr-2"></i>正在生成...';

  // 显示预览区
  const area=document.getElementById('ppt-preview-area');
  area.classList.remove('hidden');
  document.getElementById('ppt-slides-list').innerHTML='<div class="text-xs text-slate-400 p-2">正在生成...</div>';
  document.getElementById('ppt-slide-viewport').innerHTML='<div class="flex items-center justify-center text-slate-400 py-20"><i class="fas fa-spinner fa-spin text-2xl"></i></div>';

  pptState.slides={};pptState.totalSlides=0;

  try{
    const resp=await fetch('/api/ppt/html/generate/stream',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({outline:pptState.outline, theme:pptState.selectedTheme})
    });
    if(!resp.ok) throw new Error('HTTP '+resp.status);

    const reader=resp.body.getReader();
    const dec=new TextDecoder();let buf='';

    while(true){
      const {done,value}=await reader.read();
      if(value) buf+=dec.decode(value,{stream:true});
      const blocks=buf.split('\n\n');buf=blocks.pop()||'';

      for(const block of blocks){
        if(block.startsWith('event: slide_ready')){
          const dl=block.split('\n').find(l=>l.startsWith('data:'));
          if(dl){
            const slide=JSON.parse(dl.substring(5));
            pptOnSlideReady(slide);
          }
        }else if(block.startsWith('event: slide_error')){
          const dl=block.split('\n').find(l=>l.startsWith('data:'));
          if(dl) console.error('Slide error:',JSON.parse(dl.substring(5)));
        }else if(block.startsWith('event: done')){
          const dl=block.split('\n').find(l=>l.startsWith('data:'));
          if(dl){
            const result=JSON.parse(dl.substring(5));
            pptOnDone(result);
          }
        }
      }
      if(done){
        // 处理剩余buffer
        if(buf.trim()){
          const remaining=buf.split('\n\n');
          for(const block of remaining){
            if(block.startsWith('event: done')){
              const dl=block.split('\n').find(l=>l.startsWith('data:'));
              if(dl) pptOnDone(JSON.parse(dl.substring(5)));
            }
          }
        }
        break;
      }
    }
  }catch(e){
    showToast('预览生成失败: '+e.message);
  }finally{
    pptState.generating=false;
    btn.disabled=false;btn.innerHTML='<i class="fas fa-play mr-2"></i>开始生成预览';
  }
}

function pptOnSlideReady(slide){
  pptState.slides[slide.index]=slide.html;
  pptState.totalSlides=Math.max(pptState.totalSlides,slide.index+1);
  const list=document.getElementById('ppt-slides-list');
  if(slide.index===0) list.innerHTML='';
  const item=document.createElement('div');
  item.className='p-2 rounded-lg cursor-pointer bg-white border border-slate-200 hover:border-violet-300 text-xs text-slate-700 truncate';
  item.innerHTML=`<span class="text-violet-500 font-bold">${slide.index+1}.</span> ${escHtml(slide.title)}`;
  item.onclick=()=>pptLoadSlide(slide.index);
  list.appendChild(item);

  document.getElementById('ppt-slide-num').textContent=`${pptState.currentSlide+1} / ${pptState.totalSlides}`;
  if(slide.index===0) pptLoadSlide(0);
}

function pptOnDone(result){
  if(!result||!result.session_id) return;
  pptState.sessionId=result.session_id;
  pptState.totalSlides=result.total;
  document.getElementById('ppt-dl-btn').disabled=false;
  document.getElementById('ppt-slide-num').textContent=`${pptState.currentSlide+1} / ${pptState.totalSlides}`;
  showToast('预览生成完成！可以下载 PPT');
}

function pptLoadSlide(idx){
  pptState.currentSlide=idx;
  document.getElementById('ppt-slide-num').textContent=`${idx+1} / ${pptState.totalSlides}`;
  document.getElementById('ppt-prev').disabled=idx===0;
  document.getElementById('ppt-next').disabled=idx>=pptState.totalSlides-1;

  // 高亮列表
  const items=document.getElementById('ppt-slides-list').children;
  for(let i=0;i<items.length;i++){
    items[i].className=i===idx
      ?'p-2 rounded-lg cursor-pointer bg-violet-100 border border-violet-400 text-xs text-slate-700 truncate'
      :'p-2 rounded-lg cursor-pointer bg-white border border-slate-200 hover:border-violet-300 text-xs text-slate-700 truncate';
  }

  const vp=document.getElementById('ppt-slide-viewport');
  const html=pptState.slides[idx];
  if(!html){vp.innerHTML='<span class="text-slate-400 text-sm">加载中...</span>';return;}

  // iframe缩放渲染
  const w=vp.clientWidth-24||600;
  const scale=w/1920;
  const h=1080*scale;
  const escaped=html.replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  vp.innerHTML=`<div style="width:${w}px;height:${h}px;position:relative;overflow:hidden;background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1)">
    <iframe srcdoc="${escaped}" style="position:absolute;top:0;left:0;width:1920px;height:1080px;border:none;transform:scale(${scale});transform-origin:top left"></iframe></div>`;
}

function pptPrevSlide(){if(pptState.currentSlide>0) pptLoadSlide(pptState.currentSlide-1);}
function pptNextSlide(){if(pptState.currentSlide<pptState.totalSlides-1) pptLoadSlide(pptState.currentSlide+1);}

function pptBackToOutline(){pptShowStep(2);}

async function pptDownload(){
  if(!pptState.sessionId){showToast('请先生成预览');return;}
  const btn=document.getElementById('ppt-dl-btn');
  btn.disabled=true;btn.innerHTML='<i class="fas fa-spinner fa-spin mr-2"></i>正在导出...';

  try{
    const resp=await fetch('/api/ppt/html/convert/'+pptState.sessionId,{
      method:'POST',headers:{'Content-Type':'application/json'}
    });
    const result=await resp.json();
    if(result.success&&result.download_url){
      const a=document.createElement('a');
      a.href=result.download_url;a.download='presentation.pptx';
      document.body.appendChild(a);a.click();
      setTimeout(()=>document.body.removeChild(a),200);
      showToast('PPT 下载开始');
    }else{
      showToast('导出失败: '+(result.error||'未知错误'));
    }
  }catch(e){
    showToast('网络错误: '+e.message);
  }finally{
    btn.disabled=false;btn.innerHTML='<i class="fas fa-download mr-2"></i>下载 PPT';
  }
}
