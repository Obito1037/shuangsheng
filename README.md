# 双生 (ShuangSheng)

本项目是“双生”前后端整合仓库，旨在提供完整的基于大模型能力的语音和视觉双生助手。

## 架构

- **`android-app/`**：Android WebView 前端应用，完全本地运行，提供用户交互界面并与后端 API 通信。
- **`backend/`**：FastAPI 后端服务，负责处理大模型交互、文件解析、RAG（Retrieval-Augmented Generation）和视觉处理。

## 目录结构

```
shuangsheng/
  ├── android-app/        # Android WebView 前端源码
  ├── backend/            # FastAPI 后端源码
  ├── docs/               # 项目文档
  ├── README.md           # 本文档
  └── .gitignore          # Git 忽略配置
```

## 开发指南

### 后端本地启动方式

使用 Python 3.9+ 运行后端服务：

```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Android 构建方式

```bash
cd android-app
.\gradlew.bat clean :app:assembleDebug --console=plain
```

APK 产物位置：`android-app/app/build/outputs/apk/debug/app-debug.apk`

### 本地联调方式

1. 本地启动后端服务，默认地址为 `http://127.0.0.1:8000` (或局域网 IP)。
2. 配置前端应用，将 API Base URL 指向本机的局域网 IP（例如 `http://192.168.x.x:8000`）。
3. 确保防火墙允许该端口，并且手机/模拟器与电脑处于同一局域网内。

### 云端后端地址

（请在部署后补充云端 API 地址）

### 当前已完成接口范围

- Auth: 登录、注册及 Token 管理
- Twin (分身): 创建、获取、修改、删除数字分身
- Chat: 基础聊天对话及流式响应
- RAG: 基于文档的知识库检索与生成
- Vision (OCR / 图文理解): 基于 Vivo 服务的 OCR 和图像分析
- Usage: 用量统计与监控

## 开发规范 (重要)

为保证仓库结构的整洁与安全，**禁止提交以下内容**：
- `.env` 及任何包含密码、API Key 的配置文件
- 数据库文件（如 `echolearn.db` 或任何 `*.db`）
- 本地生成的文件存储（如 `storage_data/`）
- 编译及构建产物（如 `build/`、`.gradle/`、`__pycache__/` 等）

请遵守 `.gitignore` 配置，不要强制提交被忽略的文件。
