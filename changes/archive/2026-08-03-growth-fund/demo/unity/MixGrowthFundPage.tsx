import React from 'react';

/**
 * 成长基金主面板 Prefab
 * 对应 C# 脚本：MixGrowthFundPage.cs (继承 BaseActivityPage)
 *
 * 字段绑定清单（共 5 个字段，包含嵌套组件的字段）：
 * - m_TxtTitle: TextMeshProUGUI
 * - m_TxtPrice: TextMeshProUGUI
 * - m_BtnPurchase: Button
 * - m_TxtBtnPurchase: TextMeshProUGUI
 * - m_ScrollRewards: SingleScrollView (使用 onCellUpdate 回调模式，cellTemplate 自动管理)
 *   - cellTemplate: MixGrowthFundRewardTierRow (嵌套组件，包含 4 个字段)
 *     - m_TxtCondition: TextMeshProUGUI
 *     - m_ConditionBar: LRProgressBar
 *     - m_FreeCell: MixGrowthFundRewardCell (嵌套组件，包含 4 个字段)
 *       - m_ImgIconRoot: Transform (运行时调用 ItemIconBase.Allocate)
 *       - m_LockBadge: GameObject
 *       - m_RedPoint: GameObject
 *       - m_ClaimedMask: GameObject
 *     - m_PayCell: MixGrowthFundRewardCell (同上)
 *
 * 使用模式：
 * - OnCreateUI(): 设置 m_ScrollRewards.onCellUpdate = OnRewardCellUpdate
 * - 刷新数据: m_ScrollRewards.Refresh(count)
 * - 回调里: OnRewardCellUpdate(Transform root, int index) 配置每个 cell
 */

