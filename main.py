# -*- coding: utf-8 -*-
"""
simplex_calc 单纯形表计算器 —— 交互主程序
打印编号菜单与公式模板，读用户输入（编号菜单选题型 / 手动输入 / 载入内置例题），
调用 simplex_core.solve 后逐张表打印计算过程、判断与结论，再回到菜单。
只用标准库 re/sys/fractions.Fraction 与同目录 simplex_core；算法全在核心模块，本文件只做界面与输入容错，输入数字一律用 Fraction 精确保存。
运行方式：python main.py（Windows 控制台中文乱码可先执行 chcp 65001）。
"""

import re
import sys
from fractions import Fraction

try:                                  # 让标准输出按 UTF-8 输出，避免控制台乱码
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# ==================== 双语选择（新增，仅此一段） ====================
# 选中文：下面继续原样运行原代码；选英文：把显示出来的中文换成英文
try:
    from lang import choose_language, install_english
    if choose_language() == 'en':
        install_english()
except ImportError:                   # 没有 lang.py 时按原样（中文）运行
    pass
# ==================== 双语选择结束 ====================

import simplex_core as core           # 同目录的核心公式模块

# ==================== 一、模块常量（菜单与公式模板文字） ====================

MENU_TEXT = '''================ 单纯形表计算器（只用 Python 标准库） ================
请选择要做的题（输入编号后按回车）：

  【按题型选方法】
   1. 标准 max 型（约束全是 ≤，右端项 ≥ 0）              → 普通单纯形法
   2. min 型（约束全是 ≤，右端项 ≥ 0）                    → 先转 max，再用普通单纯形法
   3. 含 ≥ 或 = 约束的问题                               → 大M法
   4. 含 ≥ 或 = 约束的问题                               → 两阶段法
   5. 右端项有负数、目标系数全 ≤ 0 的 ≤ 型问题            → 对偶单纯形法
   6. 目标函数含参数 λ（约束全是 ≤，右端项 ≥ 0）          → 参数 λ 单纯形法（含分类讨论）

  【其它功能】
   7. 手动输入一个完整问题（逐项输入，程序自动判断题型并选方法）
   8. 载入内置例题（再输入例题编号 1~12）
   9. 显示输入格式模板与说明
   0. 退出程序'''

TEMPLATE_TEXT = {
    'objective': '''【目标函数模板】max z = c1x1 + c2x2 + ... + cnxn
  请输入 n 个系数，用空格分开，可写分数（例：2 3   或   3/2 -1 2）
  max 型就按原样输入；min 型也按原样输入，程序自己转''',
    'constraints': '''【约束模板】a1x1 + a2x2 + ... + anxn  ( <= | >= | = )  b
  例：1 2 <= 8        4 0 <= 16        0 4 <= 12
  符号可以写 <= >= = ，也可以写中文的 ≤ ≥ ＝，程序会自动识别''',
    'lambda_obj_coeffs': '''【含 λ 目标系数模板】cj(λ) = p + qλ（p 是常数部分，q 是 λ 的系数）
  例：输入 "1 1" 表示 c1 = 1 + λ；输入 "-2 3" 表示 c2 = -2 + 3λ；输入 "4 0" 表示 c3 = 4''',
    'var_count': '【变量个数】请输入 1~8 之间的整数',
    'lambda_lower_bound': '''【λ 讨论域模板】程序在 [λ下界, +∞) 上分类讨论 λ（默认 λ ≥ 0，直接回车表示下界取 0）''',
}

MENU_METHOD_TABLE = {1: '普通单纯形法', 2: '普通单纯形法', 3: '大M法',
         4: '两阶段法', 5: '对偶单纯形法', 6: '参数λ单纯形法', 7: '自动'}


# ==================== 二、输入工具 ====================

def read_line(prompt):
    """读一行文字（input() 的文字包装，方便测试时用替身替换）。"""
    return input(prompt)


def split_fragments(text):
    """把一行输入切成片段（空格、制表符、英文逗号、中文逗号、顿号都当分隔符）。"""
    return [term for term in re.split('[,\\s、，]+', str(text).strip()) if term != '']


def fragment_to_number(fragment):
    """把一个片段转成精确有理数（支持 3、-2、1.5、3/2）。"""
    fragment = str(fragment).strip()
    if fragment == '':
        raise ValueError('没有输入内容')
    try:
        value = Fraction(fragment)                    
    except ZeroDivisionError:
        raise ValueError('分母不能为 0')
    except (ValueError, TypeError):
        raise ValueError('"%s" 不是合法的数字（可以写 3、-2、1.5、3/2）' % fragment)
    return value


