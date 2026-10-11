# -*- coding: utf-8 -*-
"""
simplex_calc 双语支持：只在"选英文"时才生效，选中文时原程序一行都不用改。

作用：
  1) choose_language()：启动时问一次语言（先中文后英文）；
  2) install_english()：把内置的 print / input 包一层，
     打印或显示提示之前先把中文片段换成英文（翻译表在 lang_en.py）。

说明：只替换"显示出来的文字"。程序内部当作数据用的中文
      （例如 result['method'] 的值、菜单返回的 '退出'）一律不动，
      所以判断逻辑、计算结果与原来完全一致。
"""

import builtins

from lang_en import TRANSLATIONS          # 中文片段 -> 英文

# 片段按长度从长到短排序：先替换长的，避免短片段先命中把长片段切碎
_PIECES = sorted(TRANSLATIONS, key=len, reverse=True)


def translate(text):
    """把一段文字里的中文片段换成英文；不是字符串就原样返回。"""
    if not isinstance(text, str) or text == '':
        return text
    for piece in _PIECES:
        if piece in text:
            text = text.replace(piece, TRANSLATIONS[piece])
    return text


def choose_language():
    """启动时问一次语言：中文在前、英文在后；返回 'zh' 或 'en'。"""
    question = ('请选择语言 / Please choose a language:\n'
                '  1. 中文 (Chinese)\n'
                '  2. English\n'
                '请输入 1 或 2 / Enter 1 or 2: ')
    while True:
        try:
            answer = input(question).strip().lower()
        except EOFError:                  # 没有输入（例如管道结束）时按中文处理
            return 'zh'
        if answer in ('1', 'zh', '中文', 'chinese'):
            return 'zh'
        if answer in ('2', 'en', 'english', 'eng'):
            return 'en'
        print('输入有误，请输入 1 或 2。 / Invalid input, please enter 1 or 2.')


def install_english():
    """把 print 与 input 换成"先翻译再输出"的版本（只在英文模式下调用）。"""
    original_print = builtins.print
    original_input = builtins.input

    def print_english(*args, **kwargs):
        """打印前把每个字符串参数里的中文换成英文。"""
        original_print(*[translate(item) for item in args], **kwargs)

    def input_english(prompt=''):
        """显示提示文字前把中文换成英文。"""
        return original_input(translate(prompt))

    builtins.print = print_english
    builtins.input = input_english
