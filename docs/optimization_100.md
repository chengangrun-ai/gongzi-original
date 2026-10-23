# 拼豆原创工坊 v3 · 本次100项优化

本次在v2源码上新增落实100项；原版已有的25项未重复计入。按不同问题和可观察结果计数，测试与说明文件本身不凑数。

001–025 配置、配色和方案；026–050 绘制与拼豆工艺；051–075 图片分析与数值核查；076–100 命令、导出和交接。

编号081来自总览视觉检查：低多边鹿的主体被清理删掉，只剩外圈。用原有墨格保留率替代成品总颗数触发兜底，避免新增白边掩盖主体丢失。

每项下面列出原问题、实际改法、源文件和回归证据。完整自动检查与人工验收范围见 [验证记录](verification.md)。

## 001 · 防止风格默认值和调用方配置串改

原问题：normalize 只做浅拷贝，修改一套作品的画幅、标签或难度会污染后续作品及原始输入。

已修改：对默认配置和用户配置深拷贝，输出中的嵌套对象独立。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_001_normalize_isolates_nested_defaults_and_input；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 002 · 让缺失颜色角色落到实际可用颜色

原问题：仅有描边色等少色风格仍会把填充退到不存在的 dark/mid，纹理代码检查角色时可能漏画。

已修改：按角色语义顺序寻找当前配色中真实存在的替代角色，保留 paper。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_002_missing_color_roles_resolve_to_available_roles；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 003 · 在绘制前挡住不安全数值配置

原问题：非有限线宽、越界概率、小数飞点数量和零难度除数会在绘制或统计中产生错误结果。

已修改：集中校验线宽、比例、清理数量、难度和配色权重，明确指出无效字段。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_003_rejects_unsafe_numeric_style_settings；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 004 · 拒绝失效的画幅配比

原问题：未知画幅、负数、无穷大或全零配比被忽略或回退，小样尺寸与用户指定不符。

已修改：限定 S/M/V、有限非负权重且至少一个正值；分配前缩放权重避免有限大数求和溢出。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_004_rejects_invalid_format_distributions；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 005 · 防止纹理名称拼错后悄悄变成平涂

原问题：错误纹理或把纹理池写成单个字符串会被误当作可用设置，成品与配置不符。

已修改：校验主体、脸部、翅膀及纹理池中的名称，要求纹理池为非空列表并去重。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_005_rejects_unknown_textures_including_pool；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 006 · 检查风格配色结构和角色拼写

原问题：拼错 accent 等角色名时颜色会被忽略，非对象配色也缺少清楚提示。

已修改：要求 palette 为映射，拒绝未知角色并在配置阶段校验角色颜色。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_006_palette_schema_reports_misspelled_roles；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 007 · 明确校验背景模式

原问题：把 fill 写成 filled 时程序按纸底继续，用户指定的满底会消失。

已修改：背景只接受 paper/fill，并在满底缺少背景色时给出字段错误。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_007_rejects_unknown_background_mode；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 008 · 从参考统计生成风格时保留原始资料

原问题：from_dna 直接往调用方的 palette_roles 中添加 line，生成结果中的题材也共享原列表。

已修改：转换前复制 DNA 和嵌套数据，再补足描边色；结果可独立修改。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_008_dna_conversion_does_not_modify_source；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 009 · 阻止风格ID冲突覆盖

原问题：两个风格文件使用相同或仅大小写不同的ID时，后读入的文件静默覆盖前一个。

已修改：加载时检测不区分大小写的ID冲突，报出冲突ID与文件；同时支持常见UTF-8 BOM文件。