def ask_repeatedly(read_func, *args):
    """反复调用读函数直到拿到合法值（非法输入只提示、不崩溃、不退出）。"""
    while True:
        try:
            return read_func(*args)
        except ValueError as error:
            print('输入有误：' + str(error) + '，请按模板重新输入。')
        except (ZeroDivisionError, KeyError, IndexError, TypeError) as error:
            print('输入有误：' + str(error) + '，请重新输入。')


def read_integer(prompt, min_value, max_value):
    """读一个整数（变量个数、约束条数、例题编号等都用它）。"""
    text = read_line(prompt).strip()
    if text == '':
        raise ValueError('没有输入内容')
    try:
        value = int(text)
    except ValueError:
        raise ValueError('"%s" 不是合法的整数' % text)
    if value < min_value or value > max_value:
        raise ValueError('输入必须是 %d~%d 之间的整数，你输入的是 %s' % (min_value, max_value, text))
    return value


def read_number(prompt):
    """读一个实数（支持分数 3/2、小数 2.5、负数 -4）。"""
    text = read_line(prompt).strip()
    if text == '':
        raise ValueError('没有输入内容')
    fragment = split_fragments(text)
    if len(fragment) != 1:
        raise ValueError('只需要 1 个数，实际输入 %d 个' % len(fragment))
    return fragment_to_number(fragment[0])


def read_sign(prompt):
    """读约束符号（<= / >= / =，也认中文的 ≤ ≥ ＝）。"""
    text = read_line(prompt).strip()
    if text == '':
        raise ValueError('没有输入内容')
    return core.normalize_sign(text)              # 识别规则与核心层共用，避免两处写法不一致


def read_original_type():
    """读目标函数类型（求最大还是最小）。"""
    text = read_line('目标函数是求最大还是最小？请输入 max 或 min（也可以写 最大 / 最小）：').strip()
    if text == '':
        raise ValueError('没有输入内容')
    no_space = text.replace(' ', '')
    normalized_text = no_space.replace('最大', 'max').replace('最小', 'min')
    if normalized_text.lower() == 'max':
        return 'max'
    if normalized_text.lower() == 'min':
        return 'min'
    raise ValueError('目标类型只能写 max 或 min')


def read_var_count():
    """读变量个数（1~8）。"""
    print_input_template('var_count')
    text = read_line('请输入变量个数（1~8）：').strip()
    if text == '':
        raise ValueError('没有输入内容')
    try:
        value = int(text)
    except ValueError:
        raise ValueError('"%s" 不是合法的整数，变量个数必须是 1~8 的整数' % text)
    if value < 1 or value > 8:
        raise ValueError('变量个数必须是 1~8 的整数')
    return value


def read_coefficients(prompt, count):
    """读一行里的若干系数（目标函数系数等）。"""
    text = read_line(prompt).strip()
    fragment = split_fragments(text)
    if len(fragment) == 0:
        raise ValueError('没有输入内容')
    number_list = [fragment_to_number(term) for term in fragment]
    if len(fragment) != count:
        raise ValueError('需要 %d 个数，实际输入 %d 个' % (count, len(fragment)))
    return number_list


def read_lambda_coefficients(count):
    """读参数 λ 的目标系数，每个 cj(λ) = p + qλ 要输入 2 个数。"""
    result = []
    for j in range(count):
        print('第 %d 个目标系数 c%d(λ) = p + qλ，请输入 2 个数（p 是常数部分，q 是 λ 的系数）：'
              % (j + 1, j + 1))
        text = read_line('  c%d(λ) = ' % (j + 1)).strip()
        fragment = split_fragments(text)
        if len(fragment) == 0:
            raise ValueError('没有输入内容')
        if len(fragment) != 2:
            raise ValueError('需要 2 个数，实际输入 %d 个' % len(fragment))
        result.append((fragment_to_number(fragment[0]), fragment_to_number(fragment[1])))
    return result


def read_one_constraint(var_count, constraint_number):
    """读一条约束：n 个系数 + 符号 + 右端项，写在一行里。"""
    needed_count = var_count + 2
    text = read_line('第 %d 条约束（写 %d 个系数 + 符号 + 右端项，共 %d 项）：'
                % (constraint_number, var_count, needed_count)).strip()
    fragment = split_fragments(text)
    if len(fragment) == 0:
        raise ValueError('没有输入内容')
    if len(fragment) != needed_count:
        raise ValueError('需要 %d 个数，实际输入 %d 个' % (needed_count, len(fragment)))
    coefficient = [fragment_to_number(term) for term in fragment[:var_count]]
    symbol = core.normalize_sign(fragment[var_count])
    rhs = fragment_to_number(fragment[var_count + 1])
    return (coefficient, symbol, rhs)


