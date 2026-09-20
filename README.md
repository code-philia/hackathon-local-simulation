# ARC-Bench 本地模拟提交环境

这个目录用于让选手在本地完成一次与竞赛平台核心运行阶段一致的模拟提交：运行上传的智能体、部署智能体生成的应用，并可选择对 `http://127.0.0.1:3000` 执行 Playwright 测试。

它不模拟登录、数据库、排队、排行榜等网站功能。

## 1. 本地环境包包含什么

```text
hackathon-local-simulation/
├── public-exercise/
│   ├── requirements/
│   │   ├── requirements.yaml       # 机器可读需求，必须存在
│   │   ├── requirements.md         # 人类可读需求
│   │   └── reference/              # 图片、说明等公开参考资料
│   └── tests/
│       └── REQ-1.spec.ts           # 公开 Playwright 测试
├── Dockerfile                      # 本地竞赛镜像定义
├── build-image.sh                  # 构建并检查镜像
├── build-image.ps1                 # Windows PowerShell 构建脚本
├── local_submit.py                 # 组装 Workspace、运行容器、汇总结果
├── submit.sh                       # 模拟提交快捷入口
├── submit.ps1                      # Windows PowerShell 提交脚本
├── result.sh                       # 重新查看结果
├── result.ps1                      # Windows PowerShell 查看结果
└── env.example                     # 模型环境变量示例
```

### 1.1 公开练习题

包内的 `public-exercise` 是一个公开 Counter 练习：

- `requirements/` 是给智能体的完整需求文档目录；
- `requirements/reference/` 用于放置公开截图、样例数据和接口说明；
- `tests/` 是本地模拟评测使用的公开 Playwright 测试。

公开测试只用于本地调试。正式平台可以额外使用不随本地包发布的隐藏测试，最终成绩以正式提交为准。

### 1.2 竞赛环境 Docker

本地镜像直接使用平台统一 Runner 的 `run_submission.py`，复现：

- Agent 安装和运行；
- 应用输出目录；
- 固定技术栈启动或自定义 `deploy.sh` 启动；
- Playwright 版本、Chromium、目标 URL 和 Worker 数；
- 日志与 JSON report。

## 2. 如何执行一次模拟提交

### 2.1 安装前置环境

选手电脑需要：

- Linux、macOS，或支持 Linux containers 的 Docker Desktop；
- Docker Engine 24 或更高版本；
- Python 3.10 或更高版本；`local_submit.py` 只使用标准库。

Windows 用户需要：

- Windows 10/11；
- Docker Desktop，开启 Linux containers 和 WSL 2 backend；
- Python 3.10 或更高版本；
- PowerShell 5.1 或 PowerShell 7。

检查：

```bash
docker version
python3 --version
```

Windows PowerShell 使用：

```powershell
docker version
python --version
```

如果 PowerShell 禁止执行本地脚本，只需对当前窗口临时放行：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

脚本只通过 Docker Desktop 创建 Linux 容器，不要求在 Windows 主机上安装 Node.js、Playwright 或 Linux 工具链。

### 2.2 构建本地模拟竞赛镜像

基础 Runner 镜像由 ARC-Bench 网站仓库的 `backend/runner/Dockerfile` 构建，**那个仓库不在本仓库里**。用 `ARCBENCH_MONOREPO_ROOT` 指向你的 checkout：

```bash
chmod +x build-image.sh
ARCBENCH_MONOREPO_ROOT=/path/to/arc-bench-website ./build-image.sh
```

构建脚本会：

1. 使用 `$ARCBENCH_MONOREPO_ROOT/backend/runner/Dockerfile` 创建基础 Runner；
2. 执行 smoke test，确认 Python、Node.js、Git、Playwright 和 Chromium 可用；
3. 创建本地镜像：

   ```text
   arcbench-local-submit:latest
   ```

确认镜像：

```bash
docker image inspect arcbench-local-submit:latest
```

Windows PowerShell：

```powershell
.\build-image.ps1
docker image inspect arcbench-local-submit:latest
```

