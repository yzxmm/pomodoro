# 打包指南 (Packaging Guide)

本文档介绍如何将 Pomodoro Widget 打包为 Windows 可执行文件 (.exe)。

## 1. 环境准备

确保你已经安装了 Python 3.12+ 和项目依赖。
此外，你需要安装 `pyinstaller`：

```bash
pip install pyinstaller
```

## 2. 快速打包

项目根目录下已经配置好了 `main.spec` 文件，直接运行以下命令即可打包：

```bash
pyinstaller main.spec
```
或者直接运行 `build.bat` 脚本。

打包过程可能需要几分钟。完成后，你会看到 `dist/` 文件夹。

## 3. 输出文件

打包成功后，可执行文件位于：
`dist/pomodoro_widget.exe`

## 4. 打包策略说明 (重要)

为了保持安装包体积轻量化，并利用云端分发功能，我们在打包时采取了以下策略：

### ✅ 包含的内容
- **核心代码**: 所有 `.py` 文件及依赖库。
- **界面资源**: `assets/` 文件夹下的所有图片。
- **基础语音**: 仅包含 `sounds/` 根目录下的 5 条默认语音文件：
  - `start.mp3`
  - `end.mp3`
  - `interval.mp3`
  - `resume.mp3`
  - `exit.mp3`

### ❌ 排除的内容
- **扩展语音库**: `sounds/random/` 文件夹及其下所有子文件**不会**被打包。
- **云端缓存**: `cloud/` 文件夹不会被打包。
- **原因**: 所有的扩展语音都应在程序首次运行时，通过内置的云端同步功能从 GitHub 下载。这确保了用户总是获得最新的语音包，且主程序体积保持最小。

## 5. 配置文件说明 (`main.spec`)

`main.spec` 是 PyInstaller 的配置文件，主要处理了以下事项：

- **资源包含**: 自动将 `assets` 文件夹和指定的 5 个音频文件打包进 exe 中。
- **隐藏控制台**: 设置 `console=False`，运行时不会弹出黑色命令行窗口。

```python
# 关键配置片段
datas = [
    ('assets', 'assets'),
    ('sounds/start.mp3', 'sounds'),
    ('sounds/end.mp3', 'sounds'),
    ...
]
```

## 6. 测试与验证

打包完成后，建议进行以下测试：

1. **启动测试**: 双击 `pomodoro_widget.exe`，确保程序能正常启动。
2. **云端下载测试**: 
   - 启动程序后，检查是否会自动触发云端下载（如果本地没有 `sounds/random` 且网络正常）。
   - 观察是否能在 `sounds/random` 下生成新的语音文件。
3. **保底测试**: 在未联网情况下，确保基础的 5 条语音能正常播放。
