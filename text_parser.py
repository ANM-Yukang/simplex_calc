# -*- coding: utf-8 -*-
"""
text_parser.py —— “自己写题目”的文字识别模块

把用户在文本框里写的一段题目文字，解析成 web_app.py / simplex_core.py
能直接使用的数据结构（目标类型、目标系数、约束矩阵、符号、右端项）。

支持的写法示例（一行写一条，也可以用分号分隔）：
    max z = 2x1 + 3x2          目标函数（max/min 都行，z 和 = 可以省略）
    x1 + 2x2 <= 8              约束（<=、>=、=，中文的 ≤、≥ 也认）
    4x1 <= 16
    x2 >= 2
    x1 + x2 = 6
    (1+λ)x1 + 2x2              目标系数可以带参数 λ（也可写 2λx1）
    x1 + x2 <= 8+λ             约束的右端项也可以带参数 λ（如 8+λ、2-λ、λ+8、3+2λ；
                               λ 项写在式子里的哪个位置都行，但约束左边只能写普通数字）
    λ >= 1                     可选：λ 的讨论下界（默认 0）
    x1, x2 >= 0                这种“非负性”说明行会自动跳过（本来默认就 ≥ 0）

系数支持整数、小数、分数（如 3、-2、1.5、3/2）；-x1 表示 -1×x1；x1 表示 1×x1。
本模块只做“文字 → 数据”，不打印、不读文件。
"""

import re
from fractions import Fraction

# ==================== 一、共用的小工具（web_app.py 也会 import 这几个） ====================

# 中文输入法可能打出全角字符（１２３、－、．），先统一换成半角再解析
FULL_WIDTH_TABLE = str.maketrans({
    '０': '0', '１': '1', '２': '2', '３': '3', '４': '4',
    '５': '5', '６': '6', '７': '7', '８': '8', '９': '9',
    '－': '-', '＋': '+', '．': '.', '，': ',', '　': ' ',
})


def normalize_text(text):
    """把全角数字、全角符号换成半角，并去掉首尾空格。"""
    return str(text).translate(FULL_WIDTH_TABLE).strip()


def pick(lang, zh_text, en_text):
    """按当前语言挑一句提示文字。"""
    return en_text if lang == 'en' else zh_text


def parse_number(text, where_zh, where_en, lang):
    """把一个数字文字转成精确分数（Fraction）；不是数字就抛出让用户看懂的错误。"""
    cleaned = normalize_text(text)
    if cleaned == '':
        raise ValueError(pick(lang, '%s 还没有填写。' % where_zh, '%s is empty.' % where_en))
    try:
        return Fraction(cleaned)
    except (ValueError, ZeroDivisionError):
        raise ValueError(pick(
            lang,
            '%s 填的“%s”不是有效数字（可以填 3、-2、1.5、3/2 这样的数）。' % (where_zh, text),
            'The value "%s" for %s is not a valid number (try 3, -2, 1.5 or 3/2).' % (text, where_en)))


# ==================== 二、线性表达式解析 ====================

# 数字的样子：3、1.5、3/2（正负号由外层处理）
NUMBER_PATTERN = r'\d+(?:\.\d+)?(?:/\d+)?'


def parse_plain_number(text, lang):
    """把一段纯数字文字变成 Fraction（支持 3、1.5、3/2、-2）。"""
    text = str(text).strip()
    if text in ('', '+', '-'):
        raise ValueError(pick(lang, '这里缺一个数字。', 'a number is missing here.'))
    try:
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        raise ValueError(pick(lang, '“%s”不是有效数字。' % text, '“%s” is not a valid number.' % text))