如果 Runner 基础镜像源码位于另一个本地 checkout：

```powershell
.\build-image.ps1 -MonorepoRoot 'D:\src\arc-bench-website'
```

或使用环境变量：

```powershell
$env:ARCBENCH_MONOREPO_ROOT = 'D:\src\arc-bench-website'
.\build-image.ps1
```

如果组织者提供了已构建的基础镜像，可以不安装主平台仓库：

```powershell
docker pull registry.example.com/arcbench/runner:v1
docker tag registry.example.com/arcbench/runner:v1 arcbench-runner:local-base
.\build-image.ps1
```

如果组织者已经发布镜像，选手可以直接拉取，并打上脚本期望的 tag，之后无需再设置 `ARCBENCH_MONOREPO_ROOT`：

```bash
docker pull registry.example.com/arcbench/local-submit:v1
docker tag  registry.example.com/arcbench/local-submit:v1 arcbench-runner:local-base
./build-image.sh
```

运行时也可以通过 `--image registry.example.com/arcbench/local-submit:v1` 直接指定已有镜像。

#### Apple Silicon（arm64）注意

`backend/runner/Dockerfile` 目前下载的是写死的 `linux-x64` Node.js 压缩包。在 arm64 主机上，Playwright 基础镜像会解析成 arm64，这个 x64 的 Node 无法执行，构建会在大约九分钟后失败：

```text
qemu-x86_64: Could not open '/lib64/ld-linux-x86-64.so.2'
```

`build-image.sh` 会在开始构建前就检测到这个组合并直接报错，而不是让你白等。两种解法：

```bash
# 1. 用模拟方式按 amd64 构建（当下可用，较慢）
ARCBENCH_LOCAL_PLATFORM=linux/amd64 \
ARCBENCH_MONOREPO_ROOT=/path/to/arc-bench-website ./build-image.sh

# 2. 把上游 Dockerfile 的 Node 下载改成架构自适应（原生，推荐）
#    使用 dpkg --print-architecture 在 x64 / arm64 之间分支
```

注意正式评测环境是 x86_64。在 arm64 上原生构建足以验证运行契约，但涉及原生模块（`sharp`、`canvas`、`better-sqlite3` 等）时行为可能与正式评测不同。

### 2.3 编写并打包自己的智能体

上传包的最小结构是：

```text
my-agent/
├── main.py
└── requirements.txt
```

`requirements.txt` 可以为空，但文件必须存在。智能体内部不一定用 Python 实现：`main.py` 可以调用 Node、Java、Shell 或其他已安装/由智能体安装的运行时。平台统一通过 Python 包装入口启动它。

`main.py` 必须接受：

```bash
python3 main.py <requirements_dir> --output-dir <output_dir>
```

含义：

- 第一个位置参数 `requirements_dir`：需求快照目录，包含 `requirements.yaml`、`reference/` 等；
- `--output-dir`：最终目标应用目录，智能体必须在这里生成或修改应用；
- 正常执行完成返回退出码 `0`；无法完成或运行异常返回非零。

示意入口：

```python
import argparse
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("requirements_dir")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    # 可以在这里直接实现智能体，也可以调用任何其他语言的程序。
    return subprocess.call([
        "node",
        "agent.js",
        args.requirements_dir,
        args.output_dir,
    ])


if __name__ == "__main__":
    raise SystemExit(main())
```

打包时必须让 `main.py` 和 `requirements.txt` 位于 ZIP 根目录：

```bash
cd /absolute/path/to/my-agent
zip -r ../my-agent.zip . \
  -x '.git/*' '.venv/*' 'node_modules/*' '__pycache__/*'
```

检查：

```bash
unzip -l ../my-agent.zip | head
```

Windows PowerShell：

```powershell
Set-Location 'D:\agents\my-agent'
Compress-Archive -Path .\main.py, .\requirements.txt -DestinationPath ..\my-agent.zip -Force
```

`Compress-Archive` 的参数直接列出文件，确保 `main.py` 和 `requirements.txt` 位于 ZIP 根目录，而不是包在额外的目录层级中。检查 ZIP 时可以使用：

