# -*- coding: utf-8 -*-
"""
simplex_calc 单纯形表计算器 —— 核心公式模块
把线性规划问题标准化成单纯形表，计算检验数 σ、比值 θ 并做旋转变换，实现普通单纯形法、
大M法、两阶段法、对偶单纯形法与带参数 λ 的单纯形法，并渲染表格与中文结论。
只用标准库 copy/fractions，不读写文件、不打印、不读键盘，只返回字符串与字典。
数值约定：所有数一律用 Fraction 精确计算，判零即等于 0。
"""

import copy                      # 深拷贝：旋转时不修改原表
from fractions import Fraction   # 精确有理数

# ==================== 一、模块常量 ====================

# 全部精确运算，不使用浮点容差；此常量只为保留接口而设，判零统一用 is_zero。
EPS = Fraction(0)
MAX_ITERATIONS = 50  # 迭代主循环的默认上限，防止退化时循环不停


# ==================== 二、数值与文本工具 ====================

def is_zero(num):
    """判断一个数是不是 0（精确判断，没有容差）。"""
    return to_fraction(num) == 0


def to_fraction(num):
    """把普通数字转成精确有理数 Fraction（后续运算就不会有浮点误差）。"""
    if isinstance(num, Fraction):
        return num
    return Fraction(num)


def number_to_text(num, decimal_places=4):
    """把数值变成表格里显示的文本（精确显示，不做四舍五入）。"""
    if isinstance(num, tuple):                       # 万一把含参数表达式传进来，交给 parametric_to_text
        return parametric_to_text(num)
    value = to_fraction(num)
    if value == 0:
        return '0'
    minus_sign = '-' if value < 0 else ''
    absolute_value = abs(value)
    denominator = absolute_value.denominator
    if denominator == 1:
        return minus_sign + str(absolute_value.numerator)
    temp = denominator
    twos_count = 0
    while temp % 2 == 0:
        temp = temp // 2
        twos_count += 1
    fives_count = 0
    while temp % 5 == 0:
        temp = temp // 5
        fives_count += 1
    if temp != 1:                              # 分母含其它因子 → 用分数显示，保证精确
        return minus_sign + '%d/%d' % (absolute_value.numerator, absolute_value.denominator)
    digit_count = max(twos_count, fives_count)              # 分母 = 2^a × 5^b → 化成 10^位数 的有限小数
    numerator = absolute_value.numerator * (10 ** digit_count) // absolute_value.denominator
    text = str(numerator)
    if len(text) <= digit_count:
        text = '0' * (digit_count + 1 - len(text)) + text
    integer_part = text[:-digit_count]
    fractional_part = text[-digit_count:].rstrip('0')
    return minus_sign + integer_part + '.' + fractional_part


def value_to_text(value, symbol=None):
    """把"普通数值"或"含参数表达式"统一转成显示文本。"""
    if is_expression(value):
        return parametric_to_text(value, symbol if symbol else 'M')
    return number_to_text(value)


def is_expression(value):
    """判断一个值是"含参数表达式"还是普通数值。"""
    return isinstance(value, tuple)


def to_expression(value):
    """把值统一成含参数表达式（普通数字补一个 0 参数部分）。"""
    if is_expression(value):
        return (to_fraction(value[0]), to_fraction(value[1]))
    return (to_fraction(value), Fraction(0))


def term_coefficient_text(value, symbol=None):
    """写"系数×变量"里系数的显示文本（含加减号的参数式加括号，普通数字原样）。"""
    text = value_to_text(value, symbol)
    if is_expression(value) and ('+' in text or '-' in text):
        return '(' + text + ')'
    return text


def format_row(term_list):
    """把若干小片段用加减号拼起来（负项用减号，不写 '+ -'）。"""
    result = ''
    for term in term_list:
        if result == '':
            result = term
        elif term.startswith('-'):
            result = result + ' - ' + term[1:]
        else:
            result = result + ' + ' + term
    return result if result else '0'


def product_text(coefficient_text, value_text):
    """写"系数×值"，值是负数时给值加括号。"""
    if value_text.startswith('-'):
        return '%s×(%s)' % (coefficient_text, value_text)
    return '%s×%s' % (coefficient_text, value_text)


def elimination_segment_text(left_label, old_value, coefficient, pivot_row_value, new_value):
    """写一条消元计算片段："新值 = 旧值 - 系数×主行值"，系数为负时自动写成加号。"""
    old_text = number_to_text(old_value)
    pivot_row_text = number_to_text(pivot_row_value)
    new_text = number_to_text(new_value)
    if coefficient > 0:
        return '%s = %s - %s = %s' % (left_label, old_text, product_text(number_to_text(coefficient), pivot_row_text), new_text)
    return '%s = %s + %s = %s' % (left_label, old_text, product_text(number_to_text(-coefficient), pivot_row_text), new_text)


# ==================== 三、含参数表达式工具（大M法的 M、参数 λ 共用） ====================

def parametric_expr(constant_part, parameter_part):
    """构造含参数表达式（大M法的 M、参数 λ 共用）。"""
    return (to_fraction(constant_part), to_fraction(parameter_part))


def parametric_to_text(expr, symbol='M'):
    """把含参数表达式变成文本（常数部分在前、参数部分在后）。"""
    constant_part, parameter_part = to_fraction(expr[0]), to_fraction(expr[1])
    constant_text = number_to_text(constant_part)
    if parameter_part == 0:
        return constant_text
    if parameter_part == 1:
        parameter_text = symbol                      # 系数是 1 → 省略数字
    elif parameter_part == -1:
        parameter_text = '-' + symbol                # 系数是 -1 → 只写负号
    else:
        parameter_text = number_to_text(parameter_part) + symbol
    if constant_part == 0:
        return parameter_text
    if parameter_text.startswith('-'):
        return constant_text + parameter_text           
    return constant_text + '+' + parameter_text         


def parametric_linear_combination(coefficient_list, expr_list):
    """含参数表达式的线性组合（σ 行计算用）。"""
    constant_sum = Fraction(0)
    parameter_sum = Fraction(0)
    for coefficient, expr in zip(coefficient_list, expr_list):
        constant_sum = constant_sum + to_fraction(coefficient) * to_fraction(expr[0])
        parameter_sum = parameter_sum + to_fraction(coefficient) * to_fraction(expr[1])
    return (constant_sum, parameter_sum)


def parametric_is_zero(expr):
    """表达式是否恒等于 0（精确判断）。"""
    return to_fraction(expr[0]) == 0 and to_fraction(expr[1]) == 0


def parametric_is_positive(expr):
    """在"M 充分大"的意义下表达式是否为正（大M法判据）。"""
    constant_part, parameter_part = to_fraction(expr[0]), to_fraction(expr[1])
    if parameter_part > 0:
        return True
    if parameter_part < 0:
        return False
    return constant_part > 0


def parametric_compare(expr_a, expr_b):
    """按"M 充分大"的字典序比较两个表达式（先比参数部分，再比常数部分）。"""
    parameter_diff = to_fraction(expr_a[1]) - to_fraction(expr_b[1])
    if parameter_diff > 0:
        return 1
    if parameter_diff < 0:
        return -1
    constant_diff = to_fraction(expr_a[0]) - to_fraction(expr_b[0])
    if constant_diff > 0:
        return 1
    if constant_diff < 0:
        return -1
    return 0


def lambda_eval(expr, lambda_value):
    """把含参数表达式在某个 λ0 处精确求值（参数 λ 法在每个区间的代表点上用）。"""
    return to_fraction(expr[0]) + to_fraction(expr[1]) * to_fraction(lambda_value)


def find_critical_lambda(sigma_list, lower_bound, upper_bound):
    """找出让 σ 行"变号或改变大小次序"的临界 λ 值（参数 λ 法的关键）。"""
    lower_bound_value = to_fraction(lower_bound)
    upper_bound_value = None if upper_bound is None else to_fraction(upper_bound)
    candidates = []
    column_count = len(sigma_list)
    for j in range(column_count):
        p, q = to_fraction(sigma_list[j][0]), to_fraction(sigma_list[j][1])
        if q != 0:
            candidates.append(-p / q)                                   
    for i in range(column_count):
        for j in range(i + 1, column_count):
            p_i, q_i = to_fraction(sigma_list[i][0]), to_fraction(sigma_list[i][1])
            p_j, q_j = to_fraction(sigma_list[j][0]), to_fraction(sigma_list[j][1])
            if q_i != q_j:
                candidates.append((p_j - p_i) / (q_i - q_j))            
    result_list = []
    for root in candidates:
        if root <= lower_bound_value:                                         
            continue
        if upper_bound_value is not None and root >= upper_bound_value:
            continue
        if root not in result_list:
            result_list.append(root)
    result_list.sort()
    return result_list


# ==================== 四、约束符号与标准化转换 ====================

def normalize_sign(text):
    """把用户写的约束符号统一成 '<='、'>='、'='（支持中文的 ≤ ≥ ＝）。"""
    cleaned = str(text).strip().replace(' ', '')
    replacement_table = [('≤', '<='), ('≥', '>='), ('＝', '='), ('＜', '<'), ('＞', '>'), ('=<', '<='), ('==', '=')]
    for old_token, new_token in replacement_table:
        cleaned = cleaned.replace(old_token, new_token)
    if cleaned in ('<=', '>='):
        return cleaned
    if cleaned == '=':
        return '='
    raise ValueError('符号只能写 <= >= = 之一')


def flip_sign(symbol):
    """把不等号方向反向（整行乘 -1 时用）。"""
    if symbol == '<=':
        return '>='
    if symbol == '>=':
        return '<='
    return '='


def to_maximization(obj_coeffs, original_type):
    """min 转 max（同时把数字转成精确的 Fraction）。"""
    if original_type == 'min':
        new_coeffs = []
        for value in obj_coeffs:
            if is_expression(value):
                new_coeffs.append((-to_fraction(value[0]), -to_fraction(value[1])))
            else:
                new_coeffs.append(-to_fraction(value))
        return (new_coeffs, '原问题为 min 型，令 z′ = -z 转成 max 型求最大，最后 z = -z′ 回代')
    new_coeffs = []
    for value in obj_coeffs:
        if is_expression(value):
            new_coeffs.append((to_fraction(value[0]), to_fraction(value[1])))
        else:
            new_coeffs.append(to_fraction(value))
    return (new_coeffs, '原问题为 max 型，不需要转换')


def classify_problem_type(original_type, signs, method):
    """判断题目属于哪一类题型。"""
    has_greater_equal = any(normalize_sign(sentence) == '>=' for sentence in signs)
    has_equality = any(normalize_sign(sentence) == '=' for sentence in signs)
    if method == '参数λ单纯形法':
        return '参数 λ 的单纯形法（分类讨论）'
    if method == PARAMETRIC_RHS_METHOD:
        return '参数 λ 的右端项分析（分类讨论）'
    if method == '对偶单纯形法':
        return '对偶单纯形法（约束可化为全 ≤、b 列有负值、初始检验数全 ≤ 0）'
    if method == '大M法':
        if has_greater_equal and has_equality:
            return '含 ≥ 与 = 约束的问题（大M法）'
        if has_equality:
            return '= 约束问题（大M法）'
        return '≥ 约束问题（大M法）'
    if method == '两阶段法':
        if has_greater_equal and has_equality:
            return '含 = 与 ≥ 约束的问题（两阶段法）'
        if has_equality:
            return '= 约束问题（两阶段法）'
        return '≥ 约束问题（两阶段法）'
    if original_type == 'min':
        return 'min 型（先转成 max 型再求最大）'
    return '标准 max 型（约束全是 ≤、右端项非负）'


def standardize(original_type, obj_coeffs, constraint_matrix, signs, rhs_list, method):
    """把用户输入的问题化成标准型（加松弛/剩余/人工变量），返回模型字典。"""
    allowed_methods = ('普通单纯形法', '大M法', '两阶段法', '对偶单纯形法', '参数λ单纯形法')
    if method not in allowed_methods:
        raise ValueError('未知的求解方法：%s' % method)
    row_count = len(constraint_matrix)
    column_count = len(obj_coeffs)
    if row_count == 0:
        raise ValueError('至少要输入 1 个约束')
    if column_count == 0:
        raise ValueError('至少要输入 1 个变量')
    if len(signs) != row_count or len(rhs_list) != row_count:
        raise ValueError('约束条数与符号、右端项的个数不一致')
    for i, row in enumerate(constraint_matrix):
        if len(row) != column_count:
            raise ValueError('第 %d 个约束的系数个数（%d 个）与变量个数（%d 个）不一致' % (i + 1, len(row), column_count))
    # 1) min → max 转换（顺带把数字变成精确的 Fraction）
    converted_obj_coeffs, conversion_notes = to_maximization(obj_coeffs, original_type)
    original_constraint_matrix = [[to_fraction(value) for value in row] for row in constraint_matrix]
    original_rhs = [to_fraction(value) for value in rhs_list]
    A = [list(row) for row in original_constraint_matrix]
    b = list(original_rhs)
    input_signs = [normalize_sign(sentence) for sentence in signs]
    # 2) 按方法检查写法（不允许的写法直接抛中文错误，交给输入层提示）
    if method in ('普通单纯形法', '参数λ单纯形法'):
        for i in range(row_count):
            if input_signs[i] != '<=' or original_rhs[i] < 0:
                if method == '普通单纯形法':
                    raise ValueError('普通单纯形法要求所有约束都是 ≤ 型且右端项非负，请改用大M法、两阶段法或对偶单纯形法')
                raise ValueError('参数 λ 单纯形法目前只支持所有约束均为 ≤ 型且右端项非负的问题，请改用大M法或两阶段法')
    if method == '对偶单纯形法':
        for i in range(row_count):
            if input_signs[i] == '=':
                raise ValueError('对偶单纯形法不支持 = 约束，请改用大M法或两阶段法')
    # 3) 逐行加松弛/剩余/人工变量，并记录中文说明
    record = [('句', conversion_notes)]
    basis = [None] * row_count
    appended_columns = []                     # 每项是 ('松弛'/'剩余'/'人工', 行下标)
    for i in range(row_count):
        sign_i = input_signs[i]
        if method in ('大M法', '两阶段法') and b[i] < 0:
            original_sign = sign_i
            A[i] = [-value for value in A[i]]
            b[i] = -b[i]
            sign_i = flip_sign(sign_i)
            record.append(('句', '第 %d 个约束的右端项为负，整行乘 -1 并把不等号反向（%s 变成 %s）' % (i + 1, original_sign, sign_i)))
        if method == '对偶单纯形法' and sign_i == '>=':
            A[i] = [-value for value in A[i]]
            b[i] = -b[i]
            sign_i = '<='
            record.append(('句', '第 %d 个约束是 ≥，整行乘 -1 化成 ≤ 型（右端项同时变号，允许为负，这正是对偶单纯形法的适用情形）' % (i + 1)))
        if sign_i == '<=':
            record.append(('松弛', i, column_count + len(appended_columns)))
            appended_columns.append(('松弛', i))
        elif sign_i == '>=':
            record.append(('剩余人工', i, column_count + len(appended_columns), column_count + len(appended_columns) + 1))
            appended_columns.append(('剩余', i))
            appended_columns.append(('人工', i))
        else:
            record.append(('等号人工', i, column_count + len(appended_columns)))
            appended_columns.append(('人工', i))
    new_column_count = column_count + len(appended_columns)
    new_matrix = [row + [Fraction(0)] * len(appended_columns) for row in A]       # 先补零列，再往对应位置填 ±1
    slack_indices = []
    surplus_indices = []
    artificial_indices = []
    for k, (kind, row_index) in enumerate(appended_columns):
        column_index = column_count + k
        if kind == '松弛':
            new_matrix[row_index][column_index] = Fraction(1)
            slack_indices.append(column_index)
            basis[row_index] = column_index
        elif kind == '剩余':
            new_matrix[row_index][column_index] = Fraction(-1)
            surplus_indices.append(column_index)
        else:
            new_matrix[row_index][column_index] = Fraction(1)
            artificial_indices.append(column_index)
            basis[row_index] = column_index
    var_names = ['x%d' % (j + 1) for j in range(new_column_count)]
    # 4) 把记录翻译成中文转换说明（这时变量名已经确定）
    explanation = []
    for term in record:
        if term[0] == '句':
            explanation.append(term[1])
        elif term[0] == '松弛':
            explanation.append('第 %d 个约束是 ≤，加上松弛变量 %s（系数 +1，进入初始基）' % (term[1] + 1, var_names[term[2]]))
        elif term[0] == '剩余人工':
            explanation.append('第 %d 个约束是 ≥，减去剩余变量 %s（系数 -1），再加人工变量 %s（系数 +1，进入初始基）'
                      % (term[1] + 1, var_names[term[2]], var_names[term[3]]))
        else:
            explanation.append('第 %d 个约束是 =，直接加上人工变量 %s（系数 +1，进入初始基）' % (term[1] + 1, var_names[term[2]]))
    # 5) 组装标准化后的目标系数（长度 = 变量总数）
    parametric_symbol = None
    final_obj_coeffs = []
    second_obj_coeffs = None
    if method == '参数λ单纯形法':
        parametric_symbol = 'λ'
        for j in range(column_count):
            value = converted_obj_coeffs[j]
            final_obj_coeffs.append(value if is_expression(value) else parametric_expr(value, 0))
        for j in range(column_count, new_column_count):
            final_obj_coeffs.append(parametric_expr(0, 0))
        explanation.append('目标系数写成 cj(λ) = p + qλ 的形式（p 是常数部分，q 是 λ 的系数）；'
                  'λ 只出现在目标函数里，约束矩阵与右端项与 λ 无关，所以比值检验也与 λ 无关')
    elif method == '大M法':
        parametric_symbol = 'M'
        for j in range(column_count):
            final_obj_coeffs.append(converted_obj_coeffs[j])
        for j in range(column_count, new_column_count):
            final_obj_coeffs.append(parametric_expr(0, -1) if j in artificial_indices else Fraction(0))
        explanation.append('人工变量的目标系数记作 -M（本程序用符号 M 精确处理，不取 1e7 这类大数近似，'
                  '所以 σ 行会出现 -M 这样的显示，这是正确结果）')
    elif method == '两阶段法':
        for j in range(new_column_count):
            final_obj_coeffs.append(Fraction(-1) if j in artificial_indices else Fraction(0))
        second_obj_coeffs = list(converted_obj_coeffs) + [Fraction(0)] * (new_column_count - column_count)
        second_obj_coeffs = [Fraction(0) if j in artificial_indices else second_obj_coeffs[j] for j in range(new_column_count)]
        explanation.append('第一阶段的目标是让各人工变量之和 w 最小（等价于最大化 -w），'
                  '所以人工变量目标系数取 -1、其余取 0；第二阶段再换回原目标函数')
    else:
        for j in range(column_count):
            final_obj_coeffs.append(converted_obj_coeffs[j])
        for j in range(column_count, new_column_count):
            final_obj_coeffs.append(Fraction(0))
        if method == '对偶单纯形法':
            explanation.append('对偶单纯形法要求初始检验数全部 ≤ 0（max 型目标系数全部 ≤ 0），本题满足')
    # 6) 对偶单纯形法：检查初始 σ 是否全 ≤ 0（初始基是松弛变量，cB = 0，所以 σ = c）
    if method == '对偶单纯形法':
        for j in range(new_column_count):
            value = final_obj_coeffs[j]
            if is_expression(value) or value > 0:
                raise ValueError('对偶单纯形法要求初始检验数全部 ≤ 0（max 型目标系数全部 ≤ 0），'
                                 '本题请改用普通单纯形法或大M法')
    # 7) 组装模型字典
    model = {
        'original_type': original_type,
        'method': method,
        'problem_type': classify_problem_type(original_type, signs, method),
        'var_names': var_names,
        'original_var_count': column_count,
        'obj_coeffs': final_obj_coeffs,
        'second_obj_coeffs': second_obj_coeffs,
        'constraint_matrix': new_matrix,
        'rhs': b,
        'signs': list(signs),
        'basis_vars': basis,
        'slack_indices': slack_indices,
        'surplus_indices': surplus_indices,
        'artificial_indices': artificial_indices,
        'conversion_notes': explanation,
        'parametric_symbol': parametric_symbol,
        'lambda_lower_bound': None,
        'original_obj_coeffs': list(obj_coeffs),
        'original_constraint_matrix': original_constraint_matrix,
        'original_rhs': original_rhs,
        'original_signs': list(signs),
    }
    return model


