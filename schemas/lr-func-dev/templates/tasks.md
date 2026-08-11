# Tasks: {变更名}

## 1. Contract 定义

- [ ] 1.1 [Contract] 分配协议号
  - REQ_XXX_YYY = {协议号}
  - RES_XXX_YYY = {协议号}

- [ ] 1.2 [Contract] 定义协议字段
  message ReqXxxYyy { ... }
  message ResXxxYyy { ... }

- [ ] 1.3 [Contract] 定义错误码
  - XXX_ERR_CODE = 值: 说明

## 2. 配置表

- [ ] 2.1 [Config] 新增 {TABLE_NAME}.xlsx
  字段：{字段清单}
  目标路径：../design/table/default_ios/activity/{table_name}.xlsx

## 3. 服务端实现

依赖：[Contract] + [Config] 完成

### 3.0 服务端架构设计

> 说明：本节先于具体任务确定文件拆分与接入点，避免新业务线全部塞进已有大文件。参考 `rules/tasks/server-implementation.md` 的"零、服务端架构设计强制要求"。

#### 3.0.1 模块与文件组织
[列出本次涉及的模块名、现有文件是否复用/需要拆分新文件，参考同类模块（如 MixGrowthFundModule）的文件拆分粒度]

#### 3.0.2 Hook 注册清单
[列出本次需要注册的 Hook 类型：AddCustomHook / AddNotifyHook / AddRefreshHook / RegisterDisposeFunc / RegistOnlineToDealOfflineFunc 等，及各自用途]

#### 3.0.3 业务线拆分决策
[如果一个模块要承载多条业务线（如本例：日常领取 + 套餐 + 赠送），说明每条业务线对应哪些函数/文件，是否需要拆出独立 .cpp]

---

- [ ] 3.1 [Server] 新增 {TABLE_NAME}_REC 表
  目标路径：FsGame/{Module}/{Module}Define.h
  对应验收：TC-xxx-01

- [ ] 3.2 [Server] 实现配置表加载
  目标路径：FsGame/{Module}/{Module}EventCallBack.cpp
  对应验收：TC-xxx-02

- [ ] 3.3 [Server] 实现业务逻辑
  目标路径：FsGame/{Module}/{Module}Func.cpp
  对应验收：TC-xxx-03

## 4. 客户端实现

依赖：[Contract] 完成

### 4.0 前端架构设计

> 说明：本节先于具体任务确定模块分层与数据流，避免所有逻辑堆进单一类。参考 `rules/tasks/client-implementation.md` 的"一点五、前端架构设计强制要求"，架构依据来自客户端知识库 `project_rag/index.md`（运营活动条目）。

#### 4.0.1 模块分层与职责
[列出 Module（数据层）/ Page（视图控制器）/ Cell（可复用组件）各自的职责与"不做什么"]

#### 4.0.2 数据流设计
[画出 Server Record 更新 → Module 缓存/通知 → Page 订阅 → Cell 刷新 的完整链路]

#### 4.0.3 状态管理策略
[说明单一数据源在哪一层、缓存位置、刷新机制（事件驱动/其他）]

#### 4.0.4 关键设计决策
| 决策点 | 方案 | 理由 |
|-------|------|------|
| Record 监听位置 | | |
| 数据缓存位置 | | |
| 协议发送位置 | | |
| 红点计算时机 | | |

#### 4.0.5 文件组织
[列出 Module/Page 目录下的文件清单及各自职责]

---

- [ ] 4.1 [Client] 生成 {Module}Module.cs 骨架
  目标路径：Assets/Script/LogicModule/{Module}Module/{Module}Module.cs

- [ ] 4.2 [Client] 实现模块逻辑
  目标路径：Assets/Script/LogicModule/{Module}Module/{Module}Module.cs
  对应验收：TC-xxx-04

- [ ] 4.3 [Client] 生成 {Panel}.cs 骨架
  目标路径：Assets/Script/UIScript/{Panel}/{Panel}.cs

- [ ] 4.4 [Client] 实现 {Panel} 状态机与交互逻辑
  目标路径：Assets/Script/UIScript/{Panel}/{Panel}.cs
  对应验收：TC-xxx-05

- [ ] 4.5 [Client] 实现 {Panel} 协议收发
  目标路径：Assets/Script/UIScript/{Panel}/{Panel}.cs
  对应验收：TC-xxx-06

## 5. 跨端联调

依赖：[Server] + [Client] 全部完成

- [ ] 5.1 [Integration] 正常流程联调
  对应验收：TC-xxx-07

- [ ] 5.2 [Integration] 异常流程测试
  对应验收：TC-xxx-08
