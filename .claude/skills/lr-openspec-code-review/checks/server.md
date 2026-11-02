# 服务端检查项（server 组，共 4 项）

> **SE 适配说明**：GodFort/神域防线及其返工频次是 DL 来源案例，不是 SE 当前文件或接口的证据。实际审查先读 SE `config.yaml` 路由的 ai-core，再用 SE CodeGraph/源码复验；来源案例和缺失的历史附件仅作说明，不作为必读依赖或通过依据。


> 由 `lr-openspec-code-review` 步骤 3 读取，只对本轮改动的服务端文件执行。
> CodeGraph 的 `projectPath` 指向服务端工程根目录（默认 `../develop/server/project`，以 `implementation-report.md` 记录的实际路径为准）。
> 档位：**P0 阻断（权重 10）** / **P1 结构契约（权重 5）** / **P2 质量建议（权重 1）**。
> 报告排序：先档位，同档按 GodFort 实证频次降序。

---

## 0. 完整性前置

用模块名查询代码，确认模块存在：

```
codegraph_explore("<模块名> OnCustom LoadResource", projectPath: "<服务端工程>")
```

- **找不到** -> 报告“缺失实施：预期有服务端 <模块名>，但搜索不到”，跳过本组质量检查。
- **找到了** -> 继续执行 server-001 ~ server-004。

---

## server-001 协议契约完整性（P0 / 权重 10 / GodFort 实证 2）

**目标**：同时成立四件事。

1. **C2S 索引起点**：处理函数从 `args.IntVal(1)` 开始解析业务参数；`args.IntVal(0)` 是消息号。
2. **S2C 字段契约**：发送报文的业务字段个数、顺序、类型与 `protocol-contract.md` / `design/server.md` 一致；有可选尾字段时两端都按 `count` 分支，不假设固定字段数。
3. **两端协议 ID 集合一致**：`cons/msg/config/client_msg.xml（按 cons/msg/Config.json 与生成链复核）` + `define/ClientCustomDefine.h` 与客户端协议定义中的 ID 集合互不缺失。
4. **处理函数已注册**：处理函数在 `XxxModule::Init()` 中通过 `ADD_INT_CUSTOM_HOOK`（或该协议对应的框架宏）注册，且注册项未被后续同 ID 注册覆盖；只写函数不注册时协议永远进不了回调。

**为什么合并**：GodFort 实际发生的两次高危问题都不是 0/1 偏移——1834 在服务端登记后被整批更新覆盖（客户端仍发，链路断开）；51 成功包从 4 字段变 5 字段（客户端 `count != 5` 直接丢弃结算包）。只查起始索引会把这两类全部漏掉。

**检查方法**：

```bash
# 1) 两端协议 ID 集合
rg -n "<协议ID>|<协议名>" "<已定位的协议源XML>" "<服务端工程>/define/ClientCustomDefine.h"
rg -n "<协议ID>|<协议名>" "<已定位的客户端协议定义文件>"

# 2) C2S 起始索引
codegraph_explore("OnCustom args.IntVal <模块名>", projectPath: "<服务端工程>")

# 3) S2C 字段数 / 类型 / 可选尾
codegraph_explore("SendMsg VarList <模块名>", projectPath: "<服务端工程>")

# 4) 处理函数注册
rg -n "ADD_INT_CUSTOM_HOOK|<协议名>" <服务端模块>.cpp <服务端模块>.h
```

逐协议先对照本变更 `design.md` 附录 A/B 的字段表；若另有 `protocol-contract.md` 也一起核对。缺少契约文档时，以客户端解析代码为准反推，并在报告里注明“无契约文档，按客户端解析反推”。

**违反示例**：

```cpp
int OnCustomGetReward(..., const IVarList& args) {
    int activityID = args.IntVal(0);  // 错误：0 是消息号，业务从 1 开始
}

// 51 成功包固定 4 字段；客户端已按 5 字段（含 hubHpPercent）解析
vSend.Add(hubHpPercent);  // 服务端多发，但契约文档仍写 4 字段
```

**符合示例**：

```cpp
int activityID = args.IntVal(1);
int tierIndex  = args.IntVal(2);
```

**豁免**：

- `args.IntVal(0)` 明确用于读取消息号本身，且代码有注释；
- 纯透传/引擎封装协议，字段表由引擎保证。

**报告格式**：

```
❌ server-001: 协议契约不一致
类型: S2C 字段数漂移 / 两端协议 ID 不一致 / C2S 索引起点错误
位置: <文件:行号>
契约: protocol-contract.md §X（写 N 字段）
实际: 发送 M 字段
影响: 客户端按 N 解析，第 N+1 个字段起错位 / 直接丢弃报文
建议: <补 count 分支 / 补登记 / 改索引>
```

---

## server-002 错误反馈完整性（P1 / 权重 5 / GodFort 实证 1）

**目标**：业务失败（资金不足、CD、上限、满级、资格不满足）必须让客户端能区分原因，不能只写日志或统一返回 `ERR_COMMON_FAIL`。