文件：`pindou/stylepack.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_009_style_registry_rejects_duplicate_ids；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 010 · 校验生成款数

原问题：零、负数、布尔值会生成空批次或意外数量，小数在numpy内部才报错。

已修改：plan 入口只接受正整数款数，错误发生在任何方案生成之前。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_010_plan_requires_a_positive_integer_count；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 011 · 完整核对用户选择的题材和构图

原问题：混合输入有效名称与错误名称时，错误项被静默剔除；显式空列表被替换成默认值。

已修改：题材和构图逐项核对，列出未知项，并区分省略参数与明确空列表。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_011_plan_reports_all_unknown_selections；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 012 · 支持直接传入单项名称

原问题：subjects="cat"、templates="badge"会被拆成字母，导致已存在的选项无法使用。

已修改：将单个名称作为一项解析，并支持用逗号分隔的名称。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_012_single_selection_strings_are_not_split_into_letters；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 013 · 消除重复选择造成的抽样偏斜

原问题：重复题材或构图会占用抽样池，导致一轮题材重复、组合更少；内置botanical也有重复flower。

已修改：保持首次出现的顺序去重，使重复配置与去重配置得到相同固定种子方案。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_013_duplicate_options_do_not_bias_or_repeat_subjects；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 014 · 大批量方案每轮都充分利用组合

原问题：第一轮组合用完后不清空已用记录，后续改为随机选择，第二轮6个名额可能只有4种组合。

已修改：用完题材×构图的整轮组合后重置记录，后续每轮仍用满全部组合再重复。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_014_each_combination_cycle_is_complete_before_repeating；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 015 · 提前检查作品编号完整性和冲突

原问题：编号数量不足会中途IndexError，重复或空编号会造成作品难以区分或覆盖文件。

已修改：明确给出ids时要求与款数等长、编号非空、忽略大小写后唯一。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_015_explicit_ids_must_be_complete_unique_and_nonempty；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 016 · 保证大整数种子准确复现

原问题：numpy int64种子乘1000时溢出成负数，布尔值又会被当成合法种子。

已修改：种子入口校验非负整数，计算派生种子前转为Python整数，避免64位乘法溢出。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_016_seed_validation_and_numpy_integer_seed_are_stable；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 017 · 绘制方案在入口一次校验

原问题：错误题材、构图、尺寸或种子直到深层绘制才报KeyError等异常，定位困难。

已修改：compose 在分配画布前校验方案类型、必需字段、可用名称和种子。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_017_compose_rejects_invalid_specs_before_drawing；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 018 · 保存独立的作品生成凭据

原问题：compose 返回原spec对象，之后用户改种子或标签，会让成品凭据与已生成网格不一致。

已修改：开始绘制时保存方案的深拷贝，并以该副本绘制和返回。

文件：`pindou/recipes.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_018_composition_provenance_is_an_independent_snapshot；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 019 · 可靠解析常用十六进制颜色

原问题：标准#RGB短写和两侧空格无法解析，8位等错误色值反而被截断成另一种颜色。

已修改：严格接收三位或六位颜色、扩展短写，拒绝额外字节和重复井号。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_019_hex_colors_accept_standard_shorthand_and_reject_extra_bytes；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 020 · 保持用户限定的备豆色卡范围

原问题：nearest 的空allowed列表被替换成全色卡，可能选出用户没有的豆色；h7等简写不能用于候选列表。

已修改：仅None表示全部色卡，空集合明确报错，候选色号先规范化、去重和核对。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_020_nearest_preserves_restricted_color_set；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 021 · 防止无效RGB参与色差计算

原问题：NaN、负值、超255及错误三通道形状被送入Lab计算，产生无效或拼接错误的颜色。

已修改：转换前验证最后一维为三个通道，所有值有限并处于0–255。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_021_rgb_conversion_rejects_nonfinite_and_invalid_shape；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 022 · 隔离公开色卡与内部缓存

原问题：card 直接返回全局缓存，调用方改一个色号RGB后，后续所有作品都会使用被改过的错误实物颜色。

已修改：公开card返回独立记录快照，内部查询使用私有缓存。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_022_color_card_callers_cannot_pollute_cached_colors；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 023 · 统一实际色号并检查配色索引

原问题：直接构造Palette使用h7时输出图例仍是h7，负索引会指到末尾颜色，布尔值会当作索引。

已修改：构造时规范化并核对真实色号；索引查询拒绝布尔值和越界整数，所有颜色访问复用检查。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_023_palette_access_uses_canonical_codes_and_valid_indices；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 024 · 完整保留读回图纸中的所有颜色

原问题：from_codes仅把前8种颜色绑定给固定角色，超过8种颜色被静默丢失。

已修改：为额外颜色生成稳定的color_009等角色，保留全部真实色号，并按亮度和色号稳定排序。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_024_imported_palette_keeps_more_than_eight_real_colors；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 025 · 修复不同颜色角色抢用同一豆色

