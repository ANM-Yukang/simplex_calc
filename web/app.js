/* ============================================================
 * app.js —— 单纯形法计算器【网页版】的前端逻辑（纯 JavaScript，不用任何第三方库）
 *
 * 主要做四件事：
 *   1. 维护中英文字典，实现"中文 / English"一键切换；
 *   2. 根据"变量个数 / 约束条数"动态生成填空的"空档"；
 *   3. 把用户填好的题目发给后台 /api/solve（Python 端 simplex_core.py 做计算）；
 *   4. 把后台返回的每张单纯形表画成 HTML 表格（入基列黄色、主元红框），
 *      最后把"最优解 x1=… x2=… 和最优值 z=…"放进大高亮答案框。
 *   另外还有一件不影响做题的小事：顶部星空背景跟着鼠标轻微视差移动。
 * ============================================================ */

/* ---------- 一、中英文字典（页面上所有固定文字都从这里取） ---------- */
const I18N = {
  zh: {
    pageTitle: '单纯形法计算器',
    themeDark: '🌙 深色',
    themeLight: '☀️ 浅色',
    langButton: '🌐 English',              // 右上角"中英双语"按钮上显示要切换到的语言
    inputTitle: '填写题目',
    inputModeLabel: '输入方式',
    inputModeForm: '表单填写',
    inputModeText: '文字输入',
    textHint: '一行写一条：目标函数（max/min …）和每条约束（如 x1 + 2x2 <= 8）；系数可以写 (1+λ)x1，右端项也可以写 8+λ 这样的 λ 式子。',
    textPlaceholder: '例如：\nmax z = 2x1 + 3x2\nx1 + 2x2 <= 8\n4x1 <= 16\n4x2 <= 12\n\n含参数 λ 的例子：\nmax z = (1+λ)x1 + 2x2\nx1 + x2 <= 4\nx1 <= 2\nλ >= 1',
    textEmptyError: '请先在文本框里写题目。',
    lambdaKeyTip: '把光标放到要写 λ 的空档里（目标系数或右端项都行），点一下就在光标处插入 λ（可写 1+λ、8+λ、2-λ）',
    lambdaNote: '光标放到空档里，点一下插入 λ',
    objectiveLabel: '目标函数',
    varCountLabel: '变量个数',
    conCountLabel: '约束条数',
    constraintWord: '约束',
    methodLabel: '做题方法',
    methodAuto: '自动选择',
    methodManual: '手动选择',
    methodHint: '不确定用哪个方法时就选“自动选择”，程序会按题型自动判断。',
    solveButton: '开始求解',
    solvingButton: '正在计算…',
    exampleLabel: '例题：',
    examplePlaceholder: '— 选择例题载入 —',
    inputHint: '每个空档填一个数字（3、-2、1.5、3/2 都行）；目标函数系数或约束右端项都可以含参数 λ（如 1+λ、8+λ）：把光标放到空档里，点 λ 按钮就能在光标处插入。',
    resultTitle: '计算过程与最终答案',
    problemLabel: '题目',
    typeMethodLabel: '题型与方法',
    reasonLabel: '为什么用这个方法',
    standardizedLabel: '标准化说明',
    stdObjective: '标准化后的目标函数',
    processLabel: '计算过程（单纯形表）',
    phase1Title: '第一阶段（最小化人工变量之和 w）',
    phase2Title: '第二阶段（回到原目标函数继续迭代）',
    phase1NoPhase2: '第一阶段已经判定原问题无可行解，不再进入第二阶段。',
    conclusionLabel: '结果讨论与结论',
    answerTitle: '最终答案',
    solutionLabel: '最优解',
    lambdaSectionTitle: '参数 λ 分类讨论',
    criticalValuesLabel: '临界值',
    representativeLabel: '代表点',
    intervalResult: '本区间结论',
    intervalUnbounded: '该区间无界（z → +∞），没有有限最优值',
    piecewiseNote: '含参数 λ 的题目，答案按 λ 的区间分别给出：',
    multipleOptimaNote: '本题有多重最优解，下面这些解的目标值都一样',
    unboundedMsg: '该问题无界：目标值可以无限变大（或变小），没有有限最优解。',
    infeasibleMsg: '该问题无可行解：约束条件互相矛盾，找不到同时满足所有约束的点。',
    limitMsg: '迭代次数达到上限，本次没有算完，请检查输入数据。',
    basisLabel: '当前基变量',
    degenerateTag: '退化表（有基变量等于 0）',
    zLabel: 'z′ 当前值（标准化目标值）',
    enterTag: '本表入基列',
    judgementLabel: '判断',
    formulasSummary: '本表计算公式（点击展开）',
    jumpToAnswer: '↓ 跳到最终答案',
    emptyError: '还有空档没有填写，请补齐后再点“开始求解”。',
    lambdaBothError: '参数 λ 只能写在目标函数系数或右端项的其中一处，不能同时写。',
    networkError: '连接服务器失败：请确认 web_app.py 还在运行，然后刷新页面重试。',
    footer: '学习用途 · 计算核心与命令行版共用 simplex_core.py · 网页后台 web_app.py（纯 Python 标准库，无需安装第三方库）'
  },
  en: {
    pageTitle: 'Simplex Method Calculator',
    themeDark: '🌙 Dark',
    themeLight: '☀️ Light',
    langButton: '🌐 中文',
    inputTitle: 'Enter the problem',
    inputModeLabel: 'Input mode',
    inputModeForm: 'Form fields',
    inputModeText: 'Type it out',
    textHint: 'One statement per line: the objective (max/min …) and each constraint (e.g. x1 + 2x2 <= 8); coefficients like (1+λ)x1 work, and right-hand sides may contain λ too, e.g. 8+λ.',
    textPlaceholder: 'e.g.\nmax z = 2x1 + 3x2\nx1 + 2x2 <= 8\n4x1 <= 16\n4x2 <= 12\n\nwith parameter λ:\nmax z = (1+λ)x1 + 2x2\nx1 + x2 <= 4\nx1 <= 2\nλ >= 1',
    textEmptyError: 'Please type the problem first.',
    lambdaKeyTip: 'Put the cursor in the blank that needs λ (objective coefficient or right-hand side), then click to insert λ (1+λ, 8+λ, 2-λ)',
    lambdaNote: 'put the cursor in a blank, click to insert λ',
    objectiveLabel: 'Objective',
    varCountLabel: 'Variables',
    conCountLabel: 'Constraints',
    constraintWord: 'Constraint',
    methodLabel: 'Method',
    methodAuto: 'Auto',
    methodManual: 'Manual',
    methodHint: 'Not sure which method to use? Keep "Auto" and the program will decide from the problem type.',
    solveButton: 'Solve',
    solvingButton: 'Solving…',
    exampleLabel: 'Examples:',
    examplePlaceholder: '— load an example —',
    inputHint: 'One number per blank (3, -2, 1.5, 3/2 all work); objective coefficients and constraint right-hand sides may contain λ (e.g. 1+λ, 8+λ) — put the cursor in the blank and click the λ button to insert it.',
    resultTitle: 'Process and final answer',
    problemLabel: 'Problem',
    typeMethodLabel: 'Type & method',
    reasonLabel: 'Why this method',
    standardizedLabel: 'Standardization',
    stdObjective: 'Standardized objective',
    processLabel: 'Calculation process (simplex tableaux)',
    phase1Title: 'Phase 1 (minimize the artificial-variable sum w)',
    phase2Title: 'Phase 2 (continue with the original objective)',
    phase1NoPhase2: 'Phase 1 has shown that the original problem is infeasible, so phase 2 is not entered.',
    conclusionLabel: 'Discussion and conclusion',
    answerTitle: 'Final answer',
    solutionLabel: 'Optimal solution',
    lambdaSectionTitle: 'Parametric λ case analysis',
    criticalValuesLabel: 'Critical values',
    representativeLabel: 'sample point',
    intervalResult: 'Result on this interval',
    intervalUnbounded: 'Unbounded on this interval (z → +∞); no finite optimum',
    piecewiseNote: 'For a parametric-λ problem the answer is given interval by interval:',
    multipleOptimaNote: 'This problem has multiple optima; the solutions below all give the same objective value',
    unboundedMsg: 'The problem is unbounded: the objective can grow (or shrink) without bound, so there is no finite optimum.',
    infeasibleMsg: 'The problem is infeasible: the constraints contradict each other and no point satisfies them all.',
    limitMsg: 'The iteration limit was reached before the solution completed; please check the input.',
    basisLabel: 'Current basis',
    degenerateTag: 'degenerate (a basic variable equals 0)',
    zLabel: "z′ (standardized objective)",
    enterTag: 'entering column',
    judgementLabel: 'Judgement',
    formulasSummary: 'Formulas used in this tableau (click to expand)',
    jumpToAnswer: '↓ jump to the final answer',
    emptyError: 'Some blanks are still empty — please fill them in and solve again.',
    lambdaBothError: 'The parameter λ may appear either in the objective coefficients or in the right-hand sides, but not in both at the same time.',
    networkError: 'Failed to reach the server. Make sure web_app.py is still running, then refresh the page.',
    footer: 'For learning · shares simplex_core.py with the console version · served by web_app.py (Python standard library only)'
  }
};

