# Changelog - lr-openspec-code-review

## 2026-11-02 - SE 适配

- 保留三端 18 项检查及权重；config-001/002 补回 SE NeedParseDataMethod 和临时 S→A 生成例外。
- 知识库/编码规范路由使用 SE ai-core，保留 SVN 工作区发现。
- DL GodFort 示例与频次保留来源标记，不能代替 SE API/文件证据。
- 生成期自检交叉引用对齐；UI 生成与验证优先 ai-game-developer MCP。


## 2026-10-31 - 新增 client-015 Module 数据边界与 Record 注册（v1.3）

### 背景

`../develop/client/project/docs/ai-core/knowledge/modules/index.md` 的 Module 层约定此前没有被任何检查项引用。Record 注册/命令分发错误属于静默失效（编译通过、页面能开，但数据永远为空或不刷新），client-009 的“删除测试”判定方法抓不到。

### 变更

- 新增 client-015（P1 / 权重 5 / GodFort 实证 3），规则来源 `../develop/client/project/docs/ai-core/knowledge/modules/index.md`。
- 检查点：一表一注册一回调一命令；禁止平行分发表（`RecordKind` switch / `m_RecordLoaded[]`）；缺表语义（`FindRecord == null` 不等于未同步）；ready 粒度（owner / 同步时点 / 缺表语义）；`RequestXxx` 保持薄；`OnInit`/`OnClose` 依赖与清理。
- 与 client-009 分工：009 管“新增但没人消费”的抽象；015 管“用了但语义/边界错误”，同一位置按 015 记。
- 清单总数 17 → 18（服务端 4 + 客户端 12 + 配置表 2）。

### 同步

- `checks/client.md` 增加 client-015 一节，标题项数改为 12。
- `SKILL.md` 更新检查清单索引、步骤 3 列表、报告模板计数；版本 v1.3。
- `.agents/skills/lr-openspec-code-review/SKILL.md` 描述同步。
- 审计补充：server-001 增加“处理函数已注册（`ADD_INT_CUSTOM_HOOK`）”；client-014 补充 `AddCustomHook` 注册；client-015 补充属性钩子注册模式。
- 同步修正 SKILL 中残留的“17 项”计数，以及规则文档中 5 处混合路径分隔符。
- 补齐 tasks §0.3 框架接入任务包：新增 Condition 注册、Module 注册与数据钩子两项（七项 → 九项），与 client-012/014/015 对齐。
- 修正 apply 三端的“生成期 P0 契约自检”标题：其中混有 P1 项（server-002 / client-003 / client-013 / config-002），标题改为“生成期契约自检”，并在每个条目标注对应检查项档位。
- 步骤 3 补充执行顺序：同端内先跑 P0 再跑 P1/P2；client-009 放到最后一遍整体评估；索引按 ID 排列，ID 不代表优先级。版本 v1.3.1。

---

## 2026-10-31 - 按 GodFort 实证重排权重（v1.2）

### 权重体系

- 严重度由“高/中/低”改为 P0 阻断（10）/ P1 结构契约（5）/ P2 质量建议（1）。
- 索引表新增档位、权重、GodFort 实证三列；报告总览输出风险分 10*P0 + 5*P1 + 1*P2。
- 排序：先档位，同档按实证频次降序。

### 检查项增删（数量保持 17）

- client-002（DettachPage 拼写）并入 client-001（UI 框架方法签名）。
- client-006（BA 索引起点）并入 client-005（协议解析契约，扩展到字段数/类型/可选尾）。
- client-007（类内成员顺序）删除，移交客户端 lr_code_review。
- 新增 client-012 框架注册完整性（UIID/UIDataTable、DynamicConfigModule 两级注册、ConditionModule、共享枚举），P0。
- 新增 client-013 序列化字段与 Prefab 绑定，P1。
- 新增 client-014 生命周期与订阅配对，P1。

### 检查项改写

