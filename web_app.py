# -*- coding: utf-8 -*-
"""
web_app.py —— 单纯形法计算器【网页版】的后台服务器

这个文件只做三件事：
  1. 把 web 文件夹里的 index.html / style.css / app.js 发给浏览器；
  2. 接收网页发来的题目和做题方法（POST /api/solve）——题目可以是"表单填写"的，
     也可以是"自己写题目"的一段文字（交给 text_parser.py 自动识别）；
     然后调用同目录的 simplex_core.solve 计算；
  3. 把计算结果（每张单纯形表、判断、公式、结论、参数 λ 的分类讨论）整理成 JSON 发回网页显示。

只用 Python 标准库（http.server / json / fractions 等），
不需要安装任何第三方库，任何有 Python 3.7+ 的电脑都能直接运行。

运行方法（在命令行进入本文件夹后执行）：
    python web_app.py
然后浏览器会自动打开 http://127.0.0.1:8000/ ，按 Ctrl+C 可以关闭服务器。

可选参数：
    python web_app.py 8080           换一个端口号（默认 8000，被占用会自动往后找）
    python web_app.py --no-browser   不自动打开浏览器
"""

import json
import os
import sys
import traceback
import webbrowser
from fractions import Fraction
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

try:                                  # 让控制台输出中文不乱码（和 main.py 一样的小技巧）
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import simplex_core as core           # 同目录的核心算法：与命令行版共用，计算结果完全一致
from lang import translate            # 同目录的中→英翻译表：网页切到英文时用它翻译输出文字
# 同目录的"题目文字识别"模块，以及全角转换 / 数字解析 / 语言选择等共用小工具
from text_parser import normalize_text, parse_coefficient, parse_number, parse_problem_text, pick

# 网页静态文件（index.html / style.css / app.js）所在文件夹
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')


# ==================== 一、显示文字的小工具 ====================

def display(text, lang):
    """按当前语言处理要显示的文字：中文原样返回；英文调用翻译表逐段替换（和命令行版英文模式同一张表）。"""
    if lang == 'en':
        return translate(text)
    return text


# 求解方法名：英文模式下的标准写法（内部数据保持中文，这里只做"显示"翻译）
METHOD_EN = {
    '普通单纯形法': 'Primal Simplex Method',
    '大M法': 'Big-M Method',
    '两阶段法': 'Two-Phase Method',
    '对偶单纯形法': 'Dual Simplex Method',
    '参数λ单纯形法': 'Parametric λ Simplex Method',
    '参数λ右端项单纯形法': 'Parametric RHS Simplex Method',
}

# 题型名：英文模式下的标准写法（键就是 core.classify_problem_type 会返回的固定几种）
PROBLEM_TYPE_EN = {
    '标准 max 型（约束全是 ≤、右端项非负）': 'Standard max type (all constraints ≤, right-hand sides ≥ 0)',
    'min 型（先转成 max 型再求最大）': 'min type (converted to a max problem first)',
    '≥ 约束问题（大M法）': 'problem with ≥ constraints (Big-M method)',
    '= 约束问题（大M法）': 'problem with = constraints (Big-M method)',
    '含 ≥ 与 = 约束的问题（大M法）': 'problem with ≥ and = constraints (Big-M method)',
    '≥ 约束问题（两阶段法）': 'problem with ≥ constraints (Two-Phase method)',
    '= 约束问题（两阶段法）': 'problem with = constraints (Two-Phase method)',
    '含 = 与 ≥ 约束的问题（两阶段法）': 'problem with = and ≥ constraints (Two-Phase method)',
    '对偶单纯形法（约束可化为全 ≤、b 列有负值、初始检验数全 ≤ 0）':
        'dual simplex type (constraints reducible to all ≤, some b < 0, initial reduced costs all ≤ 0)',
    '参数 λ 的单纯形法（分类讨论）': 'parametric λ simplex type (case analysis)',
    '参数 λ 的右端项分析（分类讨论）': 'parametric right-hand side type (case analysis)',
    '参数 λ 的右端项分析': 'parametric right-hand side analysis',
}

