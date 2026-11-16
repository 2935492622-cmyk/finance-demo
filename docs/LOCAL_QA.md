# 本地浏览器验证环境

应用运行不依赖浏览器自动化；本文件说明 QA 截图和交互验证使用的项目内工具。不会安装 Codex CLI、多 Agent 框架或系统级项目依赖。

## 当前实测

本机已有 Chromium 缓存，但启动时报 `libnspr4.so` 缺失。进一步检查发现缺少 NSS 和 ALSA 运行库。主 Agent 仅下载 Ubuntu 的 `libnspr4`、`libnss3`、`libasound2t64` 软件包，将内容解包到 `.tools/browser-runtime/root/`，没有使用 sudo 或系统安装命令。

给浏览器进程提供项目内库路径后，`--version` 实测返回 Chrome for Testing 156.0.8078.4，`ldd` 不再列出缺失动态库。该结果只证明浏览器具备启动前提；页面检查和截图结果由 QA 另行记录。

Playwright 驱动作为前端开发依赖安装在 `frontend/node_modules/`。现有浏览器只读复用，不更改其缓存。`.tools/`、前端 npm 缓存和 node_modules 已加入 Git 忽略规则。

## 恢复方式

Ubuntu 相同环境下，必要时在项目根目录执行：

```bash
mkdir -p .tools/browser-runtime/packages .tools/browser-runtime/root
cd .tools/browser-runtime/packages
apt download libnspr4 libnss3 libasound2t64
cd ../../..
for package in .tools/browser-runtime/packages/*.deb; do
  dpkg-deb -x "$package" .tools/browser-runtime/root
done
```

这些命令只下载和解包文件，不更改系统已安装软件。其他系统应使用其已有浏览器与对应运行库，不照搬 Ubuntu 软件包。不要使用 `playwright install-deps` 进行全局安装。

如果需要重新下载浏览器，指定项目内下载目录：

```bash
PLAYWRIGHT_BROWSERS_PATH="$PWD/.tools/ms-playwright" frontend/node_modules/.bin/playwright install chromium
```

本次未执行浏览器下载，直接复用已有文件：

```text
/home/ava/.cache/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-linux64/chrome-headless-shell
```

QA 脚本应接受浏览器可执行文件路径和附加动态库路径，具体执行命令以 `tests/README.md` 为准。测试时由主 Agent 统一启动 8000 后端和 5173 前端，避免多个角色同时占用同一端口；结束后只停止本项目拥有的进程，不动共享 MySQL。

截图须记录当时的真实数据库状态。数据库未连接时的错误状态截图不能作为成功新增、统计或持久化验收证据。