def parse_lambda_inner(text, lang):
    """解析含 λ 的表达式（1+λ、1-2λ、2λ、λ、λ+8、2λ+1 等），返回 (p, q)，即 p + qλ。

    λ 可以写在式子里的任意位置：常数项与 λ 项按 + / - 拆开后分别累加，
    所以 8+λ、λ+8、1-2λ、2λ+1 都能解析。
    """
    text = text.strip()
    if 'λ' not in text:
        return parse_plain_number(text, lang), Fraction(0)
    # 按 + / - 把式子切成若干项（保留每项自己的符号），例如 2λ+1 → ['2λ', '+1']
    terms = re.findall(r'[+-]?[^+-]+', text)
    if ''.join(terms).strip() != text:               # 有落单的 + / - 之类，说明式子没写完整
        raise ValueError(pick(lang, '“%s”不是有效的含 λ 式子。' % text,
                              '“%s” is not a valid λ expression.' % text))
    total_p = Fraction(0)
    total_q = Fraction(0)
    for term in terms:
        term = term.strip()
        if 'λ' in term:
            sign = 1
            if term[0] in '+-':
                sign, term = (-1 if term[0] == '-' else 1), term[1:].strip()
            # λ 项只允许写成「数字λ」或「λ」：λ、-λ、2λ、1/2λ
            if term != 'λ' and re.fullmatch(NUMBER_PATTERN + r'λ', term) is None:
                raise ValueError(pick(lang, '“%s”里的 λ 项看不懂（可以写 λ、2λ、1-λ 这样）。' % text,
                                      'the λ term in “%s” is not understood (write λ, 2λ or 1-λ).' % text))
            factor_text = term[:-1]
            factor = Fraction(1) if factor_text == '' else parse_plain_number(factor_text, lang)
            total_q += sign * factor
        else:
            sign = 1
            if term[0] in '+-':
                sign, term = (-1 if term[0] == '-' else 1), term[1:].strip()
            if term == '':
                raise ValueError(pick(lang, '“%s”不是有效的含 λ 式子。' % text,
                                      '“%s” is not a valid λ expression.' % text))
            total_p += sign * parse_plain_number(term, lang)
    return total_p, total_q


def parse_coefficient(text, where_zh, where_en, lang):
    """解析一个系数空档：普通数字（3、1.5、3/2）或含参数 λ 的式子（1+λ、2-λ、1+2λ、2λ、λ+8）。

    返回 (p, q)，表示这个系数等于 p + qλ；普通数字的 q 就是 0。
    """
    cleaned = normalize_text(text)
    # 允许整体带一层括号，如 (1+λ)；也允许写成 lamda / lambda 拼写
    if cleaned.startswith('(') and cleaned.endswith(')') and cleaned.count('(') == 1:
        cleaned = cleaned[1:-1].strip()
    cleaned = re.sub(r'lamda|lambda', 'λ', cleaned, flags=re.IGNORECASE)
    if 'λ' not in cleaned:
        if re.search(r'[a-zA-Z]', cleaned):    # 例如误把变量名也写进来了（1+x2）
            raise ValueError(pick(
                lang,
                '%s 填的“%s”看不懂：只能填数字（3、1.5、3/2）或含 λ 的式子（1+λ、2-λ）。' % (where_zh, text),
                'The value "%s" for %s is not understood; fill in a number (3, 1.5, 3/2) or a λ expression (1+λ, 2-λ).' % (text, where_en)))
        return parse_number(cleaned, where_zh, where_en, lang), Fraction(0)
    try:
        return parse_lambda_inner(cleaned, lang)
    except ValueError:
        raise ValueError(pick(
            lang,
            '%s 填的“%s”看不懂：λ 系数可以写成 1+λ、2-λ、8+λ、λ+8、1+2λ、2λ 这样。' % (where_zh, text),
            'The value "%s" for %s is not understood; write λ expressions like 1+λ, 2-λ, 8+λ, λ+8, 1+2λ or 2λ.' % (text, where_en)))


def parse_rhs(text, where_zh, where_en, lang):
    """解析约束的右端项：普通数字返回 Fraction；含参数 λ（8+λ、2-λ、λ、3+2λ）时返回 (p, q) 元组（= p + qλ）。

    右端项是唯一允许出现 λ 的地方（约束左边只能写普通数字），
    所以这里复用 parse_coefficient 的 λ 解析逻辑，再把"没有 λ"的情况简化回普通的 Fraction，
    保证原有普通数字题目的解析结果完全不变。
    """
    cleaned = normalize_text(text).replace(' ', '').replace('*', '').replace('×', '')
    p, q = parse_coefficient(cleaned, where_zh, where_en, lang)
    return p if q == 0 else (p, q)


