# SalesAgent GitHub 协作与自动化

## 当前检查结果（2026-10-10）

- 原工作区配置分支：`chore/github-collaboration`，基于本地 `SalesAgent(韦)` 的 `c0c74d4`，保留原有工作区修改。
- **用于发布的分支**：`chore/github-collaboration-target`，独立 worktree 位于 `.ci-local/target-repo`，基于目标 main 的 `5cbe27f`。只复制本次配置及锁文件，不携带原功能分支历史。
- 指定目标：`https://github.com/weilinqi/salesagent`；只读查询确认默认分支为 `main`。
- 现有 origin 是 `https://github.com/weilinqi/SalesAgent-1.git`，upstream 是 `git@github.com:xinyi-eng/SalesAgent.git`。没有更改这些地址。
- 原有未提交内容：修改的 `backend/app/data/asr_debug/last_user_audio_processed.wav`，已删除状态的 `backend/salesagent.db-journal`；原有未跟踪文件包括 `.claude/settings.local.json` 和 SQLite WAL/SHM。没有还原、暂存或提交这些内容。
- `.gitignore` 原本忽略 npm 锁文件，现在允许提交现有 `frontend/package-lock.json`，CI 使用 `npm ci`。

## CI 的范围

所有 PR 创建、更新、重新打开均运行 `.github/workflows/ci.yml`，不设路径过滤；推送 main/master、merge group 和手动触发也运行。

| 必需检查名称 | 内容 |
| --- | --- |
| Frontend build | Node 22，`npm ci`，`npm run lint`，`npm run build`（严格 lint、TypeScript 检查及 Vite 生产构建） |
| Backend tests | Python 3.12，安装完整 requirements，`pip check`，全部 app Python 语法编译，11 项 unittest 行为测试 |

后端测试覆盖密码哈希、访问与刷新 token、过期与损坏 token、回应文本轮换及触发条件。测试不导入 `app.main`，不打开业务数据库，不读取应用 `.env`，不调用外部 AI 或下载模型。后端依赖安装失败、类型错误、构建失败或测试失败都会使检查失败，没有 `continue-on-error` 或虚假成功步骤。

这是初始回归覆盖，不代表已验证所有 API、数据库迁移、ASR/TTS 或浏览器交互。以后补充测试应放入 `backend/tests/test_*.py`；前端没有现成测试框架，lint 与构建检查不能代替交互测试。前端已配置 ESLint，CI 会执行严格 lint。

本地验证结果：目标 worktree 内 `npm ci` 成功（277 个包），随后 `npm run build` 成功；11 项后端测试全部通过，56 个 app Python 文件语法检查通过。复用原项目 Python 3.12 虚拟环境运行后端测试，`pip check` 无依赖冲突；尚未在全新 Ubuntu 环境安装完整 Python 依赖或运行 GitHub Actions。工作流 YAML、锁文件与 package.json 一致性和 `git diff --check` 通过。原工作区的前端构建也通过，输出到 `.ci-local/frontend-build`，没有覆盖原 dist。

## 首次发布顺序（必须先确认）

1. 已核实原工作区与目标 main **无共同祖先**，但 CI 涉及的源码和依赖清单一致。必须在独立 worktree 发布：

   ```powershell
   cd C:/Users/W2008/Desktop/SalesAgent/.ci-local/target-repo
   git branch --show-current
   git diff
   ```

   分支应为 `chore/github-collaboration-target`。不要发布原工作区的 `chore/github-collaboration`。
2. 只暂存本次配置文件及锁文件，禁止 `git add .`：

   ```powershell
   git add .gitignore .github/workflows/ci.yml .github/pull_request_template.md backend/tests/test_ci_behavior.py frontend/package-lock.json docs/github-collaboration.md
   git diff --cached --stat
   git diff --cached --check
   git commit -m "chore: configure GitHub collaboration and CI"
   ```

3. 确认后才添加独立远程（保留 origin/upstream）：

   ```powershell
   git remote add collaboration https://github.com/weilinqi/salesagent.git
   git fetch collaboration
   git merge-base HEAD collaboration/main
   git diff --stat collaboration/main...HEAD
   ```

   如果没有共同祖先，停止发布当前分支。另建目录克隆目标仓库，从其 main 创建配置分支，仅复制本次配置文件；核实目标代码是否匹配这些测试，再重新验证。不要使用 `--allow-unrelated-histories` 或强推，也不要把整套现有功能变更混入配置 PR。

4. 若存在共同祖先，仍需审查 PR 差异是否含原功能分支的额外变更。确认本次 PR 范围后才执行：

   ```powershell
   git push -u collaboration chore/github-collaboration-target
   ```

5. 在目标仓库创建 base `main` 的 PR，等待两个检查出现并通过。选择必需检查后才合并，避免先设置不存在的检查造成阻塞。首次配置 PR 中的 workflow 能运行于 PR；后续主分支触发需要文件合入 main。

以上命令为操作说明；本次未执行 Commit、Push 或 Merge。远程设置也未修改。

## GitHub 网页配置步骤

需要仓库管理员权限。如果私有仓库看不到保护/auto-merge 选项，核实 GitHub 套餐；这些能力在公开 Free 仓库和相应付费私有仓库可用。

### 1. Actions 与协作者

1. 进入目标仓库 → Settings → Actions → General。
2. 允许本 CI 使用的 `actions/checkout`、`actions/setup-node`、`actions/setup-python`；若组织有 Action 白名单，需由管理员放行。
3. Workflow permissions 保持只读即可；不需要允许 workflow 创建或批准 PR。
4. Settings → Collaborators（组织仓库可能显示 Collaborators and teams）→ Add people，邀请真实开发者账号，给予开发所需 Write 权限，避免普遍给予 Admin。受邀人员需接受邀请。

