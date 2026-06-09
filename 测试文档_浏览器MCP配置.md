# SalesAgent 浏览器测试文档

## 测试环境

- **前端**: Vite React (localhost:5173)
- **后端**: FastAPI (localhost:8001)
- **浏览器**: Chrome with --remote-debugging-port=9222
- **系统**: Windows 11

---

## 一、Chrome DevTools MCP 配置指南

### 问题描述

Chrome 浏览器的 `--remote-debugging-port=9222` 参数**不是持久化**的。每次关机/重启后需要重新手动打开 Chrome 并添加调试端口，否则 MCP 连接会失败。

### 解决方案：创建 Chrome 调试快捷方式

#### 步骤 1：创建 PowerShell 脚本

创建文件 `C:\Users\zsndz\Desktop\SalesAgent\create_shortcut.ps1`：

```powershell
$shell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$lnk = $shell.CreateShortcut("$desktop\Chrome Debug.lnk")
$lnk.TargetPath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$lnk.Arguments = "--no-sandbox --remote-debugging-port=9222 --user-data-dir=C:\temp\chrome-debug"
$lnk.Save()
Write-Host "Shortcut created on Desktop"
```

#### 步骤 2：运行脚本创建快捷方式

```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\zsndz\Desktop\SalesAgent\create_shortcut.ps1"
```

#### 步骤 3：使用快捷方式启动 Chrome

1. 双击桌面上的 `Chrome Debug.lnk` 快捷方式
2. Chrome 会在调试模式下启动，端口 9222 处于监听状态
3. MCP 工具（mcp__chrome-devtools__*）即可连接

### 关键参数说明

| 参数 | 说明 |
|------|------|
| `--no-sandbox` | 避免权限问题（Windows 下建议添加） |
| `--remote-debugging-port=9222` | 开启 Chrome 远程调试端口 |
| `--user-data-dir=C:\temp\chrome-debug` | 指定独立的用户数据目录，避免与正常 Chrome 冲突 |

### 验证连接

```bash
curl http://127.0.0.1:9222/json/version
```

成功响应示例：
```json
{
   "Browser": "Chrome/148.0.7778.216",
   "Protocol-Version": "1.3",
   "WebSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."
}
```

---

## 二、测试流程记录

### 2.1 启动服务

**后端服务**：
```bash
cd C:\Users\zsndz\Desktop\SalesAgent\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001
```

**前端服务**：
```bash
cd C:\Users\zsndz\Desktop\SalesAgent\frontend
npm run dev
```

### 2.2 登录测试

1. 访问 http://localhost:5173/login
2. 输入任意邮箱和密码（如 test@test.com / password123）
3. 点击登录按钮

**结果**：✅ 登录成功，自动跳转到 /practice 页面

### 2.3 场景选择测试

页面显示 12 个内置场景：
- 竞品对比应对
- 大客户开发
- 促成成交技巧
- 防御性销售(异议防范)
- 客户拒绝挽回
- 再次拜访与跟进
- 挖掘客户需求(SPIN)
- 处理价格异议
- 处理能力异议
- 产品方案呈现
- 电话销售跟进
- 首次拜访客户

**结果**：✅ 场景加载成功

### 2.4 角色配置测试

选择"首次拜访客户"场景后，进入角色配置页面：

| 配置项 | 选项 |
|--------|------|
| 岗位级别 | 高级的总监 |
| 客户性格 | 果断型 |
| 决策风格 | 价值导向 |

配置完成后，"开始对练"按钮变为可点击状态。

**结果**：✅ 角色配置功能正常

### 2.5 对练页面测试

点击"开始对练"后，进入 `/practice/chat` 页面。

页面显示：
- 顶部：AI 客户角色信息（高级总监 / 果断型 / 价值导向）
- 左侧：聊天区域，显示 AI 初始消息
- 右侧：实时 SPIN 指导（开场破冰阶段）
- 底部：消息输入框和语音录制按钮

**结果**：✅ 页面结构正常，SPIN 指导侧边栏显示正常

### 2.6 WebSocket 连接状态

当前状态：**连接中...**

问题分析：
- 前端 WebSocket URL 配置为 `/ws/practice/{session_id}`
- 后端 WebSocket 端点需要正确建立连接

**结果**：⚠️ WebSocket 连接未完成，需要进一步调试

### 2.7 发送消息测试

在输入框输入：`您好，请问您公司的销售团队目前有多少人？`

按 Enter 发送后，消息显示在聊天区域，但 AI 未回复。

**结果**：⚠️ 消息发送功能正常，但 AI 响应未收到

### 2.8 WebSocket 问题修复

**问题描述**：
- 控制台显示 WebSocket 连接失败
- 后端日志显示 `connection closed` 立即跟随 `connection open`

**根本原因**：
1. 后端 `datetime` 模块未导入
2. `WebSocketDisconnect` 异常未正确处理
3. Vite WebSocket 代理存在兼容性问题

**修复内容**：
1. 添加 `from datetime import datetime` 导入
2. 添加 WebSocket 连接确认消息 `{"type":"connected",...}`
3. 修复异常处理避免无限循环
4. 前端改用直接连接 `ws://localhost:8001/ws/practice/{session_id}`

**验证结果**：
```python
# Python 直接测试 - 连接稳定
Connected!
Server: {"type":"connected","session_id":"test-open",...}
Sent ping
Connection still open, staying alive for another 10 seconds...
Test complete - connection was stable!

# 直接测试发送消息 - AI 正常回复
Response: {"type":"status_update","state":"processing",...}
Response: {"type":"ai_message","content":"很好，请问您有什么问题？"}
```

**结果**：✅ WebSocket 连接已修复

---

## 三、已知问题

### 3.1 Chrome DevTools MCP 连接不稳定

Chrome DevTools MCP 在长时间会话后可能出现工具不可用。

Chrome DevTools MCP 在当前 session 中频繁断开重连，导致测试不稳定。

**建议**：
- 每次重新启动 Chrome 后，等待几秒再使用 MCP 工具
- 如果 MCP 工具报错，先用 `curl http://127.0.0.1:9222/json/version` 验证 Chrome 调试端口是否可用

### 3.2 Chrome 调试端口需要每次手动启动

每次开机后需要：
1. 关闭所有 Chrome 窗口
2. 双击 Chrome Debug.lnk 启动调试模式 Chrome
3. 重新进行 MCP 连接

### 3.3 进程残留

Windows 下 Chrome 进程可能残留，需要手动清理：
```bash
taskkill /F /IM chrome.exe
```

---

## 四、快捷命令汇总

```bash
# 创建 Chrome 调试快捷方式
powershell -ExecutionPolicy Bypass -File "C:\Users\zsndz\Desktop\SalesAgent\create_shortcut.ps1"

# 启动调试 Chrome
taskkill /F /IM chrome.exe 2>/dev/null; powershell -Command "Start-Process 'C:\Program Files\Google\Chrome\Application\chrome.exe' -ArgumentList '--no-sandbox','--remote-debugging-port=9222','--user-data-dir=C:\temp\chrome-debug' -PassThru | Select-Object Id"

# 验证 Chrome 调试端口
curl http://127.0.0.1:9222/json/version

# 启动后端
cd /c/Users/zsndz/Desktop/SalesAgent/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &

# 启动前端
cd /c/Users/zsndz/Desktop/SalesAgent/frontend && npm run dev &
```

---

*文档生成时间：2026-06-02*