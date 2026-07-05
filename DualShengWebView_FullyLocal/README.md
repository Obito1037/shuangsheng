# DualShengWebView_FullyLocal

这是“双生”WebView 全本地化版本。

## 本地化内容

- `index.html`：来源于你上传的源码，已去除 Google Fonts / Material Symbols / Tailwind CDN 外链。
- `tailwind-local.css`：本地 Tailwind utility fallback，防止 WebView 离线或 CDN 失败时页面串行。
- `offline-icons.js` + `offline-icons.css`：把 Material Symbols 的英文图标名替换成本地 SVG 图标，避免离线时显示 `menu`、`lock`、`route` 等英文单词。
- `webview-runtime-check.js`：本地运行检测和移动端视口修正。

## 不再依赖外网的 UI 部分

- 页面布局
- 卡片、按钮、输入框、弹层样式
- 页面切换动画
- 启动页 SVG 动画
- Material 图标的本地 SVG 兜底

## 仍需联网的部分

- 后端 API：登录、注册、聊天、上传资料等真实服务请求。

## 使用方式

解压到英文路径，例如：

```text
C:\AndroidProjects\DualShengWebView_FullyLocal
```

用 Android Studio 打开该目录，Sync 后运行。
