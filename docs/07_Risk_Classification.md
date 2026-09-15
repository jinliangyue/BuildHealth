# 07 · 风险分级（Risk Classification）

## 1. 分级体系（Prototype Risk Classification v0.1）

| BHI 范围 | 风险等级 | 颜色 | 含义 |
|---|---|---|---|
| 90–100 | **Normal** | 绿色 | 综合状态正常，无需特别关注 |
| 75–89  | **Attention** | 黄色 | 存在需要关注的指标，建议巡检 |
| 60–74  | **Abnormal** | 橙色 | 存在异常，建议安排专业评估 |
| 0–59   | **High Risk** | 红色 | 综合健康度严重偏低，建议立即专业检测 |

**强制声明**：

> 本分级为 Prototype Risk Classification，**非法定建筑安全等级**。
> 系统**不得**用于预测建筑倒塌、替代专业结构检测、替代安全鉴定、自动完成结构加固设计。
> 风险结果仅作为辅助评估 / 数字化演示 / 工程决策支持。

## 2. 判定算法

```python
def classify_risk(bhi: float, anomalies: list[Anomaly]) -> dict:
    if bhi >= 90:
        level = "Normal"
    elif bhi >= 75:
        level = "Attention"
    elif bhi >= 60:
        level = "Abnormal"
    else:
        level = "HighRisk"

    # 高严重度异常数
    high_count = sum(1 for a in anomalies if a.severity == Severity.HIGH)
    medium_count = sum(1 for a in anomalies if a.severity == Severity.MEDIUM)

    # 优先级覆盖：即使 BHI 尚可，若有 HIGH 异常且涉及结构/裂缝，至少 Attention
    if level == "Normal" and high_count > 0:
        level = "Attention"

    # 顶层原因
    if high_count > 0:
        top_reason = f"检测到 {high_count} 条 HIGH 级异常，建议优先排查"
    elif bhi < 60:
        top_reason = f"BHI 仅 {bhi:.1f}，综合健康度严重偏低"
    elif bhi < 75:
        top_reason = f"BHI {bhi:.1f}，多项指标低于正常水平"
    elif medium_count > 0:
        top_reason = f"存在 {medium_count} 条 MEDIUM 级异常，建议关注"
    else:
        top_reason = "监测数据基本正常"

    return {
        "risk_level": level,
        "bhi_at_alert": bhi,
        "top_reason": top_reason,
    }
```

## 3. 风险预警生命周期

```
[初始无预警]
    ↓ 评估完成
[RiskAlert 创建 · is_active=True]
    ↓ 7 天后重新评估
[若等级变化]
    ├─ 升级 → 新建 RiskAlert，旧记录 is_active=False
    └─ 维持 → 不新建，仅更新评估记录
[若等级降至 Normal]
    └─ 旧 RiskAlert.is_active=False（保留历史）
```

## 4. UI 展示规范

### 4.1 Risk & Health 页面

- Top 区域：4 个统计卡片（每档数量）
- 中部：风险列表（按 BHI 升序）
- 底部：单建筑雷达图 + 历史趋势

### 4.2 Building Detail 页面

- Header 显示当前风险等级徽章 + 颜色
- 紧邻徽章下方显示免责提示（小字）

### 4.3 颜色规范

| 等级 | Hex | Tailwind class |
|---|---|---|
| Normal | #10B981 | `bg-emerald-500` |
| Attention | #F59E0B | `bg-amber-500` |
| Abnormal | #F97316 | `bg-orange-500` |
| HighRisk | #EF4444 | `bg-red-500` |

## 5. 禁止事项（强约束）

1. ❌ 不得在任何位置写"建筑即将倒塌""结构即将失稳"等表述
2. ❌ 不得使用"危险""危急"等情绪化词汇（除非直接引用专业报告）
3. ❌ 不得在 Dashboard 主屏显示"建议立即撤离"
4. ❌ 不得将风险等级输出为 API 唯一字段，必须同时返回 BHI + 异常计数
5. ❌ 不得省略免责声明

## 6. 当前状态

**Phase 0** — 设计完成

- ✅ 4 档分级 + 算法已设计
- ✅ UI 颜色规范已规划
- ✅ 强约束清单已编写
- ⏳ 实际代码未实现

---

**文档版本**：v0.1 · Phase 0 起草
**最后更新**：2026-09-15
**状态**：Designed but not implemented