```powershell
tar -tf ..\my-agent.zip
```

### 2.4 准备模型环境变量

```bash
cp env.example .env
chmod 600 .env
```

Windows PowerShell：

```powershell
Copy-Item .\env.example .\.env
```

`.env` 只由 Docker 读取，不要提交或发送给其他人。可以用记事本或 VS Code 编辑它。

填写智能体需要的配置：

```dotenv
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-provider.example/v1
MODEL=your-model
VISUAL_API_KEY=your-key
VISUAL_BASE_URL=https://your-provider.example/v1
VISUAL_MODEL=deepseek-v4-flash-vision-exp
```

`.env` 已被 Git 忽略。不要把密钥放进 Agent ZIP。

### 2.5 启动本地模拟竞赛环境

显式指定 Agent ZIP、需求目录、测试目录和本机输出目录：

```bash
./submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --requirements-dir "$PWD/public-exercise/requirements" \
  --tests-dir "$PWD/public-exercise/tests" \
  --output-dir "$PWD/runs/counter-run-001" \
  --env-file "$PWD/.env"
```

Windows PowerShell 等价命令：

```powershell
.\submit.ps1 `
  -Agent 'D:\agents\my-agent.zip' `
  -RequirementsDir "$PWD\public-exercise\requirements" `
  -TestsDir "$PWD\public-exercise\tests" `
  -OutputDir "$PWD\runs\counter-run-001" `
  -EnvFile "$PWD\.env"
```

PowerShell 版本使用命名参数，不要把 Bash 的 `--agent` 和反斜杠续行符直接复制过来。Windows 路径可以使用盘符、反斜杠和空格；脚本会将路径转换为绝对路径，Docker 使用 `--mount` 挂载到容器内的 `/workspace`。

参数说明：

| 参数 | 内容 |
|---|---|
| `--agent` | 智能体 `.zip` 的绝对或相对路径 |
| `--requirements-dir` | 包含 `requirements.yaml` 和可选 `reference/` 的需求目录 |
| `--tests-dir` | 可选；包含全部公开 Playwright 测试的目录。不传时不执行评测 |
| `--output-dir` | 本机保存 Workspace、生成应用、日志和测试结果的空目录 |
| `--env-file` | 可选的模型环境变量文件 |
| `--image` | 可选；默认 `arcbench-local-submit:latest` |

输出目录必须不存在或为空，工具不会覆盖以前的结果。

如果不填写需求路径，默认使用包内 Counter 的需求。下面的命令没有指定 `--tests-dir`，因此只运行智能体并部署应用，不执行 Playwright：

```bash
./submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --output-dir "$PWD/runs/counter-run-001" \
  --env-file "$PWD/.env"
```

Windows PowerShell（不指定测试目录，因此不执行 Playwright）：

```powershell
.\submit.ps1 `
  -Agent 'D:\agents\my-agent.zip' `
  -OutputDir "$PWD\runs\deploy-only" `
  -EnvFile "$PWD\.env"
```

PowerShell 的完整评测结果和跳过评测结果都保存在 `-OutputDir` 指定的 Windows 目录中。例如：

```powershell
Get-Content .\runs\counter-run-001\local-result.json
```

也可以显式指定需求目录但不指定测试目录：

```bash
./submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --requirements-dir /absolute/path/to/practice/requirements \
  --output-dir "$PWD/runs/deploy-only" \
  --env-file "$PWD/.env"
```

此模式仍会完整执行智能体、执行 `deploy.sh` 或默认部署流程，并等待应用在 `127.0.0.1:3000` 就绪；确认部署成功后跳过 Playwright 并结束容器。`local-result.json` 中会记录：

```json
{
  "evaluation_status": "skipped",
  "playwright_report": null
}
```

只组装输入、不启动 Docker：

```bash
./submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --output-dir "$PWD/runs/inspect-only" \
  --prepare-only
```

### 2.6 等待完成并查看输出

命令在前台运行。容器退出后会被删除，但 `--output-dir` 中的文件会保留：