原问题：重复颜色检测把色号与角色名字典键比较，永远发现不了冲突，多角色可能全部变成同一颗豆。

已修改：使用真实色号集合检测冲突，从尚未使用的允许色号中选次优，并同步更新色差报告。

文件：`pindou/palette.py`、`tests/test_data_planning.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_data_planning.py -v；test_025_distinct_color_roles_receive_distinct_real_beads；原版红测失败，修复后通过。整组25项测试通过，python scripts/pindou.py selftest通过，14种内置风格各1款生成且四邻连通。

## 026 · 拒绝零尺寸或缩放后没有格子的画布

原问题：零宽高、零缩放和过小尺寸能进入绘制，产生空网格或后续异常。

已修改：构造画布时核查有限正数，并确认缩放后至少一行一列。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_026_canvas_rejects_unusable_dimensions -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 027 · 负线宽与负半径不再画出一颗豆

原问题：负线宽会进入单颗线分支，负半径也会直接落豆，错误参数生成了可见成品。

已修改：记录图形前校验线宽、半径和线帽；零宽或零半径跳过绘制。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_027_invalid_stroke_and_dot_sizes_are_rejected -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 028 · 统一拦截非法采样数

原问题：零采样会输出全空图、触发除零或空切片警告。

已修改：网格、遮罩和原画入口统一要求正整数采样数；原画格像素也提前核查。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_028_sampling_parameters_are_positive_integers -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 029 · 单颗落格不侵占右邻和下邻

原问题：单颗绘制右下边界多加一像素，S=1时一颗豆变成四颗；画布外负坐标还可能渗入边缘。

已修改：落格使用左闭右开的精确格边界，并在绘制前忽略画布外格子。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_029_snapped_cells_use_half_open_bounds -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 030 · 直接点名的格子出现在高清原画里

原问题：pixels生成了网格中的豆，高清原画重放时却跳过整个pixel类型。

已修改：原画分支按网格格心绘制小圆点，正确处理缩放、裁剪和越界格。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_030_explicit_pixels_appear_in_original_art -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 031 · 同一画布重复渲染保持点刺和渐变一致

原问题：每次grid都会再次消耗随机数，重新导出会改变单颗豆位置。

已修改：内置随机效果首次渲染保存随机顺序和噪声，后续原样重放；首次随机序列保持原有语义。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_031_random_effects_replay_identically -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 032 · 后续修改输入数组不再偷偷改作品

原问题：点刺和渐变闭包保留调用者的遮罩、密度或亮度数组引用，外部修改会改变待导出的图。

已修改：登记效果时复制遮罩和广播后的场，并固定颜色层列表。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_032_effect_inputs_are_snapshots -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 033 · 点刺与渐变错误在登记时明确报出

原问题：错误遮罩尺寸、超范围密度、空颜色层和NaN直到出图时才崩溃，或静默当作有效效果。

已修改：效果入口检查完整网格形状、0到1的有限数值、非空颜色层和非负抖动强度。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_033_effect_inputs_fail_before_render -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 034 · 密度场不再掩盖无定义的方向或半径

原问题：线性轴两点重合和径向外半径小于内半径被极小分母吞掉，输出无意义的密度。

已修改：密度辅助函数验证端点、半径先后关系、密度范围和正gamma，去掉掩盖错误的分母钳制。

文件：`pindou/canvas.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_034_density_fields_reject_undefined_axes -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 035 · 坏坐标不再被悄悄重排成图形

原问题：一行四列被reshape当成两个点，NaN和无穷坐标继续流入Pillow。

已修改：点集入口检查每行坐标对和有限数值，保留合法空点集的二维形状。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_035_points_reject_nonfinite_and_malformed_rows -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 036 · 折线重采样保住原始拐角

原问题：按整条线等距采样可能跨过折点，后续连线把直角截成斜边。

已修改：逐段重采样并保留每个原始端点，确保采样间距不超过指定步长。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_036_resampling_keeps_corners -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 037 · 负几何采样间距不再静默降成粗线

原问题：折线、样条、圆弧和螺旋遇到负间距会返回极少点，用户图形悄悄失真。