# 求解状态：code 给前端判断用（决定答案框的颜色和文字），zh/en 是显示文字
STATUS_INFO = {
    '最优': {'code': 'optimal', 'zh': '已求得最优解', 'en': 'Optimal solution found'},
    '无界': {'code': 'unbounded', 'zh': '问题无界（没有有限最优值）', 'en': 'Unbounded (no finite optimum)'},
    '无可行': {'code': 'infeasible', 'zh': '问题无可行解（约束互相矛盾）', 'en': 'Infeasible (constraints contradict)'},
    '达到最大迭代次数': {'code': 'limit', 'zh': '达到最大迭代次数，没有算完', 'en': 'Iteration limit reached'},
}


# ==================== 二、把网页发来的题目"翻译"成 core.solve 的参数 ====================
# （全角转半角、数字解析等小工具都放在 text_parser.py 里共用，这里只写表单数据的检查）


def parse_problem(data, lang):
    """检查网页"表单填写"发来的题目数据，转换成 core.solve 需要的参数。"""
    original_type = data.get('type', 'max')
    if original_type not in ('max', 'min'):
        raise ValueError(pick(lang, '目标函数类型只能是 max 或 min。', 'The objective type must be max or min.'))

    raw_obj = data.get('obj') or []
    if not 1 <= len(raw_obj) <= 8:
        raise ValueError(pick(lang, '变量个数要在 1~8 之间。', 'The number of variables must be between 1 and 8.'))
    var_count = len(raw_obj)

    # 每个目标系数可以填普通数字（3、1.5、3/2），也可以填含参数 λ 的式子（1+λ、2-λ、1+2λ、2λ）
    pairs = [
        parse_coefficient(value, '目标函数 x%d 的系数' % (j + 1),
                          'objective coefficient of x%d' % (j + 1), lang)
        for j, value in enumerate(raw_obj)
    ]
    # 只要有一个系数带 λ，就整体走"参数 λ"模式（每个系数都表示成 p + qλ）
    has_lambda = any(q != 0 for _p, q in pairs)
    obj_coeffs = [(p, q) for p, q in pairs] if has_lambda else [p for p, _q in pairs]
    lambda_lower_bound = Fraction(0)       # 表单填写默认讨论域 λ ≥ 0（文字输入时可以写 λ >= 1）

    raw_constraints = data.get('constraints') or []
    if not 1 <= len(raw_constraints) <= 8:
        raise ValueError(pick(lang, '约束条数要在 1~8 之间。', 'The number of constraints must be between 1 and 8.'))
    constraint_matrix = []
    signs = []
    rhs_list = []
    for i, item in enumerate(raw_constraints):
        row = item.get('coeffs') or []
        if len(row) != var_count:
            raise ValueError(pick(lang, '第 %d 条约束的系数个数不对。' % (i + 1),
                                  'Constraint %d has a wrong number of coefficients.' % (i + 1)))
        constraint_matrix.append([
            parse_number(value, '第 %d 条约束 x%d 的系数' % (i + 1, j + 1),
                         'coefficient of x%d in constraint %d' % (j + 1, i + 1), lang)
            for j, value in enumerate(row)
        ])
        try:
            signs.append(core.normalize_sign(item.get('sign', '<=')))
        except Exception:
            raise ValueError(pick(lang, '第 %d 条约束的符号无法识别。' % (i + 1),
                                  'The sign of constraint %d is not recognized.' % (i + 1)))
        # 右端项可以含参数 λ：普通数字（3、-2、1.5、3/2）存成 Fraction，
        # 含 λ 的式子（8+λ、2-λ、λ、3+2λ）存成 (p, q) 元组（= p + qλ），核心算法会自动识别
        rhs_pair = parse_coefficient(
            normalize_text(item.get('rhs')).replace(' ', '').replace('*', '').replace('×', ''),
            '第 %d 条约束的右端项' % (i + 1), 'right-hand side of constraint %d' % (i + 1), lang)
        rhs_list.append(rhs_pair[0] if rhs_pair[1] == 0 else (rhs_pair[0], rhs_pair[1]))

    return {
        'original_type': original_type, 'obj_coeffs': obj_coeffs,
        'constraint_matrix': constraint_matrix, 'signs': signs, 'rhs_list': rhs_list,
        'lambda_lower_bound': lambda_lower_bound, 'has_lambda': has_lambda,
    }


