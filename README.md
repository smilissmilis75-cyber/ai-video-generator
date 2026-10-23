---
title: AI Video Studio
emoji: 🎬
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# AI 视频工坊（Android 友好）

输入主题后自动生成分镜、普通话配音、字幕和 MP4。

## 当前能力
- Gradio 网页操作界面
- 动漫 / 真人电影风格的抽象场景卡片
- 普通话语音（通过 edge-tts 在线服务）
- SRT 字幕文件与烧录字幕
- FFmpeg 合成 MP4
- 输出分镜 JSON，便于后续编辑

## 重要限制
当前版本是可运行的 MVP：画面由程序绘制，不是真正的 AI 文生视频；分镜脚本使用内置模板，不调用大语言模型。`edge-tts` 需要联网，服务可用性由其上游决定。长视频渲染需要足够的 CPU、磁盘和运行时间。

## 部署
推荐将此仓库导入 Hugging Face Spaces，并选择 Docker SDK。Space 会构建 Dockerfile，安装 FFmpeg 后启动应用。

也可以在任何安装了 Python 3.11、FFmpeg 的服务器运行：

```bash
pip install -r requirements.txt
python app.py
```

## 安卓手机部署流程
1. 在 GitHub 创建公开仓库 `ai-video-generator`。
2. 在手机浏览器打开 Hugging Face，登录并创建一个新的 Space。
3. Space SDK 选择 Docker；将此仓库的文件上传到 Space，或在 Space 设置中连接 GitHub 仓库（如果该选项在你的账号中可用）。
4. 等待构建完成，打开 Space 页面即可使用。
5. 输入主题，选择画风和配音，点击“生成视频”。完成后下载 MP4。

## 成本说明
- GitHub：保存代码通常免费；GitHub 不负责运行视频模型。
- Hugging Face Spaces：CPU 免费运行环境可能有休眠、资源与时长限制，长视频生成可能失败；以账号页面当前配额为准。
- FFmpeg/Pillow/Gradio：开源免费。
- edge-tts：此项目不需要自行填写 API Key，但依赖网络和上游服务可用性，不保证长期稳定。
- 真正的 AI 图片/视频：需要接入外部模型 API 或部署开源模型。外部 API 可能收费；本地/自托管模型通常需要较强 GPU。
- 语言模型：本项目当前用内置模板，不需要 LLM API Key。若要生成更有创意的剧情，可选接入 LLM API。

## 安全
不要把 API Key、密码或访问令牌提交到 GitHub。后续接入 API 时使用部署平台的 Secrets/环境变量。