已修改：四类采样入口统一要求有限正间距，并检查样条alpha与圆弧/螺旋半径。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_037_geometry_rejects_negative_sampling_steps -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 038 · 闭合样条真正回到起点

原问题：闭合样条采完最后一段后附加了最后控制点，造成末尾折返而非闭合。

已修改：闭合样条末端改用首控制点，消除额外折返。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_038_closed_spline_finishes_at_start -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 039 · 渐变线宽按实际距离变化

原问题：文档承诺按弧长插值，但实现按点序号分配宽度；控制点密集处会异常增粗。

已修改：宽度曲线和函数的u改为累计路程比例，仍保留逐点明确给宽度的语义。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_039_widths_follow_distance_not_vertex_number -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 040 · 重复点与单点不再破坏法线

原问题：单点触发numpy梯度异常；连续重复点产生零法线，使粗线和身体局部塌陷。

已修改：单点返回零切向量，重复点先合并计算再映射回原位置。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_040_normals_handle_single_and_repeated_vertices -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 041 · 单点和重复点凸包保持有效形状

原问题：单个唯一点的凸包被删除或重复返回；空凸包变成一维数组。

已修改：先去除重复坐标，小于等于两个唯一点直接返回，保持(N,2)形状；同时移除二维cross弃用警告。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_041_hull_preserves_single_unique_point -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 042 · 沿脊线身体的采样数参数生效

原问题：body_along的n无论给多少都被忽略，无法控制轮廓点数和资源消耗。

已修改：指定n时按累计长度精确插值n个脊线点，并校验n至少为2。

文件：`pindou/geom.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_042_body_sampling_count_is_honored -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 043 · 整数遮罩正确填洞且支持空遮罩

原问题：对uint8的0/1遮罩直接按位取反，把整个背景都变成非零，洞不能填；空遮罩越界。

已修改：先核查并转换布尔遮罩；空遮罩直接返回；按标签查表一次性填符合面积限制的洞。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_043_hole_filling_accepts_binary_integer_masks -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 044 · 工艺坏参数不再意外铺满画布或擦掉作品

原问题：SciPy把负迭代数当作反复运算；负面积、NaN距离和纸色托底也被接受。

已修改：整理入口明确检查非负迭代次数、面积和桥距，并要求有效非零托底色。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_044_finalize_rejects_destructive_parameters -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 045 · 相邻碎片可通过接力桥完整保留

原问题：原实现只量到原始主体的距离，远处碎片即使能经邻近碎片相连也会被提前删除。

已修改：每接最近的合格块就重新计算主体与距离，直到无可桥接块；移除任意40轮上限。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_045_bridge_can_keep_a_chain_of_nearby_islands -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 046 · 空作品显示零工时和零用板

原问题：全空网格仍显示一块底板、入门两星和1到2小时，误导备料和工时估计。

已修改：空作品的用板、星数和时间归零，明确标记空作品等级。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_046_empty_pattern_has_no_work_estimate -v；红：原版空52×52网格boards实际1、期望0，测试失败；绿：同一断言及本组28测试通过。

## 047 · 网格预览查表提速

原问题：原预览每个色号都展开一张完整大遮罩并扫描全部像素，色数越多越慢，还重复分配大数组。

已修改：先将每格颜色索引一次查成RGB，再沿两个方向放大，保留网格线逐像素结果；同色孤立豆统计同时用相邻数组比较替代逐颗Python循环。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_047_preview_is_pixel_identical_with_less_work -v；同一156×156网格、B=8、7角色，五次均值：旧预览0.085944秒，新预览0.011896秒，7.22倍；singles旧0.060620秒，新0.000060秒；两者与原版逐像素/数值一致。红：回退旧预览路径后，相对性能测试实测0.063498秒未低于旧参考0.063280秒的70%，测试失败；恢复查表后通过。

## 048 · 难度系数不能产生反向评分或除零

原问题：负分母会让大作品更简单，零分母直接崩溃，NaN和无穷系数也会进入评分。

已修改：难度入口要求分母有限正值、加分系数有限非负值。

文件：`pindou/beadify.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_048_difficulty_parameters_cannot_invert_rating -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 049 · 渐变真正覆盖图形并随缩放保持位置

原问题：默认渐变以画布原点的一格半径计算，大部分图形全变暗；lo/hi无效，注册纹理还混用网格与设计坐标。