def normalize_method(method, lang, has_lambda):
    """检查做题方法参数：“自动”表示按题型判断；含参数 λ 时统一交给核心自动选择。"""
    method = method or '自动'
    if method not in ('自动', '普通单纯形法', '大M法', '两阶段法', '对偶单纯形法'):
        raise ValueError(pick(lang, '未知的做题方法：%s' % method, 'Unknown method: %s' % method))
    if has_lambda:
        return '自动'          # 含 λ 的题必须走"参数λ单纯形法"，由核心自动挑
    return method


# ==================== 三、把计算结果整理成网页好显示的 JSON ====================

def table_to_json(table, lang, highlight):
    """把一张单纯形表转成 JSON 结构（每个数字先转成文字，网页直接放到格子里）。

    highlight 为 True 时顺便算出：
      - enter_col：入基列（网页把它涂成黄色）；
      - leave_row：离基行（结合入基列可以标出主元格子）。
    这两个只是为了"好看好懂"，不参与计算。
    """
    symbol = table.get('parametric_symbol')
    var_names = table['var_names']
    enter_col = None
    leave_row = None
    if symbol == 'λ':
        highlight = False             # λ 题的表不标注入基列/主元（判断写在每个区间的结论里）
    if highlight:
        enter_col = table.get('enter_col')
        if table.get('is_dual'):
            leave_row, _ = core.dual_select_leaving_row(table)
        elif table.get('ratio_list'):
            leave_row, _ = core.ratio_test(table['ratio_list'], table)
    return {
        'title': display(table['title'], lang),
        'c': [core.value_to_text(value, symbol) for value in table['c']],
        'var_names': list(var_names),
        'basis': list(table['basis']),
        'basis_names': [var_names[k] for k in table['basis']],
        'basis_coeffs': [core.value_to_text(value, symbol) for value in table['basis_coeffs']],
        'matrix': [[core.value_to_text(value, symbol) for value in row] for row in table['constraint_matrix']],
        'rhs': [core.value_to_text(value, symbol) for value in table['rhs']],
        'sigma': [core.value_to_text(value, symbol) for value in table['sigma']],
        'objective_value': core.value_to_text(table['objective_value'], symbol),
        'judgement': display(table['judgement'], lang),
        'formulas': [display(line, lang) for line in table['formulas']],
        'enter_col': enter_col,
        'leave_row': leave_row,
        'is_dual': bool(table.get('is_dual')),
        'degenerate': bool(table.get('degenerate')),
    }


def tables_to_json(tables, lang, status):
    """把一串单纯形表转成 JSON 列表。

    只有"这张表后面还要做旋转"的才标注入基列和主元；
    最优表、无可行表不标注（它们没有下一步旋转），避免误导。
    """
    highlight_last = status in ('无界', '达到最大迭代次数')
    return [table_to_json(table, lang, highlight=(i < len(tables) - 1) or highlight_last)
            for i, table in enumerate(tables)]