/* ---------- 二、内置例题（从下拉框选一个就自动填好，方便快速体验） ---------- */
const EXAMPLES = [
  {
    name: { zh: '标准 max 型：max z = 2x1 + 3x2', en: 'Standard max: max z = 2x1 + 3x2' },
    type: 'max',
    obj: ['2', '3'],
    constraints: [
      { coeffs: ['1', '2'], sign: '<=', rhs: '8' },
      { coeffs: ['4', '0'], sign: '<=', rhs: '16' },
      { coeffs: ['0', '4'], sign: '<=', rhs: '12' }
    ]
  },
  {
    name: { zh: 'min 型：min z = -x1 + x2', en: 'min type: min z = -x1 + x2' },
    type: 'min',
    obj: ['-1', '1'],
    constraints: [
      { coeffs: ['1', '1'], sign: '<=', rhs: '4' },
      { coeffs: ['1', '0'], sign: '<=', rhs: '3' },
      { coeffs: ['0', '1'], sign: '<=', rhs: '3' }
    ]
  },
  {
    name: { zh: '大M法：含 ≥ 约束', en: 'Big-M: with a ≥ constraint' },
    type: 'max',
    obj: ['1', '2'],
    constraints: [
      { coeffs: ['1', '1'], sign: '<=', rhs: '7' },
      { coeffs: ['2', '-1'], sign: '>=', rhs: '2' }
    ]
  },
  {
    name: { zh: '两阶段法：含 = 与 ≥ 约束', en: 'Two-phase: with = and ≥ constraints' },
    type: 'max',
    obj: ['5', '3'],
    constraints: [
      { coeffs: ['1', '1'], sign: '=', rhs: '6' },
      { coeffs: ['1', '2'], sign: '>=', rhs: '8' }
    ]
  },
  {
    name: { zh: '对偶单纯形法：右端项为负', en: 'Dual simplex: negative right-hand sides' },
    type: 'max',
    obj: ['-1', '-1'],
    constraints: [
      { coeffs: ['-1', '-2'], sign: '<=', rhs: '-3' },
      { coeffs: ['-2', '-1'], sign: '<=', rhs: '-3' }
    ]
  },
  {
    name: { zh: '无界解的例子', en: 'Unbounded example' },
    type: 'max',
    obj: ['1', '1'],
    constraints: [
      { coeffs: ['1', '-1'], sign: '<=', rhs: '1' },
      { coeffs: ['-1', '1'], sign: '<=', rhs: '1' }
    ]
  },
  {
    name: { zh: '无可行解的例子', en: 'Infeasible example' },
    type: 'max',
    obj: ['1', '1'],
    constraints: [
      { coeffs: ['1', '1'], sign: '<=', rhs: '1' },
      { coeffs: ['1', '1'], sign: '>=', rhs: '3' }
    ]
  },
  {
    name: { zh: '多重最优解的例子', en: 'Multiple optima example' },
    type: 'max',
    obj: ['2', '4'],
    constraints: [
      { coeffs: ['1', '2'], sign: '<=', rhs: '5' },
      { coeffs: ['1', '1'], sign: '<=', rhs: '4' }
    ]
  },
  {
    // 目标系数含参数 λ：系数空档里直接写 1+λ（点 λ 按钮就能把 λ 插进去）
    name: { zh: '参数 λ：max z = (1+λ)x1 + 2x2', en: 'Parametric λ: max z = (1+λ)x1 + 2x2' },
    type: 'max',
    obj: ['1+λ', '2'],
    constraints: [
      { coeffs: ['1', '1'], sign: '<=', rhs: '4' },
      { coeffs: ['1', '0'], sign: '<=', rhs: '2' }
    ]
  },
  {
    name: { zh: '参数 λ（min 型）：min z = (2-λ)x1 + 3x2', en: 'Parametric λ (min): min z = (2-λ)x1 + 3x2' },
    type: 'min',
    obj: ['2-λ', '3'],
    constraints: [
      { coeffs: ['1', '1'], sign: '<=', rhs: '4' },
      { coeffs: ['1', '0'], sign: '<=', rhs: '2' }
    ]
  },
  {
    // 右端项含参数 λ：约束右端项空档里直接写 8+λ（把光标放到右端项里，点上面的 λ 按钮就能插进去）
    name: { zh: '参数 λ（右端项）：max z = 2x1 + 3x2，b1 = 8+λ', en: 'Parametric λ (right-hand side): max z = 2x1 + 3x2, b1 = 8+λ' },
    type: 'max',
    obj: ['2', '3'],
    constraints: [
      { coeffs: ['1', '2'], sign: '<=', rhs: '8+λ' },
      { coeffs: ['4', '0'], sign: '<=', rhs: '16' },
      { coeffs: ['0', '4'], sign: '<=', rhs: '12' }
    ]
  }
];

