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
