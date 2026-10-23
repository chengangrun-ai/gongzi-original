# v3 独立审查记录

审查时间：2026-10-23。基线：`184b7e4`。本轮只读源码、测试与优化清单；除本报告外未修改项目文件。结论：发现5项实际可复现问题，建议修正后再交付；未发现更改原创性阈值的行为。

## 范围与证据

- 读过根目录 AGENTS.md、实施计划、当前13个源码/打包文件的完整 Git diff，并对照相关未改调用路径。
- 读过4个回归测试文件及已有的 data/render/delivery 优化清单。分析领域清单在审查开始时尚未落盘，最终100项合并清单也尚未生成，因此本报告不能替代最后的逐项去重核验。
- 未重复运行主代理正在执行的全套测试或 selftest。以下问题均通过独立、很小的 Python 复现实际运行确认，临时产物使用 TemporaryDirectory 并清理。
- 实测291色网格经 `grid_text` → `load_grid` 后尺寸、整数网格和真实色号全部一致；超8色的文件导出/导入本身没有丢色。
- 静态核对了空作品拒绝、损坏参考图标记 incomplete、缺参考图 limited、阈值保持、报告单元格转义、ZIP明确文件清单、相对路径与还原SHA256处理。没有把这些阅读结果表述为本轮重新执行全套测试。

## 1. [P1] auto拒绝旧输出目录之前，已经覆盖旧风格资料

位置：`pindou/cli.py:67–80`；新加入的目录保护位于 `pindou/build.py:129–132`。

`cmd_auto` 先调用 analyze.run 写风格分析.json，再以 `w` 模式写风格包.json，最后才调用 builder.build。旧目录含 catalog.json 时，build 会正确拒绝继续，但前两个原始文件已经被新参考图覆盖。旧作品和旧风格凭据因此不再对应。

最小复现：创建 out/catalog.json、out/风格包.json（内容 KEEP_STYLE）、out/风格分析.json（内容 KEEP_ANALYSIS）；refs放任意4×4黑色PNG。用 n=1、cs=12 调用 `cmd_auto`。实际结果是 FileExistsError，同时两个 KEEP 文件均未保留。应将保护移动或复用到整个 auto 写入开始之前。

## 2. [P2] 291色配色被接受，绘图却仍发生索引溢出或崩溃

位置：`pindou/canvas.py:417`、`pindou/canvas.py:446–449`；相关新增能力：`pindou/palette.py:314–327`。

Palette.from_codes现在保留全291色，Canvas也接受这个合法配色。grid仍转int8，超127的索引会改变；art只分配256项查色表，超255会越界。

最小复现：

```python
pal = palette.Palette.from_codes(palette.resolve_set('mard291'))
cv = Canvas(1, 1, pal)
cv.pixels([(0, 0)], 291)
assert cv.grid(S=1)[0, 0] == 291
cv.art(px=2, ss=1)
```

实际grid为35，art抛 `IndexError: index 291 is out of bounds for axis 0 with size 256`。现有024测试只核对Palette本身，没有覆盖绘图。建议网格类型和LUT容量都按真实配色处理。

## 3. [P2] 正常重跑check后，交付清单校验立刻失效

位置：`pindou/cli.py:124–135`、`pindou/build.py:194–207`。

check直接重写原创性报告，但不刷新manifest中的SHA256，已有全套ZIP也保持旧报告。甚至不提供新参考图也能复现，因为build报告使用风格中文名，check从catalog读出的是风格id，报告内容会改变。

最小复现：用ink_tattoo、n=1、flower/badge、cs=12、art_px=1、mockup_b=1构建；保存manifest；调用 `cli.cmd_check(Namespace(out=目录, refs=None))`；再次计算manifest每项SHA256。实际不匹配项为 `原创性报告.md`。若使用不同refs，则JSON结论也可能变化，目录内与ZIP中的结论会分离。应让重查结果与清单/压缩包同步，或明确保存为独立核查产物。

## 4. [P2] 单款且无参考图时，说明和终端声称款间查重通过

位置：`pindou/build.py:102–105`。

originality.check已准确给出 `scope='pair_only'`、`pair_status='not_applicable'`，报告Markdown也写明单款没有可比较对；但result_label仅根据has_refs返回“仅款间查重通过，参考图未核查”。build说明、build终端和check终端均复用这一错误表述。

最小复现：

```python
r = originality.check([('A', np.ones((1, 1), np.int32),
                         palette.Palette({'line': 'H07'}))])
print(r['pair_status'], build.result_label(r))
```