def parse_term(chunk, lang, allow_lambda):
    """解析一项（不含它前面的正负号），返回 (变量下标, p, q)；常数项返回下标 None。"""
    chunk = chunk.strip()
    if chunk == '':
        raise ValueError(pick(lang, '有一个空项，检查一下加号两边是否漏写了东西。',
                              'an empty term — check the expression around the plus signs.'))
    # 带括号的写法：(1+λ)x2、(-2)x1
    if '(' in chunk or ')' in chunk:
        match = re.match(r'^\(([^()]+)\)(.*)$', chunk)
        if match is None:
            raise ValueError(pick(lang, '括号没写完整，例如要写成 (1+λ)x1。',
                                  'incomplete parentheses; write e.g. (1+λ)x1.'))
        inner, rest = match.group(1).strip(), match.group(2).strip()
        if 'λ' in inner and not allow_lambda:
            raise ValueError(pick(lang, '参数 λ 只能写在目标函数里或约束的右端项中（约束左边只能写普通数字）。',
                                  'the parameter λ may only appear in the objective or in a right-hand side (keep the left-hand side numeric).'))
        if rest == '':
            raise ValueError(pick(lang, '括号后面要跟变量名，例如 (1+λ)x1。',
                                  'a variable name must follow the parentheses, e.g. (1+λ)x1.'))
        var_match = re.match(r'^x(\d*)$', rest)
        if var_match is None:
            raise ValueError(pick(lang, '“%s”看不懂，变量请写成 x1、x2 这样的形式。' % rest,
                                  '"%s" not understood; write variables like x1, x2.' % rest))
        p, q = parse_lambda_inner(inner, lang)
        return int(var_match.group(1) or 1), p, q
    # 不带括号、含 λ 的写法：2λx1、λx2
    lambda_var_match = re.match(r'^(' + NUMBER_PATTERN + r')?λx(\d*)$', chunk)
    if lambda_var_match is not None:
        if not allow_lambda:
            raise ValueError(pick(lang, '参数 λ 只能写在目标函数里或约束的右端项中（约束左边只能写普通数字）。',
                                  'the parameter λ may only appear in the objective or in a right-hand side (keep the left-hand side numeric).'))
        q = parse_plain_number(lambda_var_match.group(1), lang) if lambda_var_match.group(1) else Fraction(1)
        return int(lambda_var_match.group(2) or 1), Fraction(0), q
    # 普通项：3x2、3/2x1、x3
    var_match = re.match(r'^(' + NUMBER_PATTERN + r')?x(\d*)$', chunk)
    if var_match is not None:
        p = parse_plain_number(var_match.group(1), lang) if var_match.group(1) else Fraction(1)
        return int(var_match.group(2) or 1), p, Fraction(0)
    # 纯数字项（常数项）
    if re.match(r'^' + NUMBER_PATTERN + r'$', chunk):
        return None, parse_plain_number(chunk, lang), Fraction(0)
    if 'λ' in chunk:
        raise ValueError(pick(lang, '带 λ 的系数请写成 (p+qλ)x1 或 2λx1 的形式，并且跟着变量名。',
                              'write λ coefficients as (p+qλ)x1 or 2λx1, followed by a variable.'))
    raise ValueError(pick(lang, '“%s”看不懂；系数请写成 3x1、-x2、3/2x3 这样的形式。' % chunk,
                          '"%s" not understood; write terms like 3x1, -x2 or 3/2x3.' % chunk))