```text
counter-run-001/
├── submission/                         # 解压后的智能体
├── template/                           # 最终目标应用
│   ├── frontend/                       # 若使用标准模板路径
│   ├── backend/                        # 若使用标准模板路径
│   └── .arc/
│       ├── stdout.log
│       ├── agent-execution.json
│       └── playwright-report.json      # 仅在提供测试并完成评测时生成
├── tests/                              # 未提供测试时为空
├── runner-spec.json
├── execution.debug.log
├── local-run.json
└── local-result.json
```

提供测试时，终端会打印 passed、failed、测试通过率、模型 Token、模型开销、币种和提交得分；未提供测试时，终端会明确显示 `evaluation_status: skipped`。这些字段也会写入 `local-result.json`。之后可以重新查看：

```bash
./result.sh \
  --workspace "$PWD/runs/counter-run-001" \
  --show-tests
```

Windows PowerShell：

```powershell
.\result.ps1 `
  -Workspace "$PWD\runs\counter-run-001" `
  -ShowTests
```

当 `.env` 中提供 `OPENAI_API_KEY` 时，本地提交会在运行前后查询 ARC Bench Meter（默认 `https://meter.arc-bench.com`）并计算差值。也可以通过 `.env` 中的 `ARCBENCH_METER_BASE_URL` 或 `--meter-base-url` 指定其他 Meter 门户地址。Meter 暂时不可用不会使评测失败；此时 `token_count`、`token_cost` 和正通过率对应的 `score` 为 `null`，具体原因记录在 `meter_error`。为兼容平台 API，`token_cost_usd` 是 `token_cost` 的同值别名，实际币种始终以 `token_cost_currency` 为准。

本地单任务得分采用参赛须知中的同一公式：`b0 = 1.2`、奖励指数 `α = 0.1`、惩罚指数 `β = 0.2`。正式比赛会先汇总两个任务的通过数、测试数和开销再计算，因此本地单任务分数仅用于调试参考。

发生错误时首先查看：

```bash
less runs/counter-run-001/execution.debug.log
less runs/counter-run-001/template/.arc/stdout.log
```

Windows PowerShell：

```powershell
Get-Content .\runs\counter-run-001\execution.debug.log
Get-Content .\runs\counter-run-001\template\.arc\stdout.log
Get-Content .\runs\counter-run-001\local-result.json
```

## 3. 竞赛平台依次做了什么

### 3.1 接收并检查智能体

本地模拟环境采用统一 Python 包装契约：ZIP 根目录必须包含：

```text
main.py
requirements.txt
```

平台将 ZIP 安全解压到：

```text
/workspace/submission
```

如果 ZIP 只有一个顶层目录，会自动去掉这一层。随后平台执行：

```bash
python3 -m pip install -r /workspace/submission/requirements.txt
```

`main.py` 可以只是其他语言智能体的启动包装器，因此该契约并不要求智能体核心逻辑必须用 Python 编写。

### 3.2 准备输入并执行智能体

平台创建：

```text
/workspace/template                   # 智能体的最终输出目录
/workspace/template/requirements      # 需求文档
/workspace/tests                      # 可选的 Playwright 测试；未提供时为空
```

为避免智能体修改原始需求，Runner 再把需求复制为本次只读语义的快照：

```text
/tmp/arcbench/requirements-source
```

实际执行：

```bash
cd /workspace/template
python3 /workspace/submission/main.py \
  /tmp/arcbench/requirements-source \
  --output-dir /workspace/template
```

所以智能体的职责是：读取第一个参数中的需求，把完整、可部署的应用写到 `--output-dir`，然后返回退出码 0。

如果下载的 Agent Template 中自带初始应用，它位于：

```text
/workspace/submission/template
```

平台不会自动把它当成输出。智能体应先将其内容复制到：

```text
/workspace/template
```

然后在该目录中继续实现需求。

### 3.3 智能体完成后部署应用

智能体正常结束后，平台按下面的优先级部署应用。

#### 路径 A：自定义 `deploy.sh`

