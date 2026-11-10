# Mock 数据垫片

## 策略

**数据缺失时默认垫，垫完必须声明并清理。**

目的是在没有服务器数据/活动数据的情况下，仍然验证 UI 的渲染、状态和交互。它不是数据链路的验证手段。

---

## 三种“没有数据”要分开

| 情况 | 例子 | 处理 | 报告 |
|---|---|---|---|
| **A. 配置表为空/未导** | `player_cumulative_recharge` 返回 0 行 | 继续垫，继续验 UI | 单列 `precondition_gap`，注明是任务未执行还是环境未同步 |
| **B. 玩家数据为空** | 积分 0、没领过、没买过 | 正常垫 | 标 `mock` |
| **C. 功能未开放** | 等级不足、活动未开 | 垫解锁条件或走 GM | 标 `mock`，注明解锁链路未验证 |

A 不阻断 UI 验证，但 **change 级判定不能是 passed**；B/C 不构成缺陷。

---

## 数据 mock ≠ 入口注入

两件事要分开记录，报告里是两个字段：

| 字段 | 回答 | 取值 |
|---|---|---|
| `mock_level` | UI 看到的数据从哪来 | `real` / `gm` / `L3` / `L4` |
| `entry` | 面板是怎么被打开的 | `real` / `gm` / `synthetic_setactivity` / `injected_ui_open` |

数据全真、面板却是注入打开的，`entry_verified` 仍然是 false。

### 活动页入口的注入方式

活动页（继承 `BaseActivityPage`）需要 `m_MenuData` 才能渲染，直接 `ui-open` 会拿到空页面。按证明力选：

| 级别 | 做法 | 标注 |
|---|---|---|
| L0 | 真实点活动图标 | `entry=real` |
| L1 | `game-execute-gm-command` 打开 | `entry=gm` |
| L2 | 反射设 `m_MenuData` + 调 `OpenPageUI(args)` / 刷新方法 | `entry=synthetic_setactivity` |
| L3 | `ui-open` 强开 + 补字段 | `entry=injected_ui_open` |

### 红线：不要用 `SetActivity(...)` 注入

`BaseActivityPage.SetActivity(menuData, args)` 内部会：

```
gameObject.SetActive(true) → m_MenuData = menuData → OpenPageUI(args)
→ RecordRedPoint() → RequestActivityInfo()
```

`RecordRedPoint()` 在 `redType=LocationDay` 时会走 `LocalPlayerConfig.SetDictionary` **写本地存档**，违反本文件的四条红线。`RequestActivityInfo()` 还会发协议。

所以 L2 只做两步：

1. 反射写 `m_MenuData`
2. 调 `OpenPageUI(args)`（或面板自己的 `Refresh*` 方法）

### `m_Module` 不要重复注入

活动页在 `OnCreateUI()` 里通常已经执行 `m_Module = m_Kernel.GetModule<XxxModule>()`。只有确实读到 `null` 时才补注入，否则会覆盖成你自己 new 出来的实例，让后续刷新走到错误对象。

---

## 三个前提，缺一不垫

1. **读得懂数据结构**：从 C# 定义拿到每个字段的含义
2. **找得到注入点和刷新入口**：写哪个字段、调哪个方法才会真正重绘
3. **造得出合法数据**：ID、枚举、奖励串格式符合真实约定

任一不满足 → `blocked_precondition`，写明缺什么。**不允许垫不了就静默跳过。**

---

## 四步

### 1. 先写 mock plan（注入前）

```
目标面板：XxxPanel
数据来源：XxxModule.m_NodeList
结构：XxxData{...}
覆盖状态：Received ×2 / CanGet ×2 / Unreached ×2 / 特殊形态 ×1
刷新入口：module.RefreshStates() + panel.OnOpen(null)
入口级别：L2（反射 m_MenuData + OpenPageUI）
数值来源：design.md / demo data.ts / 配置表文件
```

### 2. 注入

按下面的优先级选手段。

### 3. 读回

注入后必须验证真的生效：

- 列表条数（SE ScrollView 用 `totalCount`，不要数子节点）
- 面板 Content 子节点数
- 关键文本/状态标记
- 截图

没生效就回到第 1 步重新识别来源，最多重试两轮。

### 4. 声明

报告里写：`data_source`、`mock_level`、`entry`、`entry_verified`、覆盖状态、未覆盖项。

---

## 注入优先级

| 级别 | 手段 | 证明力 | 标注 |
|---|---|---|---|
| 1 | 真实数据 | 最强 | `data_source=real` |
| 2 | GM 造数 | 接近真实链路 | `mock_level=gm` |
| 3 | Module 缓存注入（写 `List<T>`/Record/积分，再调模块刷新） | 证明 Module→UI | `mock_level=L3` |
| 4 | 面板私有字段注入 | 只证明渲染 | `mock_level=L4` |

能高不低。L3/L4 的结论只能写 `runtime_passed_mock`。

---

## 最小化

- 只造 TC 需要的状态，不造“完整数据集”
- 数值优先取真实来源（design.md、demo `data.ts`、配置表 txt）
- ID/枚举必须合法；凭空编会验到错误渲染路径

---

## 清理契约（必须执行）

### 注入前：快照

- 被改列表的原始内容（条数 + 每条 key 字段）
- 被改集合的完整拷贝（例如已领取奖励集合）
- 其他被改字段/开关（含 `m_MenuData`、`m_Module`）
- 快照放内存，不落文件

### 验证后：恢复 + 读回

- 还原快照（含把 `m_MenuData` 还原为 null、`m_Module` 还原为原实例）
- 调模块/面板刷新入口
- 读回比对：条数、集合内容、关键 UI 状态
- 恢复失败 → `cleanup=failed`，建议直接退出 Play

### 最终：退出 Play

最强清理手段，默认收尾。

### 报告：写清理状态

```
cleanup: restored | exited_play | failed
```

**注意**：“清空”不等于“恢复”。像已领取奖励集合这种真实玩家状态，必须快照原值再还原，不能直接 Clear。

---

## 四条红线

1. 只在本次 Play 内存里，不落库、不写 `PlayerPrefs` / `LocalPlayerConfig` / 本地存档
2. mock 模式下不触发写协议的操作（购买/领取/消耗）；只读请求可发，但失败不判缺陷
3. **不用 `SetActivity(...)` 注入活动页**（它会写本地红点并请求协议）
4. 改过的真实状态必须恢复；恢复不了就退 Play

---

## mock 下发现的异常要复核

| 判断 | 例子 | 结论 |
|---|---|---|
| 与 mock 无关 | 语言 key 未录入、按钮没绑、滚动方向错、组件类型错 | 确认缺陷，正常上报 |
| 与 mock 有关 | 文本值不对、数量不对、某状态没出现 | 标 `mock_suspected`，不算确认缺陷；换真实数据或另一套 mock 复核 |

---

## 局限声明（必须写进报告）

> mock 数据只能证明“UI 对给定数据的渲染与交互状态正确”，**不能证明**服务端 Record → Module → UI 的字段映射正确，也不能证明配置表解析正确。

> 通过 L2/L3 注入打开的面板，**不能证明真实入口链路可用**。

这两类验证仍留在联调/人工清单。