def parse_linear_expression(expr, lang, allow_lambda):
    """解析一个线性表达式，返回 ({变量下标: (p, q)}, 常数项)。"""
    expr = expr.replace(' ', '').replace('*', '').replace('×', '')   # 乘号可写可不写：2*x1 = 2x1
    if expr == '':
        raise ValueError(pick(lang, '这里是空的，没有写表达式。', 'the expression here is empty.'))
    coefficients = {}
    constant = Fraction(0)
    sign = 1
    depth = 0
    current = ''
    pieces = []
    for ch in expr:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth < 0:
                raise ValueError(pick(lang, '括号不配对，检查一下多余的右括号。', 'unbalanced parentheses.'))
        if ch in '+-' and depth == 0:
            if current == '':
                if ch == '-':
                    sign = -sign                  # 开头的负号（或连续符号）
                continue
            pieces.append((sign, current))
            current = ''
            sign = 1 if ch == '+' else -1
            continue
        current += ch
    if depth != 0:
        raise ValueError(pick(lang, '括号不配对，检查一下是不是少了右括号。', 'unbalanced parentheses.'))
    if current != '':
        pieces.append((sign, current))
    if not pieces:
        raise ValueError(pick(lang, '这里没有可以识别的项。', 'no recognizable terms here.'))
    for sign_value, chunk in pieces:
        index, p, q = parse_term(chunk, lang, allow_lambda)
        if index is None:                          # 常数项
            constant += sign_value * p
            continue
        p, q = sign_value * p, sign_value * q
        if index in coefficients:
            old_p, old_q = coefficients[index]
            coefficients[index] = (old_p + p, old_q + q)
        else:
            coefficients[index] = (p, q)
    return coefficients, constant


def split_constraint(statement, lang):
    """把一条约束按 <= / >= / = 拆成 (左边, 符号, 右边)。"""
    candidates = []
    for symbol in ('<=', '>=', '='):
        pos = statement.find(symbol)
        if pos != -1:
            candidates.append((pos, symbol))
    if not candidates:
        raise ValueError(pick(lang, '没找到 <=、>= 或 =，分开左边和右边。',
                              'no <=, >= or = found to separate the two sides.'))
    pos, symbol = min(candidates, key=lambda item: item[0])
    return statement[:pos], symbol, statement[pos + len(symbol):]


# ==================== 三、整段题目的解析（主入口） ====================