> **⚠️ 这条路径目前只有本地模拟环境支持，正式评测平台不支持。**
>
> `deploy.sh` 分支由本地镜像的 `local_runner.py` 以 monkey-patch 方式加在生产 Runner 之上。正式评测使用的 `run_submission.py` **没有这个分支**：它的 `run_web_template()` 无条件要求输出根目录存在 `frontend/` 和 `backend/`，缺任何一个就直接抛
>
> ```text
> web template is incomplete: expected frontend/ and backend/ directories
> ```
>
> 流程会停在 `Running agent` 阶段，**一个测试都不会执行**。
>
> 也就是说：一个只产出 `deploy.sh` 的智能体在本地可以拿满分，正式提交却会零分，而且错误信息不会提示原因。
>
> **在上游把这条契约同步到正式 Runner 之前，请使用下面的路径 B。**

如果输出根目录存在：

```text
/workspace/template/deploy.sh
```

本地模拟环境不会再要求 `frontend/` 和 `backend/`，也不会执行固定的 npm 命令，而是执行：

```bash
cd /workspace/template
HOST=0.0.0.0 \
PORT=3000 \
ARCBENCH_WEB_BASE_URL=http://127.0.0.1:3000 \
bash /workspace/template/deploy.sh
```

`deploy.sh` 负责全部工作，包括：

- 安装目标应用依赖；
- 构建前端或其他产物；
- 启动目标应用；
- 让应用可以通过 `http://127.0.0.1:3000` 访问。

脚本必须保持在前台运行，不要启动服务后立即退出。最后一条启动命令建议使用 `exec`：

```bash
#!/usr/bin/env bash
set -euo pipefail

# 示例：这里可以安装、构建任意技术栈
python3 -m pip install --target .deploy-deps -r app-requirements.txt
export PYTHONPATH="$PWD/.deploy-deps${PYTHONPATH:+:$PYTHONPATH}"
exec python3 server.py --host 0.0.0.0 --port "${PORT:-3000}"
```

该路径允许生成任意技术栈，只要 Runner 镜像中已有所需工具，或 `deploy.sh` 能在容器权限和网络限制内完成安装。

本地镜像通过 `/opt/arcbench/local_runner.py` 明确实现这项契约。它会在进入默认部署流程前检查 `deploy.sh`；因此这不是文档约定或伪代码，而是本地模拟环境实际执行的分支。修改本地 Runner 或首次获取此功能后，需要重新构建镜像：

```bash
./build-image.sh
```

#### 使用包内示例验证 deploy.sh

`examples/custom-deploy-agent/` 提供了一个最小示例。该智能体不生成 `frontend/` 和 `backend/`，只生成：

```text
<output-dir>/
├── deploy.sh
├── server.py
└── public/
    └── index.html
```

将示例打包：

```bash
cd examples/custom-deploy-agent
zip -r /tmp/custom-deploy-agent.zip main.py requirements.txt
cd ../../..
```

然后使用公开练习题运行：

```bash
./submit.sh \
  --agent /tmp/custom-deploy-agent.zip \
  --requirements-dir "$PWD/public-exercise/requirements" \
  --tests-dir "$PWD/public-exercise/tests" \
  --output-dir "$PWD/runs/custom-deploy-example"
```

Windows PowerShell 可以用同一个示例。Compress-Archive 会把示例目录中的入口和部署文件放到 ZIP 根目录：

```powershell
Set-Location "$PSScriptRoot\examples\custom-deploy-agent"
Compress-Archive `
  -Path .\main.py, .\requirements.txt `
  -DestinationPath "$PSScriptRoot\custom-deploy-agent.zip" `
  -Force

Set-Location $PSScriptRoot
.\submit.ps1 `
  -Agent "$PSScriptRoot\custom-deploy-agent.zip" `
  -RequirementsDir "$PSScriptRoot\public-exercise\requirements" `
  -TestsDir "$PSScriptRoot\public-exercise\tests" `
  -OutputDir "$PSScriptRoot\runs\custom-deploy-example"