- server-001 扩展为协议契约完整性：C2S 索引 + S2C 字段数/类型 + 两端协议 ID 集合。
- server-002 由错误处理风格改为错误反馈完整性。
- server-003 基准改为实际导出 txt 表头。
- server-004 改为项目实际的 IRecord 加 Exist 风格，并核对列数/列序。
- config-002 补齐导出 txt 层，改为三层一致性。
- client-003 明确归属/注册为 P1、置脏时机为 P2，补多期活动过滤。
- client-009 增加职责倒置维度。
- client-010 降为 P2；client-011 拆为缺 key/硬编码 P1 + 静态文案 P2。

### 生成期自检同步

- 客户端 apply/client-execution.md 新增 §5.2：UI 签名、协议契约、框架注册、Prefab 绑定清单、红点归属。
- 服务端 apply/server-execution.md 新增 §5：协议契约、配置字段名、Record 保护、错误反馈。
- 配置 apply/config-execution.md 新增 §3.4：need_copy、三层一致、生成边界。

### 修正

- client-005 规则来源改为 client-structure.md §1.4（原 §1.3.1/§1.3.2 不存在）。
- config-001 标注实际路径 develop/client/tools/table/table_config/outcode_config.json。
- 退役 ID client-002/006/007 不再复用。
- 同步修正规则文档：outcode_config 实际路径、DynamicConfigModule 新增 §2.3.1、server-structure 新增 §1.2.1/§1.3.1、compile-verification 重复编号。

---

## 2026-10-31 - 检查项拆分与流程修正（v1.1）

### 结构调整

- 检查项从 SKILL 正文拆到 `checks/server.md`、`checks/client.md`、`checks/config.md`；SKILL 只保留流程骨架、索引表和报告模板（1004 行 -> 367 行）。
- 新增 `checks/config.md` 的 config-002 字段属性标注检查（原清单有项、无执行步骤）。

### 正确性修正

- client-003 改为“红点归属与触发时机”：活动红点走 `BusinessActivityModule_RedPoint`（`RegisterRedPointCallback` / `DirtyRedPoint`），普通系统功能红点走 `RedPointModule`（`Register` / `Bind` / `SetHookRecord` / `SetHookProp` / `SetDirty`）。
- client-004 移除“必需调用 RegisterRedPointCallback”的普适要求，非活动功能不再被误判。
- 报告示例路径 `UIScript` -> `UISript`（客户端真实目录）。
- 报告示例计数修正为 14 + 3 + 0 = 17。

### 流程增强

- 使用方式新增显式文件/目录入口。
- 步骤 2 fallback 从 SVN 改为 `git -C <repo> status --porcelain`，去掉 `cd` 串联。
- 新增“审查边界”：默认只报告不改代码；修改后按 `compile-verification.md` §5.3 验证。
- 工具写法统一为 `codegraph_explore` / `rg` / `Read` / `git -C`。
- 1.4 空结果处理、1.5 完整性对照合并，删除重复的 2.4 可选步骤。
- 输出提示后明确停止，不自动串下一阶段。

### 维护

- 新增/修改检查项的落点固定为 `checks/<role>.md` + SKILL 索引表 + 本文件。

---

## 2026-08-13 - 步骤 2 重构：优先使用 implementation-report.md

### 改进内容

**修改章节**：`步骤 2：获取目标文件清单`

**核心变化**：
- **旧方案**：仅使用 SVN status + grep 过滤获取改动文件
- **新方案**：优先从 `implementation-report.md` 读取文件清单，SVN 方案作为 fallback

### 详细修改

#### 1. 新增方法选择逻辑

```
1. 优先：检查 changes/<change-id>/implementation-report.md 是否存在
2. 如果存在且完整：解析 report 获取文件清单（方法 A）
3. 如果不存在或不完整：回退到 SVN status（方法 B）
```

#### 2. 新增 2.1 节：方法 A - 从 implementation-report.md 读取（推荐）

**步骤**：
1. 检查 report 是否存在
2. 读取"生成文件清单"章节
3. 提取文件路径（3 种方法）
4. 按角色分类（服务端/客户端/配置表）

**优势**：
- ✅ 精确：apply 工具已验证的文件清单，无噪音
- ✅ 结构化：按功能分组，便于理解
- ✅ 完整：包含新增 + 修改的所有相关文件
- ✅ 无需过滤：不受 SVN 大量无关改动干扰