def result_to_json(result, lang):
    """把 core.solve 的返回值整理成网页需要的全部数据。"""
    model = result['model']
    status = result['status']
    status_info = STATUS_INFO.get(status, STATUS_INFO['达到最大迭代次数'])
    problem_type = model['problem_type']
    if lang == 'en':
        problem_type = PROBLEM_TYPE_EN.get(problem_type, display(problem_type, lang))

    data = {
        'problem_text': display(core.original_problem_text(model), lang),
        'problem_type': problem_type,
        'method': METHOD_EN[model['method']] if lang == 'en' else model['method'],
        'method_reason': display(result.get('method_reason', ''), lang),
        'conversion_notes': [display(note, lang) for note in result['conversion_notes']],
        'standardized_objective': display(core.standardized_objective_text(model), lang),
        'status_code': status_info['code'],
        'status_text': status_info[lang],
        'phase1': None,
        'tables': tables_to_json(result['iteration_tables'], lang, status),
        'lambda': None,
        'conclusion': display(result['conclusion'], lang),
        'objective_name': core.objective_name(model),
        'answer': None,
    }

    # 两阶段法：第一阶段（w）的表单独放在 phase1 里，网页会先画第一段再画第二段
    phase_one = result.get('phase_one')
    if phase_one is not None:
        phase_status = '最优' if phase_one.get('entered_phase_two') else '无可行'
        data['phase1'] = {
            'judgement': display(phase_one['judgement'], lang),
            'entered_phase_two': bool(phase_one.get('entered_phase_two')),
            'tables': tables_to_json(phase_one['iteration_tables'], lang, phase_status),
        }

    # 参数 λ 题：表分散在每个区间里，答案也要按区间分段给出
    intervals = result.get('interval_results')
    if intervals is not None:
        data['tables'] = []               # λ 题的表都在各区间里画，避免重复
        interval_items = []
        for interval in intervals:
            interval_items.append({
                'interval_text': interval['interval_text'],
                'representative': core.number_to_text(interval['representative_point']),
                'optimal_ok': interval['status'] == '最优',
                'judgement': display(interval['judgement'], lang),
                'tables': tables_to_json(interval['iteration_tables'], lang, interval['status']),
                'basis_text': core.format_basis_names(interval['optimal_basis'], model) if interval.get('optimal_basis') else None,
                'solution_text': core.interval_solution_text(interval) if interval.get('optimal_solution') else None,
                'value_text': interval.get('optimal_value_text'),
                'endpoint_notes': [display(core.endpoint_conclusion_text(endpoint, model), lang)
                                   for endpoint in (interval.get('endpoint_conclusions') or [])],
            })
        data['lambda'] = {
            'critical_values': display(core.critical_value_text(result), lang),
            'intervals': interval_items,
        }
        piecewise = []
        for item in interval_items:
            piecewise.append({
                'interval_text': item['interval_text'],
                'optimal': item['optimal_ok'],
                'solution_text': item['solution_text'],
                'value_text': item['value_text'],
                'note': pick(lang, '该区间无界（z → +∞），没有有限最优值',
                             'unbounded on this interval (z → +∞), no finite optimum'),
            })
        data['answer'] = {'piecewise': piecewise}
        return data

    # 有最优解时：整理最显眼的"最终答案"（x1 = ?、x2 = ?、z = ?；多重最优解连备选解一起给出）
    if status == '最优' and result.get('optimal_solution') is not None:
        solution = [
            {'name': model['var_names'][k],
             'value': core.number_to_text(result['optimal_solution'].get(model['var_names'][k], Fraction(0)))}
            for k in range(model['original_var_count'])
        ]
        answer = {
            'solution': solution,
            'value_text': core.number_to_text(result['optimal_value']),
            'multiple': bool(result['has_multiple_optima']),
            'alternatives': [],
        }
        for item in result.get('alternative_optima') or []:
            values = item['solution']
            answer['alternatives'].append({
                'solution': [
                    {'name': model['var_names'][k],
                     'value': core.number_to_text(values.get(model['var_names'][k], Fraction(0)))}
                    for k in range(model['original_var_count'])
                ],
                'value_text': core.number_to_text(item['objective_value']),
                'note': display(item['note'], lang),
            })
        data['answer'] = answer
    return data


# ==================== 四、网页服务器 ====================

