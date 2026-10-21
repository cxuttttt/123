# PocketAgent · U 盘随身编程智能体

把完整便携包解压到 U 盘，插到 Windows 10/11 的 64 位电脑，双击就能使用。
使用体验以 Codex、Claude Code 一类编程智能体为目标：读项目、改代码、执行命令、运行测试、
连续完成任务，并通过自己的模型 API 工作。

**智能体核心直接复用 [OpenCode](https://github.com/anomalyco/opencode)。**
不重新编写 agent 循环、文件编辑器、终端工具、模型客户端或 MCP 协议。
本项目只负责便携启动、运行环境整合、配置存储及实际集成检查。

## 下载与启动

从本仓库的 **Releases** 下载 `PocketAgent-windows-x64.zip`。
不要下载 GitHub 的 Source code ZIP；源码包不包含运行环境。

1. 把 ZIP **完整解压**到 U 盘，例如 `E:\PocketAgent`。
2. 双击 `PocketAgent.exe` 或 `Start.cmd`。
3. 在 OpenCode 里输入 `/connect`，选择 DeepSeek 或其他服务商，填写自己的 API 密钥。
4. 输入 `/models`，选择实际可用的模型，然后直接描述任务。

不需要管理员权限，不需要在目标电脑预先安装 Git、Node.js、Python、uv 或 OpenCode。
需要能访问模型 API 的网络。模型费用由所用服务商计费。

## 打开自己的项目

把项目文件夹拖到 `Start.cmd` 上，或者在终端运行：

```powershell
.\PocketAgent.exe --project "D:\我的项目"
```

默认工作目录是包内的 `workspaces\default`。如果项目也希望随身携带，可把项目放到
`workspaces` 中；只把智能体放在 U 盘，并不会把原电脑上的项目文件一起带走。

常用入口：

| 入口 | 用途 |
| --- | --- |
| `PocketAgent.exe` / `Start.cmd` | 启动原生 OpenCode 交互界面 |
| `Configure-API.cmd` | 使用上游的模型登录配置流程 |
| `Check.cmd` | 检查全部运行环境和配置路径 |
| `PocketAgent.exe --shell` | 打开已经配置好便携工具的命令行 |
| `PocketAgent.exe --project "路径" --continue` | 使用上游能力续接最近会话 |
| `PocketAgent.exe session list` | 列出已有会话 |

其他 OpenCode 命令也能直接透传，例如 `PocketAgent.exe --help`。
在交互界面中使用 `/help`、`/sessions`、`/models`、`/connect`。

## 模型与自定义 API

DeepSeek 等已有服务商优先通过 `/connect` 配置，无需手工填写模型名称。
支持的模型、接口及工具调用能力由上游 OpenCode 与具体服务商决定。

使用第三方 OpenAI 兼容接口时：

1. 参考 `defaults\providers.example.json`，编辑 `data\config\opencode\opencode.json`。
2. 填写真实的接口地址、服务商标识和模型 ID。
3. 在 `/connect` 中选择 Other，输入相同的服务商标识，再输入密钥。
4. 在 `/models` 里选择模型。

示例使用 `/v1/chat/completions`；需要 `/v1/responses` 的接口应把 `npm` 改为
`@ai-sdk/openai`。不要把密钥写进项目源码并推送 GitHub。

## 随身保存的内容

| 路径 | 内容 |
| --- | --- |
| `data\config\opencode` | OpenCode 配置、全局提示及自定义能力 |
| `data\share\opencode` | 上游 API 凭据、会话数据库、日志等 |
| `data\cache`、`data\state` | 工具缓存与状态 |
| `data\gitconfig` | 随身 Git 配置；不覆盖宿主机的 Git 配置 |
| `workspaces` | 希望随身携带的项目 |

所有路径在每次启动时按实际位置解析，不写死 U 盘盘符。
`data` 不随发布包分发，也不会提交到 GitHub。凭据沿用 OpenCode 的本地存储方式，
并非加密保险箱；持有 U 盘的人也可能读取其中的密钥。

退出智能体并关闭相关终端后，再安全弹出 U 盘，避免正在写入的数据库受损。
不承诺 Windows 缓存、崩溃报告和模型服务端不留下记录。

## 已整合的上游能力

- OpenCode：任务推理、文件搜索与修改、工具执行、会话、权限交互、MCP 扩展。
- PortableGit：Git 与 Bash，不依赖宿主机安装 Git。
- Node.js + npm/npx：运行 JavaScript 项目及基于 Node 的扩展。
- Python + uv：运行 Python 脚本及管理项目依赖。
- ripgrep：本地搜索，首次搜索也不用额外下载。

扩展使用 OpenCode 原生的 skills、plugins 和 MCP 配置，不维护另一套工具体系。
Java、.NET SDK、Rust、CUDA 等完整开发工具链没有全部打包；需要时按项目另行配置。

## 验证范围

Windows 构建会检查：原始依赖 SHA256、原生启动器编译、所有运行环境、中文与空格路径、
两种盘符下的路径解析、真实 OpenCode 的文件读取/修改/执行工具以及持久化会话。
测试结果和日志随 Actions 构建产物保存。测试使用本地合成 API，避免把个人密钥放入 CI；
它验证实际工具链，不代表已用每家真实模型完成任务。

目标系统是常见 Windows 10/11 x64。企业管控、禁止执行外部程序、只读 U 盘、异常旧版系统，
以及宿主机缺少的项目专用工具链，不在“插入即用”的保证范围内。
尚未通过的测试不能作为已验证能力宣传。

## 从源码构建

在 Windows 上准备 Python 3.13+ 和 7-Zip，运行：

```powershell
python scripts/build.py
powershell -NoProfile -ExecutionPolicy Bypass -File tests/windows-smoke.ps1 -Bundle dist/PocketAgent
python tests/agent_roundtrip.py --launcher dist/PocketAgent/PocketAgent.exe
```

GitHub Actions 会在干净的 Windows Runner 上构建和检查，通过后发布便携 ZIP。
依赖版本及 SHA256 固定于 `upstream.lock.json`；不会在目标电脑上临时下载整套运行环境。

## 许可证

本项目新增的整合代码使用 MIT。上游组件分别保持原许可证，见 `THIRD_PARTY.md`。