```

日志中出现以下信息，表示 Runner 选择了自定义部署路径：

```text
Starting generated application with deploy.sh
deploy.sh started
Template application is reachable on http://127.0.0.1:3000
```

#### 路径 B：标准 `frontend` + `backend`

如果没有 `deploy.sh`，输出目录必须包含：

```text
/workspace/template/
├── frontend/
│   └── package.json
└── backend/
    └── package.json
```

平台依次执行：

```bash
cd /workspace/template/frontend
npm install --include=optional --no-audit --no-fund
npm run build

cd /workspace/template/backend
npm install --include=optional --no-audit --no-fund
HOST=0.0.0.0 PORT=3000 npm run start
```

下载的 Blank Agent Template 使用的就是这条路径：智能体先将 ZIP 中的 `template/` 复制到输出目录，再在其中实现需求。

两条路径最终都必须满足：

```text
http://127.0.0.1:3000 可访问
```

Runner 最多等待 120 秒。获得小于 500 的 HTTP 响应后，如果提供了测试目录则开始评测；如果没有提供测试目录，则记录部署成功并跳过评测。

### 3.4 执行 Playwright

本节只适用于传入 `--tests-dir` 的运行。应用 ready 后，平台强制生成 Playwright 配置：

```text
baseURL:       http://127.0.0.1:3000
browser:       Chromium
workers:       1
test timeout:  10 秒
expect timeout:10 秒
trace:         off
screenshot:    off
```

同时设置：

```text
E2E_BASE_URL=http://127.0.0.1:3000
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000
ARC_WEB_BASE_URL=http://127.0.0.1:3000
```

先枚举测试：

```bash
cd /workspace/tests
npx playwright test --list
```

再执行全部测试：

```bash
npx playwright test --workers=1
```

Playwright 与目标应用位于同一个 Docker 容器，因此这里的 `127.0.0.1:3000` 指向本次运行自己的应用，不会与其他容器冲突。

## 4. 竞赛环境信息

本地镜像由 ARC-Bench 网站仓库的 `backend/runner/Dockerfile` 构建（见 2.2），当前环境如下：

| 项目 | 当前配置 |
|---|---|
| 基础镜像 | `mcr.microsoft.com/playwright/python:v1.57.0-noble` |
| 操作系统 | Ubuntu Noble 系列 Linux |
| Node.js | `20.19.3` |
| JavaScript Playwright | `@playwright/test 1.57.0` |
| Python Playwright | `playwright 1.57.0` |
| 浏览器 | 镜像内置 Chromium |
| Git | 已安装 |
| 编译工具 | `build-essential`、`pkg-config`、`libssl-dev` |
| 常用命令 | `curl`、`git`、`lsof`、`npm`、`python3` |
| 常用 Python 包 | OpenAI SDK、Anthropic、Pydantic、PyYAML、HTTPX、Requests、Tenacity、Rich、JSON Schema、Jinja2 等 |
| 应用目标 URL | `http://127.0.0.1:3000` |
| Playwright Worker | 1 |
| 应用启动等待 | 最多 120 秒 |
| 单个 Playwright 测试超时 | 10 秒 |

Python 的精确补丁版本继承自固定基础镜像。构建完成后可查看实际版本：

```bash
docker run --rm --entrypoint python3 \
  arcbench-local-submit:latest --version
```

竞赛平台每次任务运行的资源限制为：

```text
CPU:    1 核
内存:   2 GB
```

本地 `submit.sh` 默认使用相同的限制，以便尽可能复现正式竞赛环境。仅在排查本地环境问题时，可以通过以下参数临时覆盖：

```bash
--cpus 2 --memory 4g
```

使用更高的本地资源限制可能掩盖性能或内存问题，不能代表正式竞赛环境下的运行结果。

本地工具目前没有额外设置磁盘配额，实际可用空间取决于 Docker 和挂载输出目录所在磁盘。容器默认使用 Docker 网络访问模型 API 和依赖源，但不会把应用的 3000 端口发布到宿主机；测试完全在容器内部完成。