/* ---------- 二·补、手动选择时可用的四种做题方法 ---------- */
// value 保持中文（核心算法用中文方法名判断）；zh/en 只是下拉框里显示的文字。
// 含参数 λ 的题目必须用"参数λ单纯形法"（由程序自动选择），所以这里只列这四种手动方法。
const METHOD_OPTIONS = [
  { value: '普通单纯形法', zh: '普通单纯形法（约束全是 ≤）', en: 'Primal Simplex (all ≤)' },
  { value: '大M法', zh: '大M法（含 ≥ 或 = 约束）', en: 'Big-M Method (with ≥ or =)' },
  { value: '两阶段法', zh: '两阶段法（含 ≥ 或 = 约束）', en: 'Two-Phase Method (with ≥ or =)' },
  { value: '对偶单纯形法', zh: '对偶单纯形法（右端项为负）', en: 'Dual Simplex (negative RHS)' }
];

/* ---------- 三、全局状态与常用小工具 ---------- */

// lang：当前语言（记住用户上次的选择）；solved：是否已经算过一次（切换语言时用它决定要不要重算）；
// methodMode：'auto' = 自动选择做题方法；'manual' = 用下拉框手动挑方法；
// inputMode：'form' = 表单填写；'text' = 自己写题目的文字输入；
// theme：'light' / 'dark'，深色浅色主题（也记住用户上次的选择）
const state = {
  lang: localStorage.getItem('simplex-lang') === 'en' ? 'en' : 'zh',
  solved: false,
  methodMode: 'auto',
  inputMode: 'form',
  theme: localStorage.getItem('simplex-theme') === 'dark' ? 'dark' : 'light'
};

// 取页面元素
function el(id) { return document.getElementById(id); }

// 取当前语言的文字
function t(key) { return I18N[state.lang][key]; }

// 标点小工具：中文用全角，英文用半角，看起来更自然
function colon() { return state.lang === 'en' ? ': ' : '：'; }
function listSeparator() { return state.lang === 'en' ? ', ' : '，'; }
function otherSeparator() { return state.lang === 'en' ? '; ' : '；'; }
function paren(text) { return state.lang === 'en' ? ' (' + text + ')' : '（' + text + '）'; }