实际为 `not_applicable` 搭配“仅款间查重通过”。应复用报告对单款的准确判断，避免把零次比较写成通过。

## 5. [P2] 还原预检查遗漏成员父子冲突，失败前会写出半套文件

位置：`scripts/restore_handoff.py:27–33`、`scripts/restore_handoff.py:49–52`。

还原脚本检查重复完整路径及磁盘现有文件，却不检查待写成员之间的父目录冲突。若包内同时包含普通文件a和a/b，两份SHA256都正确，预检查全部通过；写出a后，为a/b创建父目录时才失败，留下半成品。类似问题也发生在目标已有普通文件作为某成员父目录时。

最小复现：制作两段合法file标记，成员分别为a、a/b，内容都为 `first\n`，各自填写正确SHA256并以三反引号围栏包裹；调用restore。实际为FileExistsError，且dest/a已经存在。应在写入前校验完整目标路径树，并确保父节点都能作为目录使用。

## 结论边界

上述5项是本轮独立复现的问题，未包含主代理已经在修正的lowpoly主体丢失。各问题修正后应补对应可观察行为测试，并重新确认最终100项清单及交接包。此报告不构成人工体验验收；完整风格抽样和最终打包还原验证仍由主代理收口。

## 集中修复复审（2026-10-23）

本轮基于 `89cdd4b` 阅读 build.py、canvas.py、cli.py、restore_handoff.py 的修复差异及新增 test_review_fixes.py。原发现保留在上方作为过程记录；以下是最终修复状态。

| 原发现 | 状态 | 复审证据 |
|---|---|---|
| 1. auto覆盖旧风格资料 | ADDRESSED | auto在分析和写文件前调用共用输出检查；旧catalog、仅有旧风格包的目录均拒绝且字节保持；新目录auto仍成功生成并保存分析。 |
| 2. 291色绘图溢出 | ADDRESSED | Canvas按配色容量选索引类型，原画LUT按实际色数分配；127、128、291网格索引正确，291色原画及叠加网格均正确；小配色保留int8结果。 |
| 3. check使manifest和ZIP过时 | ADDRESSED | check先取得受管理交付上下文，重写报告和说明后更新其SHA256及对应交付ZIP；复核每项字节数/摘要和ZIP各成员与磁盘一致，其他文件及用户ZIP保持。 |
| 4. 单款零比较被写成通过 | ADDRESSED | result_label检查pair_status=not_applicable，明确写单款无法做款间查重；无参考图单款标签不含“通过”，多款正常比较仍能显示结果。 |
| 5. 还原成员父子冲突留下半套文件 | ADDRESSED | 写入前遍历全部成员父路径；a与a/b的两种排列、目标已有普通文件充当父目录均在开始写入前拒绝，原文件保持。 |

R3最后补充的两个边界也已纳入同轮复审：旧manifest未记录archive时，只有同名ZIP内的manifest参数和文件清单一致才认领为交付ZIP；同名用户压缩包保持原字节。清单中的源路径必须与解析后路径一致，目录链接不能借“网格”目录名把私有文件纳入刷新后的交付包。对应两个测试实际通过，没有跳过。

实际执行记录：

- 冻结后的 `python -m unittest discover -s tests -p test_review_fixes.py -v`：18项全部通过，4.403秒。
- 主代理额外提出的蕨叶修复已核对：`motifs._fern`只补上中心平移，没有重复缩放。`test_fern_is_drawn_at_requested_center`实际通过，0.044秒；另做同种子、s=10、中心从(20,20)到(40,40)的独立复现，平移20格后网格逐格一致，两幅均101颗豆。
- 本轮未重新运行全套测试或selftest；最终全套、成品视觉检查和交接包还原由主代理独立收口，不引用尚未完成的结果。

最终优化清单静态核对：optimization_100.json恰好100项，按顺序连续001–100，引用的18个不同文件全部存在，每项均有对应编号回归测试。结合上一轮源码审查及本轮重点映射，未发现明显重复计数或整项没有实现的条目。易混淆的057/068分别处理图片对称性与款间相似度，071/088分别处理核查接口与空目录命令，010/090分别处理款数参数与失败时不创建目录，属于不同可观察结果。蕨叶额外修复没有另计入100项。

本轮范围内未发现剩余阻塞问题。该结论限于上述修复、对应测试和清单核对，不表示所有输入或实际拼豆体验均已人工验收。
