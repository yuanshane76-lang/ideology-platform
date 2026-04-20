# tests/eval_questions.py
# 思政问答评估题集（LLM-as-Judge 对比测试）
# 题目设计覆盖4类问题：理论类、时政类、混合类、应用类
# 共50道题：纯理论15题 / 时政10题 / 混合15题 / 应用10题

EVAL_QUESTIONS = [

    # ── 类别一：纯理论类（共15题）────────────────────────────────────────────────
    {
        "id": "TH-01", "category": "theory", "label": "纯理论",
        "question": "什么是唯物辩证法的对立统一规律？请结合具体例子说明其在现实生活中的体现。",
        "expected_focus": "对立统一规律、矛盾、毛泽东思想或马列原著引用",
    },
    {
        "id": "TH-02", "category": "theory", "label": "纯理论",
        "question": "如何理解马克思主义的群众史观？人民群众在历史发展中发挥了怎样的作用？",
        "expected_focus": "群众史观、历史创造者、人民主体性",
    },
    {
        "id": "TH-03", "category": "theory", "label": "纯理论",
        "question": "习近平新时代中国特色社会主义思想的核心要义是什么？",
        "expected_focus": "两个确立、十四个坚持、党的十九大报告",
    },
    {
        "id": "TH-04", "category": "theory", "label": "纯理论",
        "question": "马克思主义实践观的基本内涵是什么？实践在认识中处于怎样的地位？",
        "expected_focus": "实践第一、认识来源于实践、实践是检验真理的标准",
    },
    {
        "id": "TH-05", "category": "theory", "label": "纯理论",
        "question": "如何理解生产力与生产关系的辩证关系？这一原理对中国经济改革有何指导意义？",
        "expected_focus": "生产力决定生产关系、生产关系反作用、历史唯物主义",
    },
    {
        "id": "TH-06", "category": "theory", "label": "纯理论",
        "question": "什么是唯物辩证法的否定之否定规律？请举例说明事物发展的螺旋式上升过程。",
        "expected_focus": "否定之否定、辩证否定、螺旋式发展",
    },
    {
        "id": "TH-07", "category": "theory", "label": "纯理论",
        "question": "马克思主义认识论的基本观点是什么？感性认识与理性认识的关系如何？",
        "expected_focus": "感性认识、理性认识、辩证统一、实践检验",
    },
    {
        "id": "TH-08", "category": "theory", "label": "纯理论",
        "question": "社会主义核心价值观的主要内容是什么？为什么说培育它是凝魂聚气的基础工程？",
        "expected_focus": "富强民主文明和谐、自由平等公正法治、爱国敬业诚信友善",
    },
    {
        "id": "TH-09", "category": "theory", "label": "纯理论",
        "question": "中国特色社会主义制度的显著优势体现在哪些方面？如何理解制度自信？",
        "expected_focus": "中国特色社会主义制度、党的集中统一领导、制度优势",
    },
    {
        "id": "TH-10", "category": "theory", "label": "纯理论",
        "question": "马克思政治经济学中的剩余价值理论揭示了什么？对理解资本主义本质有何意义？",
        "expected_focus": "剩余价值、劳动价值论、资本主义剥削本质",
    },
    {
        "id": "TH-11", "category": "theory", "label": "纯理论",
        "question": "中国式现代化有哪些鲜明的中国特色？它与西方现代化模式有何本质区别？",
        "expected_focus": "人口规模巨大、共同富裕、人与自然和谐、和平发展",
    },
    {
        "id": "TH-12", "category": "theory", "label": "纯理论",
        "question": "共产主义远大理想与中国特色社会主义共同理想是什么关系？大学生应如何处理二者关系？",
        "expected_focus": "远大理想与共同理想统一、阶段性目标、理想信念教育",
    },
    {
        "id": "TH-13", "category": "theory", "label": "纯理论",
        "question": "如何理解'两个结合'——马克思主义同中国具体实际相结合、同中华优秀传统文化相结合？",
        "expected_focus": "两个结合、马克思主义中国化时代化、中华文明根脉",
    },
    {
        "id": "TH-14", "category": "theory", "label": "纯理论",
        "question": "什么是全过程人民民主？它与西方选举民主制度相比有哪些本质区别和制度优势？",
        "expected_focus": "全过程人民民主、选举民主、协商民主、人民当家作主",
    },
    {
        "id": "TH-15", "category": "theory", "label": "纯理论",
        "question": "人类命运共同体理念的哲学依据是什么？它体现了马克思主义哪些基本原理？",
        "expected_focus": "唯物辩证法联系观、整体性思维、反对零和博弈",
    },

    # ── 类别二：时政类（共10题）──────────────────────────────────────────────────
    {
        "id": "PO-01", "category": "politics", "label": "时政",
        "question": "党的二十届三中全会提出了哪些重要改革举措？这对推进中国式现代化有何意义？",
        "expected_focus": "三中全会、全面深化改革、中国式现代化",
    },
    {
        "id": "PO-02", "category": "politics", "label": "时政",
        "question": "什么是新质生产力？发展新质生产力的关键路径是什么？",
        "expected_focus": "新质生产力、科技创新、高质量发展",
    },
    {
        "id": "PO-03", "category": "politics", "label": "时政",
        "question": "面对复杂的国际贸易环境和外部压力，中国经济为何能保持较强韧性？",
        "expected_focus": "经济韧性、内需市场、产业链完整、高质量发展战略",
    },
    {
        "id": "PO-04", "category": "politics", "label": "时政",
        "question": "中国推进共同富裕的核心举措有哪些？如何避免'先富带后富'变成口号？",
        "expected_focus": "共同富裕、分配制度改革、三次分配、区域协调发展",
    },
    {
        "id": "PO-05", "category": "politics", "label": "时政",
        "question": "中国在应对气候变化方面做出了哪些重要承诺？'双碳'目标的战略意义是什么？",
        "expected_focus": "碳达峰碳中和、2030年2060年目标、绿色低碳转型",
    },
    {
        "id": "PO-06", "category": "politics", "label": "时政",
        "question": "'一带一路'倡议的核心理念是什么？它如何体现中国的外交主张和发展合作观？",
        "expected_focus": "共商共建共享、互联互通、人类命运共同体、南南合作",
    },
    {
        "id": "PO-07", "category": "politics", "label": "时政",
        "question": "乡村振兴战略的总要求是什么？当前推进乡村振兴面临的主要挑战有哪些？",
        "expected_focus": "产业兴旺生态宜居乡风文明治理有效生活富裕、三农问题",
    },
    {
        "id": "PO-08", "category": "politics", "label": "时政",
        "question": "数字经济对中国经济转型升级有什么战略意义？国家在数字经济领域有哪些重要布局？",
        "expected_focus": "数字经济、数字中国、平台经济治理、数据要素市场",
    },
    {
        "id": "PO-09", "category": "politics", "label": "时政",
        "question": "新时代加强国防和军队建设的核心原则是什么？党对军队的绝对领导为何是强军之魂？",
        "expected_focus": "党对军队绝对领导、强军目标、世界一流军队",
    },
    {
        "id": "PO-10", "category": "politics", "label": "时政",
        "question": "中国特色大国外交的核心理念和主要目标是什么？与霸权主义外交有何本质区别？",
        "expected_focus": "独立自主和平外交政策、大国关系、周边外交、多边主义",
    },

    # ── 类别三：理论+时政混合类（共15题）────────────────────────────────────────
    {
        "id": "HY-01", "category": "hybrid", "label": "混合",
        "question": "运用马克思主义生产力理论分析，为什么说发展新质生产力是推动高质量发展的内在要求？",
        "expected_focus": "生产力理论、生产关系、新质生产力与高质量发展",
    },
    {
        "id": "HY-02", "category": "hybrid", "label": "混合",
        "question": "从历史唯物主义视角分析，中国共产党为什么能够带领人民实现脱贫攻坚的伟大成就？",
        "expected_focus": "历史唯物主义、党的领导核心、脱贫攻坚、人民主体地位",
    },
    {
        "id": "HY-03", "category": "hybrid", "label": "混合",
        "question": "请结合生态文明理论，谈谈'绿水青山就是金山银山'理念的哲学内涵和实践意义。",
        "expected_focus": "生态文明思想、两山理论、人与自然和谐共生",
    },
    {
        "id": "HY-04", "category": "hybrid", "label": "混合",
        "question": "运用矛盾论分析当前中美关系，斗争性与同一性如何在双边关系中具体体现？",
        "expected_focus": "矛盾的同一性和斗争性、中美博弈与合作共存、底线思维",
    },
    {
        "id": "HY-05", "category": "hybrid", "label": "混合",
        "question": "马克思主义群众史观如何解释人民代表大会制度的制度设计逻辑？",
        "expected_focus": "群众史观、人民代表大会制度、人民主权原则",
    },
    {
        "id": "HY-06", "category": "hybrid", "label": "混合",
        "question": "马克思主义文化理论如何指导中华优秀传统文化的创造性转化与创新性发展？",
        "expected_focus": "社会存在与社会意识、文化强国、创造性转化创新性发展",
    },
    {
        "id": "HY-07", "category": "hybrid", "label": "混合",
        "question": "运用唯物辩证法的发展观，如何看待改革开放以来中国社会的深刻变革与曲折前进？",
        "expected_focus": "前进性与曲折性统一、量变质变规律、改革开放历程",
    },
    {
        "id": "HY-08", "category": "hybrid", "label": "混合",
        "question": "马克思主义分配理论如何解释中国推进共同富裕政策的内在逻辑？",
        "expected_focus": "按劳分配为主、多种分配方式、第三次分配、共同富裕路径",
    },
    {
        "id": "HY-09", "category": "hybrid", "label": "混合",
        "question": "从认识论视角分析'实事求是'思想路线，它如何在党的历史重大转折中发挥指导作用？",
        "expected_focus": "实事求是、从实际出发、遵义会议、改革开放历史节点",
    },
    {
        "id": "HY-10", "category": "hybrid", "label": "混合",
        "question": "运用社会基本矛盾理论，解释新时代我国社会主要矛盾发生了怎样的历史性转化？",
        "expected_focus": "社会主要矛盾转变、美好生活需要、不平衡不充分发展",
    },
    {
        "id": "HY-11", "category": "hybrid", "label": "混合",
        "question": "马克思主义国家学说如何解释中国共产党执政的历史合法性与现实合法性？",
        "expected_focus": "国家本质、政权人民性、党的执政合法性、历史选择",
    },
    {
        "id": "HY-12", "category": "hybrid", "label": "混合",
        "question": "从历史唯物主义角度论证科技强国战略的必要性，科技与生产力是什么关系？",
        "expected_focus": "科技是第一生产力、创新驱动发展战略、生产力发展规律",
    },
    {
        "id": "HY-13", "category": "hybrid", "label": "混合",
        "question": "马克思关于人的全面发展理论如何指导我们理解教育强国战略的深层逻辑？",
        "expected_focus": "人的全面发展、教育目的论、劳动与教育相结合",
    },
    {
        "id": "HY-14", "category": "hybrid", "label": "混合",
        "question": "生产关系必须适应生产力发展的规律如何解释国有企业深化改革的内在动力？",
        "expected_focus": "生产关系变革、所有制改革、国企混改、市场化方向",
    },
    {
        "id": "HY-15", "category": "hybrid", "label": "混合",
        "question": "从马克思主义全球化理论来看，如何对'逆全球化'思潮和单边主义进行批判性分析？",
        "expected_focus": "全球化本质、资本主义内在矛盾、多边主义、人类命运共同体",
    },

    # ── 类别四：应用/引导类（共10题）────────────────────────────────────────────
    {
        "id": "AP-01", "category": "applied", "label": "应用",
        "question": "作为当代大学生，应该如何理解'四个自信'？在日常学习和生活中如何践行？",
        "expected_focus": "道路自信、理论自信、制度自信、文化自信、日常践行路径",
    },
    {
        "id": "AP-02", "category": "applied", "label": "应用",
        "question": "面对西方国家对中国制度的质疑，我们应该如何理性看待和有理有据地回应？",
        "expected_focus": "制度自信、制度比较优势、中国特色社会主义制度实践成效",
    },
    {
        "id": "AP-03", "category": "applied", "label": "应用",
        "question": "面对激烈的就业竞争和生活压力，大学生应如何用马克思主义理想信念克服焦虑？",
        "expected_focus": "理想信念、奋斗精神、个人价值与社会价值统一、人生观",
    },
    {
        "id": "AP-04", "category": "applied", "label": "应用",
        "question": "网络上流行的历史虚无主义言论有何危害？大学生应如何辨别和批驳？",
        "expected_focus": "历史虚无主义危害、唯物史观、党史国史、批判性思维",
    },
    {
        "id": "AP-05", "category": "applied", "label": "应用",
        "question": "作为有志青年，应如何理解和参与乡村振兴战略？青年在其中能发挥什么独特作用？",
        "expected_focus": "乡村振兴、青年担当、返乡创业、服务基层情怀",
    },
    {
        "id": "AP-06", "category": "applied", "label": "应用",
        "question": "大学生如何在日常生活中践行绿色发展理念，成为生态文明建设的积极参与者？",
        "expected_focus": "绿色生活方式、个人生态责任、节能减排实践",
    },
    {
        "id": "AP-07", "category": "applied", "label": "应用",
        "question": "有同学认为'思政课都是大道理，与现实脱节'，你如何用具体事例反驳这种观点？",
        "expected_focus": "思政课的价值、理论联系实际、世界观方法论作用",
    },
    {
        "id": "AP-08", "category": "applied", "label": "应用",
        "question": "如何正确认识中西方文化差异，做到既不自卑于西方文化也不排斥外来文明？",
        "expected_focus": "文化自信、文明交流互鉴、批判性吸收、文化主体性",
    },
    {
        "id": "AP-09", "category": "applied", "label": "应用",
        "question": "面对社会上流行的'躺平'文化，应如何用马克思主义实践观和奋斗精神加以回应？",
        "expected_focus": "实践第一、劳动价值观、奋斗精神、青年自我实现",
    },
    {
        "id": "AP-10", "category": "applied", "label": "应用",
        "question": "如何理解当代青年在中国式现代化进程中的历史使命？青年与民族复兴是什么关系？",
        "expected_focus": "青年强则国家强、历史使命、民族复兴、强国有我",
    },
]