**检查方法**：

```
codegraph_explore("OnCustom return ERR_ <模块名>", projectPath: "<服务端工程>")
```

```bash
rg -n "ERR_COMMON_FAIL|LogError|LogWarning" <本次改动的服务端文件>
```

逐条失败分支判断：

- 返回可区分错误码，或调用通用错误提示接口（如 `CustomCommonErrorSysInfo`）-> 通过；
- 只打日志 + 统一 `ERR_COMMON_FAIL` -> 违反；
- 内部一致性错误、防御性分支（不可能发生）-> 豁免。

**说明**：原“`return 0;` 占比 > 80% 即符合模式 1”的统计规则已删除。GodFort 实测 0 命中，且它会把“业务失败无提示”判为通过。

**违反示例**：

```cpp
if (cost > player->GetGold()) {
    LogError("gold not enough");   // 错误：客户端拿不到原因
    return ERR_COMMON_FAIL;
}
```

**符合示例**：

```cpp
if (cost > player->GetGold()) {
    return SendCommonError(player, ERR_GOLD_NOT_ENOUGH);
}
```

**报告格式**：

```
⚠️ server-002: 业务失败缺少可区分反馈
位置: <文件:行号>
分支: 资金不足 / CD / 上限 / 满级 / 资格
现状: 仅 LogError + ERR_COMMON_FAIL
建议: 映射到通用错误码或错误提示接口
```

---

## server-003 配置字段名与列结构（P0 / 权重 10 / GodFort 实证 ≥3）

**目标**：`txt.ReadInt/ReadString` 的字段名与**实际导出 txt 的表头**完全一致（大小写、下划线）；Record 列数与 `cons/res/struct/*.xml`、`*Define.h` 枚举一致。

**基准顺序（重要）**：

1. 实际导出 txt 表头（权威）；
2. 服务端 `LoadResource` / `READ_FILE` 代码；
3. `design/config.md`（只用于确认意图，不能作为唯一基准——GodFort 的设计文档已多次过期）。

**检查方法**：

```bash
# 定位实际导出表
rg -n "^.*" cons/res/ini/<模块>/*.txt | head -5
# 对照加载代码
codegraph_explore("LoadResource READ_FILE txt.ReadInt <模块名>", projectPath: "<服务端工程>")
```

逐字段核对：字段名拼写、大小写、是否有设计写了但 txt 没有的列、是否有 txt 有但设计漏掉的列。

**违反示例**：

- Excel/txt 列名 `recharge_id`，代码写 `txt.ReadInt(i, "RechargeId")` -> 解析为空；
- 设计有 `TalentPoints`，代码读取，但 `design/config.md` 的字段表没有该列 -> 设计缺列；
- 设计写 `UnlockSkill`，实际导出 txt 头是 `UnlockBuff` -> 设计字段名错误。

**报告格式**：

```
❌ server-003: 配置字段/列结构不一致
表: <表名>
位置: <文件:行号>
实际表头: <字段列表>
代码读取: <字段名>
建议: <以实际 txt 为准修正代码 / 修正设计文档>
```

---

## server-004 Record 访问保护与结构（P0 / 权重 10 / GodFort 实证 0 违规，但有 6→7 列漂移）

**目标**：

1. `GetRecord` / `FindRecord` 之后必须判存在。本项目实际风格是 `IRecord& + rec.Exist()`，不是指针判空。
2. 列索引必须使用 `*Define.h` 中的具名枚举，不写裸数字。
3. 列数与 `cons/res/struct/*.xml` 的 `cols` 一致；新增列时同步更新枚举。

**检查方法**：

```
codegraph_explore("GetRecord FindRecord Exist <模块名>", projectPath: "<服务端工程>")
```

```bash
rg -n "QueryInt\([^,]+,\s*[0-9]+" <本次改动的服务端文件>
rg -n "cols=\"" cons/res/struct/<模块>.xml
```

**违反示例**：

```cpp
IRecord& rec = m_Kernel.GetRecord(player, GOD_FORT_LEVEL_REC);
int level = rec.QueryInt(0, 3);   // 错误：裸列索引；且未判 Exist()

// 结构 7 列，枚举仍按 6 列定义
```

**符合示例**：

```cpp
IRecord& rec = m_Kernel.GetRecord(player, GOD_FORT_LEVEL_REC);
if (!rec.Exist()) {
    return ERR_RECORD_NOT_FOUND;
}
int level = rec.QueryInt(0, GOD_FORT_LEVEL_REC_LEVEL);
```

**豁免**：同一函数内上方已判 `Exist()` 且中间无重新获取；引擎保证非空的内置 Record（需注释说明）。

**报告格式**：

```
❌ server-004: Record 访问未保护 / 列结构漂移
位置: <文件:行号>
问题: 未判 Exist() / 裸列索引 / 枚举列数 6 与实际 7 不符
建议: <补 Exist / 改用枚举 / 更新 define 与 struct>
```
