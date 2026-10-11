# 单纯形法计算器

一个给运筹学课程学习用的线性规划单纯形表计算器。把题目输进去，它会把题型判断、标准化过程、每一张单纯形表、每一步的计算公式一直到最终结论完整地展示出来，方便对照课本核对。

纯 Python 标准库实现，不用装任何第三方库，Python 3.7 以上都能跑。作者：ANM-Yukang · TimeLi。

## 快速开始

1. 装好 Python 3.7 以上；
2. 双击 `start.bat`；
3. 浏览器会自动打开 http://127.0.0.1:8000/ ，填好题目点"开始求解"就行。

想退出就关掉命令行窗口，或者在窗口里按 Ctrl+C。

`start.bat` 会自动在电脑里找 Python（依次试 `python`、`py -3`、`python3`），一个都没找到会提示你先去装。也可以在命令行带参数运行：

```
start.bat 8080          换端口（默认 8000，被占用的话自动往后换一个）
start.bat --no-browser  不自动打开浏览器
```

## 能算什么

- 普通单纯形法：标准 max 型直接算，min 型自动转成 max 再算；
- 大M法、两阶段法：处理带 ≥ 或 = 约束的题；
- 对偶单纯形法：右端项有负数的题；
- 参数 λ 单纯形法：目标系数写成 p + qλ，程序按临界值把 λ 分区间讨论，每个区间给出最优基、x(λ) 和 z(λ)；
- 最优、无界、无可行、退化、多重最优解都能判断；多重最优解会把几个顶点的解都列出来。

所有数字都用分数（Fraction）精确计算，不存在小数一路四舍五入的误差。大M法输出里的 M（比如 `1+2M`）是符号形式的精确结果，不是没算完。

变量个数和约束条数最多 8 个，再多表格会宽得没法看。

## 怎么输入题目

网页上有两种输入方式：

**表单填写**：选 max 或 min，系数一格一格填，整数、小数、分数（如 3/2）都行。目标系数里可以直接写 λ，比如 `1+λ`、`2-λ`、`1+2λ`，空档旁边的 λ 按钮点一下就插入。约束就是系数、符号（≤ / ≥ / = 下拉选）、右端项。

**文字输入**：像写作业一样把题目敲成几行，程序自动识别。

λ 系数写成 `(1+λ)x1` 或 `2λx1`；想改 λ 的讨论下界，写一行 `λ >= 1`（默认从 0 开始讨论）。`<=`、`>=`、`=` 和中文的 ≤、≥ 都可以，全角数字、乘号 * 也没问题，几条约束用分号写在一行也行。像 `x1, x2 >= 0` 这样的非负说明行会自动跳过。

做题方法默认"自动选择"，程序按题型自己挑；也可以手动指定普通单纯形法 / 大M法 / 两阶段法 / 对偶单纯形法，方便对比同一个题用不同方法做出来的表。含 λ 的题固定走参数 λ 单纯形法。

## 结果怎么看

从上往下依次是：

1. 题型判断、用的方法以及理由；
2. 标准化说明：加了哪些松弛变量、剩余变量、人工变量，目标函数怎么转换；
3. 每一轮一张单纯形表，画成带颜色的表格：基变量列浅蓝、入基列黄色、主元格红框；表下面可以展开"本表计算公式"，把从上一张表到这张表的每一步（主元选取、比值检验、每一行怎么算）都写清楚；
4. 两阶段法会先把第一阶段（w）的表单独放一段，第一阶段结束后再进入第二阶段；
5. λ 题按区间分组，先给出临界值，每个区间一套表和结论；
6. 最后绿色高亮框里是最终答案：各变量取多少、最优值多少。

无界、无可行、达到最大迭代次数这些算不出来的情况也会明确说明。

页面右上角有中英文切换（计算过程的文字会跟着切换）和深色 / 浅色主题，选择浏览器会记住。内置 10 道例题（含 2 道 λ 题），下拉框选一个自动填好，打开页面时也已经摆好一道题，点"开始求解"就能看到完整过程。

## 文件说明

- `start.bat` —— 启动入口，双击它就行
- `web_app.py` —— 网页版后台服务器
- `web/` —— 网页版前端（index.html、style.css、app.js）
- `simplex_core.py` —— 核心算法，网页版和命令行版共用
- `text_parser.py` —— 文字输入的题目识别
- `main.py` —— 命令行版（终端交互，启动时选语言，内置 12 道例题）
- `lang.py`、`lang_en.py` —— 中英文翻译表

## 注意事项

