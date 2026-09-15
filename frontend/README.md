# BuildHealth Frontend

Phase 0 Skeleton · React 18 + TypeScript + Vite + Tailwind + ECharts

## 启动

```bash
npm install
npm run dev
```

启动后访问：

- `http://localhost:5173/` — 应用首页（Dashboard 占位）

后端 API 通过 Vite proxy 转发到 `http://localhost:8000`。

## 构建

```bash
npm run build
npm run preview
```

## 目录

```
frontend/
├── src/
│   ├── pages/           # 6 个页面（Phase 0 占位）
│   ├── components/      # 通用组件（Phase 1 实现）
│   ├── api/             # API client（Phase 0 占位）
│   ├── types/           # TypeScript 类型（与后端 Pydantic 对应）
│   ├── hooks/           # 自定义 Hooks
│   ├── App.tsx          # 路由配置
│   └── main.tsx         # 入口
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 当前状态（Phase 0）

- ✅ Vite + React 18 + TypeScript 脚手架
- ✅ Tailwind CSS 配置（含工程仪表盘主题色）
- ✅ React Router 6 配置 + 6 个页面占位
- ✅ Axios client 初始化
- ✅ TypeScript 类型定义（与 Pydantic 对应）
- ⏳ ECharts 图表组件未实现
- ⏳ 实际 API 调用未实现
- ⏳ 前端测试用例未编写

详见 `../docs/03_System_Architecture.md`。
