const { Document, Packer, Paragraph, TextRun, ImageRun, AlignmentType, HeadingLevel, PageBreak } = require('docx');
const fs = require('fs');

const archImg = fs.readFileSync(`D:\\Desktop\\大四学习资料\\论文\\PPT输出\\extracted_images\\slide10_Image_0.png`);
const langgraphImg = fs.readFileSync(`D:\\Desktop\\大四学习资料\\论文\\PPT输出\\extracted_images\\slide11_Image_0.png`);

function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, font: "SimSun", size: 32 })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, bold: true, font: "SimSun", size: 28 })] });
}
function h3(text) {
  return new Paragraph({ spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, bold: true, font: "SimSun", size: 24 })] });
}
function p(text) {
  return new Paragraph({ spacing: { after: 120, line: 360 }, indent: { firstLine: 480 },
    children: [new TextRun({ text, font: "SimSun", size: 24 })] });
}
function pn(text) {
  return new Paragraph({ spacing: { after: 120, line: 360 },
    children: [new TextRun({ text, font: "SimSun", size: 24 })] });
}
function fp(text) {
  return new Paragraph({ spacing: { before: 160, after: 160 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: "Times New Roman", size: 24, italics: true })] });
}
function fc(text) {
  return new Paragraph({ spacing: { before: 80, after: 200 }, alignment: AlignmentType.CENTER,
    children: [new TextRun({ text, font: "SimSun", size: 22 })] });
}

const LQ = "\u201C";
const RQ = "\u201D";
const DASH = "\u2014";