def parse_problem_text(text, lang):
    """把整段题目文字解析成题目数据。

    返回字典：
        original_type / obj_coeffs / constraint_matrix / signs / rhs_list /
        lambda_lower_bound（λ 的下界，默认 0）/ has_lambda（目标是否含 λ）

    λ 可以写在目标系数里（(1+λ)x1、2λx2），也可以写在约束的右端项里（如 8+λ、2-λ），
    但两者不能同时出现（核心算法会给出提示）；约束左边只能写普通数字。
    右端项里没有 λ 时仍是 Fraction，含 λ 时是 (p, q) 元组（= p + qλ）。
    """
    # 统一符号写法：≤ ≥、最大值、lambda 的各种拼写
    cleaned = normalize_text(text)
    cleaned = cleaned.replace('≤', '<=').replace('≥', '>=')
    cleaned = cleaned.replace('最大化', 'max').replace('最小化', 'min').replace('最大', 'max').replace('最小', 'min')
    cleaned = re.sub(r'lamda|lambda', 'λ', cleaned, flags=re.IGNORECASE)

    statements = [piece.strip() for piece in re.split(r'[;\n；]+', cleaned) if piece.strip() != '']
    if not statements:
        raise ValueError(pick(lang, '题目是空的，请先写一点内容（例如 max z = 2x1 + 3x2）。',
                              'The text is empty; write something like max z = 2x1 + 3x2.'))

    objective = None                                # (max/min, {变量下标: (p,q)})
    constraints = []                                # (系数字典, 符号, 右端项)
    lambda_lower = Fraction(0)

    for i, raw_statement in enumerate(statements):
        statement = raw_statement.lower()           # max/max 大小写都认
        try:
            # 1) 目标函数：以 max / min 开头
            if statement.startswith('max') or statement.startswith('min'):
                match = re.match(r'^(max|min)\s*(.*)$', statement)
                original_type, expression = match.group(1), match.group(2).strip()
                if expression.startswith('z'):      # 允许写 "z ="，也允许直接省略
                    expression = expression[1:].strip()
                    if expression.startswith('='):
                        expression = expression[1:].strip()
                coefficients, constant = parse_linear_expression(expression, lang, allow_lambda=True)
                if constant != 0:
                    raise ValueError(pick(lang, '目标函数不要写常数项（只写带变量的部分）。',
                                          'do not write a constant term in the objective.'))
                if objective is not None:
                    raise ValueError(pick(lang, '只能写一个目标函数。', 'only one objective is allowed.'))
                objective = (original_type, coefficients)
                continue
            # 2) λ 的讨论下界：λ >= 1（默认 0，可以不写）
            if statement.startswith('λ'):
                match = re.match(r'^λ\s*(?:>=|>|=)\s*(.+)$', statement)
                if match is None:
                    raise ValueError(pick(lang, 'λ 这一行请写成 λ >= 1 这样的形式（默认 λ >= 0）。',
                                          'write it as λ >= 1 (the default is λ >= 0).'))
                lambda_lower = parse_plain_number(match.group(1), lang)
                continue
            # 3) 约束：必须带 <=、>= 或 =
            if ('<=' in statement) or ('>=' in statement) or ('=' in statement):
                left, symbol, right = split_constraint(statement, lang)
                # 3a) “x1, x2 >= 0”这种非负性说明行：直接跳过（变量本来默认 ≥ 0）
                if re.fullmatch(r'x\d*([,，、\s]+x\d*)*', left.strip()) and right.strip() in ('0', '+0'):
                    continue
                coefficients, constant = parse_linear_expression(left, lang, allow_lambda=False)
                if constant != 0:
                    raise ValueError(pick(lang, '不等号左边不要写常数项，请把常数移到右边。',
                                          'move constant terms to the right-hand side.'))
                if 'x' in right.lower():
                    raise ValueError(pick(lang, '请把变量都写到不等号左边，右边只写常数或含 λ 的式子（如 8+λ）。',
                                          'move all variables to the left-hand side; keep a constant or a λ expression (e.g. 8+λ) on the right.'))
                # 右端项可以含参数 λ：普通数字仍是 Fraction，含 λ（8+λ、2-λ、λ、3+2λ）时是 (p, q) 元组
                rhs = parse_rhs(right, '约束右端项', 'right-hand side of a constraint', lang)
                constraints.append((coefficients, symbol, rhs))
                continue
            # 4) 其它情况：给提示
            raise ValueError(pick(lang, '看不懂这一行；目标函数要以 max 或 min 开头，约束要有 <=、>= 或 =。',
                                  'this line is not understood; start the objective with max or min, and use <=, >= or = in constraints.'))
        except ValueError as error:
            raise ValueError(pick(lang, '第 %d 段「%s」：%s' % (i + 1, raw_statement, error),
                                  'Statement %d "%s": %s' % (i + 1, raw_statement, error)))

    if objective is None:
        raise ValueError(pick(lang, '没有找到目标函数，请写一行以 max 或 min 开头的式子。',
                              'No objective found; add a line starting with max or min.'))
    if not constraints:
        raise ValueError(pick(lang, '至少写一条约束（记得带 <=、>= 或 =）。',
                              'Write at least one constraint (with <=, >= or =).'))

    # 变量个数 = 出现过的最大变量下标（x1、x2……）
    original_type, obj_dict = objective
    all_indices = set(obj_dict)
    for coefficient in constraints:
        all_indices.update(coefficient[0])
    if not all_indices:
        raise ValueError(pick(lang, '没有找到变量，请用 x1、x2 这样的写法。',
                              'No variables found; write them like x1, x2.'))
    var_count = max(all_indices)
    if var_count > 8:
        raise ValueError(pick(lang, '变量个数要在 1~8 之间。', 'The number of variables must be between 1 and 8.'))

    # 有任何一个目标系数带 λ，就整体走“参数 λ”模式（每个系数都写成 p + qλ）
    has_lambda = any(q != 0 for _, q in obj_dict.values())
    obj_coeffs = []
    for j in range(1, var_count + 1):
        p, q = obj_dict.get(j, (Fraction(0), Fraction(0)))
        obj_coeffs.append((p, q) if has_lambda else p)

    constraint_matrix = []
    signs = []
    rhs_list = []
    for coefficient, symbol, rhs in constraints:
        row = []
        for j in range(1, var_count + 1):
            p, _q = coefficient.get(j, (Fraction(0), Fraction(0)))
            row.append(p)
        constraint_matrix.append(row)
        signs.append(symbol)
        rhs_list.append(rhs)

    return {
        'original_type': original_type,
        'obj_coeffs': obj_coeffs,
        'constraint_matrix': constraint_matrix,
        'signs': signs,
        'rhs_list': rhs_list,
        'lambda_lower_bound': lambda_lower,
        'has_lambda': has_lambda,
    }