### 2. 保护 main

进入 Settings → Branches → Add classic branch protection rule，Branch name pattern 填 `main`。若页面入口是 Add rule，选择分支保护规则。已有 main 规则时应编辑现有规则，避免相互重叠。

- 勾选 **Require a pull request before merging**。
- 勾选 **Require approvals**，数量 `1`；由另一位有相应权限的成员审核，作者不能批准自己的 PR。
- 勾选 **Dismiss stale pull request approvals when new commits are pushed**。
- 勾选 **Require approval of the most recent reviewable push**。
- 勾选 **Require status checks to pass before merging**，并勾选 **Require branches to be up to date before merging**。
- CI 至少实际跑过一次后，选择 **Frontend build** 和 **Backend tests**，来源选 GitHub Actions（若 UI 提供来源选择）。检查须在最近 7 天出现，名称须与实际 job 一致。
- 勾选 **Require conversation resolution before merging**。
- 勾选 **Do not allow bypassing the above settings**，让管理员也受约束。不要添加绕过 PR 的账号或 App。
- **Allow force pushes** 和 **Allow deletions** 保持关闭。
- 不启用 Lock branch，它会阻止正常协作；本方案也不需要付费 merge queue。
- 保存。用一次失败的测试 PR 验证合并按钮被阻止，再修复并检查需要重新审核；不要用生产 main 做破坏性试验。

### 3. 自动合并及自动删除远程功能分支

Settings → General → Pull Requests：

- 打开 **Allow squash merging**。
- 打开 **Allow auto-merge**。
- 打开 **Automatically delete head branches**。

在每个准备合并的 PR 页面：选择 Squash and merge → **Enable auto-merge** → 确认。之后 GitHub 会等待必需检查和审核完成再合并。仓库开关只是允许 auto-merge，不会自动为所有 PR 启用；本方案每个 PR 由有 Write 权限的开发者主动启用，无需存储 PAT 或赋予 Actions 写权限。

存在冲突或分支落后时必须更新分支、解决冲突并重跑 CI。功能分支若受到禁止删除规则保护，则不会自动删除；只对 main 设置删除保护。自动删除仅针对 GitHub 远程分支，不删除本地文件或本地分支。

参考：[分支保护](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule)、[必需检查排障](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)、[允许 auto-merge](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-auto-merge-for-pull-requests-in-your-repository)、[PR 启用 auto-merge](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request)、[自动删除分支](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/managing-the-automatic-deletion-of-branches)。

## VS Code 日常多人流程

每位开发者使用自己的 clone、自己的功能分支；不同开发者不要同时推送同一个分支。提前在 Issue/PR 分配工作，修改共享文件前沟通，可减少冲突，不能保证完全无冲突。

1. 工作区干净时，通过左下角分支按钮切到 main，在 Source Control 获取远程并 Pull；终端可用 `git pull --ff-only collaboration main`。每个人新 clone 的正确仓库通常叫 origin，将下面 collaboration 替换成自己的正确远程名。
2. 从更新后的 main 创建 `feature/姓名-功能` 或 `fix/姓名-问题` 分支。
3. 修改后逐个暂存文件，检查 diff，运行本地检查，再 Commit。使用 Publish Branch/Push 发布到正确远程。
4. 用 GitHub Pull Requests 扩展或网页创建目标 main 的 PR，填写模板，请另一位成员审核，启用 auto-merge。
5. GitHub Actions 自动运行；失败时点 Details 查看日志，在同一功能分支修复再 Push，CI 自动重跑。
6. 更新落后的功能分支前，先提交自己的工作，再 fetch，并在自己的分支 merge 最新 main；解决冲突后重新构建、测试和提交。不要对共享分支强推。
7. PR 合并后，切回 main，工作区干净时 `git pull --ff-only collaboration main`；`git fetch --prune collaboration` 只清理已消失的远程引用。保留本地功能分支，直到确认提交和工作均已安全保存。

本地检查：

```powershell
cd frontend
npm ci
npm run lint
npm run build
cd ../backend
.venv/Scripts/python.exe -m pip check
.venv/Scripts/python.exe -m unittest discover -s tests -p 'test_*.py' -v
```

`npm ci` 会重新安装 node_modules，开发者应在适合的时间自行运行。后端新环境使用 Python 3.12 创建虚拟环境并安装 `requirements.txt`。Ubuntu CI 和本地 Windows 有平台差异，首个 GitHub CI 的全新安装结果仍需确认。

## 文件保护边界

新忽略规则覆盖 `.env.*`（保留 example）、本地 Claude 设置、常见私钥文件、SQLite sidecar、运行时录音目录和验证输出。现有锁文件重新允许提交用于可重复安装。

Git 已跟踪的文件不会因为 `.gitignore` 被停止跟踪。本次发现 Git 已跟踪：

- `backend/app/data/asr_debug/converted.wav`
- `backend/app/data/asr_debug/last_user_audio_processed.wav`
- `backend/salesagent.db-journal`

以上是原工作区的跟踪情况；目标 main 的独立 worktree 中，仅 `converted.wav` 被跟踪。本次配置 PR 不会带入原工作区那两个不同的文件状态。

本次没有执行 `git rm --cached`。如果以后获准停止跟踪，应先备份和确认运行中的数据库状态，再单独提交索引变更；注意其他开发者 pull 这类删除提交可能删除其对应工作区文件，应提前通知并备份。不要运行 `git clean` 或 `reset --hard`。忽略规则不能抹除历史里的数据，敏感信息若曾提交，需要独立评估密钥轮换及历史处理。
