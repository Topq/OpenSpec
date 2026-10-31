---
name: lr-openspec-archive
description: 归档已完成的变更，合并 specs delta 到主规范，移动变更目录到 archive（封装 openspec archive 命令）
---

# lr-openspec-archive

> **职责**: 封装 `openspec archive` 命令，提供统一的归档入口，保持流程一致性。
> **阶段**: 阶段 12（最终阶段）
> **依赖**: 所有前置阶段完成（apply → reconcile → code-review → test-validate → rule-candidates）

---

## 使用场景

**适用于**：
- 变更已完成，所有任务已勾选
- 代码已提交/合并（如需要）
- 报告中的问题已修复或确认可接受

**归档操作**：
- 自动执行 validate（检查变更完整性）
- 合并 specs delta 到 `openspec/specs/`
- 移动变更目录到 `openspec/changes/archive/{日期}-{变更名}/`

---

## 使用方式

### 标准归档

```bash
/lr-openspec-archive growth-fund
```

等价于：
```bash
openspec archive growth-fund
```

---

### 跳过 specs 合并（工具/基础设施类变更）

```bash
/lr-openspec-archive growth-fund --skip-specs
```

等价于：
```bash
openspec archive growth-fund --skip-specs
```

---

### 跳过 validation（不推荐）

```bash
/lr-openspec-archive growth-fund --no-validate
```

等价于：
```bash
openspec archive growth-fund --no-validate
```

⚠️ **不推荐**：跳过 validation 可能导致不完整的变更被归档。

---

## 执行流程

### 步骤 1：执行归档命令

```bash
Bash(openspec archive {change-id} {options})
```

**命令选项**：
- 无选项：标准归档（validate + 合并 specs + 移动目录）
- `--skip-specs`：跳过 specs 合并（工具/文档类变更）
- `--no-validate`：跳过 validation（不推荐）
- `--yes`：跳过确认提示（自动化场景）

---

### 步骤 2：解析归档结果

**成功输出示例**：
```
✓ Validated change 'growth-fund'
✓ Merged specs delta to openspec/specs/
✓ Moved changes/growth-fund to changes/archive/2026-07-24-growth-fund/
✓ Change 'growth-fund' archived successfully
```

**失败输出示例**：
```
✗ Validation failed: 
  - design.md has unresolved Open Questions
  - tasks.md has 3 unchecked tasks

Run 'openspec validate growth-fund' for details.
```

---

### 步骤 3：输出归档报告

#### 成功情况

```
✅ 归档完成：growth-fund

📦 归档操作：
  ✅ Validation 通过
  ✅ Specs delta 已合并到 openspec/specs/
  ✅ 变更目录已移动到 changes/archive/2026-07-24-growth-fund/

📂 归档位置：
  openspec/changes/archive/2026-07-24-growth-fund/

📋 包含文件：
  - proposal.md
  - specs/（5 个 spec）
  - design.md + design/（3 个三端设计）
  - test-cases.md
  - tasks.md
  - reconcile-report.md（如果存在）
  - code-review-report.md
  - test-validate-report.md
  - rule-candidates.md
  - implementation-report.md

🎉 变更已成功归档，可以开始新的变更了！
```

---

#### 失败情况

```
❌ 归档失败：growth-fund

原因：Validation 未通过

详细错误：
  - design.md 存在未解决的 Open Questions（3 处）
  - tasks.md 存在未勾选任务（5 个）

📋 建议操作：
1. 运行 openspec validate growth-fund 查看详细问题
2. 解决所有 Open Questions
3. 完成所有必需任务（或标记为不适用）
4. 重新运行 /lr-openspec-archive growth-fund

⚠️ 如果确认可以忽略 validation，使用：
   /lr-openspec-archive growth-fund --no-validate
```

---

## 归档前检查清单（可选）

在执行归档前，可以手动确认：

### 必需检查

- [ ] 所有 tasks.md 任务已勾选（或标记为不适用）
- [ ] design.md 的 Open Questions 已解决（或标记为"已确认"）
- [ ] 代码已提交到 Git（如适用）

### 推荐检查

- [ ] reconcile-report.md 的差异已处理
- [ ] code-review-report.md 的高严重度问题已修复
- [ ] test-validate-report.md 的人工测试清单已执行
- [ ] rule-candidates.md 的勾选已回写到 config.yaml/schemas/

### 可选检查

- [ ] PR 已合并（如适用）
- [ ] 相关文档已更新（如 README、CHANGELOG）
- [ ] QA 已签字确认（如团队流程要求）

---

## 与原生命令的关系

| 场景 | 命令 |
|-----|------|
| SKILL 封装（推荐） | `/lr-openspec-archive growth-fund` |
| 原生命令（等价） | `openspec archive growth-fund` |

**SKILL 的额外价值**：
- 统一的命令前缀（`/lr-openspec-*`）
- 格式化的归档报告输出
- 失败时的建议操作提示

**原生命令的优势**：
- 更简短（少 `/lr-openspec-` 前缀）
- 支持更多选项（如 `--json`、`--store`）

---

## 常见问题

### Q1: 归档后能否撤销？

**A**: 归档操作**不可自动撤销**。如果需要恢复变更：
```bash
# 手动移回变更目录
mv openspec/changes/archive/2026-07-24-growth-fund openspec/changes/growth-fund

# 如果 specs 已合并，需要手动回滚 specs/
git revert <合并 specs 的 commit>
```

---

### Q2: 归档时 validation 失败怎么办？

**A**: 
1. 运行 `openspec validate growth-fund` 查看详细问题
2. 解决问题后重新归档
3. 如果确认可以忽略（如有意遗留 Open Questions），使用 `--no-validate`

---

### Q3: 工具类变更（不涉及 specs）如何归档？

**A**: 使用 `--skip-specs` 跳过 specs 合并：
```bash
/lr-openspec-archive build-script-update --skip-specs
```

---

### Q4: 归档后 changes/ 目录为空是正常的吗？

**A**: 是的。归档后变更目录会移动到 `changes/archive/`，`changes/` 下只剩下未归档的活跃变更。

---

### Q5: 归档操作是否需要 git commit？

**A**: `openspec archive` **不会自动 commit**。如果你希望归档操作进入版本控制：
```bash
/lr-openspec-archive growth-fund
git add openspec/specs/ openspec/changes/archive/
git commit -m "Archive: growth-fund"
```

---

## 版本信息

**版本**: v1.0  
**创建日期**: 2026-07-24  
**设计哲学**: 封装原生命令，保持流程统一性，不增加额外复杂度