def arrange_basis(model):
    """检查并整理初始基：把基变量所在的列化为单位列。"""
    A = [list(row) for row in model['constraint_matrix']]
    b = list(model['rhs'])
    basis = list(model['basis_vars'])
    if any(k is None for k in basis):
        raise ValueError('初始基还没有确定，无法生成单纯形表')
    for r, k in enumerate(basis):
        if A[r][k] == 0:                          # 这一行该基变量系数是 0 → 换一行过来
            swapped = False
            for i in range(len(A)):
                if i != r and A[i][k] != 0:
                    A[r], A[i] = A[i], A[r]
                    b[r], b[i] = b[i], b[r]
                    model['conversion_notes'].append('第 %d 行与第 %d 行对调，使 %s 成为基变量' % (r + 1, i + 1, model['var_names'][k]))
                    swapped = True
                    break
            if not swapped:
                raise ValueError('基变量 %s 所在的列是零列，无法作为初始基' % model['var_names'][k])
        pivot_value = A[r][k]
        if pivot_value != 1:                             # 把这一行的主元化成 1
            A[r] = [value / pivot_value for value in A[r]]
            b[r] = b[r] / pivot_value
            model['conversion_notes'].append('第 %d 行整行除以 %s，使 %s 的系数变成 1' % (r + 1, number_to_text(pivot_value), model['var_names'][k]))
        for i in range(len(A)):                   # 其它行的该列系数化成 0
            if i == r or A[i][k] == 0:
                continue
            coefficient = A[i][k]
            A[i] = [A[i][j] - coefficient * A[r][j] for j in range(len(A[i]))]
            b[i] = b[i] - coefficient * b[r]
            model['conversion_notes'].append('第 %d 行减去第 %d 行的 %s 倍，消去 %s 的系数'
                              % (i + 1, r + 1, number_to_text(coefficient), model['var_names'][k]))
    return (A, b, basis)


# ==================== 五、检验数（σ 行）、入基变量、比值检验 ====================

def compute_sigma(table):
    """计算检验数行 σ 和目标函数值 z。"""
    symbol = table.get('parametric_symbol')
    c = table['c']
    basis_coeffs = table['basis_coeffs']
    A = table['constraint_matrix']
    b = table['rhs']
    row_count = len(A)
    column_count = len(c)
    sigma = []
    formulas = []
    for j in range(column_count):
        symbolic_sum = ' + '.join('cB%d×a%d%d' % (i + 1, i + 1, j + 1) for i in range(row_count))
        if symbol is None:
            total = Fraction(0)
            term = []
            for i in range(row_count):
                total = total + to_fraction(basis_coeffs[i]) * A[i][j]
                term.append(product_text(number_to_text(basis_coeffs[i]), number_to_text(A[i][j])))
            sigma_value = to_fraction(c[j]) - total
            formulas.append('σ%d = c%d - (%s) = %s - (%s) = %s'
                      % (j + 1, j + 1, symbolic_sum, number_to_text(c[j]), format_row(term), number_to_text(sigma_value)))
        else:
            constant_sum = Fraction(0)
            parameter_sum = Fraction(0)
            term = []
            for i in range(row_count):
                expr_a = to_expression(basis_coeffs[i])
                constant_sum = constant_sum + expr_a[0] * A[i][j]
                parameter_sum = parameter_sum + expr_a[1] * A[i][j]
                term.append(product_text(term_coefficient_text(basis_coeffs[i], symbol), number_to_text(A[i][j])))
            constant_part = to_expression(c[j])[0] - constant_sum
            parameter_part = to_expression(c[j])[1] - parameter_sum
            sigma_value = (constant_part, parameter_part)
            formulas.append('σ%d = c%d - (%s) = %s - (%s) = %s'
                      % (j + 1, j + 1, symbolic_sum, term_coefficient_text(c[j], symbol),
                         format_row(term), parametric_to_text(sigma_value, symbol)))
        sigma.append(sigma_value)
    # 目标函数值 z = 各 cBi×bi 之和
    if symbol is None:
        z = Fraction(0)
        term = []
        for i in range(row_count):
            z = z + to_fraction(basis_coeffs[i]) * b[i]
            term.append(product_text(number_to_text(basis_coeffs[i]), number_to_text(b[i])))
        symbolic_sum = ' + '.join('cB%d×b%d' % (i + 1, i + 1) for i in range(row_count))
        formulas.append('z = %s = %s = %s' % (symbolic_sum, format_row(term), number_to_text(z)))
    else:
        constant_sum = Fraction(0)
        parameter_sum = Fraction(0)
        term = []
        for i in range(row_count):
            expr_a = to_expression(basis_coeffs[i])
            constant_sum = constant_sum + expr_a[0] * b[i]
            parameter_sum = parameter_sum + expr_a[1] * b[i]
            term.append(product_text(term_coefficient_text(basis_coeffs[i], symbol), number_to_text(b[i])))
        z = (constant_sum, parameter_sum)
        symbolic_sum = ' + '.join('cB%d×b%d' % (i + 1, i + 1) for i in range(row_count))
        formulas.append('z = %s = %s = %s' % (symbolic_sum, format_row(term), parametric_to_text(z, symbol)))
    return (sigma, z, formulas)


def sigma_texts(sigma_list, symbol=None):
    """把 σ 行变成文本列表。"""
    return [number_to_text(value) if not is_expression(value) else parametric_to_text(value, symbol if symbol else 'M')
            for value in sigma_list]


def select_entering_column(sigma_list, symbol=None):
    """选入基列：三种方法统一取 σ > 0 中最大者（并列取下标小者）。"""
    column_count = len(sigma_list)
    if symbol == 'M':
        candidates = [j for j in range(column_count) if parametric_is_positive(sigma_list[j])]
        if not candidates:
            return (None, '所有 σj ≤ 0，已达最优（在 M 充分大的意义下）')
        best = candidates[0]
        for j in candidates[1:]:
            if parametric_compare(sigma_list[j], sigma_list[best]) > 0:
                best = j
        text = parametric_to_text(sigma_list[best], 'M')
        return (best, '在 M 充分大的意义下存在 σ%d = %s > 0，未达最优 → 入基变量取 σ 最大者 σ%d = %s'
                % (best + 1, text, best + 1, text))
    candidates = [j for j in range(column_count) if numeric_part(sigma_list[j]) > 0]
    if not candidates:
        return (None, '所有 σj ≤ 0，已达最优（max 型判据）')
    best = candidates[0]
    for j in candidates[1:]:
        if numeric_part(sigma_list[j]) > numeric_part(sigma_list[best]):
            best = j
    text = value_to_text(sigma_list[best], symbol)
    return (best, '存在 σ%d = %s > 0，未达最优 → 入基变量取 σ 最大者 σ%d = %s'
            % (best + 1, text, best + 1, text))


def numeric_part(value):
    """取一个值的"数值部分"：普通数原样返回，含参数表达式返回它的常数部分。"""
    if is_expression(value):
        return to_fraction(value[0])
    return to_fraction(value)


def compute_ratio_list(table, enter_col):
    """算最小比值 θ。"""
    enter_col = int(enter_col)
    table['enter_col'] = enter_col
    ratio_list = []
    for i in range(len(table['constraint_matrix'])):
        coefficient = table['constraint_matrix'][i][enter_col]
        if coefficient > 0:
            ratio_list.append(table['rhs'][i] / coefficient)
        else:
            ratio_list.append(None)
    return ratio_list


def ratio_test(ratio_list, table):
    """按最小比值规则选离基行。"""
    var_names = table['var_names']
    enter_col = table.get('enter_col')
    column_name = var_names[enter_col] if enter_col is not None else '入基列'
    valid_ratios = [(ratio_value, table['basis'][i], i) for i, ratio_value in enumerate(ratio_list) if ratio_value is not None]
    if not valid_ratios:
        return (None, '入基列 %s 的所有系数 ≤ 0，比值不存在 → 原问题无界（z → +∞）' % column_name)
    minimum = min(ratio_value for ratio_value, _, _ in valid_ratios)
    basis_index, leave_row = min((basis_index, i) for ratio_value, basis_index, i in valid_ratios if ratio_value == minimum)
    fragment = []
    for i, ratio_value in enumerate(ratio_list):
        coefficient = table['constraint_matrix'][i][enter_col]
        if ratio_value is None:
            fragment.append('θ%d 不存在（a(%d,%s) = %s ≤ 0）' % (i + 1, i + 1, column_name, number_to_text(coefficient)))
        else:
            fragment.append('θ%d = %s/%s = %s' % (i + 1, number_to_text(table['rhs'][i]), number_to_text(coefficient), number_to_text(ratio_value)))
    pivot_value = table['constraint_matrix'][leave_row][enter_col]
    message = ('比值 θi = bi / a(i,%s)：%s → 最小比值 θ = %s 在第 %d 行 → 离基变量 %s；'
           '主元 a(第%d行, %s列) = %s，继续迭代。'
           % (column_name, '，'.join(fragment), number_to_text(minimum), leave_row + 1, var_names[basis_index],
              leave_row + 1, column_name, number_to_text(pivot_value)))
    return (leave_row, message)


def dual_select_leaving_row(table):
    """对偶单纯形法：选离基行（b 列最负且为负数的行）。"""
    candidates = [(table['rhs'][i], i) for i in range(len(table['rhs'])) if table['rhs'][i] < 0]
    if not candidates:
        return (None, '所有 b_i ≥ 0 且所有 σj ≤ 0，已达最优')
    min_value = min(ratio_value for ratio_value, _ in candidates)
    row = min(i for ratio_value, i in candidates if ratio_value == min_value)
    return (row, 'b 列中最负的是第 %d 行（b%d = %s < 0）→ 离基变量 %s'
            % (row + 1, row + 1, number_to_text(table['rhs'][row]), table['var_names'][table['basis'][row]]))


def dual_ratio_test(table, leave_row):
    """对偶单纯形法：选入基列（按 θ′ = σj / a(r,j) 最小者）。"""
    var_names = table['var_names']
    column_count = len(var_names)
    row_coeffs = table['constraint_matrix'][leave_row]
    ratio_list = [None] * column_count
    candidates = []
    for j in range(column_count):
        if row_coeffs[j] < 0:
            ratio_value = numeric_part(table['sigma'][j]) / row_coeffs[j]
            ratio_list[j] = ratio_value
            candidates.append((ratio_value, j))
    if not candidates:
        return (None, [], '第 %d 行 b%d = %s < 0 且该行所有系数 ≥ 0 → 原问题无可行解'
                % (leave_row + 1, leave_row + 1, number_to_text(table['rhs'][leave_row])))
    minimum = min(ratio_value for ratio_value, _ in candidates)
    enter_col = min(j for ratio_value, j in candidates if ratio_value == minimum)
    fragment = []
    for j, ratio_value in enumerate(ratio_list):
        if ratio_value is None:
            continue
        fragment.append('θ′%d = σ%d / a(%d,%d) = %s / %s = %s'
                  % (j + 1, j + 1, leave_row + 1, j + 1, number_to_text(table['sigma'][j]),
                     number_to_text(row_coeffs[j]), number_to_text(ratio_value)))
    pivot_value = row_coeffs[enter_col]
    message = ('比值 θ′j = σj / a(r,j)（只取 a(r,j) < 0 的列）：%s → 最小者 θ′ = %s 在第 %d 列 → 入基变量 %s；'
           '主元 a(第%d行, %s列) = %s，继续迭代。'
           % ('，'.join(fragment), number_to_text(minimum), enter_col + 1, var_names[enter_col],
              leave_row + 1, var_names[enter_col], number_to_text(pivot_value)))
    return (enter_col, ratio_list, message)


# ==================== 六、读表、判断文字、初始表与旋转 ====================

def table_basic_solution(table):
    """从一张表读出全部变量的取值（基0变量 = 该行的 b，非基变量 = 0）。"""
    var_count = len(table['var_names'])
    solution = {j: Fraction(0) for j in range(var_count)}
    for i in range(len(table['basis'])):
        solution[table['basis'][i]] = table['rhs'][i]
    return solution


def sigma_is_zero(sigma, symbol):
    """判断一个检验数是不是 0（含参数时用表达式判零）。"""
    if is_expression(sigma):
        return parametric_is_zero(sigma)
    return to_fraction(sigma) == 0


def optimal_supplement_text(table):
    """给"已达最优"的表补上最优解取值、目标函数值、唯一性、退化提示。"""
    symbol = table.get('parametric_symbol')
    var_names = table['var_names']
    solution = table_basic_solution(table)
    basis_text = '，'.join('%s = %s' % (var_names[k], number_to_text(solution[k])) for k in table['basis'])
    nonbasis_list = [j for j in range(len(var_names)) if j not in table['basis']]
    segment = ['本表基变量取值：' + basis_text]
    if nonbasis_list:
        segment.append('非基变量：' + '，'.join('%s = 0' % var_names[j] for j in nonbasis_list))
    segment.append('目标函数值 z = %s' % value_to_text(table['objective_value'], symbol))
    zero_sigma_columns = [j for j in nonbasis_list if sigma_is_zero(table['sigma'][j], symbol)]
    if zero_sigma_columns:
        if table.get('phase') == 1:
            segment.append('存在非基变量 %s 的 σ = 0 → 第一阶段（最小化人工变量之和 w）的最优表不止一个，'
                    '这只说明 w 的最优基可以换，不影响原问题的最优解（原问题是否多重最优看第二阶段末表）'
                    % '、'.join(var_names[j] for j in zero_sigma_columns))
        else:
            segment.append('存在非基变量 %s 的 σ = 0 → 有多重最优解（见结论）' % '、'.join(var_names[j] for j in zero_sigma_columns))
    else:
        segment.append('最优表中非基变量的 σ 都严格小于 0 → 最优解唯一')
    degenerate, degenerate_message = check_degenerate(table)
    if degenerate:
        segment.append(degenerate_message)
    return '。'.join(segment) + '。'