已修改：默认亮度按图形包围盒计算并应用lo/hi；渐变场统一换回设计坐标，修复放大后渐变偏移。

文件：`pindou/brushes.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_049_default_gradient_spans_the_shape_at_any_zoom -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 050 · 纹样零间距不再让程序卡死

原问题：点阵、棋盘、鳞片等while循环在零或负周期时永不前进；负排线间距静默漏画。

已修改：排线、点阵、鱼鳞、青海波、波浪、棋盘和半调统一要求有限正周期。

文件：`pindou/brushes.py`、`tests/test_render_craft.py`。提交：`680e523`。

验证：python -m unittest discover -s tests -p test_render_craft.py -k test_050_brush_spacing_fails_instead_of_looping -v；红：首次原实现执行本组25测试，45个断言失败及5个原行为异常，本项回归失败；绿：修复后本组28测试通过。

## 051 · 按照片实际显示方向分析和核查

原问题：忽略EXIF旋转会把竖图当横图，并使相同画面产生不同核查结果。

已修改：图片统一先应用EXIF方向；风格分析与参考图缩格共用同一读取逻辑。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_051_exif_rotation_is_applied_in_both_image_readers；python -m unittest discover -s tests -p test_analysis_originality.py -v

## 052 · 透明图片按白纸合成后统计

原问题：直接转RGB会把透明区的隐藏颜色当成可见画面，污染主色和相似度。

已修改：RGBA及带透明信息图片先合成到白色背景，再用于两个模块的统计。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_052_transparency_uses_visible_white_composite；透明红块与同样可见的白底红块结果逐像素相同

## 053 · 整数图像聚类保留小数中心

原问题：uint8样本的聚类中心保持整数类型，均值0.5被截成0，连续更新产生偏差。

已修改：聚类样本及中心使用float64，输入0和1时得到真实均值0.5。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_053_integer_samples_retain_fractional_cluster_center

## 054 · 主色列表去除重复及空簇

原问题：纯色图片产生8个相同主色，其中7个占比为0，误导角色配色和颜色数量。

已修改：按唯一RGB及真实像素次数聚类，仅输出非空主色。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_054_flat_image_has_one_active_color；纯色图只返回一种颜色且占比1

## 055 · 拒绝无效聚类输入

原问题：空样本、错误RGB维数、NaN、越界颜色及无效聚类次数会产生底层异常或错误结果。

已修改：在聚类入口明确检查矩阵形状、数值范围和整数控制参数，统一给出ValueError。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_055_invalid_cluster_samples_and_controls_are_rejected

## 056 · 区分原图尺寸与内部采样尺寸

原问题：大图被压到640像素后，把采样尺寸写成原图尺寸，用户看到错误画幅信息。

已修改：size记录旋转后的原图尺寸，另加analysis_size说明内部采样尺寸，比例按原图计算。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_056_source_dimensions_are_not_sampling_dimensions；1000×10图保留原尺寸，采样为640×6

## 057 · 小图与纯色图也有有限的对称性统计

原问题：100像素以内图片一律报0对称，大纯色图片相关系数产生NaN警告。

已修改：所有尺寸使用稳定归一化相关计算，完全相同的常量镜像记为1。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_057_small_and_constant_mirror_symmetry_is_finite；1、4、16边长纯色图均为1且严格JSON可编码

## 058 · 边缘像素及两像素窄图参与边缘统计

原问题：梯度只算内部像素，两像素条纹全部被统计为无边缘。

已修改：边界使用单向亮度差，内部继续使用原有双向差，单行单列也能计算。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_058_two_pixel_stripe_has_detectable_edges；2×2黑白条纹边缘密度大于0.9

## 059 · 糊格率不把画布两端接在一起

原问题：np.roll环绕比较会把最右列变化传播到最左列，虚增糊格。

已修改：改为边界复制的3×3局部最大和最小值比较，保留原有亮度及差值判定。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_059_mud_does_not_join_opposite_canvas_edges；52列仅最右列变白时糊格率为1/52约0.019

## 060 · 背景采样的四角只计一次

原问题：四边拼接把角点重复采样，小图背景中位色会被角点主导。

已修改：通过边框布尔掩码采样，每个边缘像素只计一次，中位色按最近整数输出。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_060_background_border_counts_each_corner_once；3×3四角黑边缘其余白时背景为#808080

## 061 · 汇总主色按占比计算代表颜色

原问题：同一色桶直接沿用首张图片颜色，交换参考图顺序就改变配色；重复簇还会虚增出现次数。

已修改：色桶累计占比加权RGB并求均值，出现次数按每张图计一次，并使用确定的排序次序。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_061_aggregate_color_center_is_order_independent_and_weighted；120和130等权汇总为125，调换输入不变

## 062 · 汇总结果与输入DNA互不影响

原问题：images及颜色RGB数组引用原始输入，修改结果会反向改坏输入，影响后续复用。

已修改：聚合入口复制嵌套DNA，输出代表颜色使用新的RGB列表。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_062_aggregate_result_does_not_alias_input_dna

## 063 · 汇总前检查外部DNA完整性

原问题：零画幅、NaN指标、错误明暗档数及空主色仍会被当成可用风格输出。

已修改：校验必需统计、五档比例、背景颜色与比例、RGB及颜色占比，拒绝缺字段和非法值。

文件：`pindou/analyze.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_063_aggregate_rejects_nonfinite_or_malformed_dna