#### 3. 重构 2.2 节：方法 B - 从 SVN 状态读取（Fallback）

**明确使用场景**：
- `implementation-report.md` 不存在（apply 未执行）
- report 格式异常无法解析
- 需要检查手动改动但未体现在 report 的文件

**保留原有逻辑**：
- SVN status 获取改动
- 用 tasks.md 模块名 grep 过滤

**新增限制说明**：
- ⚠️ 噪音大
- ⚠️ 过滤可能失效
- ⚠️ 需要猜测模块名

#### 4. 更新 2.3 节：提取模块名

**适配双方法**：
- 方法 A：从文件清单直接提取模块名作为 CodeGraph 查询关键词
- 方法 B：从 tasks.md 提取作为 grep 过滤关键词

#### 5. 更新 2.4 节：完整性检查

**统一对比逻辑**：
- 方法 A：report 文件清单 vs tasks.md 预期
- 方法 B：svn status vs tasks.md 预期

**标记为可选**：此步骤为可选，主要用于发现遗漏。

### 改进理由

#### 实际案例验证（marriage-func code review）

**使用 SVN 方案遇到的问题**：
```bash
# 返回 70+ 文件，包括大量无关文件
svn status | grep -E "^(M|A)" | awk '{print $2}'

# 过滤失败：返回空（模块名不匹配路径）
svn status | ... | grep -i "marriage\|wedding"
```

**最终实际使用的方案**：
- 直接查看 `implementation-report.md` 的"生成文件清单"
- 从中提取明确的文件列表
- 使用 CodeGraph 查询：`MarriageModule OnCellUpdated protocol handler`

**结果**：
- ✅ 精确获取 10 个目标文件
- ✅ 0 个无关文件
- ✅ 无需 grep 过滤

#### 方法对比

| 维度 | 方法 A (report) | 方法 B (SVN) |
|------|----------------|--------------|
| **精确性** | ✅ 高（apply 验证过） | ⚠️ 中（需人工过滤） |
| **噪音** | ✅ 无 | ❌ 大（数十/上百个无关文件） |
| **结构化** | ✅ 按功能分组 | ❌ 平铺列表 |
| **完整性** | ✅ 新增+修改都有 | ✅ 新增+修改都有 |
| **依赖** | ⚠️ 需 apply 先执行 | ✅ 独立 |
| **过滤逻辑** | ✅ 不需要 | ⚠️ grep 可能失效 |

### 兼容性

**向后兼容**：
- ✅ 保留 SVN 方案作为 fallback
- ✅ 旧流程（直接使用 SVN）仍可工作
- ✅ 不依赖 apply 必须完成

**适用场景**：
- **推荐场景**：apply 已执行 → 使用方法 A
- **兼容场景**：apply 未执行 / 手动改动 → 使用方法 B

### 影响范围

**修改文件**：
- `.claude/skills/lr-openspec-code-review/SKILL.md`

**修改章节**：
- § 步骤 2：获取目标文件清单（重构）
- § 2.1：新增方法 A（推荐）
- § 2.2：重构方法 B（fallback）
- § 2.3：适配双方法（模块名提取）
- § 2.4：统一对比逻辑（完整性检查）

**未修改章节**：
- § 步骤 1：加载检查清单 ✓
- § 步骤 3：执行服务端检查 ✓
- § 步骤 4：执行客户端检查 ✓
- § 步骤 5：执行配置表检查 ✓
- § 步骤 6：生成审查报告 ✓

### 后续建议

1. **实际使用验证**：
   - 在下一个 code-review 任务中测试新方法 A
   - 验证文件提取逻辑是否准确
   - 确认 fallback 到方法 B 的流程顺畅

2. **文档完善**（可选）：
   - 添加 implementation-report.md 解析的示例代码
   - 记录常见的 markdown 格式变体

3. **工具化**（可选）：
   - 封装文件提取逻辑为独立函数
   - 自动检测使用哪种方法

---

**修改人**：Claude
**修改日期**：2026-08-13
**验证状态**：已通过理论验证，待实际使用验证
