# BuildHealth Frontend

**Phase 6B / v1.1.0** · React 18 + TypeScript + Vite 5 + Tailwind 3
+ ECharts 5 + React Router 6

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
│   ├── pages/           # 8 个页面(Dashboard / Buildings / BuildingDetail
│   │                    # / Monitoring / RiskHealth / RetrofitDecision
│   │                    # / AIAssistant / DataSettings)
│   ├── components/      # 通用组件 + charts/ 子目录(4 个 ECharts)
│   ├── api/             # axios client + endpoint 封装
│   ├── types/           # TypeScript 类型(后端 Pydantic 镜像,含
│   │                    # AIProviderType 等)
│   ├── hooks/           # 自定义 Hooks(useApi 等)
│   ├── App.tsx          # 路由配置(9 条 Route)
│   ├── main.tsx         # 入口
│   ├── test/            # vitest setup(jsdom + @testing-library/jest-dom)
│   └── index.css        # Tailwind base
├── tests/               # 15 个 vitest 测试文件(97 用例)
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json        # include = src + tests (2026-10-16 起)
├── tsconfig.node.json   # 仅 vite.config.ts
└── eslint.config.js     # eslint 9 flat config(2026-10-16 起)
├── public/
├── package.json
├── vite.config.ts
├── tailwind.config.js
└── tsconfig.json
```

## 当前状态(Phase 6B · v1.1.0)

- ✅ Vite + React 18 + TypeScript 5 脚手架
- ✅ Tailwind CSS 3 配置(工程仪表盘主题色)
- ✅ React Router 6 + 9 条路由
- ✅ Axios client + 与后端 API 联通
- ✅ TypeScript 类型定义(与 Pydantic 对应,0 errors 覆盖 src/ + tests/)
- ✅ 4 个 ECharts 图表组件(BhiRadar / TrendChart / DistributionPie +
  echarts 共用工具)
- ✅ 15 个 vitest 测试文件 / 97 用例全过
- ✅ `npm run lint` 退出 0(eslint 9 + react-hooks + no-console)

详见 `../docs/03_System_Architecture.md` · `../docs/28_Project_Fact_Sheet.md` §18–§20。
