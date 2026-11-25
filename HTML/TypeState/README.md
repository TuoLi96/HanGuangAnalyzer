# TypeState Review Desk

这是一个仅绑定 `127.0.0.1` 的本地 patch / typestate 审核工作台，不需要安装前端依赖。

## 启动

需要 Node.js 18 或更高版本。如果系统没有 Node.js，可以在 PowerShell 中安装 LTS 版本：

```powershell
winget install OpenJS.NodeJS.LTS
```

安装完成后请重新打开 PowerShell，再运行：

```powershell
node server.js
```

然后打开 <http://127.0.0.1:8765>。

也可以双击 `start-local.bat` 启动。

## 功能

- 按 commit、文件、函数、Bug 类型搜索 patch；按待审核、正确、错误、已审核、已修改筛选。
- 选择 patch 后编辑 commit message、diff、版本信息、代码上下文和审核备注。
- 载入同 commit 的 `data/TSes/<commit>.json`；没有对应文件时显示空白，可直接新建。
- Typestate JSON 修改时实时解析，并同步刷新状态转移图。
- 点击“同步到本地”后，patch 回写到 `data/Patches/tasks.jsonl`，typestate 回写到对应的 `data/TSes/<commit>.json`。
- `Ctrl+S` 可执行同样的同步操作。

数据文件统一放在 `data/` 目录，并已加入 `.gitignore`。审核状态会以 `review_status` 字段写入 patch JSON；审核备注写入 `review_note` 字段，原始数据的其它字段会被保留。
