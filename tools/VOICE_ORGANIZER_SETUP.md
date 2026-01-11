# 语音整理助手 (Voice Organizer) 环境配置指南

如果您更换了电脑，或初次使用“语音识别”功能，请按照以下步骤配置环境。

## 1. 安装 Python 依赖

本项目依赖 OpenAI 的 Whisper 模型进行本地离线识别。请在项目根目录下运行以下命令安装所需库：

```bash
pip install -r requirements.txt
```

或者单独安装：

```bash
pip install openai-whisper
```

*注意：`openai-whisper` 会自动安装 `torch` (PyTorch)，这是一个较大的依赖库（约 2GB+），请耐心等待下载。*

## 2. 安装 FFmpeg (关键步骤)

**这是 Windows 用户最容易遗漏的步骤。**
Whisper 依赖 `ffmpeg` 来处理音频文件。如果没有它，识别会直接报错或卡住。

### 安装步骤：

1.  **下载**：
    *   访问 [FFmpeg 官网下载页](https://ffmpeg.org/download.html) 或直接访问 [gyan.dev builds](https://www.gyan.dev/ffmpeg/builds/)。
    *   下载 `ffmpeg-git-full.7z` 或 `ffmpeg-release-essentials.zip`。

2.  **解压**：
    *   将压缩包解压到一个固定位置，例如 `C:\ffmpeg`。
    *   解压后，你应该能找到 `bin` 文件夹，里面有 `ffmpeg.exe`。
    *   路径示例：`C:\ffmpeg\bin\ffmpeg.exe`

3.  **配置环境变量 (Path)**：
    *   按 `Win + S` 搜索“编辑系统环境变量”。
    *   点击“环境变量”按钮。
    *   在“系统变量”区域找到 `Path`，选中并点击“编辑”。
    *   点击“新建”，输入 `ffmpeg.exe` 所在的 `bin` 目录路径（例如 `C:\ffmpeg\bin`）。
    *   连续点击“确定”保存。

4.  **验证**：
    *   打开一个新的 CMD 或 PowerShell 窗口。
    *   输入 `ffmpeg -version`。
    *   如果显示了版本信息，说明安装成功。

## 3. 首次运行与模型下载

首次点击“识别”按钮时，软件会自动下载 Whisper 的模型文件（默认为 `base` 模型，约 140MB）。

*   **现象**：点击识别后，可能会卡顿一小会儿，这是因为正在下载模型。
*   **缓存位置**：模型通常保存在用户目录下的 `.cache/whisper` 文件夹中。
*   **离线使用**：一旦下载完成，后续使用无需联网。

## 4. 常见问题

**Q: 点击识别后提示“缺少依赖库 (Whisper/Torch)”？**
A: 请确保您运行了 `pip install openai-whisper`，并且安装过程中没有报错。

**Q: 提示“未检测到 ffmpeg”？**
A: 请仔细检查第 2 步，确保 `ffmpeg` 的 `bin` 目录已经添加到了系统的 `Path` 环境变量中，并且重启了软件（甚至重启电脑）。

**Q: 识别速度很慢？**
A: 语音识别需要大量的 CPU 算力。如果您有 NVIDIA 显卡并配置了 CUDA 版本的 PyTorch，速度会快很多。但在纯 CPU 模式下，处理长音频确实需要一些时间。

**Q: 软件卡死？**
A: 我们已优化了防卡死机制。如果依然卡死，请检查是否在识别的同时尝试播放文件，或者磁盘读写是否过高。