## 064 · 参考目录按统一次序递归扫描

原问题：只对单目录文件排序、目录依赖系统顺序，大小写及创建顺序会影响汇总和最近参考图的先后。

已修改：统一按相对路径的大小写无关次序排序，再用原路径打破平局，分析及核查共用扫描器。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_064_recursive_scan_has_canonical_directory_order

## 065 · 重复可见画面不重复加权

原问题：同图另存PNG、BMP会多次参与统计和参考计数，批量复制即可改变分析结果。

已修改：使用方向和透明处理后的尺寸及RGB内容摘要去重，保留重复数及对应文件名。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_065_duplicate_visible_images_do_not_bias_statistics_or_ref_count；两份黑图加白图只统计两张

## 066 · 图片读取失败可追踪且不暴露本地路径

原问题：损坏图片被静默吞掉，或在verbose=False仍打印带绝对目录的Pillow错误。

已修改：scan报告发现数、成功数、失败数、文件名和错误类别，安静模式不输出，异常原始路径不进入报告。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_066_corrupt_image_diagnostics_are_quiet_and_do_not_leak_paths

## 067 · 非法网格不再被当成白色像素

原问题：负数、超出色卡索引、小数及NaN被忽略成零墨量，产生失真的核查结果。

已修改：网格转墨量前核对非空二维、有限整数、索引范围及色卡RGB范围。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_067_ink_map_rejects_invalid_grid_indices

## 068 · 相同常量图也能查出重复

原问题：相同纯色作品的零均值范数为0，原先NCC返回0，完全重复款错误通过。

已修改：两张相同常量图相关值记为1，不同常量图仍为0，常规图继续用原有NCC。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_068_identical_constant_maps_are_duplicates；两个同色实心网格款间核查不通过

## 069 · 相似度入口拒绝错误矩阵

原问题：不同尺寸可被numpy广播比较，空图和NaN会产出无意义数值，越界墨量被dHash截断绕回。

已修改：NCC检查非空有限二维且形状相同，dHash额外检查0到1墨量及正整数尺寸。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_069_similarity_rejects_invalid_map_shapes_and_nonfinite_data

## 070 · NCC计算避免浮点平方溢出

原问题：float32大数图的范数和内积溢出，连自身比较也返回NaN。

已修改：用float64并在去均值前按最大幅值缩放，最后把舍入误差限制在[-1,1]，判定阈值保持不变。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_070_ncc_does_not_overflow_float32_norms；0到3e30自身比较为1且不产生警告

## 071 · 拒绝无作品、重复编号和全空白核查

原问题：零作品及全空白作品会自动通过；重复编号使报告无法准确定位问题款。

已修改：核查入口要求至少一款、非空唯一字符串编号，以及至少一个放豆格。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_071_check_rejects_empty_designs_duplicate_ids_and_blank_work

## 072 · 区分有限检查与参考图读取失败

原问题：无参考图、路径写错和参考图全部损坏都被当成完整通过，-1及999也被显示为真实指标。

