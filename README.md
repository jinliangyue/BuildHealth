# BuildHealth

> 既有建筑健康监测与智能更新决策平台 · Existing Building Health Monitoring & Intelligent Retrofit Decision Platform

## 当前状态

**Phase 0 — Project Initialization & Architecture Design**

仅完成：

- 项目目录结构
- 文档骨架（9 份设计文档初稿）
- 后端骨架（FastAPI 健康检查可运行）
- 前端骨架（Vite + React + TypeScript 初始化完成）
- 数据库 Schema 设计与 ER 图
- API 架构设计
- Analytics / Health Assessment / Risk Classification 引擎设计
- 模拟数据生成器设计

**未实现**：

- 完整 V1 业务代码
- Dashboard / Buildings / Building Detail / Monitoring / Risk & Health 完整页面
- 异常检测算法完整实现
- 真实数据接入

详细路线图见 `docs/09_Version_Roadmap.md`。

## 启动

```bash
# 后端
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

## 文档

`docs/` 目录共 9 份设计文档：

- `01_Project_Overview.md` — 项目定位 + 范围 + 原则
- `02_Engineering_Requirements.md` — 工程真实性原则与红线
- `03_System_Architecture.md` — 整体架构图与模块边界
- `04_Data_Model.md` — 数据库 ER 结构
- `05_Analytics_Design.md` — 趋势分析 + 异常检测架构
- `06_Health_Assessment.md` — BHI 评分公式与版本化
- `07_Risk_Classification.md` — 风险分级与免责说明
- `08_Testing_Strategy.md` — 测试分层与最小集
- `09_Version_Roadmap.md` — Phase 0 → V1 → 未来

## 重要声明

- 本系统使用 **Prototype Design Parameters**（原型设计参数），**不是国家标准、行业标准或真实工程鉴定标准**。
- 所有数据均为 **Simulated Data**，**不来自任何真实小区或真实建筑**。
- 系统**不得**用于预测建筑倒塌、替代专业结构检测、替代安全鉴定、自动完成结构加固设计。
- 风险结果仅作为辅助评估 / 数字化演示 / 工程决策支持。

## 技术栈

- **Frontend**：React 18 + TypeScript + Vite + Tailwind CSS + ECharts
- **Backend**：Python 3.9 + FastAPI + SQLAlchemy + Pydantic
- **Database**：SQLite（开发期）
- **Data Analysis**：Pandas + NumPy + SciPy + scikit-learn（仅确有必要时）

## License

Private / Proprietary — 仅限十八个人项目使用。