def build_judgement(table):
    """生成一张表的【判断】文字，并把比值列表写回表字典。"""
    symbol = table.get('parametric_symbol')
    if symbol == 'λ':
        table['ratio_list'] = []
        table['ratio_message'] = '本表 σ 行含参数 λ，比值检验与 λ 无关，最优性要在每个 λ 区间上分别判断（见各区间结论）'
        return '本表 σ 行含参数 λ，最优性需要按 λ 的区间分类讨论（见后面每个区间的结论）。'
    if table.get('is_dual'):
        leave_row, leaving_message = dual_select_leaving_row(table)
        if leave_row is None:
            table['ratio_list'] = []
            table['ratio_message'] = '本表所有 b 都 ≥ 0，不需要再算比值'
            return leaving_message + '。' + optimal_supplement_text(table)
        enter_col, ratio_list, ratio_message = dual_ratio_test(table, leave_row)
        table['ratio_list'] = ratio_list
        table['ratio_message'] = ratio_message
        if enter_col is None:
            return leaving_message + '；' + ratio_message
        table['enter_col'] = enter_col
        return leaving_message + '；' + ratio_message
    enter_col, entering_message = select_entering_column(table['sigma'], symbol)
    if enter_col is None:
        table['ratio_list'] = []
        table['ratio_message'] = '本表已达最优，不需要再算比值'
        return entering_message + '。' + optimal_supplement_text(table)
    table['enter_col'] = enter_col
    entering_message = entering_message + '（第 %d 列，即 %s）' % (enter_col + 1, table['var_names'][enter_col])
    ratio_list = compute_ratio_list(table, enter_col)
    table['ratio_list'] = ratio_list
    leave_row, ratio_message = ratio_test(ratio_list, table)
    table['ratio_message'] = ratio_message
    return entering_message + '；' + ratio_message


def build_initial_table(model):
    """生成初始单纯形表（第 0 张表）。"""
    A, b, basis = arrange_basis(model)
    c = list(model['obj_coeffs'])
    is_dual = model['method'] == '对偶单纯形法'
    table = {
        'iteration_number': 0,
        'title': ('对偶单纯形表（第 0 轮，初始表）' if is_dual else '单纯形表（第 0 轮，初始表）'),
        'var_names': list(model['var_names']),
        'c': c,
        'basis': basis,
        'basis_coeffs': [c[k] for k in basis],
        'constraint_matrix': A,
        'rhs': b,
        'sigma': [],
        'objective_value': Fraction(0),
        'ratio_list': [],
        'formulas': [],
        'judgement': '',
        'degenerate': False,
        'parametric_symbol': model['parametric_symbol'],
        'is_dual': is_dual,
        'enter_col': None,
        'ratio_message': '',
        'conversion_notes': list(model['conversion_notes']),
    }
    sigma, objective_value, sigma_formulas = compute_sigma(table)
    table['sigma'] = sigma
    table['objective_value'] = objective_value
    table['judgement'] = build_judgement(table)
    table['formulas'] = initial_table_formulas(table, sigma_formulas)
    table['degenerate'] = check_degenerate(table)[0]
    return table


def parametric_note_item(symbol):
    """第 10 项计算公式：说明含参数（M / λ）时 σ 行怎么算。"""
    if symbol == 'M':
        return ('10) 含参数 M 的处理：人工变量目标系数记作 -M，σj 与 z 都按"常数部分 + 参数部分×M"'
                '两部分分别精确计算；比较大小按 M 充分大的字典序（先比参数部分、再比常数部分），'
                '不用 1e7 这类大数近似')
    if symbol == 'λ':
        return ('10) 含参数 λ 的处理：cj(λ) = p + qλ，σj(λ) 的"常数部分"与"λ 的系数"分别算出来；'
                '最优性要在每个 λ 区间上分别判断，临界值由 σj(λ) = 0 与 σi(λ) = σj(λ) 精确解出')
    return '10) 本题不含参数 M 或 λ，σ 行全部是普通数值，按精确有理数直接计算'


def initial_table_formulas(table, sigma_formulas):
    """给初始表（第 0 张表）生成【本表计算公式】清单（10 项，逐项带数字）。"""
    symbol = table.get('parametric_symbol')
    var_names = table['var_names']
    row_count = len(table['constraint_matrix'])
    items = []
    items.append('1) cj 行：直接抄标准化后的目标函数系数：' + '，'.join(
        'c%d = %s' % (j + 1, value_to_text(table['c'][j], symbol)) for j in range(len(table['c']))))
    basis_text = ' → '.join('%s（第 %d 行）' % (var_names[k], i + 1) for i, k in enumerate(table['basis']))
    items.append('2) xB 列（基变量）：初始基由松弛变量/人工变量直接给出：' + basis_text)
    items.append('3) cB 列：' + '，'.join(
        'cB%d = c%d = %s' % (i + 1, table['basis'][i] + 1, value_to_text(table['basis_coeffs'][i], symbol)) for i in range(row_count)))
    items.append('4) b 列：直接抄标准化后的右端项：' + '，'.join(
        'b%d = %s' % (i + 1, number_to_text(table['rhs'][i])) for i in range(row_count)))
    row_text = []
    for i in range(row_count):
        row_text.append('   第 %d 行：%s' % (i + 1, '，'.join(
            'a(%d,%s) = %s' % (i + 1, var_names[j], number_to_text(table['constraint_matrix'][i][j]))
            for j in range(len(var_names)))))
    items.append('5) 约束行系数：直接抄标准化后的系数矩阵（松弛/剩余/人工变量列已按规则填好）：\n' + '\n'.join(row_text))
    items.append('6) 检验数（σ 行）：用统一公式 σj = cj - (cB1×a1j + cB2×a2j + …) 逐列计算：\n'
              + '\n'.join('   ' + sentence for sentence in sigma_formulas[:-1]))
    items.append('7) 目标函数值：' + sigma_formulas[-1])
    items.append('8) 比值：' + table['ratio_message'])
    items.append('9) 判断依据：' + table['judgement'])
    items.append(parametric_note_item(symbol))
    return items


def pivot(table, enter_col, leave_row):
    """对表做一次旋转变换，返回新表（不修改原表，用深拷贝）。"""
    pivot_value = table['constraint_matrix'][leave_row][enter_col]
    if pivot_value == 0:
        raise ValueError('主元等于 0，无法继续旋转')
    new_table = copy.deepcopy(table)
    new_table['constraint_matrix'] = [list(row) for row in table['constraint_matrix']]
    new_table['rhs'] = list(table['rhs'])
    new_table['constraint_matrix'][leave_row] = [value / pivot_value for value in table['constraint_matrix'][leave_row]]   # 新主行
    new_table['rhs'][leave_row] = table['rhs'][leave_row] / pivot_value
    for i in range(len(table['constraint_matrix'])):                                  # 其余行消元
        if i == leave_row:
            continue
        coefficient = table['constraint_matrix'][i][enter_col]
        if coefficient == 0:
            new_table['constraint_matrix'][i] = list(table['constraint_matrix'][i])
            new_table['rhs'][i] = table['rhs'][i]
            continue
        new_table['constraint_matrix'][i] = [table['constraint_matrix'][i][j] - coefficient * new_table['constraint_matrix'][leave_row][j]
                          for j in range(len(new_table['constraint_matrix'][i]))]
        new_table['rhs'][i] = table['rhs'][i] - coefficient * new_table['rhs'][leave_row]
    new_table['basis'] = list(table['basis'])
    new_table['basis'][leave_row] = enter_col
    new_table['basis_coeffs'] = [new_table['c'][k] for k in new_table['basis']]
    new_table['iteration_number'] = table['iteration_number'] + 1
    if table.get('is_dual'):
        new_table['title'] = '对偶单纯形表（第 %d 轮）' % new_table['iteration_number']
    else:
        new_table['title'] = '单纯形表（第 %d 轮）' % new_table['iteration_number']
    sigma, objective_value, sigma_formulas = compute_sigma(new_table)
    new_table['sigma'] = sigma
    new_table['objective_value'] = objective_value
    new_table['judgement'] = build_judgement(new_table)
    new_table['formulas'] = pivot_table_formulas(table, new_table, enter_col, leave_row, pivot_value, sigma_formulas)
    new_table['degenerate'] = check_degenerate(new_table)[0]
    return new_table


def b_column_formulas(old_table, new_table, enter_col, leave_row, pivot_value):
    """写旋转后 b 列的逐项计算文字（主行除法 + 其余行消元）。"""
    row_number = leave_row + 1
    fragment = ['b(%d) = %s ÷ %s = %s'
           % (row_number, number_to_text(old_table['rhs'][leave_row]), number_to_text(pivot_value), number_to_text(new_table['rhs'][leave_row]))]
    for i in range(len(old_table['constraint_matrix'])):
        if i == leave_row:
            continue
        coefficient = old_table['constraint_matrix'][i][enter_col]
        if coefficient == 0:
            fragment.append('b(%d) = %s（入基列系数为 0 → 该行不变）' % (i + 1, number_to_text(new_table['rhs'][i])))
        else:
            fragment.append(elimination_segment_text('b(%d)' % (i + 1), old_table['rhs'][i], coefficient,
                                new_table['rhs'][leave_row], new_table['rhs'][i]))
    return '   ' + '；\n   '.join(fragment)


def constraint_row_formulas(old_table, new_table, enter_col, leave_row, pivot_value):
    """写旋转后约束行系数的逐项计算文字（主行除法 + 其余行消元）。"""
    var_names = old_table['var_names']
    row_number = leave_row + 1
    column_name = var_names[enter_col]
    segment = []
    fragment = ['a(%d,%s) = %s ÷ %s = %s'
           % (row_number, var_names[j], number_to_text(old_table['constraint_matrix'][leave_row][j]), number_to_text(pivot_value),
              number_to_text(new_table['constraint_matrix'][leave_row][j])) for j in range(len(var_names))]
    segment.append('主行（第 %d 行 = 原第 %d 行 ÷ 主元 %s）：%s'
             % (row_number, row_number, number_to_text(pivot_value), '；'.join(fragment)))
    for i in range(len(old_table['constraint_matrix'])):
        if i == leave_row:
            continue
        coefficient = old_table['constraint_matrix'][i][enter_col]
        if coefficient == 0:
            fragment = ['a(%d,%s) = %s' % (i + 1, var_names[j], number_to_text(new_table['constraint_matrix'][i][j]))
                   for j in range(len(var_names))]
            segment.append('第 %d 行：a(%d,%s) = 0 → 该行不变（%s）' % (i + 1, i + 1, column_name, '，'.join(fragment)))
            continue
        fragment = [elimination_segment_text('a(%d,%s)' % (i + 1, var_names[j]), old_table['constraint_matrix'][i][j], coefficient,
                          new_table['constraint_matrix'][leave_row][j], new_table['constraint_matrix'][i][j])
               for j in range(len(var_names))]
        segment.append('第 %d 行：原a(%d,%s) = %s →\n     %s' % (i + 1, i + 1, column_name, number_to_text(coefficient), '；\n     '.join(fragment)))
    return '   ' + '\n   '.join(segment) + '\n   （入基列 %s 在主行化成 1、在其它行化成 0）' % column_name


def pivot_table_formulas(old_table, new_table, enter_col, leave_row, pivot_value, sigma_formulas):
    """给"由旋转得到的新表"生成【本表计算公式】清单（10 项，逐项带数字）。"""
    symbol = new_table.get('parametric_symbol')
    var_names = old_table['var_names']
    row_number = leave_row + 1
    column_name = var_names[enter_col]
    old_basis_name = var_names[old_table['basis'][leave_row]]
    items = []
    items.append('1) cj 行：与上一张表相同：' + '，'.join(
        'c%d = %s' % (j + 1, value_to_text(new_table['c'][j], symbol)) for j in range(len(new_table['c']))))
    items.append('2) 基变量与 cB 列：第 %d 行的基变量由 %s 换成 %s，cB%d = c%d = %s'
              % (row_number, old_basis_name, column_name, row_number, enter_col + 1, value_to_text(new_table['basis_coeffs'][leave_row], symbol)))
    items.append('3) b 列（主行除以主元、其余行消元）：\n' + b_column_formulas(old_table, new_table, enter_col, leave_row, pivot_value))
    items.append('4) 约束行系数（主行除以主元、其余行消元）：\n' + constraint_row_formulas(old_table, new_table, enter_col, leave_row, pivot_value))
    ratio_values = [ratio_value for ratio_value in old_table.get('ratio_list', []) if ratio_value is not None]
    min_ratio_text = number_to_text(min(ratio_values)) if ratio_values else '（见上一张表的判断文字）'
    items.append('5) 主元：a(第%d行, %s列) = %s（入基变量 %s 由 σ 选出；离基行第 %d 行由最小比值 θ = %s 选出）'
              % (row_number, column_name, number_to_text(pivot_value), column_name, row_number, min_ratio_text))
    items.append('6) 检验数（用统一公式 σj = cj - (cB1×a1j + cB2×a2j + …) 重算，不跳步）：\n'
              + '\n'.join('   ' + sentence for sentence in sigma_formulas[:-1]))
    items.append('7) 目标函数值：' + sigma_formulas[-1])
    items.append('8) 比值（供下一轮用）：' + new_table['ratio_message'])
    items.append('9) 判断依据：' + new_table['judgement'])
    items.append(parametric_note_item(symbol))
    return items


# ==================== 七、迭代主循环与结果整理 ====================

def select_bland_entering_column(sigma_list, symbol=None):
    """Bland 规则用的入基选择：取 σ > 0 的列里下标最小者（防止退化时循环）。"""
    for j in range(len(sigma_list)):
        value = sigma_list[j]
        if symbol == 'M':
            if parametric_is_positive(value):
                return (j, '按 Bland 规则（防循环）取下标最小的正检验数 → 入基变量为第 %d 列' % (j + 1))
        elif numeric_part(value) > 0:
            return (j, '按 Bland 规则（防循环）取下标最小的正检验数 → 入基变量为第 %d 列' % (j + 1))
    if symbol == 'M':
        return (None, '所有 σj ≤ 0，已达最优（在 M 充分大的意义下）')
    return (None, '所有 σj ≤ 0，已达最优（max 型判据）')


def simplex_iteration(initial_table, symbol=None, max_iterations=50, avoid_cycles=False):
    """普通单纯形法/大M法/两阶段法的迭代主循环。"""
    iteration_tables = [initial_table]
    current_table = initial_table
    status = '达到最大迭代次数'
    for _round in range(max_iterations):
        if avoid_cycles:
            enter_col, _ = select_bland_entering_column(current_table['sigma'], symbol)
        else:
            enter_col, _ = select_entering_column(current_table['sigma'], symbol)
        if enter_col is None:
            status = '最优'
            break
        ratio_list = compute_ratio_list(current_table, enter_col)
        leave_row, _ = ratio_test(ratio_list, current_table)
        if leave_row is None:
            status = '无界'
            break
        current_table = pivot(current_table, enter_col, leave_row)
        iteration_tables.append(current_table)
    return {'status': status, 'iteration_tables': iteration_tables, 'last_table': iteration_tables[-1], 'conversion_notes': list(initial_table.get('conversion_notes', []))}


def dual_simplex_iteration(initial_table, max_iterations=50):
    """对偶单纯形法的迭代主循环（判据与普通法不同）。"""
    iteration_tables = [initial_table]
    current_table = initial_table
    status = '达到最大迭代次数'
    for _round in range(max_iterations):
        leave_row, _ = dual_select_leaving_row(current_table)
        if leave_row is None:
            status = '最优'
            break
        enter_col, _, _ = dual_ratio_test(current_table, leave_row)
        if enter_col is None:
            status = '无可行'
            break
        current_table = pivot(current_table, enter_col, leave_row)
        iteration_tables.append(current_table)
    return {'status': status, 'iteration_tables': iteration_tables, 'last_table': iteration_tables[-1], 'conversion_notes': list(initial_table.get('conversion_notes', []))}


def check_degenerate(table):
    """判断是否有基变量取值为 0。"""
    for i, k in enumerate(table['basis']):
        if to_fraction(table['rhs'][i]) == 0:
            return (True, '存在基变量取值为 0（第 %d 行 %s = 0），本表为退化解' % (i + 1, table['var_names'][k]))
    return (False, '所有基变量取值都大于 0，没有退化')


def check_artificial(last_table, model):
    """检查人工变量是否残留（大M法/两阶段法用）。"""
    artificial_indices = model['artificial_indices']
    if not artificial_indices:
        return (False, '本题没有人工变量（约束全是 ≤ 型）')
    position = {name: j for j, name in enumerate(last_table['var_names'])}
    solution = table_basic_solution(last_table)
    leftover = []
    for k in artificial_indices:
        name = model['var_names'][k]
        j = position.get(name)
        value = solution[j] if j is not None else Fraction(0)
        if value != 0:
            leftover.append((name, value))
    if leftover:
        name, value = leftover[0]
        return (True, '人工变量 %s = %s ≠ 0 → 原问题无可行解' % (name, number_to_text(value)))
    return (False, '人工变量取值全为 0（%s），约束都被满足'
            % '、'.join('%s = 0' % model['var_names'][k] for k in artificial_indices))


def extract_optimal_solution(last_table, model):
    """从末表读出最优解（含松弛/剩余/人工变量）。"""
    solution = table_basic_solution(last_table)
    return {name: solution[j] for j, name in enumerate(last_table['var_names'])}