class SimplexWebHandler(BaseHTTPRequestHandler):
    """处理浏览器请求：GET 发静态文件，POST /api/solve 做计算。"""

    # 允许直接访问的静态文件（文件名写死，避免别人拼路径乱读电脑里的其它文件）
    STATIC_FILES = {
        '/index.html': ('index.html', 'text/html; charset=utf-8'),
        '/style.css': ('style.css', 'text/css; charset=utf-8'),
        '/app.js': ('app.js', 'application/javascript; charset=utf-8'),
    }

    def do_GET(self):
        """浏览器打开页面时的入口：'/' 返回 index.html，其它按文件名白名单返回。"""
        path = urlparse(self.path).path
        if path == '/':
            path = '/index.html'
        if path not in self.STATIC_FILES:
            self.send_error(404, 'Page not found')
            return
        file_name, content_type = self.STATIC_FILES[path]
        try:
            with open(os.path.join(WEB_DIR, file_name), 'rb') as file:
                body = file.read()
        except OSError:
            self.send_error(404, 'File not found')
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')     # 每次都用最新页面，避免浏览器缓存住旧的界面/代码
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        """网页点"求解"时调用：收题目 -> 调核心算法 -> 回结果或错误。"""
        if urlparse(self.path).path != '/api/solve':
            self.send_error(404, 'API not found')
            return
        try:
            length = int(self.headers.get('Content-Length') or 0)
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            self.send_json({'ok': False, 'error': '请求格式不对 / Bad request'}, 400)
            return

        lang = 'en' if payload.get('lang') == 'en' else 'zh'
        try:
            if payload.get('mode') == 'text':
                # 文字输入：交给 text_parser 识别，例如 "max z = 2x1 + 3x2; x1 + 2x2 <= 8"
                item = parse_problem_text(payload.get('text') or '', lang)
            else:
                item = parse_problem(payload, lang)
            has_lambda = item['has_lambda'] or any(core.is_expression(value) for value in item['obj_coeffs'])
            item['method'] = normalize_method(payload.get('method'), lang, has_lambda)
        except ValueError as error:       # 输入问题：把带说明的中文/英文提示回给网页
            self.send_json({'ok': False, 'error': str(error)})
            return

        try:
            # 与命令行版同一个入口：method 可能是"自动"（程序判断题型选方法），也可能是用户手动指定的方法
            result = core.solve(item['original_type'], item['obj_coeffs'], item['constraint_matrix'],
                                item['signs'], item['rhs_list'], method=item['method'],
                                lambda_lower_bound=item['lambda_lower_bound'])
            self.send_json({'ok': True, 'data': result_to_json(result, lang)})
        except ValueError as error:       # 算法层对输入的限制（例如某行系数全 0）
            self.send_json({'ok': False, 'error': display(str(error), lang)})
        except Exception as error:        # 其它意外错误：控制台打印细节，网页给一句友好的话
            traceback.print_exc()
            self.send_json({'ok': False, 'error': pick(
                lang, '计算时出现意外错误：%s' % error, 'Unexpected error while calculating: %s' % error)})

    def send_json(self, obj, status=200):
        """把字典当 JSON 发回浏览器（ensure_ascii=False 让中文直接可读）。"""
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format_string, *args):
        """默认会往控制台刷一屏请求日志，这里保持安静，程序出错时会另外打印。"""
        pass


def main():
    """启动服务器：解析端口参数 -> 打开浏览器 -> 一直服务直到按 Ctrl+C。"""
    port = 8000
    open_browser = True
    for argument in sys.argv[1:]:
        if argument.isdigit():
            port = int(argument)
        elif argument in ('--no-browser', '-n'):
            open_browser = False

    server = None
    for try_port in range(port, port + 20):        # 端口被别的程序占用就往后换一个
        try:
            server = ThreadingHTTPServer(('127.0.0.1', try_port), SimplexWebHandler)
            port = try_port
            break
        except OSError:
            continue
    if server is None:
        print('端口 8000~8019 都被占用了，请先关掉占用端口的程序再运行。')
        return

    url = 'http://127.0.0.1:%d/' % port
    print('=' * 56)
    print(' 单纯形法计算器【网页版】已启动')
    print(' 请在浏览器里打开：' + url)
    print(' 按 Ctrl+C 可以关闭服务器')
    print('=' * 56)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n服务器已关闭，再见！')
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