已修改：新增status、scope、ref_status、pair_status；未执行指标为null，指定参考目录无效或存在读取失败时标为incomplete且pass_=false。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_072_reference_scope_distinguishes_missing_and_failed_checks；无参考为limited，损坏或缺目录为incomplete

## 073 · 最小dHash真正覆盖全部参考图

原问题：最小dHash只取最大NCC所对应的参考图，遗漏其他更小哈希距离。

已修改：分别记录最大NCC参考与最小dHash参考，逐款及全局均汇总所有参考比较。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_073_minimum_ref_hash_uses_all_references；合成两参考夹具原版误报14，修复后返回真实最小值8；work/analysis-minhash-red.log

## 074 · 同名参考图可准确区分

原问题：不同私有子目录的同名图片在最近参考、标记列表中无法区分。

已修改：同basename的参考加稳定序号，不把父目录和绝对路径写进报告。

文件：`pindou/analyze.py`、`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_074_same_basename_references_have_distinct_private_labels

## 075 · 防止报告字段破坏表格和插入HTML

原问题：用户编号、系列标题、风格和参考文件名直接拼入Markdown，可破坏表格、换行插段或注入HTML。

已修改：表格及标题统一做HTML与Markdown转义，安全展示输入；报告同时消费真实核查状态，说明数值检测边界。

文件：`pindou/originality.py`、`tests/test_analysis_originality.py`。提交：`8b5e702`。

验证：test_075_markdown_escapes_user_cells_and_states_check_boundary；python scripts/pindou.py selftest

## 076 · Windows终端自测正常退出

原问题：旧版输出勾号导致GBK编码错误

已修改：将自测完成符号改为兼容中文终端的ASCII，清理自测临时目录

文件：`pindou/cli.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 076 -v；test_076_cli_selftest_runs_in_gbk_terminal

## 077 · 核查不通过返回失败退出码

原问题：命令总返回0，批处理无法识别核查失败

已修改：main根据核查pass_返回2，常见用户输入错误给出简明提示

文件：`pindou/cli.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 077 -v；test_077_check_failure_produces_nonzero_cli_exit

## 078 · 目录正确保存逗号和换行

原问题：手工拼接CSV导致作品名拆列或拆行

已修改：改用标准CSV写入器并保留Excel中文编码

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 078 -v；test_078_catalog_quotes_commas_quotes_and_newlines

## 079 · 作品名不会被表格软件执行为公式

原问题：以等号等开头的名字被当作公式

已修改：CSV文本单元格对公式前缀转义，JSON保留原始名字

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 079 -v；test_079_catalog_neutralizes_formula_names

## 080 · 目录提供可搬运的文件链接

原问题：catalog缺少图纸和网格文件位置

已修改：保存色号图、原画、效果图、网格相对路径

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 080 -v；test_080_catalog_contains_portable_artifact_paths

## 081 · 防止白边掩盖主体被删空

原问题：低多边鹿被碎块清理删掉后，外圈新增白豆抵消了丢豆数量，错误地跳过重试

已修改：按原有墨格实际保留率触发桥接重试，恢复主体并保持四邻连通

文件：`pindou/recipes.py`、`tests/test_delivery.py`。提交：`b8d65ad`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 081 -v；test_081_subject_survives_white_border_cleanup

## 082 · 拒绝不规则网格行

原问题：不同宽度的网格被默默接受或读回崩溃

已修改：解析时检查非空二维矩形并指出行宽错误

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 082 -v；test_082_ragged_grid_rejected

## 083 · 拒绝未定义网格符号

原问题：未知符号被当成空白，作品会丢豆

已修改：符号必须出现在图例中，支持BOM和常用换行

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 083 -v；test_083_unknown_grid_symbol_rejected

## 084 · 拒绝冲突图例

原问题：重复符号覆盖原色号，读回后颜色变化

已修改：图例去冲突并核验真实色号

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 084 -v；test_084_conflicting_legend_rejected

## 085 · 核验网格声明尺寸

原问题：文件头写52x52但正文不匹配也能核查

已修改：声明宽高必须与正文实际行列一致

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 085 -v；test_085_declared_dimensions_checked

## 086 · 导出前验证网格色号索引

原问题：负数或越界值导出时崩溃或错指颜色

已修改：拒绝无效索引，额外角色自动分配不冲突单字符号

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 086 -v；test_086_grid_export_rejects_invalid_palette_index

## 087 · 统一网格色号还原

原问题：check独立手写解析器，额外色号和错误处理不一致

已修改：新增load_grid并由check使用，按真实色号还原且使用32位索引

文件：`pindou/build.py`、`pindou/cli.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 087 -v；test_087_grid_loader_roundtrips_bead_codes