def build_all_variable_solution(last_table, model):
    """把末表的变量取值同时用"变量名"和"变量下标"两种键存起来。"""
    name_to_value = extract_optimal_solution(last_table, model)
    index_mapping = last_table.get('full_index_mapping')          # 表里的列下标 → 模型里的变量下标（两阶段第二阶段会重排）
    solution_map = {}
    for j, name in enumerate(last_table['var_names']):
        index = index_mapping[j] if index_mapping else j
        solution_map[name] = name_to_value[name]
        solution_map[index] = name_to_value[name]
    return solution_map


def back_substitute_objective(table, model):
    """把一张表的 z′ 按原始 min/max 回代成用户要的目标值。"""
    value = table['objective_value']
    if is_expression(value):
        value = to_fraction(value[0])
    if model['original_type'] == 'min':
        value = -value
    return value


def find_alternative_optima(last_table, model, max_count=5):
    """找出多重最优解（末表存在"非基且 σj = 0"的列时）。"""
    symbol = last_table.get('parametric_symbol')
    items = [{'solution': build_all_variable_solution(last_table, model), 'objective_value': back_substitute_objective(last_table, model), 'note': '当前最优表给出的最优解'}]
    basis_set = set(last_table['basis'])
    for j in range(len(last_table['var_names'])):
        if j in basis_set or len(items) >= max_count:
            continue
        if not sigma_is_zero(last_table['sigma'][j], symbol):
            continue
        ratio_list = compute_ratio_list(last_table, j)
        leave_row, _ = ratio_test(ratio_list, last_table)
        if leave_row is None:
            continue
        new_table = pivot(last_table, j, leave_row)
        value = back_substitute_objective(new_table, model)
        if value != items[0]['objective_value']:
            continue
        items.append({'solution': build_all_variable_solution(new_table, model), 'objective_value': value,
                   'note': '把非基变量 %s（它的 σ = 0）换入基，得到另一组最优解' % last_table['var_names'][j]})
    if len(items) == 1:
        items[0]['note'] = '末表没有"非基且 σ = 0"的列，最优解唯一'
    return items


def extract_original_solution(last_table, model):
    """只取原始变量（x1..xn）的最优解。"""
    all_values = extract_optimal_solution(last_table, model)
    result = {}
    for k in range(model['original_var_count']):
        name = model['var_names'][k]
        if name in all_values:
            result[name] = all_values[name]
    return result


def build_result(model, method, status, iteration_tables):
    """把迭代出来的表整理成统一的"结果字典"（补最优解、最优值、退化、多重最优、人工变量检查）。"""
    last_table = iteration_tables[-1] if iteration_tables else None
    result = {
        'model': model, 'method': method, 'problem_type': model['problem_type'], 'status': status,
        'iteration_tables': iteration_tables, 'last_table': last_table,
        'optimal_solution': None, 'all_variable_solution': None, 'optimal_value': None,
        'conversion_notes': list(model['conversion_notes']),
        'degenerate': False, 'has_multiple_optima': False, 'alternative_optima': [],
        'artificial_check': '本题没有人工变量（约束全是 ≤ 型）',
        'phase_one': None, 'interval_results': None, 'critical_values': None, 'conclusion': '',
        'method_reason': default_reason(method),
    }
    if last_table is None:
        return result
    result['all_variable_solution'] = build_all_variable_solution(last_table, model)
    result['degenerate'] = check_degenerate(last_table)[0]
    if model['artificial_indices']:
        result['artificial_check'] = check_artificial(last_table, model)[1]
    if status == '最优':
        result['optimal_value'] = back_substitute_objective(last_table, model)
        result['optimal_solution'] = extract_original_solution(last_table, model)
        result['alternative_optima'] = find_alternative_optima(last_table, model)
        result['has_multiple_optima'] = len(result['alternative_optima']) > 1
    return result


# ==================== 八、结论讨论用的小工具 ====================

def default_reason(method):
    """给出每种方法的一句话推荐理由（【题型与方法】里用）。"""
    if method == '大M法':
        return '含 ≥ 或 = 约束，需要人工变量，大M法用 -M 惩罚人工变量'
    if method == '两阶段法':
        return '含 ≥ 或 = 约束，需要人工变量，两阶段法先最小化人工变量之和 w 再求原目标'
    if method == '对偶单纯形法':
        return '约束可化为全 ≤ 型但存在负右端项，初始基不可行而检验数全 ≤ 0，用对偶单纯形法最合适'
    if method == '参数λ单纯形法':
        return '目标函数含参数 λ，需要在 λ 的每个区间上分类讨论'
    if method == PARAMETRIC_RHS_METHOD:
        return ('约束右端项含参数 λ，需要按 λ 的区间分类讨论：'
                '区间内最优基不变，到换基点再用对偶单纯形换基继续推进')
    return '所有约束都是 ≤ 型、右端项都非负，松弛变量直接给出初始可行基，不需要人工变量'


def objective_name(model):
    """给出目标函数的写法（'max z' 或 'min z'）。"""
    if model['original_type'] == 'min':
        return 'min z'
    return 'max z'


def solution_sentence(model, result):
    """把最优解写成中文句子（先报原始变量，再报松弛/剩余/人工变量）。"""
    all_values = result.get('all_variable_solution') or {}
    original_vars = [model['var_names'][k] for k in range(model['original_var_count'])]
    fragment_1 = '，'.join('%s = %s' % (name, number_to_text(all_values.get(name, Fraction(0)))) for name in original_vars)
    others = [name for name in all_values if isinstance(name, str) and name not in original_vars]
    fragment_2 = '，'.join('%s = %s' % (name, number_to_text(all_values[name])) for name in others)
    message = fragment_1
    if fragment_2:
        message = message + '；其余变量 ' + fragment_2
    return message + '。'


def uniqueness_text(result):
    """写唯一性讨论（有没有多重最优解）。"""
    if not result.get('has_multiple_optima'):
        return '末表里没有"非基且 σ = 0"的列，最优表中非基变量的 σ 都严格小于 0 → 最优解唯一。'
    group = result.get('alternative_optima') or []
    fragment = []
    for group_item in group[:3]:
        solution = group_item['solution']
        fragment.append('、'.join('%s = %s' % (name, number_to_text(solution[name])) for name in solution if isinstance(name, str)))
    if not fragment:
        return '存在非基的 σ = 0 列，原问题有多重最优解。'
    return ('存在非基变量的 σ = 0，原问题有多重最优解，共给出 %d 组：%s（目标值都等于 %s）。'
            % (len(group), '；'.join(fragment), number_to_text(group[0]['objective_value'])))


def verification_text(model, result):
    """把最优解代回原约束逐条验算。"""
    all_values = result.get('all_variable_solution') or {}
    fragment = []
    for i, row in enumerate(model['original_constraint_matrix']):
        lhs_value = Fraction(0)
        for j, coefficient in enumerate(row):
            lhs_value = lhs_value + coefficient * all_values.get(model['var_names'][j], Fraction(0))
        symbol = normalize_sign(model['original_signs'][i])
        rhs_column = model['original_rhs'][i]
        if symbol == '<=':
            satisfied = lhs_value <= rhs_column
        elif symbol == '>=':
            satisfied = lhs_value >= rhs_column
        else:
            satisfied = lhs_value == rhs_column
        fragment.append('第 %d 个约束左端 = %s %s %s %s' % (i + 1, number_to_text(lhs_value), symbol, number_to_text(rhs_column),
                                                '满足' if satisfied else '不满足'))
    return '把最优解代回原约束：' + '；'.join(fragment) + '，说明求得的解确实是可行最优解。'


def format_basis_names(basis_index_list, model):
    """把最优基（变量下标列表）写成 'x2、x4' 这样的文字。"""
    return '、'.join(model['var_names'][k] for k in basis_index_list)


def interval_solution_text(interval):
    """把参数 λ 法某个区间的最优解写成文字（右端项含 λ 时取值写成 λ 的表达式）。"""
    solution = interval.get('optimal_solution') or {}
    return '，'.join('%s = %s' % (name, value_to_text(value, 'λ')) for name, value in solution.items())


def critical_value_text(result):
    """把临界值列表写成文字。"""
    critical_values = result.get('critical_values') or []
    if not critical_values:
        return '无（λ 的整个讨论域上最优基不变）'
    return '、'.join('λ = %s' % number_to_text(value) for value in critical_values)


def lambda_conclusion_lines(model, result):
    """写参数 λ 法专属的第 3~8 项结论（分类讨论表 + 临界值说明）。"""
    row = []
    intervals = result.get('interval_results') or []
    lower_bound = model.get('lambda_lower_bound')
    lower_bound_text = number_to_text(lower_bound) if lower_bound is not None else '0'
    critical_list = result.get('critical_values') or []
    unbounded_intervals = [interval for interval in intervals if interval.get('status') == '无界']
    bounded_intervals = [interval for interval in intervals if interval.get('status') != '无界']
    row.append('3) 讨论域：λ ∈ [%s, +∞)；临界值：%s。' % (lower_bound_text, critical_value_text(result)))
    if unbounded_intervals:
        row.append('4) 分类讨论表（每个区间的最优基、最优解与最优值；无界区间没有有限最优值，'
                '也就没有最优值表达式）：')
    else:
        row.append('4) 分类讨论表（每个区间的最优基、最优解、最优值表达式）：')
    if not intervals:
        row.append('   没有算出任何区间（可能是迭代次数限制或数据异常）。')
    for interval in intervals:
        endpoint_segment = '；'.join(endpoint_conclusion_text(endpoint, model) for endpoint in (interval.get('endpoint_conclusions') or []))
        if interval.get('optimal_basis'):
            row.append('   区间 %s：最优基 %s → 最优解 %s；%s = %s'
                    % (interval['interval_text'], format_basis_names(interval['optimal_basis'], model), interval_solution_text(interval),
                       objective_name(model), interval['optimal_value_text']))
            if endpoint_segment:
                row.append('     （端点精化）' + endpoint_segment)
        elif interval.get('status') == '无界':
            if endpoint_segment:
                row.append('   区间 %s：%s；区间内部 %s 无界，没有有限最优值（z → +∞）'
                        % (interval['interval_text'], endpoint_segment, interval_interior_text(interval['interval_lower_bound'], interval['interval_upper_bound'])))
            else:
                row.append('   区间 %s：该区间无界，没有有限最优值（z → +∞），也没有最优值表达式'
                        % interval['interval_text'])
        else:
            row.append('   区间 %s：%s' % (interval['interval_text'], interval.get('judgement', '该区间没有有限最优值')))
    if not critical_list:
        if unbounded_intervals:
            row.append('5) 临界值说明：讨论域内没有临界值；本题区间%s无界，没有有限最优值（见第 4 条），'
                    '也不存在由临界值产生的其它最优解。'
                    % '、'.join(interval['interval_text'] for interval in unbounded_intervals))
        else:
            row.append('5) 临界值说明：讨论域内没有临界值，最优基在整个讨论域上不变，'
                    '不存在由临界值产生的多重最优解。')
    elif unbounded_intervals:
        row.append('5) 临界值说明：临界值 %s 处，有有限最优值的区间上相邻两个最优基都满足最优判据；'
                '本题还有无界区间（见第 4 条），那里没有有限最优值，所以不讨论临界点上的多重最优解。'
                % critical_value_text(result))
    else:
        row.append('5) 临界值说明：临界值 %s 处，相邻两个区间的最优基都满足最优判据，'
                '所以 λ 取临界值时原问题有多重最优解（两组解的目标值相同）。' % critical_value_text(result))
    degenerate = any(interval.get('degenerate') for interval in intervals)
    row.append('6) 退化：%s' % ('有区间的最优表出现基变量取值为 0，存在退化解'
                            if degenerate else '所有区间的最优表基变量取值都大于 0，没有退化'))
    row.append('7) 人工变量：参数 λ 法只支持"约束全 ≤、右端项非负"的问题，本题没有人工变量')
    if unbounded_intervals and bounded_intervals:
        row.append('8) 结论：在 λ ≥ %s 上一共分成 %d 个区间；其中区间 %s 无界，该区间无有限最优值'
                '（z → +∞），其余区间的最优基与最优值见上面的分类讨论表。%s'
                % (lower_bound_text, len(intervals), '、'.join(interval['interval_text'] for interval in unbounded_intervals),
                   endpoint_summary_sentence(intervals, model)))
    elif unbounded_intervals:
        row.append('8) 结论：在 λ ≥ %s 上，区间 %s 无界，该区间无有限最优值（z → +∞），'
                '原问题没有有限最优解。%s'
                % (lower_bound_text, '、'.join(interval['interval_text'] for interval in unbounded_intervals),
                   endpoint_summary_sentence(intervals, model)))
    elif critical_list:
        row.append('8) 结论：在 λ ≥ %s 上一共分成 %d 个区间，每个区间都有有限最优值，'
                '最优基与最优值见上面的分类讨论表；'
                'λ 正好等于临界值时两个相邻基都是最优基（多重最优解）。%s'
                % (lower_bound_text, len(intervals), endpoint_summary_sentence(intervals, model)))
    else:
        row.append('8) 结论：在 λ ≥ %s 上最优基在整个讨论域上不变，最优解与最优值不随 λ 变化'
                '（表达式见分类讨论表）。%s' % (lower_bound_text, endpoint_summary_sentence(intervals, model)))
    return row


def infeasible_conclusion_lines(model, result):
    """写"无可行"时的第 8) 条结论，按所用方法分派归因。"""
    last_table = result.get('last_table')
    last_table_judgement = last_table['judgement'] if last_table is not None else '末表不存在'
    phase_one = result.get('phase_one')
    if result['method'] == '对偶单纯形法':
        return ['8) 无可行结论：%s原问题的约束互相矛盾，没有可行解'
                '（对偶单纯形法在 b 列最负的那一行上找不到可以入基的负系数列，说明这一行永远无法满足）。'
                % (('末表判断：%s；' % last_table_judgement) if last_table is not None else '')]
    if result['method'] == '大M法':
        return ['8) 无可行结论：%s，说明原来的约束互相矛盾，原问题没有可行解'
                '（大M法用 -M 惩罚人工变量，惩罚不掉就代表无可行解）。' % result['artificial_check']]
    if phase_one is not None:
        return ['8) 无可行结论：原问题的约束互相矛盾，没有可行解（第一阶段判断：%s）。' % phase_one['judgement']]
    return ['8) 无可行结论：原问题的约束互相矛盾，没有可行解（末表判断：%s）。' % last_table_judgement]


def write_conclusion(model, result):
    """写结果讨论与结论（多行中文文本，共 8 项）。"""
    row = []
    phase_one = result.get('phase_one')
    if phase_one and phase_one.get('entered_phase_two'):
        row.append('1) 本题属于【%s】，采用【%s】求解：第一阶段 %d 张单纯形表、第二阶段 %d 张单纯形表'
                '（含各自的初始表，两段都会打印出来）。'
                % (model['problem_type'], result['method'], len(phase_one['iteration_tables']), len(result['iteration_tables'])))
    elif phase_one:
        summary = '，判为无可行，不进入第二阶段' if result['status'] == '无可行' else '，没有进入第二阶段'
        row.append('1) 本题属于【%s】，采用【%s】求解，一共 %d 张单纯形表（第一阶段%s）。'
                % (model['problem_type'], result['method'], len(phase_one['iteration_tables']), summary))
    else:
        row.append('1) 本题属于【%s】，采用【%s】求解，一共 %d 张单纯形表（含初始表）。'
                % (model['problem_type'], result['method'], len(result['iteration_tables'])))
    if model['original_type'] == 'min':
        row.append('2) 原问题为 min 型，已令 z′ = -z 转成 max 型求解，最后按 z = -z′ 回代。')
    else:
        row.append('2) 原问题为 max 型，不需要 min→max 转换。')
    if result['method'] == '参数λ单纯形法':
        row.extend(lambda_conclusion_lines(model, result))
        return '\n'.join(row)
    if result['method'] == PARAMETRIC_RHS_METHOD:
        row.extend(lambda_rhs_conclusion_lines(model, result))
        return '\n'.join(row)
    last_table = result.get('last_table')
    degenerate_message = check_degenerate(last_table)[1] if last_table is not None else '没有表可以检查退化'
    if result['status'] == '最优':
        row.append('3) 最优解：' + solution_sentence(model, result))
        row.append('4) 最优值：%s = %s（由末表 z′ = %s 回代得到）。'
                % (objective_name(model), number_to_text(result['optimal_value']),
                   value_to_text(last_table['objective_value'], last_table.get('parametric_symbol'))))
        row.append('5) 唯一性：' + uniqueness_text(result))
        row.append('6) 退化：' + degenerate_message + '。')
        row.append('7) 人工变量：' + result['artificial_check'] + '。')
        row.append('8) 结论：' + verification_text(model, result))
    elif result['status'] == '无界':
        row.append('3) 最优解：不存在（目标函数在可行域上可以无限增大）。')
        row.append('4) 最优值：%s → +∞，没有有限最优值。' % objective_name(model))
        row.append('5) 唯一性：不适用（本题无界，没有最优解可比）。')
        row.append('6) 退化：' + degenerate_message + '。')
        row.append('7) 人工变量：' + result['artificial_check'] + '。')
        row.append('8) 无界结论：%s' % (last_table['judgement'] if last_table is not None else '末表不存在'))
    elif result['status'] == '无可行':
        row.append('3) 最优解：不存在（原问题没有可行解）。')
        row.append('4) 最优值：不存在（没有可行解就没有最优值）。')
        row.append('5) 唯一性：不适用（本题无可行解）。')
        row.append('6) 退化：' + degenerate_message + '。')
        row.append('7) 人工变量：' + result['artificial_check'] + '。')
        row.extend(infeasible_conclusion_lines(model, result))
    else:
        row.append('3) 最优解：本次求解没有走到最优表，暂不给出最优解。')
        row.append('4) 最优值：暂不给出。')
        row.append('5) 唯一性：暂不能判断。')
        row.append('6) 退化：' + degenerate_message + '。')
        row.append('7) 人工变量：' + result['artificial_check'] + '。')
        row.append('8) 结论：迭代次数达到上限（%s），可能因为退化产生循环，'
                '可以把最大迭代次数调大或打开 Bland 规则（避免循环=True）再试。' % result['status'])
    return '\n'.join(row)