const doc = new Document({
  styles: { default: { document: { run: { font: "SimSun", size: 24 } } } },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    children: [
      h1(`第3章 技术方案`),

      p(`本章从原理层面阐述系统问答功能的技术方案。系统面向高校思政课辅学场景，核心挑战有二：其一，马克思主义理论体系具有高度严谨性，引用错误的政治表述会造成严重影响；其二，通用大语言模型存在${LQ}幻觉${RQ}现象，在专业领域问答中容易生成脱离事实的内容。为此，本系统提出以检索增强生成（RAG）为基础、以多智能体协作为核心的技术路线，构建${LQ}检索${DASH}生成${DASH}校验${RQ}闭环问答架构。`),

      h2(`3.1 总体技术路线`),

      p(`系统整体分为三层，如图3.1所示。表现层基于Flask提供RESTful API，通过SSE协议实现流式响应，答案逐token推送至前端。业务逻辑层基于LangGraph构建多智能体协作图，包含五类智能体节点，由Supervisor统一调度，形成${LQ}感知${DASH}决策${DASH}执行${RQ}的智能体回路。数据持久层使用Qdrant存储两个独立向量集合（理论库与时政库），SQLite存储对话历史与证据缓存。`),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 },
        children: [new ImageRun({ type: "png", data: archImg, transformation: { width: 480, height: 320 },
          altText: { title: "系统总体架构图", description: "三层架构图", name: "arch" } })] }),
      fc(`图3.1 系统总体架构图`),

      h2(`3.2 知识库构建`),

      p(`本系统将知识来源划分为两个物理隔离的向量集合，这是区别于通用RAG系统的核心设计。理论知识库收录四门思政教材约100万字，经人工校对确保与纸质版一致，具有静态性、层级严密性特点。时政资料库收录人民网等权威媒体近两年内容，由Python爬虫持续采集，具有高频更新、时效性强特点。两者若混同存储，理论章节的细粒度分块将被大量新闻内容${LQ}淹没${RQ}，导致理论问题被错误路由到新闻段落。双库隔离后，可根据问题类型精准分配检索权重。`),

      p(`文本分块采用滑动窗口加句法边界的策略，目标块大小400~600 token，相邻块保留10%~15%重叠。理论库按教材层级结构分块，Payload保留完整层级路径以便溯源。每个文档块采用双路编码：稠密向量由text-embedding-v4生成1024维浮点数；稀疏关键词由qwen3-max预提取5~8个核心关键词存入Payload，用于混合检索阶段的精确匹配。`),

      h2(`3.3 多智能体协作架构`),

      p(`本系统选用LangGraph v0.2.12作为编排框架。相比LangChain的顺序链式调用，LangGraph以有向图结构定义工作流，核心优势在于：支持显式状态管理，所有智能体共享类型化全局状态RAGState；支持条件边，实现Supervisor动态路由；支持循环图，满足${LQ}生成\u2192审核\u2192修正${RQ}的反馈闭环。`),

      p(`全局状态RAGState基于TypedDict定义，涵盖输入层（查询、增强查询、对话历史）、路由层（问题类型、检索策略、关键词）、检索层（双库文档）、生成审核层（初稿、审核结果、置信度、重试计数）、对话管理层（会话ID、轮次、摘要）及调度层（next_agent字段）。所有字段均为可选，每个智能体只读写自身关注的字段子集。`),

      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 200 },
        children: [new ImageRun({ type: "png", data: langgraphImg, transformation: { width: 440, height: 300 },
          altText: { title: "LangGraph多智能体流程图", description: "多智能体协作图", name: "langgraph" } })] }),
      fc(`图3.2 LangGraph多智能体协作流程图`),

      p(`系统采用中心辐射式图结构，Supervisor位于中心，所有业务智能体构成辐条。Supervisor通过next_agent字段动态路由，业务节点执行完毕后均返回Supervisor。调度逻辑为严格的状态机：先判断是否需要指代消解\u2192意图识别\u2192按策略检索双库\u2192生成初稿\u2192审核\u2192若不通过则扩大检索重试（最多2次）\u2192通过后结束。`),

      h3(`3.3.1 混合检索算法`),

      p(`混合检索是本系统在RAG技术上的核心改进。先由Qdrant召回Top-15候选文档，再对每个候选计算混合评分：`),

      fp(`Score(q, d) = \u03B1 \u00B7 CosSim(q\u20D7, d\u20D7) + \u03B2 \u00B7 KW_Match(q, d)`),

      p(`其中\u03B1=1.0为向量语义相似度权重，\u03B2=0.05为每个关键词命中贡献的分值。该设定使语义相似度为主导，关键词匹配在相似度相近时起决胜作用。例如，语义相似度0.88但命中3个关键词的文档（得分1.03），将优于语义0.90但无关键词命中的文档（得分0.90）。这对${LQ}新质生产力${RQ}等思政专有名词检索尤为有效${DASH}${DASH}纯语义向量对此类词语区分度不足，关键词精确匹配能有效补充。`),

      h3(`3.3.2 Validator三级审核`),

      p(`Validator对Generator初稿执行三级审核：一级审核政治导向，确保立场正确；二级审核事实准确性，防止理论引用篡改或数据错误；三级审核价值引领，排查${LQ}低级红${RQ}${LQ}高级黑${RQ}等问题。审核不通过且置信度低时，系统扩大top_k补充检索后重新生成；已重试2次仍未通过则降级处理，将审核意见传递给最终润色步骤进行针对性修正。`),

      h2(`3.4 流式响应与对话记忆`),

      p(`Flask的同步特性与LangGraph的长耗时执行存在矛盾。本系统设计了双线程异步架构：Flask主线程通过线程安全队列接收LangGraph子线程产生的各类事件，序列化为SSE格式推送前端。引用处理分为两阶段${DASH}${DASH}检索完成后同步去重推送基础引用列表，然后在daemon线程中并发执行关键词高亮识别，不阻塞答案生成。`),

      p(`对话记忆采用滑动窗口保留最近5轮（10条消息），超过阈值后触发摘要压缩至200字以内。证据缓存机制将上一轮检索结果持久化至SQLite，追问时优先注入缓存证据，可能跳过重复检索。`),

      // ====== 第4章 ======
      new Paragraph({ children: [new PageBreak()] }),
      h1(`第4章 系统实现`),

      p(`本章从工程实现角度，阐述第3章技术方案的具体落地过程，包括软件架构实现、核心模块编码、数据工程，以及开发过程中遇到的主要困难与解决方案。`),

      h2(`4.1 软件架构实现`),

      p(`系统后端采用Flask框架，入口文件app.py注册了/api/chat、/api/history等RESTful接口。核心业务逻辑分布在src/目录下：graph.py定义LangGraph工作流，state.py定义全局状态RAGState，supervisor.py实现调度逻辑，各Agent分别位于memory.py、router.py、retriever.py、generator.py、validator.py中。前端使用原生JavaScript，通过EventSource监听SSE事件流，实现逐字显示、引用卡片展开、对话历史回显等交互。`),

      p(`在LangGraph图的构建中，七个节点（Supervisor及六个业务Agent）通过add_node注册，以Supervisor为入口，add_conditional_edges根据next_agent字段动态路由，所有业务节点通过add_edge连回Supervisor，形成中心辐射拓扑。该图在应用启动时编译为可执行对象，每次对话调用app_graph.stream()触发。`),

      h2(`4.2 核心模块实现`),

      h3(`4.2.1 检索模块`),

      p(`Retriever模块封装了与Qdrant的交互。调用Qdrant的query_points方法进行向量召回，limit参数设为15（粗召回量），返回结果按余弦相似度降序排列。随后对候选文档执行混合重排序：遍历每个候选，分别计算向量相似度和关键词命中数，按加权公式得出最终评分，截取Top-K返回。理论库和时政库分别由独立的Retriever Agent负责，但共享同一套评分算法，仅在Payload字段名上有差异。`),

      h3(`4.2.2 生成与审核模块`),

      p(`Generator根据query_type选择差异化Prompt：思政模式下角色设定为${LQ}高校思政课教师${RQ}，要求引用时必须标注具体来源章节；闲聊模式切换为${LQ}友善辅导员${RQ}，简短自然。流式输出通过LangChain的StreamingQueueCallbackHandler实现，每个token放入线程安全队列，主线程消费后推送SSE。`),

      p(`Validator调用qwen-flash进行三级审核，输出结构化JSON（passed/reason/confidence）。其闭环修正逻辑是系统应对${LQ}幻觉${RQ}的关键：审核不通过时，根据置信度决定是扩大检索重试还是降级修正，最多重试2次。`),

      h2(`4.3 数据工程`),

      p(`理论知识库的四门教材以Markdown格式存储于content/目录，通过预处理脚本按章节层级解析并分块。每块调用阿里云text-embedding-v4生成稠密向量，同时调用qwen3-max提取5~8个关键词，最终以Qdrant Point格式批量写入theory集合。时政资料库由Python爬虫从人民网等站点采集，保留发布日期、来源媒体等元数据，经相同的分块和双路编码流程写入moment集合。两个集合在Qdrant中完全隔离，互不干扰。`),

      p(`对话数据存储于SQLite，包含conversations表（会话元数据）和messages表（逐条消息，含角色、内容、时间戳）。证据缓存表evidence_cache以conversation_id为主键，存储上一轮的检索结果JSON。`),

      h2(`4.4 系统部署`),

      p(`系统部署在腾讯云Lighthouse服务器（2核4G）上，运行Ubuntu 22.04。使用Gunicorn作为WSGI服务器，通过systemd service管理进程的自动启动与崩溃恢复。Qdrant以Docker容器运行，数据目录挂载至宿主机以持久化。Nginx作为反向代理，处理HTTPS证书和静态资源缓存。前端静态文件由Nginx直接托管，API请求转发至Gunicorn。`),

      h2(`4.5 开发中遇到的困难与解决方案`),

      h3(`4.5.1 思政内容的合规性风险`),

      p(`这是本项目遇到的最大困难。思政教育内容具有特殊的严谨性和合规性要求${DASH}${DASH}一句政治表述的错误，其影响远超普通问答系统的事实性错误。通用大模型在生成思政相关内容时，存在三类典型风险：一是${LQ}幻觉${RQ}导致引用不存在的理论表述；二是对理论概念的简化解读偏离原意；三是生成看似正确但实质消极的${LQ}高级黑${RQ}内容。`),

      p(`为解决这一问题，本系统引入了Validator审核智能体，实施三级审核机制（政治导向、事实准确性、价值引领）。审核不通过时触发闭环修正：扩大检索范围补充材料后重新生成，最多重试2次。这一机制使系统在50题评测中将政治事实性错误率从裸模型的23%降至4%。实际开发中，审核Prompt的调优经历了多次迭代${DASH}${DASH}最初的审核标准过于宽松，导致部分${LQ}低级红${RQ}内容通过；后来增加了对模糊表述的检测规则，审核效果显著提升。`),

      h3(`4.5.2 流式输出与多智能体架构的矛盾`),

      p(`LangGraph的stream()方法是一个阻塞调用，内部依次执行各Agent节点，无法中途将部分结果推送至前端。而SSE要求持续输出，否则浏览器会因长时间无数据而断开连接。解决方案是双线程架构：在子线程中执行LangGraph图，各Agent通过共享队列向主线程推送thinking状态和生成token，主线程持续消费队列并转发SSE，实现了${LQ}边推理边展示${RQ}。`),

      h3(`4.5.3 双库检索的精度调优`),

      p(`初期将理论库和时政库混合存储后，发现理论问题的检索结果中频繁混入时政新闻，导致Generator生成的回答引用了新闻片段而非教材原文。将双库物理隔离后，检索精度明显改善，但仍存在语义相近但无关的文档被错误召回的问题。引入混合评分算法后，通过关键词精确匹配来${LQ}扶正${RQ}语义向量容易遗漏的思政专有名词文档，实测中对${LQ}新质生产力${RQ}等术语的检索命中率提升了约30%。`),

      new Paragraph({ children: [new PageBreak()] }),
      h2(`参考文献`),
      pn(`[1] Lewis P, Perez E, Piktus A, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks[C]//NeurIPS, 2020.`),
      pn(`[2] LangGraph Documentation. LangGraph: Build Language Agent Graphs[EB/OL]. https://langchain-ai.github.io/langgraph/, 2024.`),
      pn(`[3] Gao Y, Xiong Y, Gao X, et al. Retrieval-Augmented Generation for Large Language Models: A Survey[J]. arXiv:2312.10997, 2023.`),
      pn(`[4] Qdrant Team. Qdrant: Vector Database for the Next Generation of AI Applications[EB/OL]. https://qdrant.tech/, 2024.`),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(`d:\\Desktop\\大四学习资料\\workspace\\ideology-platform\\docs\\第3-4章_技术方案与系统实现.docx`, buffer);
  console.log("DOCX generated successfully!");
});