// 把文字里的特殊符号转义，防止用户填的内容破坏页面（安全性小常识）
function esc(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// 判断、结论这类长句里是用"；"分句的：把每个分句单独放一行，读起来更清楚
function sentenceLines(text) {
  return esc(text)
    .split(/[；;]/)
    .map(function (part) { return part.trim(); })
    .filter(function (part) { return part !== ''; })
    .join('<br>');
}

// 生成一个小标签（如 "x1"、"+"、蓝色"约束 1"）
function makeSpan(className, text) {
  const span = document.createElement('span');
  span.className = className;
  span.textContent = text;
  return span;
}

// 生成一个数字输入框（value 为空时显示 placeholder 提示）
function makeNumberInput(className, value, placeholder) {
  const input = document.createElement('input');
  input.type = 'text';
  input.className = className;
  input.value = value !== undefined && value !== null ? value : '';
  if (placeholder) input.placeholder = placeholder;
  return input;
}

// 在某个空档的光标处插入 λ：空档已经聚焦就插到光标处，没聚焦就插到末尾；
// 插完把光标放到 λ 后面，并清掉"没填"的红色标记
function insertLambdaAtCursor(input) {
  const focused = document.activeElement === input;
  const start = focused && input.selectionStart !== null ? input.selectionStart : input.value.length;
  const end = focused && input.selectionEnd !== null ? input.selectionEnd : input.value.length;
  input.value = input.value.slice(0, start) + 'λ' + input.value.slice(end);
  input.focus();
  input.setSelectionRange(start + 1, start + 1);
  input.classList.remove('invalid');
}

/* ---------- 四、动态生成输入区 ---------- */

// "变量个数"、"约束条数"两个下拉框的选项（1~8，与核心算法限制一致）
function makeCountOptions() {
  const varSelect = el('var-count');
  const conSelect = el('con-count');
  for (let n = 1; n <= 8; n++) {
    varSelect.add(new Option(String(n), String(n)));
    conSelect.add(new Option(String(n), String(n)));
  }
  varSelect.value = '2';
  conSelect.value = '2';
}

// 生成目标函数的系数空档："max z = [ ]x1 + [ ]x2 + ..."
// 空档里可以填普通数字，也可以填含参数 λ 的式子（1+λ、2-λ），旁边有 λ 按钮帮忙输入
function buildObjectiveInputs(values) {
  const box = el('objective-inputs');
  box.innerHTML = '';
  const count = Number(el('var-count').value);
  for (let j = 0; j < count; j++) {
    if (j > 0) box.appendChild(makeSpan('plus-sign', '+'));
    const slot = document.createElement('span');
    slot.className = 'obj-slot';
    const input = makeNumberInput('num-input obj-input', values ? values[j] : '', '');
    input.setAttribute('aria-label', 'x' + (j + 1));
    slot.appendChild(input);
    box.appendChild(slot);
    box.appendChild(makeSpan('var-name', 'x' + (j + 1)));
  }
}

// 生成每条约束：蓝色"约束 i" + 系数空档 + 符号下拉框（≤ ≥ =）+ 右端项空档
function buildConstraintRows(values) {
  const box = el('constraints-box');
  box.innerHTML = '';
  const varCount = Number(el('var-count').value);
  const rowCount = Number(el('con-count').value);
  for (let i = 0; i < rowCount; i++) {
    const oldRow = values ? values[i] : null;      // 重建前先记住旧数值，尽量保留用户填的内容
    const row = document.createElement('div');
    row.className = 'constraint-row';
    row.appendChild(makeSpan('con-label', t('constraintWord') + ' ' + (i + 1)));
    for (let j = 0; j < varCount; j++) {
      if (j > 0) row.appendChild(makeSpan('plus-sign', '+'));
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'num-input coef-input';
      input.value = oldRow && oldRow.coeffs[j] !== undefined ? oldRow.coeffs[j] : '';
      input.setAttribute('aria-label', 'x' + (j + 1));
      row.appendChild(input);
      row.appendChild(makeSpan('var-name', 'x' + (j + 1)));
    }
    const signSelect = document.createElement('select');
    signSelect.className = 'sign-select';
    [['<=', '≤'], ['>=', '≥'], ['=', '=']].forEach(function (pair) {
      signSelect.add(new Option(pair[1], pair[0]));
    });
    signSelect.value = oldRow && oldRow.sign ? oldRow.sign : '<=';
    row.appendChild(signSelect);
    const rhsInput = document.createElement('input');
    rhsInput.type = 'text';
    rhsInput.className = 'num-input rhs-input';
    rhsInput.value = oldRow && oldRow.rhs !== undefined ? oldRow.rhs : '';
    rhsInput.setAttribute('aria-label', 'b');
    row.appendChild(rhsInput);
    box.appendChild(row);
  }
}

// 把页面上现在填的内容读出来（改条数、切语言时用它保留旧内容）
function readCurrentValues() {
  return {
    // 目标系数：直接读每个空档里写的内容（可能是数字，也可能含 λ）
    obj: Array.from(document.querySelectorAll('#objective-inputs .obj-input')).map(function (input) {
      return input.value;
    }),
    constraints: Array.from(document.querySelectorAll('#constraints-box .constraint-row')).map(function (row) {
      return {
        coeffs: Array.from(row.querySelectorAll('.coef-input')).map(function (input) { return input.value; }),
        sign: row.querySelector('.sign-select').value,
        rhs: row.querySelector('.rhs-input').value
      };
    })
  };
}

// 条数改变时重建输入区，并把原来填好的数字尽量保留
function rebuildInputs() {
  const old = readCurrentValues();
  buildObjectiveInputs(old.obj);
  buildConstraintRows(old.constraints);
}

// 例题下拉框的文字（中英文各一份）
function refreshExampleOptions() {
  const select = el('example-select');
  const oldValue = select.value;
  select.innerHTML = '';
  select.add(new Option(t('examplePlaceholder'), ''));
  EXAMPLES.forEach(function (example, index) {
    select.add(new Option(example.name[state.lang], String(index)));
  });
  select.value = oldValue;
  if (select.selectedIndex === -1) select.selectedIndex = 0;
}

// 一个"系数×变量"项的文字：2x2、"1"→x2、"-1"→-x2、0 直接省略；
// 含 λ 的多段式子加括号，如 (1+λ)x1；2λ、-λ 这类单段式直接写在变量前
function coefficientTerm(value, name) {
  let text = String(value === undefined ? '' : value).trim().replace(/\s+/g, '');
  if (text === '' || text === '0') return '';
  if (text.startsWith('(') && text.endsWith(')')) text = text.slice(1, -1).trim();   // 已带括号就不重复加
  const numberLike = /^[-+]?\d+(\.\d+)?(\/\d+)?$/.test(text);
  const lambdaLike = /^[-+]?(\d+(\.\d+)?(\/\d+)?)?λ$/.test(text);
  if (lambdaLike) return text + name;                 // 2λx1、-λx2
  if (!numberLike) return '(' + text + ')' + name;    // 1+λ、2-λ 等多段式子
  if (text === '1') return name;
  if (text === '-1') return '-' + name;
  return text + name;
}

// 把"目标类型 + 系数空档内容"拼成文字（文字输入模式用），如 "max z = (1+λ)x1 + 2x2"
function objectiveText(type, values) {
  const terms = values.map(function (value, index) {
    return coefficientTerm(value, 'x' + (index + 1));
  }).filter(function (term) { return term !== ''; });
  return type + ' z = ' + terms.join(' + ').replace(/\+ -/g, '- ');
}

// 把一条约束拼成文字，如 "x1 + 2x2 <= 8"
function constraintText(coeffs, sign, rhs) {
  const terms = coeffs.map(function (value, index) {
    const text = String(value === '' || value === undefined ? '0' : value).trim() || '0';
    return coefficientTerm(text, 'x' + (index + 1));
  }).filter(function (term) { return term !== ''; });
  const left = terms.length > 0 ? terms.join(' + ').replace(/\+ -/g, '- ') : '0';
  const right = String(rhs === '' || rhs === undefined ? '0' : rhs).trim() || '0';
  return left + ' ' + sign + ' ' + right;
}

// 把一道例题转成文字题目（文字输入模式下选例题用）
function exampleToText(example) {
  const lines = [objectiveText(example.type, example.obj)];
  example.constraints.forEach(function (row) { lines.push(constraintText(row.coeffs, row.sign, row.rhs)); });
  return lines.join('\n');
}

// 把表单里现在填好的内容转成文字题目（切到文字模式时自动填进文本框，方便对照修改）
function formToText() {
  const current = readCurrentValues();
  const lines = [objectiveText(el('objective-type').value, current.obj)];
  current.constraints.forEach(function (row) { lines.push(constraintText(row.coeffs, row.sign, row.rhs)); });
  return lines.join('\n');
}

// 把一道例题填进输入区（表单模式填表单；文字模式把题目转成文字填进文本框）
function fillExample(example) {
  el('objective-type').value = example.type;
  el('var-count').value = String(example.obj.length);
  el('con-count').value = String(example.constraints.length);
  buildObjectiveInputs(example.obj.slice());
  buildConstraintRows(example.constraints);
  if (state.inputMode === 'text') {
    el('problem-text').value = exampleToText(example);
  }
}

// 方法下拉框的选项文字（中英文各一份；value 不变，一直是中文方法名）
function refreshMethodOptions() {
  const select = el('method-select');
  const oldValue = select.value;
  select.innerHTML = '';
  METHOD_OPTIONS.forEach(function (method) {
    select.add(new Option(state.lang === 'en' ? method.en : method.zh, method.value));
  });
  if (oldValue) select.value = oldValue;
}

// 切换"自动选择 / 手动选择"两个按钮的选中状态
function setMethodMode(mode) {
  state.methodMode = mode;
  el('method-auto').classList.toggle('active', mode === 'auto');
  el('method-manual').classList.toggle('active', mode === 'manual');
  el('method-select').disabled = mode !== 'manual';      // 自动模式下下拉框是灰的，不能点
}

/* ---------- 五、收集题目并请求后台求解 ---------- */

// 当前选择的做题方法（自动模式发"自动"；手动模式发下拉框里选的方法名）
function currentMethod() {
  return state.methodMode === 'manual' ? el('method-select').value : '自动';
}

// 切换 表单填写 / 文字输入 两种方式
function setInputMode(mode) {
  state.inputMode = mode;
  el('inputmode-form').classList.toggle('active', mode === 'form');
  el('inputmode-text').classList.toggle('active', mode === 'text');
  el('form-inputs').classList.toggle('hidden', mode !== 'form');
  el('text-input-wrap').classList.toggle('hidden', mode !== 'text');
  // 切到文字模式时，如果文本框是空的，就把表单里已经填好的题目转成文字填进去，方便对照修改
  if (mode === 'text' && el('problem-text').value.trim() === '') {
    el('problem-text').value = formToText();
  }
}

// 检查空档 / 收集数据，并把题目整理成要发给后台的数据
function collectRequest() {
  if (state.inputMode === 'text') {
    // 文字输入：把整段文字交给后台的"题目识别"模块处理
    const textValue = el('problem-text').value.trim();
    if (textValue === '') throw new Error(t('textEmptyError'));
    return { lang: state.lang, mode: 'text', method: currentMethod(), text: textValue };
  }
  // 表单输入：检查每个空档都填了没有（目标系数空档里也可以写含 λ 的式子）
  let emptyFound = false;
  document.querySelectorAll('.obj-input, .coef-input, .rhs-input').forEach(function (input) {
    input.classList.remove('invalid');
    if (input.value.trim() === '') {
      input.classList.add('invalid');       // 没填的空档标红
      emptyFound = true;
    }
  });
  if (emptyFound) throw new Error(t('emptyError'));
  const current = readCurrentValues();
  // 预检：参数 λ 只能写在目标函数系数或右端项的其中一处，两处同时写后端 solve() 也会拒绝；
  // 这里提前拦下来，把出问题的空档标红，提示比后端报错更友好
  const objHasLambda = current.obj.some(function (value) { return String(value).indexOf('λ') !== -1; });
  const rhsHasLambda = current.constraints.some(function (row) { return String(row.rhs).indexOf('λ') !== -1; });
  if (objHasLambda && rhsHasLambda) {
    document.querySelectorAll('#objective-inputs .obj-input, #constraints-box .rhs-input').forEach(function (input) {
      if (input.value.indexOf('λ') !== -1) input.classList.add('invalid');
    });
    throw new Error(t('lambdaBothError'));
  }
  return {
    lang: state.lang,
    mode: 'form',
    method: currentMethod(),
    type: el('objective-type').value,
    obj: current.obj,
    constraints: current.constraints.map(function (row) {
      return { coeffs: row.coeffs, sign: row.sign, rhs: row.rhs };
    })
  };
}

// 点"开始求解"：把题目发给后台，把结果显示出来
async function solveProblem() {
  const errorBox = el('error-box');
  const solveButton = el('solve-button');
  errorBox.classList.add('hidden');

  let payload;
  try {
    payload = collectRequest();
  } catch (error) {                        // 有空档没填
    hideResult();
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
    return;
  }

  solveButton.disabled = true;
  const oldText = solveButton.textContent;
  solveButton.textContent = t('solvingButton');
  try {
    const response = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const json = await response.json();
    if (!json.ok) {                        // 后台说输入有问题（比如某格不是数字、方法和题型不符）
      hideResult();
      errorBox.textContent = json.error;
      errorBox.classList.remove('hidden');
      return;
    }
    state.solved = true;
    renderResult(json.data);
  } catch (error) {                        // 连不上服务器（比如 web_app.py 被关掉了）
    hideResult();
    errorBox.textContent = t('networkError');
    errorBox.classList.remove('hidden');
  } finally {
    solveButton.disabled = false;
    solveButton.textContent = oldText;
  }
}

/* ---------- 六、把计算结果显示到页面上 ---------- */

// 求解失败时把上一次的旧结果收起来，避免和当前输入混淆（老结果对应的可能是别的题目）
function hideResult() {
  el('result-card').classList.add('hidden');
  state.solved = false;
}

// 总入口：依次拼出"题目摘要 -> 标准化说明 -> 表格 -> 结论 -> 最终答案"
function renderResult(data) {
  const parts = [];

  // 顶部状态徽章 + "跳到最终答案"链接
  parts.push(
    '<div class="result-head">' +
      '<span class="status-chip status-' + data.status_code + '">' + esc(data.status_text) + '</span>' +
      '<a class="jump-link" href="#answer-box">' + esc(t('jumpToAnswer')) + '</a>' +
    '</div>'
  );

  // 题目摘要
  parts.push(
    '<div class="summary-box">' +
      '<div><b>' + esc(t('problemLabel')) + colon() + '</b>' + esc(data.problem_text) + '</div>' +
      '<div><b>' + esc(t('typeMethodLabel')) + colon() + '</b>' + esc(data.problem_type) + ' · ' + esc(data.method) + '</div>' +
      '<div><b>' + esc(t('reasonLabel')) + colon() + '</b>' + esc(data.method_reason) + '</div>' +
    '</div>'
  );

  // 标准化说明（第一步怎么加松弛/剩余/人工变量）
  parts.push('<h3>' + esc(t('standardizedLabel')) + '</h3>');
  parts.push('<ol class="notes">');
  data.conversion_notes.forEach(function (note) { parts.push('<li>' + esc(note) + '</li>'); });
  parts.push('</ol>');
  parts.push('<p class="std-objective"><b>' + esc(t('stdObjective')) + colon() + '</b>' + esc(data.standardized_objective) + '</p>');

  // 计算过程：λ 题按区间分组画；两阶段法先画第一阶段、再画第二阶段；其它方法直接画
  parts.push('<h3>' + esc(t('processLabel')) + '</h3>');
  let tableNumber = 0;
  if (data.lambda) {
    parts.push('<div class="lambda-summary">' + esc(t('criticalValuesLabel')) + colon() + esc(data.lambda.critical_values) + '</div>');
    data.lambda.intervals.forEach(function (interval) {
      parts.push(
        '<h4 class="interval-title">λ ∈ ' + esc(interval.interval_text) +
        '　<span class="interval-rep">' + esc(t('representativeLabel')) + ' λ0 = ' + esc(interval.representative) + '</span></h4>'
      );
      parts.push('<div class="judgement phase-judgement">' + sentenceLines(interval.judgement) + '</div>');
      interval.tables.forEach(function (table) {
        tableNumber += 1;
        parts.push(renderTableau(table, tableNumber));
      });
      if (interval.optimal_ok && interval.solution_text) {
        let verdict = esc(t('intervalResult')) + colon() + esc(interval.solution_text) +
                      '　·　' + esc(data.objective_name) + ' = ' + esc(interval.value_text || '');
        if (interval.basis_text) {
          verdict = esc(t('basisLabel')) + colon() + esc(interval.basis_text) + '；' + verdict;
        }
        parts.push('<div class="interval-verdict">' + verdict + '</div>');
      } else {
        parts.push('<div class="interval-verdict unbounded">' + esc(t('intervalUnbounded')) + '</div>');
      }
      if (interval.endpoint_notes && interval.endpoint_notes.length > 0) {
        parts.push('<div class="interval-endpoint">' + interval.endpoint_notes.map(esc).join('<br>') + '</div>');
      }
    });
  } else {
    if (data.phase1) {
      parts.push('<h4 class="phase-title">' + esc(t('phase1Title')) + '</h4>');
      parts.push('<div class="judgement phase-judgement">' + sentenceLines(data.phase1.judgement) + '</div>');
      data.phase1.tables.forEach(function (table) {
        tableNumber += 1;
        parts.push(renderTableau(table, tableNumber));
      });
      if (data.phase1.entered_phase_two) {
        parts.push('<h4 class="phase-title">' + esc(t('phase2Title')) + '</h4>');
      } else {
        parts.push('<p class="phase-end">' + esc(t('phase1NoPhase2')) + '</p>');
      }
    }
    data.tables.forEach(function (table) {
      tableNumber += 1;
      parts.push(renderTableau(table, tableNumber));
    });
  }

  // 结果讨论与结论（后台生成的多行文字，CSS 里用 pre-wrap 保留换行）
  parts.push('<h3>' + esc(t('conclusionLabel')) + '</h3>');
  parts.push('<div class="conclusion-box">' + sentenceLines(data.conclusion) + '</div>');

  // 最显眼的最终答案大框
  parts.push(renderAnswer(data));

  el('result-body').innerHTML = parts.join('');
  el('result-card').classList.remove('hidden');
  el('result-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 画一张单纯形表：
//   表头：编号徽章 + 标题（"单纯形表（第 N 轮）"等）
//   第一行 cj →    各变量的目标系数
//   第二行 cB xB b 各变量名
//   中间行          每条约束
//   最后一行 σj     检验数
//   （基变量列涂淡蓝；入基列涂黄；主元格子加深并加红框）
function renderTableau(table, number) {
  const columnCount = table.var_names.length;
  const enter = table.enter_col;           // 入基列（后台算好；没有则为 null）
  const leave = table.leave_row;           // 离基行（后台算好；没有则为 null）

  function columnClass(j) { return j === enter ? ' enter-col' : ''; }

  // animation-delay：让多张表出现时有一点点"依次浮出"的感觉（最多错开 8 张）
  const delay = Math.min(number, 8) * 0.05;
  let html = '<div class="tableau-card" style="animation-delay:' + delay + 's">';
  html += '<div class="tableau-head">' +
            '<span class="tableau-badge">' + number + '</span>' +
            '<span class="tableau-title">' + esc(table.title) + '</span>' +
          '</div>';
  html += '<div class="tableau-caption">' + esc(t('basisLabel')) + colon() + esc(table.basis_names.join(' → '));
  if (table.degenerate) {
    html += ' <span class="chip chip-warn">' + esc(t('degenerateTag')) + '</span>';
  }
  html += '</div>';

  html += '<div class="tableau-scroll"><table class="simplex-table">';

  // 第一行：cj → 各变量的目标系数
  html += '<tr class="row-cj"><td class="corner"></td><td class="row-label">cj →</td><td class="corner"></td>';
  for (let j = 0; j < columnCount; j++) {
    html += '<td class="num' + columnClass(j) + '">' + esc(table.c[j]) + '</td>';
  }
  html += '</tr>';

  // 第二行：cB xB b + 变量名（基变量画蓝底）
  html += '<tr class="row-head"><th>cB</th><th>xB</th><th>b</th>';
  for (let j = 0; j < columnCount; j++) {
    const isBasis = table.basis.indexOf(j) !== -1;
    html += '<th class="num' + columnClass(j) + (isBasis ? ' basis-mark' : '') + '">' + esc(table.var_names[j]) + '</th>';
  }
  html += '</tr>';

  // 中间：每条约束一行
  for (let i = 0; i < table.matrix.length; i++) {
    html += '<tr>';
    html += '<td class="num">' + esc(table.basis_coeffs[i]) + '</td>';
    html += '<th class="basis-name">' + esc(table.basis_names[i]) + '</th>';
    html += '<td class="num' + (i === leave ? ' leave-row' : '') + '">' + esc(table.rhs[i]) + '</td>';
    for (let j = 0; j < columnCount; j++) {
      const isPivot = (i === leave && j === enter);
      html += '<td class="num' + columnClass(j) + (isPivot ? ' pivot-cell' : '') + '">' + esc(table.matrix[i][j]) + '</td>';
    }
    html += '</tr>';
  }

  // 最后：σj 检验数行
  html += '<tr class="row-sigma"><td></td><th class="row-label">σj</th><td></td>';
  for (let j = 0; j < columnCount; j++) {
    html += '<td class="num' + columnClass(j) + '">' + esc(table.sigma[j]) + '</td>';
  }
  html += '</tr>';

  html += '</table></div>';

  // 表下小字：当前 z′ 值、本表选了哪一列入基
  html += '<div class="tableau-footer">' + esc(t('zLabel')) + ' = ' + esc(table.objective_value);
  if (enter !== null && enter !== undefined) {
    html += '　<span class="chip chip-enter">' + esc(t('enterTag')) + colon() + esc(table.var_names[enter]) + '</span>';
  }
  html += '</div>';

  // 本表判断（为什么选这一列、比值检验结果、是否最优等）
  html += '<div class="judgement">' + esc(t('judgementLabel')) + colon() + sentenceLines(table.judgement) + '</div>';

  // 本表计算公式：默认折叠，想看细节点开
  if (table.formulas.length > 0) {
    html += '<details class="formulas"><summary>' + esc(t('formulasSummary')) + '</summary>' +
            '<pre>' + esc(table.formulas.join('\n')) + '</pre></details>';
  }

  html += '</div>';
  return html;
}

// 画最终答案大框：
//   有最优解 -> 绿底大字："最优解：x1 = …，x2 = …" + "max z = …"（多重最优解还会列出备选解）
//   无界 / 无可行 / 没算完 -> 橙色警示框说明原因
function renderAnswer(data) {
  // 参数 λ 题：答案按区间分段显示
  if (data.answer && data.answer.piecewise) {
    const rows = data.answer.piecewise.map(function (piece) {
      let body;
      if (piece.optimal) {
        body = esc(piece.solution_text || '') + '　·　' + esc(data.objective_name) + ' = ' + esc(piece.value_text || '');
      } else {
        body = '<span class="answer-piece-unbounded">' + esc(piece.note) + '</span>';
      }
      return '<div class="answer-piece">' +
        '<span class="answer-piece-range">λ ∈ ' + esc(piece.interval_text) + '</span>' +
        '<span class="answer-piece-body">' + body + '</span>' +
      '</div>';
    }).join('');
    return '<div class="answer-box" id="answer-box">' +
      '<div class="answer-title">✅ ' + esc(t('answerTitle')) + '</div>' +
      '<div class="answer-piece-note">' + esc(t('piecewiseNote')) + '</div>' +
      rows +
    '</div>';
  }
  if (data.answer) {
    const item = data.answer;
    const solutionText = item.solution.map(function (s) { return s.name + ' = ' + s.value; }).join(listSeparator());
    let html = '<div class="answer-box" id="answer-box">';
    html += '<div class="answer-title">✅ ' + esc(t('answerTitle')) + '</div>';
    html += '<div class="answer-solution">' + esc(t('solutionLabel')) + colon() + esc(solutionText) + '</div>';
    html += '<div class="answer-value">' + esc(data.objective_name) + ' = ' + esc(item.value_text) + '</div>';
    if (item.multiple && item.alternatives.length > 1) {
      const others = item.alternatives.slice(1).map(function (alt) {
        const text = alt.solution.map(function (s) { return s.name + ' = ' + s.value; }).join(listSeparator());
        return text + paren(data.objective_name + ' = ' + alt.value_text);
      }).join(otherSeparator());
      html += '<div class="answer-note">' + esc(t('multipleOptimaNote')) + colon() + esc(others) + '</div>';
    }
    html += '</div>';
    return html;
  }
  let message = t('limitMsg');
  if (data.status_code === 'unbounded') message = t('unboundedMsg');
  if (data.status_code === 'infeasible') message = t('infeasibleMsg');
  return '<div class="answer-box warn" id="answer-box">' +
    '<div class="answer-title">⚠️ ' + esc(t('answerTitle')) + '</div>' +
    '<div class="answer-solution">' + esc(message) + '</div>' +
    '</div>';
}

/* ---------- 七、语言切换与主题切换 ---------- */

// 点"中文 / English"按钮
function toggleLanguage() {
  state.lang = state.lang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('simplex-lang', state.lang);     // 记住选择，下次打开还是这个语言
  applyLanguage();
}

// 应用主题：给 <html> 加上 data-theme="dark"，CSS 里两套颜色就自动切换；
// 按钮文字显示"要切换到的主题"（现在浅色就显示"🌙 深色"）
function applyTheme() {
  document.documentElement.dataset.theme = state.theme;
  el('theme-button').textContent = state.theme === 'dark' ? t('themeLight') : t('themeDark');
}

// 点"🌙 深色 / ☀️ 浅色"按钮
function toggleTheme() {
  state.theme = state.theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('simplex-theme', state.theme);
  applyTheme();
}

// 按当前语言刷新整个界面
function applyLanguage() {
  document.documentElement.lang = state.lang === 'en' ? 'en' : 'zh-CN';
  document.title = t('pageTitle');
  // 所有带 data-i18n 标记的固定文字统一替换
  document.querySelectorAll('[data-i18n]').forEach(function (element) {
    element.textContent = t(element.dataset.i18n);
  });
  el('lang-button').textContent = t('langButton');
  applyTheme();                  // 主题按钮的文字要按当前语言刷新
  el('problem-text').placeholder = t('textPlaceholder');   // 文字输入框里的示例提示
  el('lambda-key').title = t('lambdaKeyTip');              // λ 按钮的悬停提示
  // 约束行里"约束 1"这样的标签、例题下拉框和方法下拉框的文字也要换（重建时保留已填数字）
  buildConstraintRows(readCurrentValues().constraints);
  refreshExampleOptions();
  refreshMethodOptions();
  // 如果已经算过一次，就用新语言自动重算一遍，让表格、判断、结论的文字都跟着切换
  if (state.solved) solveProblem();
}

/* ---------- 八、顶部星空的鼠标视差（纯装饰，出错也不影响做题） ---------- */

// 鼠标在页面上移动时，先算出它在窗口里的相对位置（-1 ~ 1），写进 <header class="hero">
// 的 --star-x / --star-y 两个变量；CSS 里三层星空各自乘上自己的"深度"，
// 远层动得少、近层动得多，看起来就有远近感，也就是星星跟着鼠标稍微动一点。
function initStarParallax() {
  const hero = document.querySelector('.hero');
  if (!hero) return;
  // 系统里开了"减少动态效果"就不做视差（星空仍然静态显示）
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

  let targetX = 0, targetY = 0;     // 鼠标算出来的目标偏移
  let currentX = 0, currentY = 0;   // 星星当前的偏移（缓动追上去，看起来更柔和）
  let animating = false;

  // 逐帧把当前值往目标值靠，靠上了就停掉循环，省点电
  function step() {
    currentX += (targetX - currentX) * 0.08;
    currentY += (targetY - currentY) * 0.08;
    hero.style.setProperty('--star-x', currentX.toFixed(4));
    hero.style.setProperty('--star-y', currentY.toFixed(4));
    if (Math.abs(targetX - currentX) < 0.0005 && Math.abs(targetY - currentY) < 0.0005) {
      animating = false;
      return;
    }
    requestAnimationFrame(step);
  }

  function start() {
    if (!animating) { animating = true; requestAnimationFrame(step); }
  }

  // 把鼠标坐标换算成以窗口中心为原点的 -1 ~ 1 偏移量
  function aim(clientX, clientY) {
    const rect = hero.getBoundingClientRect();
    if (rect.bottom < 0 || rect.top > window.innerHeight) {   // 顶部区域滚出视线了就不用动
      targetX = 0;
      targetY = 0;
      return;
    }
    targetX = Math.max(-1, Math.min(1, (clientX - (rect.left + rect.width / 2)) / (window.innerWidth / 2)));
    targetY = Math.max(-1, Math.min(1, (clientY - (rect.top + rect.height / 2)) / (window.innerHeight / 2)));
  }

  window.addEventListener('mousemove', function (event) {
    aim(event.clientX, event.clientY);
    start();
  });
  // 鼠标移出窗口：星星慢慢回到原位
  document.addEventListener('mouseleave', function () {
    targetX = 0;
    targetY = 0;
    start();
  });
}

/* ---------- 九、页面启动 ---------- */

function init() {
  makeCountOptions();
  refreshExampleOptions();
  fillExample(EXAMPLES[0]);      // 打开页面先摆好例题 1 的数据，点"开始求解"立刻能看到完整效果

  el('solve-button').addEventListener('click', solveProblem);
  el('lang-button').addEventListener('click', toggleLanguage);
  el('theme-button').addEventListener('click', toggleTheme);
  el('method-auto').addEventListener('click', function () { setMethodMode('auto'); });
  el('method-manual').addEventListener('click', function () { setMethodMode('manual'); });
  el('inputmode-form').addEventListener('click', function () { setInputMode('form'); });
  el('inputmode-text').addEventListener('click', function () { setInputMode('text'); });
  // λ 按钮：全页只有这一颗。先记住最后点过的空档（目标系数、约束系数、右端项都算），
  // 点按钮就在那个空档的光标处插入 λ（mousedown 里 preventDefault，免得点按钮时输入框失焦、光标丢失）
  let lastNumberInput = null;
  document.addEventListener('focusin', function (event) {
    if (event.target.classList && event.target.classList.contains('num-input')) lastNumberInput = event.target;
  });
  const lambdaKey = el('lambda-key');
  lambdaKey.addEventListener('mousedown', function (event) {
    event.preventDefault();       // 别把输入光标从空档里抢走
  });
  lambdaKey.addEventListener('click', function () {
    const focused = document.activeElement;
    let target = (focused && focused.classList && focused.classList.contains('num-input'))
      ? focused : lastNumberInput;
    if (!target || !document.body.contains(target)) {          // 没聚焦过 / 空档被"改条数"重建掉了
      target = document.querySelector('#objective-inputs .obj-input');
    }
    if (target) insertLambdaAtCursor(target);
  });
  el('var-count').addEventListener('change', rebuildInputs);
  el('con-count').addEventListener('change', rebuildInputs);
  el('example-select').addEventListener('change', function (event) {
    if (event.target.value !== '') fillExample(EXAMPLES[Number(event.target.value)]);
  });
  // 在空档里按回车 = 点"开始求解"
  document.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && event.target.classList && event.target.classList.contains('num-input')) {
      solveProblem();
    }
  });

  setMethodMode('auto');         // 默认用"自动选择方法"
  applyLanguage();               // 按上次记住的语言（默认中文）先刷新一遍界面
  initStarParallax();            // 顶部星空的鼠标视差（纯装饰）
}

init();