def read_constraints(var_count):
    """读全部约束（先读条数，再一条一条读；每条都能单独重问）。"""
    constraint_count = ask_repeatedly(read_integer, '请输入约束条数（1~8）：', 1, 8)
    constraint_matrix = []
    signs = []
    rhs_list = []
    for i in range(constraint_count):
        coefficient, symbol, rhs = ask_repeatedly(read_one_constraint, var_count, i + 1)
        constraint_matrix.append(coefficient)
        signs.append(symbol)
        rhs_list.append(rhs)
        print('  第 %d 条已读入：%s %s %s'
              % (i + 1, core.linear_expression_text(coefficient, ['x%d' % (j + 1) for j in range(var_count)]),
                 symbol, core.number_to_text(rhs)))
    return (constraint_matrix, signs, rhs_list)


def read_menu_choice():
    """读菜单编号（0~9，也可以输入 q / quit 退出）。"""
    text = read_line('请输入编号（0~9，输入 q 或 quit 退出）：').strip()
    if text == '':
        raise ValueError('没有输入内容')
    if text.lower() in ('q', 'quit', 'exit', '退出'):
        return '退出'
    try:
        number = int(text)
    except ValueError:
        raise ValueError('菜单编号只能是 0~9 的整数（输入 q 或 quit 退出）')
    if number < 0 or number > 9:
        raise ValueError('菜单编号只能是 0~9 的整数（输入 q 或 quit 退出）')
    return number


def read_has_lambda():
    """问用户目标函数里有没有参数 λ。"""
    text = read_line('目标函数里含参数 λ 吗？（输入 y 表示含 λ，直接回车表示不含）：').strip()
    if text == '':
        return False
    if text.lower() in ('y', 'yes', '是', '1', '有'):
        return True
    if text.lower() in ('n', 'no', '否', '0', '没有'):
        return False
    raise ValueError('只能输入 y 或 n（y 表示含参数 λ，n 表示不含）')


def read_lambda_lower_bound():
    """读参数 λ 的讨论下界（只有这一处允许空输入，空输入表示 0）。"""
    print_input_template('lambda_lower_bound')
    text = read_line('请输入 λ 的讨论下界（直接回车表示 0）：').strip()
    if text == '':
        return Fraction(0)
    fragment = split_fragments(text)
    if len(fragment) != 1:
        raise ValueError('只需要 1 个数，实际输入 %d 个' % len(fragment))
    return fragment_to_number(fragment[0])


# ==================== 三、菜单与模板打印 ====================

def print_menu():
    """打印编号菜单（最后一行提示也认 q / quit）。"""
    print(MENU_TEXT)


def print_input_template(item_name):
    """打印输入格式模板（每次请求输入前都打印）。"""
    if item_name == '全部':
        for name in ('objective', 'constraints', 'lambda_obj_coeffs', 'var_count', 'lambda_lower_bound'):
            print_input_template(name)
            print('')
        return
    message = TEMPLATE_TEXT.get(item_name)
    if message is None:
        print('（没有这个模板：%s）' % item_name)
        return
    print(message)


# ==================== 四、选题（菜单 / 手动 / 例题） ====================

def read_problem_data(method, original_type=None, has_lambda=False):
    """按模板逐项读取一个完整问题，返回可以交给 core.solve 的题目字典。"""
    print_input_template('objective')
    if original_type is None:
        kind = ask_repeatedly(read_original_type)
    else:
        kind = original_type
        print('本题按【%s 型】处理（目标函数按原样输入，程序自己转换）。' % kind)
    var_count = ask_repeatedly(read_var_count)
    var_names = ['x%d' % (j + 1) for j in range(var_count)]
    if has_lambda:
        print_input_template('lambda_obj_coeffs')
        obj_coeffs = ask_repeatedly(read_lambda_coefficients, var_count)
        print('目标函数已读入：%s z(λ) = %s'
              % (kind, core.linear_expression_text(obj_coeffs, var_names, 'λ')))
    else:
        obj_coeffs = ask_repeatedly(read_coefficients, '请输入 %d 个目标函数系数 c1~c%d（用空格分开）：' % (var_count, var_count), var_count)
        print('目标函数已读入：%s z = %s' % (kind, core.linear_expression_text(obj_coeffs, var_names)))
    print_input_template('constraints')
    constraint_matrix, signs, rhs_list = read_constraints(var_count)
    lambda_bound_value = read_lambda_lower_bound() if has_lambda else Fraction(0)
    return {'mode': '菜单' if method != '自动' else '手动', 'method': method, 'original_type': kind,
            'obj_coeffs': obj_coeffs, 'constraint_matrix': constraint_matrix, 'signs': signs,
            'rhs_list': rhs_list, 'lambda_lower_bound': lambda_bound_value}