# ==================== 九、五种求解方法 ====================

def primal_simplex(model, max_iterations=MAX_ITERATIONS):
    """普通单纯形法（max 型、全 ≤ 约束、右端项非负）。"""
    initial_table = build_initial_table(model)
    iteration_result = simplex_iteration(initial_table, symbol=model['parametric_symbol'], max_iterations=max_iterations)
    result = build_result(model, '普通单纯形法', iteration_result['status'], iteration_result['iteration_tables'])
    result['conclusion'] = write_conclusion(model, result)
    return result


def mark_infeasible(table, message):
    """把一张表的【判断】改写成"无可行"结论。"""
    solution = table_basic_solution(table)
    basis_text = '，'.join('%s = %s' % (table['var_names'][k], number_to_text(solution[k])) for k in table['basis'])
    new_judgement = ('%s。本表基变量取值：%s；因为人工变量没有全部消成 0，'
            '本表只是"原问题的约束互相矛盾"的证据，不是最优表。' % (message, basis_text))
    table['judgement'] = new_judgement
    table['degenerate'] = check_degenerate(table)[0]
    for i, term in enumerate(table['formulas']):
        if term.startswith('9) 判断依据：'):
            table['formulas'][i] = '9) 判断依据：' + new_judgement
    return None


def big_m_method(model, max_iterations=MAX_ITERATIONS):
    """大M法（含 ≥ 或 = 约束）。"""
    initial_table = build_initial_table(model)
    iteration_result = simplex_iteration(initial_table, symbol='M', max_iterations=max_iterations)
    result = build_result(model, '大M法', iteration_result['status'], iteration_result['iteration_tables'])
    if result['last_table'] is not None:
        leftover, message = check_artificial(result['last_table'], model)
        result['artificial_check'] = message
        if result['status'] == '最优' and leftover:
            result['status'] = '无可行'
            result['optimal_solution'] = None
            result['optimal_value'] = None
            result['has_multiple_optima'] = False
            result['alternative_optima'] = []
            mark_infeasible(result['last_table'], message)      # 末表【判断】也要改成无可行表述
    result['conclusion'] = write_conclusion(model, result)
    return result


def artificial_sum(last_table, model):
    """算第一阶段的 w：各人工变量取值之和。"""
    solution = table_basic_solution(last_table)
    position = {name: j for j, name in enumerate(last_table['var_names'])}
    grand_total = Fraction(0)
    for k in model['artificial_indices']:
        j = position.get(model['var_names'][k])
        if j is not None:
            grand_total = grand_total + solution[j]
    return grand_total


def build_phase_two_table(model, phase_one_last_table):
    """用第一阶段末表造第二阶段的初始表（去掉人工变量列、换成第二目标系数）。"""
    kept_indices = [j for j in range(len(model['var_names'])) if j not in model['artificial_indices']]
    index_mapping = {old_token: new_token for new_token, old_token in enumerate(kept_indices)}
    rows = [[row[j] for j in kept_indices] for row in phase_one_last_table['constraint_matrix']]
    rhs_column = list(phase_one_last_table['rhs'])
    basis = [index_mapping[k] for k in phase_one_last_table['basis']]
    for r in range(len(basis)):                      # 万一人工变量还留在基里（取值为 0 的退化情形）
        if phase_one_last_table['basis'][r] not in model['artificial_indices']:
            continue
        replacement_column = None
        for j in range(len(kept_indices)):
            if rows[r][j] != 0:
                replacement_column = j
                break
        if replacement_column is None:                          # 这一行是 0 = 0，属于多余约束，整行删掉
            model['conversion_notes'].append('第一阶段发现第 %d 行是多余的（0 = 0），第二阶段去掉这一行' % (r + 1))
            del rows[r]
            del rhs_column[r]
            del basis[r]
            break
        pivot_value = rows[r][replacement_column]
        rows[r] = [value / pivot_value for value in rows[r]]
        rhs_column[r] = rhs_column[r] / pivot_value
        for i in range(len(basis)):
            if i == r or rows[i][replacement_column] == 0:
                continue
            coefficient = rows[i][replacement_column]
            rows[i] = [rows[i][j] - coefficient * rows[r][j] for j in range(len(kept_indices))]
            rhs_column[i] = rhs_column[i] - coefficient * rhs_column[r]
        basis[r] = replacement_column
        model['conversion_notes'].append('第一阶段结束时人工变量还留在基里，用第 %d 行的 %s 把它替换出去'
                          % (r + 1, model['var_names'][kept_indices[replacement_column]]))
    new_table = {
        'iteration_number': 0,
        'title': '第二阶段单纯形表（第 0 轮，初始表）',
        'var_names': [model['var_names'][j] for j in kept_indices],
        'c': [model['second_obj_coeffs'][j] for j in kept_indices],
        'basis': basis,
        'constraint_matrix': rows,
        'rhs': rhs_column,
        'sigma': [],
        'objective_value': Fraction(0),
        'ratio_list': [],
        'formulas': [],
        'judgement': '',
        'degenerate': False,
        'parametric_symbol': None,
        'is_dual': False,
        'enter_col': None,
        'ratio_message': '',
        'full_index_mapping': kept_indices,
        'phase': 2,
        'conversion_notes': list(model['conversion_notes']),
    }
    new_table['basis_coeffs'] = [new_table['c'][k] for k in new_table['basis']]
    sigma, objective_value, sigma_formulas = compute_sigma(new_table)
    new_table['sigma'] = sigma
    new_table['objective_value'] = objective_value
    new_table['judgement'] = build_judgement(new_table)
    new_table['formulas'] = phase_two_formulas(new_table, sigma_formulas, model)
    new_table['degenerate'] = check_degenerate(new_table)[0]
    return (new_table, kept_indices)


def phase_two_formulas(new_table, sigma_formulas, model):
    """给第二阶段初始表生成【本表计算公式】清单（在初始表 10 项前面加一条来源说明）。"""
    items = initial_table_formulas(new_table, sigma_formulas)
    artificial_names = '、'.join(model['var_names'][k] for k in model['artificial_indices'])
    items.insert(0, '0) 本表由第一阶段的末表得到：去掉人工变量列（%s），把 cj 行换成原目标函数'
               '（人工变量位置记 0），基变量、系数矩阵、右端项都沿用第一阶段末表'
               % (artificial_names if artificial_names else '无'))
    return items


def full_solution(last_table, model, kept_indices):
    """把第二阶段末表的解还原成"模型全部变量"的解（人工变量按 0 记）。"""
    name_to_value = extract_optimal_solution(last_table, model)
    solution_map = {}
    for old_index in kept_indices:
        name = model['var_names'][old_index]
        value = name_to_value.get(name, Fraction(0))
        solution_map[name] = value
        solution_map[old_index] = value
    for old_index in model['artificial_indices']:
        name = model['var_names'][old_index]
        solution_map[name] = Fraction(0)
        solution_map[old_index] = Fraction(0)
    return solution_map


def two_phase_method(model, max_iterations=MAX_ITERATIONS):
    """两阶段法（含 ≥ 或 = 约束）。"""
    initial_table = build_initial_table(model)
    initial_table['phase'] = 1                      # 标记这是第一阶段（判断文字里要按 w 来说，别说成原问题的多重最优）
    phase_one_iteration = simplex_iteration(initial_table, symbol=None, max_iterations=max_iterations)
    phase_one_last_table = phase_one_iteration['last_table']
    w_value = artificial_sum(phase_one_last_table, model)
    if w_value != 0:
        judgement = '第一阶段求得 w_min = %s > 0 → 原问题无可行解' % number_to_text(w_value)
        mark_infeasible(phase_one_last_table, judgement)     # 第一阶段末表的【判断】也要改成无可行表述
    elif phase_one_iteration['status'] != '最优':
        judgement = '第一阶段没有走到最优表（状态：%s），无法判断原问题是否有可行解' % phase_one_iteration['status']
    else:
        judgement = '第一阶段求得 w_min = 0 → 原问题有可行解，进入第二阶段'
    result = build_result(model, '两阶段法', phase_one_iteration['status'] if w_value == 0 else '无可行', phase_one_iteration['iteration_tables'])
    result['phase_one'] = {'iteration_tables': phase_one_iteration['iteration_tables'], 'artificial_sum': w_value, 'judgement': judgement,
                    'entered_phase_two': '进入第二阶段' in judgement}
    result['artificial_check'] = check_artificial(phase_one_last_table, model)[1]
    if w_value != 0 or phase_one_iteration['status'] != '最优':
        result['conclusion'] = write_conclusion(model, result)
        return result
    new_table, kept_indices = build_phase_two_table(model, phase_one_last_table)
    phase_two_iteration = simplex_iteration(new_table, symbol=None, max_iterations=max_iterations)
    result = build_result(model, '两阶段法', phase_two_iteration['status'], phase_two_iteration['iteration_tables'])
    result['phase_one'] = {'iteration_tables': phase_one_iteration['iteration_tables'], 'artificial_sum': w_value, 'judgement': judgement,
                    'entered_phase_two': True}
    result['all_variable_solution'] = full_solution(phase_two_iteration['last_table'], model, kept_indices)
    result['artificial_check'] = check_artificial(phase_one_last_table, model)[1]
    if result['status'] == '最优':
        result['optimal_solution'] = extract_original_solution(phase_two_iteration['last_table'], model)
    result['conclusion'] = write_conclusion(model, result)
    return result


def dual_simplex_method(model, max_iterations=MAX_ITERATIONS):
    """对偶单纯形法（b 列有负数、σ 全部 ≤ 0 时用）。"""
    initial_table = build_initial_table(model)
    iteration_result = dual_simplex_iteration(initial_table, max_iterations=max_iterations)
    result = build_result(model, '对偶单纯形法', iteration_result['status'], iteration_result['iteration_tables'])
    if result['status'] != '最优':
        result['optimal_solution'] = None
        result['optimal_value'] = None
    result['conclusion'] = write_conclusion(model, result)
    return result


def has_zero_sigma_nonbasic(table):
    """判断一张表里有没有"非基且 σ = 0"的列（多重最优解的标志）。"""
    basis_set = set(table['basis'])
    for j in range(len(table['var_names'])):
        if j in basis_set:
            continue
        if sigma_is_zero(table['sigma'][j], table.get('parametric_symbol')):
            return True
    return False


def table_objective_expression(table, model):
    """把一张 λ 表的目标值 z′(λ) 按原始 min/max 回代成 z(λ) 表达式。"""
    value = table['objective_value']
    constant_part, parameter_part = to_expression(value)
    if model['original_type'] == 'min':
        constant_part, parameter_part = -constant_part, -parameter_part
    return (constant_part, parameter_part)


def endpoint_check(table, lambda_value, model):
    """在一个具体的 λ 值（一般是区间端点）上做一次精确判定。"""
    current_table = table
    path = [copy.deepcopy(table)]
    record = {'status': '未判定', 'optimal_solution': None, 'optimal_value_expression': None,
          'optimal_value_text': None, 'has_multiple_optima': False, 'iteration_tables': path}
    for _round in range(MAX_ITERATIONS):
        numeric_sigma = [lambda_eval(sigma_value, lambda_value) for sigma_value in current_table['sigma']]
        enter_col, _ = select_entering_column(numeric_sigma, None)
        if enter_col is None:
            basis_set = set(current_table['basis'])
            nonbasis_columns = [j for j in range(len(current_table['var_names'])) if j not in basis_set]
            record['status'] = '最优'
            record['basis'] = list(current_table['basis'])
            record['optimal_solution'] = extract_original_solution(current_table, model)
            record['optimal_value_expression'] = table_objective_expression(current_table, model)
            record['optimal_value_text'] = parametric_to_text(record['optimal_value_expression'], 'λ')
            # 端点上的多重最优要按"这一点"的数值 σ 判（不能要求 σj(λ) 恒等于 0）
            record['has_multiple_optima'] = any(numeric_sigma[j] == 0 for j in nonbasis_columns)
            return record
        ratio_list = compute_ratio_list(current_table, enter_col)
        leave_row, _ = ratio_test(ratio_list, current_table)
        if leave_row is None:
            record['status'] = '无界'
            return record
        current_table = pivot(current_table, enter_col, leave_row)
        path.append(current_table)
        record['iteration_tables'] = path
    return record


def endpoint_check_group(table, lower_bound, upper_bound, model, inner_status):
    """对一个区间的两个端点各做一次精确判定，只保留"与区间内部状态不同"的端点。"""
    conclusion = []
    for position, lambda_value in (('左端点', lower_bound), ('右端点', upper_bound)):
        if lambda_value is None:
            continue
        verdict = endpoint_check(table, lambda_value, model)
        if verdict['status'] == '未判定' or verdict['status'] == inner_status:
            continue
        conclusion.append({'position': position, 'lambda_value': lambda_value, 'verdict': verdict})
    return conclusion


def interval_interior_text(lower_bound, upper_bound):
    """写区间"内部"的开区间文本（端点精化说明用）。"""
    if upper_bound is None:
        return '(%s, +∞)' % number_to_text(lower_bound)
    return '(%s, %s)' % (number_to_text(lower_bound), number_to_text(upper_bound))


def endpoint_conclusion_text(endpoint_item, model):
    """把一条端点判定结果写成中文结论。"""
    verdict = endpoint_item['verdict']
    position = '%s λ = %s' % (endpoint_item['position'], number_to_text(endpoint_item['lambda_value']))
    if verdict['status'] == '最优':
        solution_text = '，'.join('%s = %s' % (name, number_to_text(value)) for name, value in (verdict['optimal_solution'] or {}).items())
        multiple_note = '；该点有多重最优解' if verdict.get('has_multiple_optima') else ''
        return ('%s 时该点有有限最优值 %s = %s（最优解 %s%s）'
                % (position, objective_name(model), verdict['optimal_value_text'], solution_text, multiple_note))
    if verdict['status'] == '无界':
        return '%s 时该点无界（z → +∞）' % position
    return ''


def endpoint_summary_sentence(intervals, model):
    """把各区间的端点结论汇总成一句话（没有端点结论就返回空串）。"""
    fragment = []
    for interval in intervals:
        for endpoint in (interval.get('endpoint_conclusions') or []):
            fragment.append('区间 %s 的%s' % (interval['interval_text'], endpoint_conclusion_text(endpoint, model)))
    if not fragment:
        return ''
    return '；'.join(fragment) + '。'


def build_interval_record(table, lower_bound, upper_bound, representative_point, path, model, status):
    """生成一个 λ 区间的记录（供归并、整理成区间字典用）。"""
    table_copies = [copy.deepcopy(term) for term in path]
    record = {'interval_lower_bound': lower_bound, 'interval_upper_bound': upper_bound, 'representative_point': representative_point,
          'iteration_tables': table_copies, 'status': status, 'model': model,
          'basis': None, 'optimal_solution': None, 'optimal_value_expression': None, 'degenerate': False, 'has_multiple_optima': False,
          'endpoint_conclusions': []}
    if status == '最优':
        record['basis'] = list(table['basis'])
        record['optimal_solution'] = extract_original_solution(table, model)
        record['optimal_value_expression'] = table_objective_expression(table, model)
        record['degenerate'] = check_degenerate(table)[0]
        record['has_multiple_optima'] = has_zero_sigma_nonbasic(table)
    start_table = path[0] if path else table               # endpoint_check 从区间的起点表开始迭代
    record['endpoint_conclusions'] = endpoint_check_group(start_table, lower_bound, upper_bound, model, status)
    return record