## 088 · 空目录不能冒充核查通过

原问题：没有作品的目录也会生成通过报告

已修改：check在没有网格文件时明确报错

文件：`pindou/cli.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 088 -v；test_088_check_empty_directory_is_error

## 089 · 生成可用于Windows的文件名

原问题：CON等保留名和结尾点号导致写文件失败

已修改：统一清理非法字符、保留名、结尾点和过长名称

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 089 -v；test_089_windows_reserved_filename_is_safe

## 090 · 错误构建参数不创建半成品

原问题：先建目录再排方案，无效数量会留下残留文件夹

已修改：把方案、尺寸和编号验证前置到创建目录前

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 090 -v；test_090_invalid_build_leaves_no_output

## 091 · 保护已有系列免于覆盖混款

原问题：同目录重复构建覆盖同编号并遗留旧款

已修改：发现已有目录或作品文件时拒绝写入，提示使用新目录

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 091 -v；test_091_existing_output_is_not_overwritten

## 092 · 压缩包只包含明确交付物

原问题：遍历整个输出目录会收进参考图、私有资料和临时文件

已修改：build传入准确文件列表，通用打包仅收已知交付目录和文件

文件：`pindou/chartkit.py`、`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 092 -v；test_092_zip_excludes_private_and_unrelated_files

## 093 · 校验压缩包内部路径

原问题：extra文件允许../等向外路径和重复成员

已修改：拒绝绝对、向外、重复路径和符号链接，排序写入

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 093 -v；test_093_zip_rejects_traversal_member_name

## 094 · 打包失败保留已有压缩包

原问题：直接打开目标zip会先清空旧包

已修改：验证成员后写临时包，成功后一次替换目标

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 094 -v；test_094_failed_zip_preserves_previous_archive

## 095 · 交付文件可校验且参数可复现

原问题：缺少整套文件指纹和完整已解析配置

已修改：新增manifest记录SHA256、字节数、风格快照、每款方案和导出尺寸

文件：`pindou/build.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 095 -v；test_095_manifest_verifies_delivered_bytes

## 096 · PNG导出创建目录并避免半文件

原问题：独立导出到新目录失败，保存中断会留下损坏PNG

已修改：建立父目录、明确PNG格式、写临时文件后替换，保留元数据

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 096 -v；test_096_png_save_creates_parent_and_keeps_metadata

## 097 · 总览缩略图不修改调用方图片

原问题：thumbnail直接缩小外部传入图片

已修改：复制图片后缩放，路径图片用上下文及时关闭

文件：`pindou/chartkit.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 097 -v；test_097_contact_sheet_does_not_resize_callers_image

## 098 · 同色号跨角色用量正确汇总

原问题：相同真实色号计数被后一个角色覆盖

已修改：Pattern和工艺统计按色号累加，图纸总量和真实豆数一致

文件：`pindou/chartkit.py`、`pindou/beadify.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 098 -v；test_098_pattern_aggregates_same_code_across_roles

## 099 · 总览和造型对照图补齐来源信息

原问题：总览没有作者和时间，audit字体写死且不能新建父目录

已修改：总览继承构建元数据，audit复用跨平台字体和统一PNG保存

文件：`pindou/build.py`、`pindou/cli.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 099 -v；test_099_overview_preserves_build_metadata

## 100 · 新版交接包可完整安全还原

原问题：固定文件列表漏新模块测试文档，原还原脚本边读边覆盖

已修改：自动收录新增源码测试文档，先验证全包SHA256和路径再写入且不覆盖现有文件

文件：`scripts/pack_handoff.py`、`scripts/restore_handoff.py`。提交：`89cdd4b`。

验证：python -m unittest discover -s tests -p test_delivery.py -k 100 -v；test_100_handoff_collects_new_modules_tests_and_docs