def load_example(number):
    """按编号取内置例题，整理成求解需要的 6 个参数。"""
    example = core.get_example(number)
    return (example['original_type'], example['obj_coeffs'], example['constraint_matrix'],
            example['signs'], example['rhs_list'], example['method'])


def choose_problem():
    """打印菜单并读入用户选择，返回一道题的完整数据。"""
    while True:
        print_menu()
        selection = ask_repeatedly(read_menu_choice)
        if selection == '退出' or selection == 0:
            return {'mode': '退出'}
        if selection == 9:
            print_input_template('全部')
            continue
        if selection == 8:
            number = ask_repeatedly(read_integer, '请输入内置例题编号（1~12）：', 1, 12)
            example = core.get_example(number)
            original_type, obj_coeffs, constraint_matrix, signs, rhs_list, method = load_example(number)
            print('已载入例题 %d：%s（期望：%s）' % (number, example['name'], example['expected']))
            return {'mode': '例题', 'method': method, 'original_type': original_type, 'obj_coeffs': obj_coeffs,
                    'constraint_matrix': constraint_matrix, 'signs': signs, 'rhs_list': rhs_list,
                    'lambda_lower_bound': example['lambda_lower_bound'] if example['lambda_lower_bound'] is not None else Fraction(0)}
        if selection == 7:
            has_lambda = ask_repeatedly(read_has_lambda)
            return read_problem_data('自动', None, has_lambda)
        if selection in (1, 2, 3, 4, 5, 6):
            method = MENU_METHOD_TABLE[selection]
            if selection == 1:
                return read_problem_data(method, 'max')
            if selection == 2:
                return read_problem_data(method, 'min')
            if selection == 6:
                return read_problem_data(method, None, True)
            return read_problem_data(method, None)


# ==================== 五、打印题目、计算过程与结论 ====================

def print_problem_type(model, result):
    """计算前先说清楚题型与所用方法。"""
    normalized_signs = [core.normalize_sign(sentence) for sentence in model['signs']]
    categories = []
    for name, sign_code in (('≤ 型', '<='), ('≥ 型', '>='), ('= 型', '=')):
        if sign_code in normalized_signs:
            categories.append('%s %d 条' % (name, normalized_signs.count(sign_code)))
    row = []
    row.append('【题型判定】原始目标是 %s 型；约束类型：%s；'
            % (model['original_type'], '、'.join(categories) if categories else '没有约束'))
    if model['artificial_indices']:
        row.append('初始基：不是纯松弛变量（有 %d 个人工变量 %s，需要先凑出单位基），'
                '所以用【%s】。'
                % (len(model['artificial_indices']),
                   '、'.join(model['var_names'][k] for k in model['artificial_indices']), result['method']))
    elif model['surplus_indices']:
        row.append('初始基：不是纯松弛变量（有剩余变量），需要用【%s】处理。' % result['method'])
    else:
        row.append('初始基：约束全是 ≤ 型，松弛变量列就是单位列，可以直接当初始基。')
    if model['method'] == '对偶单纯形法':
        row.append('检验数：初始 σ 行全部 ≤ 0，不需要迭代入基，但 b 列有负值，'
                '所以选【对偶单纯形法】。')
    elif model['method'] == '参数λ单纯形法':
        row.append('检验数：σ 行含参数 λ（σj(λ) = p + qλ），符号随 λ 变，'
                '所以要【按 λ 区间分类讨论】。')
    elif any(core.numeric_part(value) > 0 for value in model['obj_coeffs']):
        row.append('检验数：初始 σ 行有正数（还有改进空间），用【%s】迭代到全部 σj ≤ 0。' % result['method'])
    else:
        row.append('检验数：初始 σ 行已经全部 ≤ 0（初始表就是最优表），用【%s】直接判定。' % result['method'])
    for sentence in row:
        print(sentence)
    print('理由：' + result.get('method_reason', '由程序自动判断题型后选择方法'))