def interval_recursion(table, lower_bound, upper_bound, path, records, candidates, model, max_intervals):
    """参数 λ 法的区间递归：按临界值二分区间，否则在代表点上迭代一次。"""
    if len(records) >= max_intervals:
        return
    criticals = find_critical_lambda(table['sigma'], lower_bound, upper_bound)
    candidates.extend(criticals)
    if criticals:
        lambda_1 = criticals[0]
        interval_recursion(table, lower_bound, lambda_1, path, records, candidates, model, max_intervals)
        interval_recursion(table, lambda_1, upper_bound, path, records, candidates, model, max_intervals)
        return
    representative_point = (lower_bound + upper_bound) / 2 if upper_bound is not None else lower_bound + 1
    numeric_sigma = [lambda_eval(sigma_value, representative_point) for sigma_value in table['sigma']]
    enter_col, _ = select_entering_column(numeric_sigma, None)
    if enter_col is None:
        records.append(build_interval_record(table, lower_bound, upper_bound, representative_point, path, model, '最优'))
        return
    ratio_list = compute_ratio_list(table, enter_col)
    table['ratio_list'] = ratio_list                     # 记下来，旋转后写"主元"公式时要用
    leave_row, _ = ratio_test(ratio_list, table)
    if leave_row is None:
        records.append(build_interval_record(table, lower_bound, upper_bound, representative_point, path, model, '无界'))
        return
    new_table = pivot(table, enter_col, leave_row)
    interval_recursion(new_table, lower_bound, upper_bound, path + [new_table], records, candidates, model, max_intervals)


def merge_intervals(records):
    """把相邻且"状态、最优基、最优值表达式都相同"的区间合并成一个区间。"""
    merged = []
    for record in records:
        if merged:
            previous_record = merged[-1]
            contiguous = previous_record['interval_upper_bound'] == record['interval_lower_bound']
            same_kind = (previous_record['status'] == record['status'] == '最优'
                  and previous_record['basis'] == record['basis']
                  and previous_record['optimal_value_expression'] == record['optimal_value_expression'])
            if contiguous and same_kind:
                previous_record['interval_upper_bound'] = record['interval_upper_bound']
                previous_record['representative_point'] = record['representative_point']
                if len(record['iteration_tables']) > len(previous_record['iteration_tables']):
                    previous_record['iteration_tables'] = record['iteration_tables']
                continue
        merged.append(record)
    return merged


def finalize_interval(record, model):
    """把合并后的区间记录整理成统一格式的"区间字典"。"""
    lower_bound = record['interval_lower_bound']
    upper_bound = record['interval_upper_bound']
    if upper_bound is None:
        interval_text = '[%s, +∞)' % number_to_text(lower_bound)
    else:
        interval_text = '[%s, %s]' % (number_to_text(lower_bound), number_to_text(upper_bound))
    iteration_tables = record['iteration_tables']
    endpoint_conclusions = record.get('endpoint_conclusions') or []
    interval = {
        'interval_text': interval_text, 'interval_lower_bound': lower_bound, 'interval_upper_bound': upper_bound,
        'representative_point': record['representative_point'], 'iteration_tables': iteration_tables, 'status': record['status'],
        'optimal_basis': record.get('basis'), 'optimal_solution': record.get('optimal_solution'),
        'optimal_value_expression': record.get('optimal_value_expression'),
        'optimal_value_text': parametric_to_text(record['optimal_value_expression'], 'λ') if record.get('optimal_value_expression') else None,
        'degenerate': record.get('degenerate', False), 'has_multiple_optima': record.get('has_multiple_optima', False),
        'endpoint_conclusions': endpoint_conclusions,
        'judgement': '',
    }
    endpoint_segment = '；'.join(endpoint_conclusion_text(endpoint, model) for endpoint in endpoint_conclusions)
    if record['status'] == '最优':
        interval['judgement'] = ('在区间 %s 内所有 σj(λ) ≤ 0（代表点 λ0 = %s 处检验数全部 ≤ 0，'
                     '且区间内没有新的临界值，σ 的符号与大小次序都不变）→ 已达最优，'
                     '本区间的最优基保持不变' % (interval_text, number_to_text(record['representative_point'])))
        if endpoint_segment:
            interval['judgement'] += '；' + endpoint_segment
    else:
        if endpoint_segment:
            interval['judgement'] = ('区间 %s：%s；区间内部 %s 无界，没有有限最优值（z → +∞）'
                        % (interval_text, endpoint_segment, interval_interior_text(lower_bound, upper_bound)))
        else:
            interval['judgement'] = ('在区间 %s 内，入基列的所有系数 ≤ 0，目标函数值可以无限增大 → 该区间无界解（z → +∞）'
                        % interval_text)
    if iteration_tables:
        iteration_tables[-1]['judgement'] = interval['judgement']
    return interval


def parametric_lambda_method(model, lambda_lower_bound=Fraction(0), max_intervals=20):
    """带参数 λ 的单纯形法（含分类讨论）。"""
    lower_bound = to_fraction(lambda_lower_bound)
    initial_table = build_initial_table(model)
    records = []
    candidates = []
    interval_recursion(initial_table, lower_bound, None, [initial_table], records, candidates, model, max_intervals)
    records.sort(key=lambda record: record['interval_lower_bound'])
    merged = merge_intervals(records)
    interval_results = [finalize_interval(record, model) for record in merged]
    critical_values = []
    for i in range(len(interval_results) - 1):
        upper_bound = interval_results[i]['interval_upper_bound']
        if upper_bound is not None and upper_bound not in critical_values:
            critical_values.append(upper_bound)
    for i, interval in enumerate(interval_results):                      # 临界点处两个基都是最优，必须写明
        next_record = interval_results[i + 1] if i + 1 < len(interval_results) else None
        if interval['interval_upper_bound'] is None:
            continue
        if interval['status'] != '最优' or next_record is None or next_record['status'] != '最优':
            continue      # 相邻区间有无界时不做"临界点多重最优"的说法（那里根本没有有限最优值）
        interval['judgement'] += ('；在临界值 λ = %s 处，本区间与下一个区间的最优基都满足最优判据，'
                    '所以 λ = %s 时原问题有多重最优解（两组的 z 值相同）'
                    % (number_to_text(interval['interval_upper_bound']), number_to_text(interval['interval_upper_bound'])))
        if interval['iteration_tables']:
            interval['iteration_tables'][-1]['judgement'] = interval['judgement']
    all_tables = []
    for interval in interval_results:
        all_tables.extend(interval['iteration_tables'])
    has_unbounded = any(interval['status'] == '无界' for interval in interval_results)
    result = {
        'model': model, 'method': '参数λ单纯形法', 'problem_type': model['problem_type'],
        'status': '无界' if has_unbounded else '最优',
        'iteration_tables': all_tables, 'last_table': all_tables[-1] if all_tables else None,
        'optimal_solution': None, 'all_variable_solution': None, 'optimal_value': None,
        'conversion_notes': list(model['conversion_notes']),
        'degenerate': any(interval['degenerate'] for interval in interval_results),
        'has_multiple_optima': any(interval['has_multiple_optima'] for interval in interval_results),
        'alternative_optima': [],
        'artificial_check': '本题没有人工变量（约束全是 ≤ 型）',
        'phase_one': None, 'interval_results': interval_results, 'critical_values': critical_values,
        'candidate_critical_values': sorted(set(candidates)),
        'method_reason': default_reason('参数λ单纯形法'), 'conclusion': '',
    }
    result['conclusion'] = write_conclusion(model, result)
    return result


# ==================== 十、自动选题型、渲染、一站式入口 ====================

def select_method(original_type, signs, rhs_list, obj_coeffs, has_lambda=False):
    """自动判断题型并推荐方法。"""
    if has_lambda:
        return ('参数λ单纯形法', '目标函数含参数 λ，需要在 λ 的每个区间上分类讨论')
    normalized_signs = [normalize_sign(sentence) for sentence in signs]
    if any(sentence in ('>=', '=') for sentence in normalized_signs):
        return ('大M法', '含 ≥ 或 = 约束，需要人工变量，大M法用 -M 惩罚人工变量（也可以改选两阶段法）')
    if any(to_fraction(value) < 0 for value in rhs_list):
        return ('对偶单纯形法', '约束全是 ≤ 型但存在负右端项，初始基不可行而检验数全 ≤ 0，用对偶单纯形法最合适')
    return ('普通单纯形法', '所有约束都是 ≤ 型、右端项都非负，松弛变量直接给出初始可行基，不需要人工变量')


def indent_continuation_lines(text):
    """给多行文本的续行加 8 个空格缩进（让【判断】文字的续行对齐）。"""
    return text.replace('\n', '\n' + ' ' * 8)


def render_table(table):
    """把一张表渲染成多行文本。"""
    symbol = table.get('parametric_symbol')
    var_names = table['var_names']
    row = [table['title'], '当前基变量：' + ' → '.join(var_names[k] for k in table['basis'])]
    cells = [' ' * 6, 'cj →'.rjust(8), ' ' * 10]
    for j in range(len(var_names)):
        cells.append(value_to_text(table['c'][j], symbol).rjust(10))
    row.append(''.join(cells))
    cells = ['cB'.rjust(6), 'xB'.rjust(8), 'b'.rjust(10)]
    for name in var_names:
        cells.append(name.rjust(10))
    row.append(''.join(cells))
    for i in range(len(table['constraint_matrix'])):
        cells = [value_to_text(table['basis_coeffs'][i], symbol).rjust(6), var_names[table['basis'][i]].rjust(8),
             value_to_text(table['rhs'][i], symbol).rjust(10)]
        for j in range(len(var_names)):
            cells.append(number_to_text(table['constraint_matrix'][i][j]).rjust(10))
        row.append(''.join(cells))
    cells = [' ' * 6, 'σj'.rjust(8), ' ' * 10]
    for value in table['sigma']:
        cells.append(value_to_text(value, symbol).rjust(10))
    row.append(''.join(cells))
    row.append('【判断】' + indent_continuation_lines(table['judgement']))
    row.append('')
    if table['iteration_number'] == 0:
        row.append('【本表计算公式】')
    else:
        row.append('【本表计算公式（本表由第 %d 轮表旋转得到）】' % (table['iteration_number'] - 1))
    for term in table['formulas']:
        row.append(term)
    return '\n'.join(row)


def linear_expression_text(coefficient_list, var_name_list, symbol=None):
    """把系数与变量名拼成 '2x1 + 3x2' 这样的式子。"""
    fragment = []
    for j, coefficient in enumerate(coefficient_list):
        text = value_to_text(coefficient, symbol)
        if text == '0':
            continue
        if text == '1':
            term_text = var_name_list[j]
        elif text == '-1':
            term_text = '-' + var_name_list[j]
        elif is_expression(coefficient) and ('+' in text or '-' in text[1:]):
            term_text = '(' + text + ')' + var_name_list[j]      # 1+λ → (1+λ)x1，避免误会
        else:
            term_text = text + var_name_list[j]
        fragment.append(term_text)
    if not fragment:
        return '0'
    result = fragment[0]
    for term_text in fragment[1:]:
        if term_text.startswith('-'):
            result = result + ' - ' + term_text[1:]
        else:
            result = result + ' + ' + term_text
    return result


def original_problem_text(model):
    """把用户输入的原始问题写成中文式子（【题目】那一行）。"""
    original_var_names = ['x%d' % (j + 1) for j in range(model['original_var_count'])]
    symbol = model['parametric_symbol']
    if model['method'] == '参数λ单纯形法':
        fragment = ['%s z(λ) = %s' % (model['original_type'], linear_expression_text(model['original_obj_coeffs'], original_var_names, 'λ'))]
    else:
        fragment = ['%s z = %s' % (model['original_type'], linear_expression_text(model['original_obj_coeffs'], original_var_names, symbol))]
    for i, row in enumerate(model['original_constraint_matrix']):
        fragment.append('%s %s %s' % (linear_expression_text(row, original_var_names, symbol),
                              normalize_sign(model['original_signs'][i]),
                              value_to_text(model['original_rhs'][i], 'λ' if model.get('has_lambda_rhs') else symbol)))
    fragment.append('，'.join(original_var_names) + ' ≥ 0')
    return '；'.join(fragment)


def standardized_objective_text(model):
    """写出标准化后的目标函数（两阶段法会分别写第一阶段与第二阶段的目标）。"""
    symbol = model['parametric_symbol']
    if model['method'] == '两阶段法':
        return ('第一阶段：max w′ = -（各人工变量之和），即 %s；第二阶段：%s（人工变量位置记 0）'
                % (linear_expression_text(model['obj_coeffs'], model['var_names'], symbol),
                   linear_expression_text(model['second_obj_coeffs'], model['var_names'], symbol)))
    if model['original_type'] == 'min':
        return 'max z′ = ' + linear_expression_text(model['obj_coeffs'], model['var_names'], symbol)
    return 'max z = ' + linear_expression_text(model['obj_coeffs'], model['var_names'], symbol)


def render_lambda_section(result, model):
    """渲染参数 λ 法的分类讨论部分（每个区间一段：区间说明 + 该区间全部表 + 区间结论）。"""
    row = []
    intervals = result.get('interval_results') or []
    row.append('========== 参数 λ 分类讨论：共 %d 个区间，临界值 %s =========='
            % (len(intervals), critical_value_text(result)))
    if result.get('candidate_critical_values'):
        row.append('（递归过程中找到的全部候选临界值：%s；其中真正改变最优基的才写进结论）'
                % '、'.join(number_to_text(value) for value in result['candidate_critical_values']))
    row.append('')
    for interval in intervals:
        row.append('---------- λ 区间 %s（代表点 λ0 = %s） ----------'
                % (interval['interval_text'], number_to_text(interval['representative_point'])))
        row.append('【区间判断】' + indent_continuation_lines(interval['judgement']))
        row.append('')
        for table in interval['iteration_tables']:
            row.append(render_table(table))
            row.append('')
        if interval.get('optimal_basis'):
            row.append('【本区间结论】最优基 %s；最优解 %s；%s = %s（在区间 %s 内成立）'
                    % (format_basis_names(interval['optimal_basis'], model), interval_solution_text(interval), objective_name(model),
                       interval['optimal_value_text'], interval['interval_text']))
            endpoint_segment = '；'.join(endpoint_conclusion_text(endpoint, model) for endpoint in (interval.get('endpoint_conclusions') or []))
            if endpoint_segment:
                row.append('【端点精化】' + endpoint_segment + '（区间内部的最优结论见上一行）')
        elif interval.get('endpoint_conclusions'):
            endpoint_segment = '；'.join(endpoint_conclusion_text(endpoint, model) for endpoint in interval['endpoint_conclusions'])
            row.append('【本区间结论】区间内部没有有限最优值；%s' % endpoint_segment)
        else:
            row.append('【本区间结论】该区间没有有限最优值：%s' % interval['judgement'])
        row.append('')
    return row


def render_process(result, model):
    """把一次求解的全部表、公式、判断、结论拼成一大段文本。"""
    row = []
    row.append('【题目】' + original_problem_text(model))
    row.append('【题型与方法】本题属于【%s】，采用【%s】。' % (model['problem_type'], result['method']))
    row.append('理由：' + result.get('method_reason', default_reason(result['method'])))
    row.append('')
    row.append('【标准化说明】')
    for i, sentence in enumerate(model['conversion_notes'], 1):
        row.append('%d) %s' % (i, sentence))
    row.append('标准化后：' + standardized_objective_text(model))
    row.append('')
    if result['method'] in ('参数λ单纯形法', PARAMETRIC_RHS_METHOD):
        row.extend(render_lambda_section(result, model))
    else:
        phase_one = result.get('phase_one')
        if phase_one:
            row.append('========== 第一阶段（最小化人工变量之和 w） ==========')
            row.append('第一阶段判断：' + phase_one['judgement'])
            row.append('')
            for table in phase_one['iteration_tables']:
                row.append(render_table(table))
                row.append('')
            if not phase_one.get('entered_phase_two'):
                row.append('（第一阶段已经判定原问题无可行解，不再进入第二阶段）')
                row.append('')
            else:
                row.append('========== 第二阶段（换回原目标函数继续迭代） ==========')
                row.append('')
        for table in result['iteration_tables']:
            row.append(render_table(table))
            row.append('')
    row.append('【结果讨论与结论】')
    row.append(result['conclusion'])
    return '\n'.join(row)


def solve(original_type, obj_coeffs, constraint_matrix, signs, rhs_list, method='自动', lambda_lower_bound=Fraction(0)):
    """一站式入口（main.py 主要调它）。"""
    has_lambda = any(is_expression(value) for value in obj_coeffs)
    has_lambda_rhs = any(is_expression(value) for value in rhs_list)
    if has_lambda and has_lambda_rhs:
        raise ValueError('参数 λ 只能写在"目标函数系数"或"约束右端项"的其中一处，不能同时写。')
    if has_lambda_rhs:
        # 右端项含 λ：走"参数右端项"分析（目标函数必须是普通数字）
        return solve_parametric_rhs(original_type, obj_coeffs, constraint_matrix, signs,
                                    [(to_expression(value)[0], to_expression(value)[1]) for value in rhs_list],
                                    lambda_lower_bound)
    if method in ('自动', None, ''):
        method, reason = select_method(original_type, signs, rhs_list, obj_coeffs, has_lambda)
    else:
        reason = default_reason(method)
    model = standardize(original_type, obj_coeffs, constraint_matrix, signs, rhs_list, method)
    model['lambda_lower_bound'] = to_fraction(lambda_lower_bound) if method == '参数λ单纯形法' else None
    if method == '普通单纯形法':
        result = primal_simplex(model)
    elif method == '大M法':
        result = big_m_method(model)
    elif method == '两阶段法':
        result = two_phase_method(model)
    elif method == '对偶单纯形法':
        result = dual_simplex_method(model)
    else:
        result = parametric_lambda_method(model, lambda_lower_bound)
    result['method_reason'] = reason
    result['conclusion'] = write_conclusion(model, result)
    return result