export default function MixGrowthFundPage() {
  return (
    <div
      data-name="MixGrowthFundPage"
      data-component="surface.panel"
      data-pos="(0, 0, 0)"
      data-size="(1920, 1080)"
      data-anchors="(0.5, 0.5, 0.5, 0.5)"
      data-pivot="(0.5, 0.5)"
    >
      {/* 顶部区域 */}
      <div
        data-name="Header"
        data-pos="(0, 440, 0)"
        data-size="(900, 100)"
        data-anchors="(0.5, 0.5, 0.5, 0.5)"
        data-pivot="(0.5, 0.5)"
      >
        {/* 基金标题 */}
        <span
          data-name="TxtTitle"
          data-component="text.localized"
          data-field="m_TxtTitle"
          data-lr-style="title"
          data-text="成长基金"
          data-text-align="Left"
          data-pos="(-300, 20, 0)"
          data-size="(300, 40)"
          data-anchors="(0.5, 0.5, 0.5, 0.5)"
          data-pivot="(0, 0.5)"
        >
          成长基金
        </span>

        {/* 描述文本（对应 m_MenuData.desc） */}
        <span
          data-name="TxtDesc"
          data-component="text.localized"
          data-field="m_TxtDesc"
          data-text="活动描述"
          data-text-align="Left"
          data-pos="(-300, -20, 0)"
          data-size="(200, 30)"
          data-anchors="(0.5, 0.5, 0.5, 0.5)"
          data-pivot="(0, 0.5)"
        >
          活动描述
        </span>

        {/* 购买按钮 */}
        <button
          data-name="BtnPurchase"
          data-component="control.button"
          data-field="m_BtnPurchase"
          data-pos="(250, 0, 0)"
          data-size="(200, 80)"
          data-anchors="(0.5, 0.5, 0.5, 0.5)"
          data-pivot="(0.5, 0.5)"
        >
          <span
            data-name="TxtBtnPurchase"
            data-component="text.localized"
            data-field="m_TxtBtnPurchase"
            data-text="购买"
            data-text-align="Center"
            data-pos="(0, 0, 0)"
            data-size="(200, 80)"
            data-anchors="(0.5, 0.5, 0.5, 0.5)"
            data-pivot="(0.5, 0.5)"
          >
            购买
          </span>
        </button>
      </div>

      {/* 奖励列表区域：list.single-scroll 由生成器的 postProcess 钩子自动创建
          Viewport/Content/Scrollbar 层级，这里只需引用 Viewport/Content 挂载
          cellTemplate。C# 侧用 SingleScrollView.cellTemplate + onCellUpdate
          回调管理复用，Page 脚本上不存在 m_RewardListContent 字段。 */}
      <div
        data-name="ScrollRewards"
        data-component="list.single-scroll"
        data-field="m_ScrollRewards"
        data-pos="(0, -50, 0)"
        data-size="(900, 700)"
        data-anchors="(0.5, 0.5, 0.5, 0.5)"
        data-pivot="(0.5, 0.5)"
      >
        <div data-prefab-child-path="Viewport/Content" data-name="Content">
          {/* 奖励行模板 (MixGrowthFundRewardTierRow) - SingleScrollView.cellTemplate，
              运行时按需 Instantiate 复用，模板自身在层级里保持 inactive。
              data-lr-component 开启新作用域：此节点自身没有 data-field（Page 脚本上
              没有对应字段，cellTemplate 由生成器的 ConfigureSingleScrollView 钩子
              自动发现并赋值），但其子树内的 data-field（m_TxtCondition 等）绑定到
              这个 Row 组件实例。 */}
          <div
            data-name="RewardRowTemplate"
            data-component="surface.page"
            data-lr-component="LR.MixGrowthFundRewardTierRow"
            data-pos="(444, -116.75, 0)"
            data-size="(860, 150)"
            data-anchors="(0, 1, 0, 1)"
            data-pivot="(0.5, 0.5)"
            data-visible="false"
          >
            {/* 条件进度列 */}
            <div
              data-name="ConditionColumn"
              data-pos="(150, 0, 0)"
              data-size="(200, 120)"
              data-anchors="(0, 0.5, 0, 0.5)"
              data-pivot="(0.5, 0.5)"
            >
              {/* 条件文本 */}
              <span
                data-name="TxtCondition"
                data-component="text.localized"
                data-field="m_TxtCondition"
                data-text="0/100"
                data-text-align="Center"
                data-pos="(0, 30, 0)"
                data-size="(200, 30)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
              >
                0/100
              </span>

              {/* 进度条 */}
              <div
                data-name="ConditionBar"
                data-component="control.progress"
                data-field="m_ConditionBar"
                data-pos="(0, -10, 0)"
                data-size="(180, 20)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
              />
            </div>

            {/* 免费奖励格子 (MixGrowthFundRewardCell) - 独立作用域，字段绑到这个 Cell 实例 */}
            <div
              data-name="FreeCell"
              data-component="surface.page"
              data-lr-component="LR.MixGrowthFundRewardCell"
              data-field="m_FreeCell"
              data-pos="(553.1, 0, 0)"
              data-size="(120, 120)"
              data-anchors="(0, 0.5, 0, 0.5)"
              data-pivot="(0.5, 0.5)"
            >
              <div
                data-name="ImgIconRoot"
                data-component="content.item-icon-root"
                data-field="m_ImgIconRoot"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-overlay="true"
              />

              <div
                data-name="LockBadge"
                data-component="content.icon"
                data-field="m_LockBadge"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />

              <div
                data-name="RedPoint"
                data-component="feedback.red-point"
                data-field="m_RedPoint"
                data-pos="(35, 35, 0)"
                data-size="(20, 20)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />

              <div
                data-name="ClaimedMask"
                data-component="content.icon"
                data-field="m_ClaimedMask"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />
            </div>

            {/* 投资奖励格子 (MixGrowthFundRewardCell) - 独立作用域，同名字段不与 FreeCell 冲突 */}
            <div
              data-name="PayCell"
              data-component="surface.page"
              data-lr-component="LR.MixGrowthFundRewardCell"
              data-field="m_PayCell"
              data-pos="(688.4, 0, 0)"
              data-size="(120, 120)"
              data-anchors="(0, 0.5, 0, 0.5)"
              data-pivot="(0.5, 0.5)"
            >
              <div
                data-name="ImgIconRoot"
                data-component="content.item-icon-root"
                data-field="m_ImgIconRoot"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-overlay="true"
              />

              <div
                data-name="LockBadge"
                data-component="content.icon"
                data-field="m_LockBadge"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />

              <div
                data-name="RedPoint"
                data-component="feedback.red-point"
                data-field="m_RedPoint"
                data-pos="(35, 35, 0)"
                data-size="(20, 20)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />

              <div
                data-name="ClaimedMask"
                data-component="content.icon"
                data-field="m_ClaimedMask"
                data-pos="(0, 0, 0)"
                data-size="(80, 80)"
                data-anchors="(0.5, 0.5, 0.5, 0.5)"
                data-pivot="(0.5, 0.5)"
                data-visible="false"
                data-overlay="true"
              />
            </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
