# 实时大屏前端

要求 Node.js 22.12 或更高版本，依赖版本由 `package-lock.json` 固定。

```powershell
npm ci
npm run build
```

构建结果写入 `dist/`。本地开发使用：

```powershell
npm run dev
```

在项目根目录也可以直接运行 `just frontend-console` 或 `just frontend-console-ui`，命令会先按锁文件安装依赖。