# ==================== 十一、参数右端项：约束右端项 b 也含参数 λ ====================
# 这一节处理"约束右端项含参数"的题目，即 b_i(λ) = p_i + q_i λ（目标函数里不含 λ）。
# 做法（参数右端项的标准算法）：
#   1) 先在讨论域左端点（这一点不可行就往右再试几个点）上解一次普通 LP，得到一个最优基；
#   2) 对固定的一组基，基变量取值 xB(λ) = B⁻¹b(λ) = v0 + λ·v1 是 λ 的一次函数，
#      由 xB(λ) ≥ 0 解出这组基"有效"的 λ 区间；
#   3) 走到区间端点时某个基变量正好取到 0：用对偶单纯形规则换一次基，继续往 λ 增大
#      （或减小）的方向推进，直到这一侧没有限制、或者再过去就没有可行解。
#   σ 行与系数矩阵只跟基有关、与 λ 无关，所以每一步换基后最优性都自动保持；
#   区间结论里的 x(λ)、z(λ) 都写成精确的一次表达式 p + qλ。

PARAMETRIC_RHS_METHOD = '参数λ右端项单纯形法'
PARAM_RHS_MAX_STEPS = 20      # 每个方向最多换基多少次（防止退化时来回打转）
PARAM_RHS_START_TRIES = 8     # 起点不可行时，最多往右再试几个 λ 值去找可行起点


def invert_matrix(matrix):
    """精确求逆（高斯-若尔当消元，全用 Fraction）；矩阵奇异时返回 None。"""
    size = len(matrix)
    augmented = []
    for i in range(size):
        row = [to_fraction(matrix[i][j]) for j in range(size)]
        row.extend(Fraction(1) if i == j else Fraction(0) for j in range(size))
        augmented.append(row)
    for col in range(size):
        pivot_row = None
        for r in range(col, size):
            if augmented[r][col] != 0:
                pivot_row = r
                break
        if pivot_row is None:
            return None
        augmented[col], augmented[pivot_row] = augmented[pivot_row], augmented[col]
        pivot_value = augmented[col][col]
        augmented[col] = [value / pivot_value for value in augmented[col]]
        for r in range(size):
            if r == col or augmented[r][col] == 0:
                continue
            coefficient = augmented[r][col]
            augmented[r] = [augmented[r][j] - coefficient * augmented[col][j] for j in range(2 * size)]
    return [row[size:] for row in augmented]


def normalize_rhs_rows(constraint_matrix, signs, rhs_pairs, lambda_point):
    """在 λ = lambda_point 这一点上，把"右端项为负"的行整行乘 -1（λ 的系数一起变号）。

    这样起点上所有 b_i(λ0) ≥ 0，松弛变量 / 人工变量给出的初始基一定可行。
    """
    matrix = []
    new_signs = []
    new_pairs = []
    for i, row in enumerate(constraint_matrix):
        constant_part, parameter_part = to_fraction(rhs_pairs[i][0]), to_fraction(rhs_pairs[i][1])
        if constant_part + parameter_part * lambda_point < 0:
            matrix.append([-to_fraction(value) for value in row])
            new_signs.append(flip_sign(normalize_sign(signs[i])))
            new_pairs.append((-constant_part, -parameter_part))
        else:
            matrix.append([to_fraction(value) for value in row])
            new_signs.append(normalize_sign(signs[i]))
            new_pairs.append((constant_part, parameter_part))
    return (matrix, new_signs, new_pairs)


def attach_parameter_rhs(model, original_pairs, flipped_pairs, signs):
    """把"右端项含 λ"的信息挂到标准化模型上（表里的 b 列要按 λ 的表达式显示）。"""
    model['method'] = PARAMETRIC_RHS_METHOD
    model['problem_type'] = classify_problem_type(model['original_type'], signs, PARAMETRIC_RHS_METHOD)
    model['parametric_symbol'] = 'λ'
    model['has_lambda_rhs'] = True
    model['rhs_pairs'] = [(to_fraction(pair[0]), to_fraction(pair[1])) for pair in flipped_pairs]
    model['rhs_zero'] = [to_fraction(pair[0]) for pair in flipped_pairs]
    model['rhs_one'] = [to_fraction(pair[1]) for pair in flipped_pairs]
    model['original_rhs_pairs'] = [(to_fraction(pair[0]), to_fraction(pair[1])) for pair in original_pairs]
    model['original_rhs'] = [parametric_expr(pair[0], pair[1]) for pair in original_pairs]
    if model.get('second_obj_coeffs') is not None:          # 两阶段法：第二阶段才用原目标函数
        model['param_rhs_c'] = list(model['second_obj_coeffs'])
    else:
        model['param_rhs_c'] = list(model['obj_coeffs'])
    model['conversion_notes'].append(
        '本题右端项含参数 λ：b(λ) = b0 + λ·b1。做法是先在某个 λ 上求出一个最优基，'
        '再把基变量取值 xB(λ) = B⁻¹b(λ) 看成 λ 的一次函数，由 xB(λ) ≥ 0 定出这组基有效的 λ 区间；'
        '走到区间端点时某个基变量正好等于 0，就用对偶单纯形换基继续推进'
        '（σ 行与系数矩阵都与 λ 无关，所以换基后最优性自动保持）')
    return model


def basis_lambda_solution(basis, matrix, b_zero, b_one):
    """给定一组基，解出基变量取值 xB(λ) = v0 + λ·v1（= B⁻¹b(λ)）；基奇异时返回 None。"""
    size = len(basis)
    basis_matrix = [[matrix[i][k] for k in basis] for i in range(size)]
    inverse = invert_matrix(basis_matrix)
    if inverse is None:
        return None
    v0 = [sum(inverse[i][k] * b_zero[k] for k in range(size)) for i in range(size)]
    v1 = [sum(inverse[i][k] * b_one[k] for k in range(size)) for i in range(size)]
    return (v0, v1)


def lambda_feasible_range(v0, v1):
    """由 xB(λ) = v0 + λ·v1 ≥ 0 解出这组基有效的 λ 范围。

    返回 (low, high, broken, low_row, high_row)：
      low / high —— 区间端点，None 表示这一侧没有限制；
      broken     —— 某一行"常数部分就是负的"，这组基在任何 λ 上都不可行；
      low_row / high_row —— 决定端点的是第几行的基变量（结论里说明"谁先到 0"）。
    """
    low = None
    high = None
    low_row = None
    high_row = None
    for i in range(len(v0)):
        constant_part, parameter_part = v0[i], v1[i]
        if parameter_part < 0:                       # 斜率向下 → λ 太大这一行就变负
            bound = Fraction(-constant_part, parameter_part)
            if high is None or bound < high:
                high = bound
                high_row = i
        elif parameter_part > 0:                     # 斜率向上 → λ 太小这一行就变负
            bound = Fraction(-constant_part, parameter_part)
            if low is None or bound > low:
                low = bound
                low_row = i
        elif constant_part < 0:
            return (None, None, True, None, None)
    return (low, high, False, low_row, high_row)


def parameter_rhs_tableau(model, kept, basis, lambda_value, iteration_number, title):
    """按当前基把标准化模型化成一张规范单纯形表（A′ = B⁻¹A，与 λ 无关），
    b 列取 λ = lambda_value 处的数值（显示时再换成 λ 的表达式）。

    返回 (table, v0, v1)：v0、v1 是 xB(λ) = v0 + λ·v1 的两部分；基奇异时返回 (None, None, None)。
    """
    matrix = model['constraint_matrix']
    row_count = len(matrix)
    basis_matrix = [[matrix[i][k] for k in basis] for i in range(row_count)]
    inverse = invert_matrix(basis_matrix)
    if inverse is None:
        return (None, None, None)
    b_zero, b_one = model['rhs_zero'], model['rhs_one']
    v0 = [sum(inverse[i][k] * b_zero[k] for k in range(row_count)) for i in range(row_count)]
    v1 = [sum(inverse[i][k] * b_one[k] for k in range(row_count)) for i in range(row_count)]
    tableau = [[sum(inverse[i][k] * matrix[k][j] for k in range(row_count)) for j in kept] for i in range(row_count)]
    coeffs = [model['param_rhs_c'][j] for j in kept]
    table = {
        'iteration_number': iteration_number,
        'title': title,
        'var_names': [model['var_names'][j] for j in kept],
        'c': coeffs,
        'basis': [kept.index(k) for k in basis],
        'basis_coeffs': [coeffs[kept.index(k)] for k in basis],
        'constraint_matrix': tableau,
        'rhs': [v0[i] + v1[i] * lambda_value for i in range(row_count)],
        'sigma': [],
        'objective_value': Fraction(0),
        'ratio_list': [],
        'formulas': [],
        'judgement': '',
        'degenerate': False,
        'parametric_symbol': 'λ',
        'is_dual': False,
        'enter_col': None,
        'ratio_message': '',
        'conversion_notes': list(model['conversion_notes']),
    }
    sigma, objective_value, _sigma_formulas = compute_sigma(table)
    table['sigma'] = sigma
    table['objective_value'] = objective_value
    table['degenerate'] = check_degenerate(table)[0]
    return (table, v0, v1)


def parameter_rhs_pivot(model, kept, basis, v0, v1, lambda_edge, edge_row, iteration_number, title):
    """在某个基变量正好取到 0 的临界 λ 上做一次对偶单纯形换基。

    返回 (新的基（模型列下标）, 换基后的表, 说明文字)；这一侧走不下去时返回 (None, None, 说明)。
    """
    table, _v0, _v1 = parameter_rhs_tableau(model, kept, basis, lambda_edge, iteration_number, title)
    if table is None:
        return (None, None, '这一组基的基矩阵奇异，无法继续换基')
    enter_col, _ratio_list, message = dual_ratio_test(table, edge_row)
    if enter_col is None:
        return (None, None, message)
    new_basis = list(basis)
    new_basis[edge_row] = kept[enter_col]              # 入基列进入第 edge_row 行
    new_table, _v0, _v1 = parameter_rhs_tableau(model, kept, new_basis, lambda_edge, iteration_number + 1, title)
    return (new_basis, new_table, message)


def parameter_rhs_walk(model, kept, basis, direction, first_table, max_steps=PARAM_RHS_MAX_STEPS):
    """沿 direction（+1 往 λ 增大的方向、-1 往减小的方向）逐段换基。

    每一段记录：{'basis','v0','v1','low','high','edge','edge_row','table','ended_by'}
      ended_by：'pivot'（正常换基继续）/ 'no_limit'（这一侧没有限制，可以一直走下去）
                / 'infeasible'（再过去就没有可行解了）/ 'cycle' / 'limit'
    """
    matrix = model['constraint_matrix']
    b_zero, b_one = model['rhs_zero'], model['rhs_one']
    segments = []
    seen = {tuple(basis)}
    current_basis = list(basis)
    current_table = first_table
    for _step in range(max_steps + 1):
        solution = basis_lambda_solution(current_basis, matrix, b_zero, b_one)
        if solution is None:
            segments.append({'basis': current_basis, 'v0': None, 'v1': None, 'low': None, 'high': None,
                             'edge': None, 'edge_row': None, 'table': current_table, 'ended_by': 'singular'})
            break
        v0, v1 = solution
        low, high, broken, low_row, high_row = lambda_feasible_range(v0, v1)
        if broken:
            segments.append({'basis': current_basis, 'v0': v0, 'v1': v1, 'low': low, 'high': high,
                             'edge': None, 'edge_row': None, 'table': current_table, 'ended_by': 'infeasible'})
            break
        edge, edge_row = (high, high_row) if direction > 0 else (low, low_row)
        if edge is None:
            segments.append({'basis': current_basis, 'v0': v0, 'v1': v1, 'low': low, 'high': high,
                             'edge': None, 'edge_row': None, 'table': current_table, 'ended_by': 'no_limit'})
            break
        segments.append({'basis': current_basis, 'v0': v0, 'v1': v1, 'low': low, 'high': high,
                         'edge': edge, 'edge_row': edge_row, 'table': current_table, 'ended_by': 'pivot'})
        title = '参数右端项单纯形表（第 %d 次换基，λ = %s 处的表）' % (len(segments), number_to_text(edge))
        new_basis, pivot_table, _message = parameter_rhs_pivot(model, kept, current_basis, v0, v1, edge, edge_row,
                                                               len(segments), title)
        if new_basis is None:
            segments[-1]['ended_by'] = 'infeasible'
            break
        key = tuple(new_basis)
        if key in seen:
            segments[-1]['ended_by'] = 'cycle'
            break
        seen.add(key)
        current_basis = new_basis
        current_table = pivot_table
    else:
        segments[-1]['ended_by'] = 'limit'
    return segments


def parameter_rhs_basis(model, last_table):
    """从数值求解的末表读出：参与迭代的列（kept）与当前基（都换算成模型里的列下标）。"""
    mapping = last_table.get('full_index_mapping')
    kept = list(mapping) if mapping else list(range(len(model['var_names'])))
    if len(last_table['constraint_matrix']) != len(model['constraint_matrix']):
        raise ValueError('本题的约束里有冗余（第一阶段出现过 0 = 0 的多余约束），'
                         '参数右端项法暂不支持，请先去掉多余的约束再试')
    basis = [kept[k] for k in last_table['basis']]
    return (kept, basis, len(last_table['constraint_matrix']))


def parameter_rhs_solution_vector(basis, v0, v1, model):
    """把这组基的取值整理成"原始变量名 → λ 表达式"（非基变量记 0）。"""
    solution = {}
    for k in range(model['original_var_count']):
        name = model['var_names'][k]
        if k in basis:
            row = basis.index(k)
            solution[name] = parametric_expr(v0[row], v1[row])
        else:
            solution[name] = Fraction(0)
    return solution


def parameter_rhs_display_table(segment, model, kept, v0, v1, value_expression, title, judgement):
    """把一段的表复制成"b 列写成 λ 表达式"的显示用表（z 也写成 λ 的表达式）。"""
    table = copy.deepcopy(segment['table'])
    table['title'] = title
    table['judgement'] = judgement
    table['rhs'] = [parametric_expr(constant_part, parameter_part) for constant_part, parameter_part in zip(v0, v1)]
    table['objective_value'] = parametric_expr(value_expression[0], value_expression[1])
    table['ratio_list'] = []
    table['formulas'] = [
        '1) 本表是"参数右端项"用的表：右端项 b(λ) = b0 + λ·b1，所以 b 列（也就是基变量取值）'
        '写成 λ 的一次式，例如 %s' % '，'.join(
            '%s = %s' % (table['var_names'][table['basis'][i]], parametric_to_text((v0[i], v1[i]), 'λ'))
            for i in range(len(v0))),
        '2) 本区间的基不变：x(λ) = B⁻¹b(λ) 是 λ 的一次函数，所以区间内每个变量的取值都按上面这些式子算',
        '3) σ 行与系数矩阵只与基有关、与 λ 无关（本题 σ 行全是普通数字），所以这一组基在'
        'x(λ) ≥ 0 的整个区间内都是最优基',
        '4) 目标函数值 z(λ) = cB·xB(λ) = %s' % parametric_to_text(value_expression, 'λ'),
    ]
    return table