- Windows 控制台如果中文显示乱码，先执行 `chcp 65001` 再启动；
- 端口 8000~8019 都被占用的话，程序会提示先关掉占用端口的软件；
- 服务器只监听本机 127.0.0.1，题目不会发到别的地方；
- 本程序供学习使用。

---

# Simplex Method Calculator

A linear programming simplex tableau calculator for learning operations research. Enter a problem and it walks you through everything: problem-type classification, the standardization step, every simplex tableau, the formulas behind each iteration, and the final conclusion — so you can check your work against the textbook step by step.

Written in pure Python standard library, no third-party packages needed; runs on Python 3.7+. Author: 一不错男子 · TimeLi.

## Quick Start

1. Install Python 3.7 or newer;
2. Double-click `start.bat`;
3. Your browser opens http://127.0.0.1:8000/ automatically — fill in a problem and click "Solve".

To quit, close the console window or press Ctrl+C in it.

`start.bat` looks for Python on your own (`python`, then `py -3`, then `python3`) and tells you to install it if none is found. You can also pass arguments:

```
start.bat 8080          use another port (default 8000; if busy, the next free one is used)
start.bat --no-browser  do not open the browser automatically
```

## What It Can Solve

- Primal simplex method: standard max problems directly; min problems are converted to max first;
- Big-M method and two-phase method: for problems with ≥ or = constraints;
- Dual simplex method: for problems with negative right-hand sides;
- Parametric λ simplex method: write objective coefficients as p + qλ and the program splits λ into intervals at the critical values, giving the optimal basis, x(λ) and z(λ) for each interval;
- Detects optimal, unbounded, infeasible, degenerate and multiple-optima cases; for multiple optima it lists the alternative vertex solutions.

All arithmetic is exact rational arithmetic (Fraction), so there is no accumulated rounding error. The M in Big-M output (e.g. `1+2M`) is an exact symbolic result, not an unfinished calculation.

Up to 8 variables and 8 constraints — beyond that the tableaux get too wide to read.

## Entering Problems

Two input modes on the page:

**Form fields**: pick max or min and fill the coefficient blanks one by one — integers, decimals and fractions (like 3/2) all work. Objective coefficients may contain λ, e.g. `1+λ`, `2-λ`, `1+2λ`; the λ button next to the blanks inserts it for you. Each constraint is coefficients, a sign (≤ / ≥ / = from a dropdown) and a right-hand side.

**Type it out**: write the problem like homework and the page recognises it.

λ coefficients are written as `(1+λ)x1` or `2λx1`; to change the lower bound of the λ discussion, add a line like `λ >= 1` (it starts from 0 by default). `<=`, `>=`, `=` and the Unicode ≤, ≥ are all accepted, so are full-width characters and the `*` sign, and several constraints may share one line separated by semicolons. Non-negativity lines such as `x1, x2 >= 0` are skipped automatically.

The method is chosen automatically by problem type; you can also pick primal / Big-M / two-phase / dual simplex manually, which is handy for comparing tableaux of the same problem. Problems containing λ always use the parametric λ method.

## Reading the Output

From top to bottom:

1. The problem type, the method used and why;
2. The standardization notes: which slack, surplus and artificial variables were added and how the objective was converted;
3. One coloured simplex tableau per iteration — basis columns in light blue, entering column in yellow, pivot cell framed in red; below each tableau you can expand the "formulas for this tableau" showing every step from the previous tableau (pivot choice, ratio test, how each row was computed);
4. For the two-phase method, the phase-one (w) tableaux are shown as a separate block before phase two;
5. Parametric λ problems are grouped by interval: critical values first, then a set of tableaux and conclusions per interval;
6. The final answer (each variable's value and the optimal objective value) is highlighted in a green box at the end.

Unbounded, infeasible and iteration-limit outcomes are stated explicitly as well.

The top-right corner has a Chinese / English switch (the process text switches too) and a dark / light theme; the browser remembers both. Ten built-in examples (two of them λ problems) can be loaded from the dropdown, and the page already has one problem filled in when it opens — just click "Solve" to see a full walkthrough.

## Files

- `start.bat` — the launcher, just double-click it
- `web_app.py` — web version backend server
- `web/` — web version front end (index.html, style.css, app.js)
- `simplex_core.py` — core algorithms, shared by the web and command-line versions
- `text_parser.py` — problem-text recognition for the "type it out" mode
- `main.py` — command-line version (interactive in a terminal, asks for language at startup, 12 built-in examples)
- `lang.py`, `lang_en.py` — Chinese-to-English translation tables

## Notes

- If Chinese characters appear garbled in the Windows console, run `chcp 65001` first;
- If every port from 8000 to 8019 is taken, the program asks you to free one;
- The server listens on 127.0.0.1 only — problems never leave your computer;
- For study use.
