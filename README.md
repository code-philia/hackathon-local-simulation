# ARC-Bench 本地模拟提交环境

这个目录用于让选手在本地完成一次与竞赛平台核心运行阶段一致的模拟提交：运行上传的智能体、部署智能体生成的应用，并对 `http://127.0.0.1:3000` 执行 Playwright 测试。

它不模拟登录、数据库、排队、排行榜等网站功能。

## 1. 本地环境包包含什么

```text
local-submit/
├── public-exercise/
│   ├── requirements/
│   │   ├── requirements.yaml       # 机器可读需求，必须存在
│   │   ├── requirements.md         # 人类可读需求
│   │   └── reference/              # 图片、说明等公开参考资料
│   └── tests/
│       └── REQ-1.spec.ts           # 公开 Playwright 测试
├── Dockerfile                      # 本地竞赛镜像定义
├── build-image.sh                  # 构建并检查镜像
├── local_submit.py                 # 组装 Workspace、运行容器、汇总结果
├── submit.sh                       # 模拟提交快捷入口
├── result.sh                       # 重新查看结果
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

检查：

```bash
docker version
python3 --version
```

### 2.2 构建本地模拟竞赛镜像

在 ARC-Bench 仓库根目录执行：

```bash
chmod +x local-submit/build-image.sh
./local-submit/build-image.sh
```

构建脚本会：

1. 使用平台的 `backend/runner/Dockerfile` 创建基础 Runner；
2. 执行 smoke test，确认 Python、Node.js、Git、Playwright 和 Chromium 可用；
3. 创建本地镜像：

   ```text
   arcbench-local-submit:latest
   ```

确认镜像：

```bash
docker image inspect arcbench-local-submit:latest
```

如果组织者已经发布镜像，选手也可以直接拉取：

```bash
docker pull registry.example.com/arcbench/local-submit:v1
```

运行时通过 `--image registry.example.com/arcbench/local-submit:v1` 指定。

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

### 2.4 准备模型环境变量

```bash
cp local-submit/env.example local-submit/.env
chmod 600 local-submit/.env
```

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
./local-submit/submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --requirements-dir "$PWD/local-submit/public-exercise/requirements" \
  --tests-dir "$PWD/local-submit/public-exercise/tests" \
  --output-dir "$PWD/local-submit/runs/counter-run-001" \
  --env-file "$PWD/local-submit/.env"
```

参数说明：

| 参数 | 内容 |
|---|---|
| `--agent` | 智能体 `.zip` 的绝对或相对路径 |
| `--requirements-dir` | 包含 `requirements.yaml` 和可选 `reference/` 的需求目录 |
| `--tests-dir` | 包含全部公开 Playwright 测试的目录 |
| `--output-dir` | 本机保存 Workspace、生成应用、日志和测试结果的空目录 |
| `--env-file` | 可选的模型环境变量文件 |
| `--image` | 可选；默认 `arcbench-local-submit:latest` |

输出目录必须不存在或为空，工具不会覆盖以前的结果。

如果不填写练习题路径，默认就使用包内的 Counter：

```bash
./local-submit/submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --output-dir "$PWD/local-submit/runs/counter-run-001" \
  --env-file "$PWD/local-submit/.env"
```

只组装输入、不启动 Docker：

```bash
./local-submit/submit.sh \
  --agent /absolute/path/to/my-agent.zip \
  --output-dir "$PWD/local-submit/runs/inspect-only" \
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
│       └── playwright-report.json
├── tests/                              # 本次测试快照
├── runner-spec.json
├── execution.debug.log
├── local-run.json
└── local-result.json
```

终端会直接打印 passed、failed、测试通过率和功能实现率。之后可以重新查看：

```bash
./local-submit/result.sh \
  --workspace "$PWD/local-submit/runs/counter-run-001" \
  --show-tests
```

发生错误时首先查看：

```bash
less local-submit/runs/counter-run-001/execution.debug.log
less local-submit/runs/counter-run-001/template/.arc/stdout.log
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
/workspace/tests                      # Playwright 测试
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

如果输出根目录存在：

```text
/workspace/template/deploy.sh
```

平台不会再要求 `frontend/` 和 `backend/`，也不会执行固定的 npm 命令，而是执行：

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
./local-submit/build-image.sh
```

#### 使用包内示例验证 deploy.sh

`local-submit/examples/custom-deploy-agent/` 提供了一个最小示例。该智能体不生成 `frontend/` 和 `backend/`，只生成：

```text
<output-dir>/
├── deploy.sh
├── server.py
└── public/
    └── index.html
```

将示例打包：

```bash
cd local-submit/examples/custom-deploy-agent
zip -r /tmp/custom-deploy-agent.zip main.py requirements.txt
cd ../../..
```

然后使用公开练习题运行：

```bash
./local-submit/submit.sh \
  --agent /tmp/custom-deploy-agent.zip \
  --requirements-dir "$PWD/local-submit/public-exercise/requirements" \
  --tests-dir "$PWD/local-submit/public-exercise/tests" \
  --output-dir "$PWD/local-submit/runs/custom-deploy-example"
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

Runner 最多等待 120 秒；获得小于 500 的 HTTP 响应后才开始测试。

### 3.4 执行 Playwright

应用 ready 后，平台强制生成 Playwright 配置：

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

本地镜像由 [backend/runner/Dockerfile](../backend/runner/Dockerfile) 构建，当前环境如下：

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