def build_parameter_rhs_intervals(model, kept, lower_bound, forward, backward, status):
    """把两个方向走出来的段拼成区间列表（换算成 interval_results 的统一格式）。"""
    segments = list(reversed(backward)) + list(forward[1:])
    intervals = []
    for segment in segments:
        low = segment['low']
        high = segment['high']
        if high is not None and high <= lower_bound:          # 整段都在讨论域左边，丢掉
            continue
        clipped_low = lower_bound if low is None or low < lower_bound else low
        if segment['v0'] is None:
            continue
        v0, v1 = segment['v0'], segment['v1']
        z0 = sum(model['param_rhs_c'][segment['basis'][i]] * v0[i] for i in range(len(segment['basis'])))
        z1 = sum(model['param_rhs_c'][segment['basis'][i]] * v1[i] for i in range(len(segment['basis'])))
        if model['original_type'] == 'min':                    # 目标值按原始 min/max 回代
            z0, z1 = -z0, -z1
        # 这张表只用来读 σ 行 / 变量名 / 基（判断这组基有没有多重最优解）：
        # 复用现成的 parameter_rhs_tableau（σ 行只与基有关、与 b 列取值无关，λ=0 处的表就够用）。
        # 注意它的 basis 参数要的是"模型列下标"，所以直接传 segment['basis']。
        table_for_value, _basis_value_zero, _basis_value_one = parameter_rhs_tableau(
            model, kept, segment['basis'], Fraction(0), 0, '')
        basis_set = set(segment['basis'])
        multiple = any(sigma_is_zero(table_for_value['sigma'][j], None)
                       for j in range(len(table_for_value['var_names'])) if j not in basis_set)
        degenerate = any(v0[i] == 0 and v1[i] == 0 for i in range(len(v0)))
        upper_text = '＋∞' if high is None else number_to_text(high)
        interval_text = '[%s, %s]' % (number_to_text(clipped_low), upper_text)
        conclusion = []
        if status == '最优':
            conclusion.append('在区间 %s 内：基变量取值 %s，其它变量取 0；%s = %s'
                              % (interval_text,
                                 '、'.join('%s = %s' % (table_for_value['var_names'][table_for_value['basis'][i]],
                                                        parametric_to_text((v0[i], v1[i]), 'λ'))
                                          for i in range(len(v0))),
                                 objective_name(model), parametric_to_text((z0, z1), 'λ')))
        else:
            conclusion.append('在区间 %s 内约束有可行解，但目标函数可以无限增大（z → +∞），没有有限最优值'
                              % interval_text)
        if segment['ended_by'] == 'pivot':
            conclusion.append('当 λ = %s 时第 %d 行的基变量 %s 正好取到 0，'
                              '再用对偶单纯形换基就能往 λ 更大（更小）的方向继续推进'
                              % (number_to_text(segment['edge']), segment['edge_row'] + 1,
                                 table_for_value['var_names'][table_for_value['basis'][segment['edge_row']]]))
        elif segment['ended_by'] == 'no_limit':
            conclusion.append('这一组基在 %s 这一侧都能保持可行，所以区间一直延伸下去'
                              % ('λ ≥ ' + number_to_text(clipped_low) if high is None else 'λ ≤ ' + number_to_text(high)))
        elif segment['ended_by'] == 'infeasible':
            conclusion.append('再往前 λ 变化时，本行的右端项会让这个基变量变负，'
                              '而这一行的所有系数都 ≥ 0，换不出新的可行基 → 再过去就没有可行解了')
        elif segment['ended_by'] == 'cycle':
            conclusion.append('出现退化，继续换基还是回到已经出现过的基，为了避免死循环就地停下')
        elif segment['ended_by'] == 'limit':
            conclusion.append('换基次数到了上限，就先停在这里')
        judgement = '；'.join(conclusion) + '。'
        representative = clipped_low if high is None else min(clipped_low, high)
        interval = {
            'interval_text': interval_text,
            'interval_lower_bound': clipped_low,
            'interval_upper_bound': high,
            'representative_point': representative,
            'iteration_tables': [parameter_rhs_display_table(
                segment, model, kept, v0, v1, (z0, z1),
                '参数右端项单纯形表（区间 %s；b 列写成 λ 的表达式）' % interval_text, judgement)],
            'status': status,
            'optimal_basis': list(segment['basis']),
            'optimal_solution': parameter_rhs_solution_vector(segment['basis'], v0, v1, model),
            'optimal_value_expression': (z0, z1),
            'optimal_value_text': parametric_to_text((z0, z1), 'λ'),
            'degenerate': degenerate,
            'has_multiple_optima': multiple,
            'endpoint_conclusions': [],
            'judgement': judgement,
        }
        intervals.append(interval)
    # 相邻区间如果基和结论都一样（退化时可能出现），合并成一个
    merged = []
    for interval in intervals:
        if merged:
            previous = merged[-1]
            if (previous['interval_upper_bound'] == interval['interval_lower_bound']
                    and previous['optimal_basis'] == interval['optimal_basis']
                    and previous['optimal_value_expression'] == interval['optimal_value_expression']):
                previous['interval_upper_bound'] = interval['interval_upper_bound']
                previous['interval_text'] = '[%s, %s]' % (number_to_text(previous['interval_lower_bound']),
                                                          '＋∞' if interval['interval_upper_bound'] is None
                                                          else number_to_text(interval['interval_upper_bound']))
                continue
        merged.append(interval)
    return merged


def solve_parametric_rhs(original_type, obj_coeffs, constraint_matrix, signs, rhs_pairs, lambda_lower_bound=Fraction(0)):
    """右端项含参数 λ 的完整分析：把讨论域切成若干区间，逐段给出 x(λ)、z(λ) 与结论。"""
    lower_bound = to_fraction(lambda_lower_bound)
    # 1) 找起点：先试讨论域左端点；这一点不可行就沿 λ 增大方向再试几个点
    #    （λ 的可行集合是一个区间，试到一个可行点之后，往两边推进就能补全）
    start_point = lower_bound
    model = None
    numeric_result = None
    for attempt in range(PARAM_RHS_START_TRIES):
        if attempt:
            start_point = lower_bound + 2 ** (attempt - 1)
        trial_matrix, trial_signs, trial_pairs = normalize_rhs_rows(constraint_matrix, signs, rhs_pairs, start_point)
        trial_rhs = [constant_part + parameter_part * start_point for constant_part, parameter_part in trial_pairs]
        inner_method = '两阶段法' if any(sentence in ('>=', '=') for sentence in trial_signs) else '普通单纯形法'
        trial_model = standardize(original_type, obj_coeffs, trial_matrix, trial_signs, trial_rhs, inner_method)
        trial_model['lambda_lower_bound'] = lower_bound
        numeric_result = two_phase_method(trial_model) if inner_method == '两阶段法' else primal_simplex(trial_model)
        attach_parameter_rhs(trial_model, rhs_pairs, trial_pairs, trial_signs)
        model = trial_model
        if numeric_result['status'] != '无可行':
            break
    if model is None or numeric_result is None or numeric_result['status'] == '无可行':
        return build_infeasible_parameter_rhs_result(model, lower_bound)
    if numeric_result['status'] == '达到最大迭代次数':
        return numeric_result_parameter_rhs_fallback(model, numeric_result, lower_bound)

    status = '无界' if numeric_result['status'] == '无界' else '最优'
    kept, basis, _row_count = parameter_rhs_basis(model, numeric_result['last_table'])
    forward = parameter_rhs_walk(model, kept, basis, 1, numeric_result['last_table'])
    backward = parameter_rhs_walk(model, kept, basis, -1, numeric_result['last_table'])
    intervals = build_parameter_rhs_intervals(model, kept, lower_bound, forward, backward, status)

    critical_values = []
    for i in range(len(intervals) - 1):
        boundary = intervals[i]['interval_upper_bound']
        if boundary is not None and boundary > lower_bound and boundary not in critical_values:
            critical_values.append(boundary)

    all_tables = []
    for interval in intervals:
        all_tables.extend(interval['iteration_tables'])
    result = {
        'model': model, 'method': PARAMETRIC_RHS_METHOD, 'problem_type': model['problem_type'],
        'status': status, 'iteration_tables': all_tables,
        'last_table': all_tables[-1] if all_tables else None,
        'optimal_solution': None, 'all_variable_solution': None, 'optimal_value': None,
        'conversion_notes': list(model['conversion_notes']),
        'degenerate': any(interval['degenerate'] for interval in intervals),
        'has_multiple_optima': any(interval['has_multiple_optima'] for interval in intervals),
        'alternative_optima': [],
        'artificial_check': ('本题按两阶段法处理（含 ≥ 或 = 约束，需要人工变量）'
                             if model.get('second_obj_coeffs') is not None
                             else '约束全是 ≤ 型，不需要人工变量'),
        'phase_one': None, 'interval_results': intervals, 'critical_values': critical_values,
        'candidate_critical_values': list(critical_values),
        'method_reason': default_reason(PARAMETRIC_RHS_METHOD), 'conclusion': '',
    }
    result['conclusion'] = write_conclusion(model, result)
    return result


def numeric_result_parameter_rhs_fallback(model, numeric_result, lower_bound):
    """起点就迭代到上限时的兜底：原样把数值结果返回，避免网页报错。"""
    numeric_result['method'] = PARAMETRIC_RHS_METHOD
    numeric_result['method_reason'] = default_reason(PARAMETRIC_RHS_METHOD)
    return numeric_result


def build_infeasible_parameter_rhs_result(model, lower_bound):
    """整个讨论域都不可行时的结果。"""
    if model is None:
        model = {'original_type': 'max', 'method': PARAMETRIC_RHS_METHOD, 'problem_type': '参数 λ 的右端项分析',
                 'var_names': [], 'original_var_count': 0, 'obj_coeffs': [], 'second_obj_coeffs': None,
                 'constraint_matrix': [], 'rhs': [], 'basis_vars': [], 'slack_indices': [],
                 'surplus_indices': [], 'artificial_indices': [], 'conversion_notes': [],
                 'parametric_symbol': 'λ', 'lambda_lower_bound': lower_bound, 'original_obj_coeffs': [],
                 'original_constraint_matrix': [], 'original_rhs': [], 'original_signs': [],
                 'rhs_zero': [], 'rhs_one': [], 'param_rhs_c': [], 'original_rhs_pairs': []}
    result = {
        'model': model, 'method': PARAMETRIC_RHS_METHOD, 'problem_type': model.get('problem_type', '参数 λ 的右端项分析'),
        'status': '无可行', 'iteration_tables': [], 'last_table': None,
        'optimal_solution': None, 'all_variable_solution': None, 'optimal_value': None,
        'conversion_notes': list(model.get('conversion_notes') or []),
        'degenerate': False, 'has_multiple_optima': False, 'alternative_optima': [],
        'artificial_check': '没有可行解，不涉及人工变量的取舍',
        'phase_one': None, 'interval_results': [], 'critical_values': [],
        'candidate_critical_values': [],
        'method_reason': default_reason(PARAMETRIC_RHS_METHOD), 'conclusion': '',
    }
    result['conclusion'] = write_conclusion(model, result)
    return result


def lambda_rhs_conclusion_lines(model, result):
    """写"参数右端项"法专属的第 3~8 项结论。"""
    row = []
    intervals = result.get('interval_results') or []
    lower_bound = model.get('lambda_lower_bound') or Fraction(0)
    lower_bound_text = number_to_text(lower_bound)
    row.append('3) 讨论域：λ ∈ [%s, +∞)；临界值（换基点）：%s。'
               % (lower_bound_text, critical_value_text(result)))
    if not intervals:
        row.append('4) 分类讨论：在讨论域内没有找到可行解，所以没有区间可以讨论。')
        row.append('5) 临界值说明：没有可行区间，不涉及临界值。')
        row.append('6) 退化：没有可行解，不涉及退化。')
        row.append('7) 人工变量：没有可行解，不涉及人工变量。')
        row.append('8) 结论：在 λ ≥ %s 上原问题没有可行解（右端项随 λ 变化时约束互相矛盾）。' % lower_bound_text)
        return row
    row.append('4) 分类讨论表（λ 的每个区间上：最优基、变量取值的表达式、目标值表达式）：')
    for interval in intervals:
        if interval.get('optimal_basis'):
            row.append('   区间 %s：最优基 %s → %s；%s = %s'
                       % (interval['interval_text'], format_basis_names(interval['optimal_basis'], model),
                          interval_solution_text(interval), objective_name(model), interval['optimal_value_text']))
        else:
            row.append('   区间 %s：%s' % (interval['interval_text'], interval.get('judgement', '')))
    if not critical_value_text(result).startswith('无'):
        row.append('5) 临界值说明：临界值 %s 处，相邻两个区间的最优基都可行，'
                   '所以 λ 取临界值时原问题有多重最优解（两组的 z 值相同）。' % critical_value_text(result))
    else:
        row.append('5) 临界值说明：讨论域内没有换基点，最优基在整个讨论域上不变。')
    degenerate = any(interval.get('degenerate') for interval in intervals)
    row.append('6) 退化：%s' % ('有区间的最优表出现基变量恒等于 0（退化）'
                            if degenerate else '各区间的最优表基变量取值都随 λ 变化，没有退化解'))
    row.append('7) 人工变量：' + result.get('artificial_check', '') + '。')
    if result['status'] == '无界':
        row.append('8) 结论：在 λ ≥ %s 上，约束有可行解但目标函数无界（z → +∞），'
                   '没有有限最优值；各区间的可行范围见第 4 条。' % lower_bound_text)
    else:
        row.append('8) 结论：右端项的 λ 只影响"可行范围"（b 列），不影响检验数 σ，'
                   '所以每个区间内最优基不变、x(λ) 与 z(λ) 都是 λ 的一次式；'
                   '在 λ ≥ %s 上一共分成 %d 个区间，换基点（临界值）处两个相邻基都是最优基。'
                   % (lower_bound_text, len(intervals)))
    return row


# ==================== 十二、内置例题库 ====================

EXAMPLE_LIBRARY = [
    {'number': 1, 'name': '标准 max 型（普通单纯形法）', 'original_type': 'max', 'obj_coeffs': [2, 3],
     'constraint_matrix': [[1, 2], [4, 0], [0, 4]], 'signs': ['<=', '<=', '<='], 'rhs_list': [8, 16, 12],
     'method': '普通单纯形法', 'lambda_lower_bound': None, 'expected': '最优解 (4, 2)，z = 14'},
    {'number': 2, 'name': 'min 型转换（先转 max 再普通单纯形法）', 'original_type': 'min', 'obj_coeffs': [-1, 1],
     'constraint_matrix': [[1, 1], [1, 0], [0, 1]], 'signs': ['<=', '<=', '<='], 'rhs_list': [4, 3, 3],
     'method': '普通单纯形法', 'lambda_lower_bound': None, 'expected': '最优解 (3, 0)，min z = -3'},
    {'number': 3, 'name': '大M法（含 ≥ 约束）', 'original_type': 'max', 'obj_coeffs': [1, 2],
     'constraint_matrix': [[1, 1], [2, -1]], 'signs': ['<=', '>='], 'rhs_list': [7, 2],
     'method': '大M法', 'lambda_lower_bound': None, 'expected': '最优解 (3, 4)，z = 11，人工变量离基'},
    {'number': 4, 'name': '两阶段法（含 = 与 ≥ 约束）', 'original_type': 'max', 'obj_coeffs': [5, 3],
     'constraint_matrix': [[1, 1], [1, 2]], 'signs': ['=', '>='], 'rhs_list': [6, 8],
     'method': '两阶段法', 'lambda_lower_bound': None, 'expected': '最优解 (4, 2)，z = 26，第一阶段 w_min = 0'},
    {'number': 5, 'name': '对偶单纯形法（右端项为负）', 'original_type': 'max', 'obj_coeffs': [-1, -1],
     'constraint_matrix': [[-1, -2], [-2, -1]], 'signs': ['<=', '<='], 'rhs_list': [-3, -3],
     'method': '对偶单纯形法', 'lambda_lower_bound': None, 'expected': '最优解 (1, 1)，z = -2'},
    {'number': 6, 'name': '参数 λ 单纯形法（max 型，分类讨论）', 'original_type': 'max',
     'obj_coeffs': [(1, 1), (2, 0)], 'constraint_matrix': [[1, 1], [1, 0]],
     'signs': ['<=', '<='], 'rhs_list': [4, 2],
     'method': '参数λ单纯形法', 'lambda_lower_bound': 0, 'expected': 'λ ∈ [0, 1]：z = 8；λ ≥ 1：z = 6 + 2λ（临界值 λ = 1）'},
    {'number': 7, 'name': '无界解', 'original_type': 'max', 'obj_coeffs': [1, 1],
     'constraint_matrix': [[1, -1], [-1, 1]], 'signs': ['<=', '<='], 'rhs_list': [1, 1],
     'method': '普通单纯形法', 'lambda_lower_bound': None, 'expected': "状态 = '无界'，第 2 张表判定"},
    {'number': 8, 'name': '无可行解（大M法）', 'original_type': 'max', 'obj_coeffs': [1, 1],
     'constraint_matrix': [[1, 1], [1, 1]], 'signs': ['<=', '>='], 'rhs_list': [1, 3],
     'method': '大M法', 'lambda_lower_bound': None, 'expected': "状态 = '无可行'，人工变量 = 2"},
    {'number': 9, 'name': '多重最优解', 'original_type': 'max', 'obj_coeffs': [2, 4],
     'constraint_matrix': [[1, 2], [1, 1]], 'signs': ['<=', '<='], 'rhs_list': [5, 4],
     'method': '普通单纯形法', 'lambda_lower_bound': None, 'expected': 'max z = 10，多重最优解 (0, 2.5) 与 (3, 1)'},
    {'number': 10, 'name': '退化（基变量取值为 0）', 'original_type': 'max', 'obj_coeffs': [2, 3],
     'constraint_matrix': [[1, 1], [1, 2], [2, 1]], 'signs': ['<=', '<=', '<='], 'rhs_list': [4, 6, 6],
     'method': '普通单纯形法', 'lambda_lower_bound': None, 'expected': '最优解 (2, 2)，z = 10，末表基变量 x5 = 0（退化）'},
    {'number': 11, 'name': '无可行解（两阶段法）', 'original_type': 'max', 'obj_coeffs': [1, 1],
     'constraint_matrix': [[1, 1], [1, 1]], 'signs': ['<=', '>='], 'rhs_list': [1, 3],
     'method': '两阶段法', 'lambda_lower_bound': None, 'expected': "状态 = '无可行'，第一阶段 w_min = 2 > 0"},
    {'number': 12, 'name': '参数 λ 单纯形法（min 型，分类讨论）', 'original_type': 'min',
     'obj_coeffs': [(2, -1), (3, 0)], 'constraint_matrix': [[1, 1], [1, 0]],
     'signs': ['<=', '<='], 'rhs_list': [4, 2],
     'method': '参数λ单纯形法', 'lambda_lower_bound': 0, 'expected': 'λ ∈ [0, 2]：z = 0；λ ≥ 2：z = 4 - 2λ（临界值 λ = 2）'},
]


def get_example(number):
    """按编号取内置例题。"""
    number = int(number)
    for example in EXAMPLE_LIBRARY:
        if example['number'] == number:
            return example
    raise ValueError('例题编号只能是 1~12，请重新输入')