def print_process(result, model):
    """打印【计算过程】部分（逐张表：标题 → 表体 → 【判断】→【本表计算公式】）。"""
    print('【公式提示】每一轮都用这 4 条公式：入基列取 σ 最大者（大M法在 M 充分大意义下）；'
          '离基行取最小比值 θ = bi ÷ a(i,入基列) 所对应的行；'
          '新主元行 = 旧主元行 ÷ 主元；其他行 = 旧行 - 该行主元列系数 × 新主元行；'
          '新 σj = cj - (各 cB×aij 之和)。')
    print('')
    if result['method'] == '参数λ单纯形法':
        for row in core.render_lambda_section(result, model):
            print(row)
        return
    phase_one = result.get('phase_one')
    if phase_one:
        print('========== 第一阶段（最小化人工变量之和 w） ==========')
        print('第一阶段判断：' + phase_one['judgement'])
        print('')
        for table in phase_one['iteration_tables']:
            print(core.render_table(table))
            print('')
        if not phase_one.get('entered_phase_two'):
            print('（第一阶段已经判定原问题无可行解，不再进入第二阶段）')
            print('')
            if result['iteration_tables'] is phase_one['iteration_tables']:
                return                    
        else:
            print('========== 第二阶段（换回原目标函数继续迭代） ==========')
            print('')
    for table in result['iteration_tables']:
        print(core.render_table(table))
        print('')


def variable_constraint_index(model, column_index):
    """找出某个松弛/剩余/人工变量是第几个约束加上的。"""
    for i, row in enumerate(model['constraint_matrix']):
        if row[column_index] != 0:
            return i + 1
    return 0


def print_variable_notes(model, result):
    """打印原变量 / 松弛变量 / 剩余变量 / 人工变量的含义与取值。"""
    all_values = result.get('all_variable_solution') or {}
    original_var_names = [model['var_names'][k] for k in range(model['original_var_count'])]
    print('【变量说明】')
    print('  原变量（决策变量）：%s —— 就是题目要求解的 x1..x%d。' % ('、'.join(original_var_names), model['original_var_count']))
    three_categories = [('slack_indices', '松弛变量（≤ 约束左边"没用完"的余量，大于 0 表示该约束没有卡死）'),
           ('surplus_indices', '剩余变量（≥ 约束左边"超出右端项"的部分，等于 0 表示该约束卡死）'),
           ('artificial_indices', '人工变量（为了让初始表有单位基而人为加上的，最优时必须为 0；大于 0 就说明原问题无可行解）')]
    for key_name, explanation in three_categories:
        index_list = model[key_name]
        if not index_list:
            continue
        fragment = []
        for j in index_list:
            value = all_values.get(model['var_names'][j], Fraction(0))
            fragment.append('%s = %s（第 %d 个约束）' % (model['var_names'][j], core.number_to_text(value), variable_constraint_index(model, j)))
        print('  ' + explanation + '：' + '，'.join(fragment) + '。')
    if not model['slack_indices'] and not model['surplus_indices'] and not model['artificial_indices']:
        print('  本题没有加任何松弛/剩余/人工变量。')


def print_result(model, result):
    """按固定顺序打印一次求解的全部内容。"""
    print('=' * 72)
    print('【题目】' + core.original_problem_text(model))
    print('')
    print('【题型与方法】本题属于【%s】，采用【%s】。' % (model['problem_type'], result['method']))
    print_problem_type(model, result)
    print('')
    print('【标准化说明】')
    for i, sentence in enumerate(model['conversion_notes'], 1):
        print('%d) %s' % (i, sentence))
    print('标准化后：' + core.standardized_objective_text(model))
    print('')
    print('【计算过程】')
    print_process(result, model)
    print('【结果讨论与结论】')
    print(result['conclusion'])
    print('')
    print_variable_notes(model, result)
    print('=' * 72)


# ==================== 六、主程序 ====================

def main_program():
    """交互主程序：print_menu → 按编号取题 → solve → 打印过程与结论 → 回到菜单，直到用户选 0 / q。"""
    print('欢迎使用单纯形表计算器：支持普通单纯形法、大M法、两阶段法、对偶单纯形法、参数 λ 法。')
    while True:
        try:
            problem = choose_problem()
            if problem['mode'] == '退出':
                print('已退出，感谢使用本计算器。')
                return
            result = core.solve(problem['original_type'], problem['obj_coeffs'], problem['constraint_matrix'],
                          problem['signs'], problem['rhs_list'],
                          method=problem['method'], lambda_lower_bound=problem.get('lambda_lower_bound') or Fraction(0))
            print_result(result['model'], result)
        except ValueError as error:
            print('无法计算：' + str(error))
            print('已回到主菜单，请换一种方法或修改数据。')
            print('')
        except (ZeroDivisionError, IndexError, KeyError, TypeError) as error:
            print('程序遇到意外情况：' + str(error) + '，已回到主菜单。')
            print('')
        except EOFError:
            print('输入已经结束，程序自动退出。')
            return


if __name__ == '__main__':
    main_program()
