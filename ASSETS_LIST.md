# 资源文件清单 / Asset Requirements List

此文档列出了软件正式运行所需的全部资源文件。请按照以下目录结构准备您的正式素材。
This document lists all the resource files required for the official release. Please prepare your assets according to the directory structure below.

## 1. 核心图片 (Core Images)
**存放目录 / Directory:** `assets/`

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `idle.png` | **待机/工作状态**人物立绘 | 400x400 (或更大) | PNG透明背景 |
| `paused.png` | **休息/暂停状态**人物立绘 | 400x400 (同上) | PNG透明背景 (休息和暂停共用此图) |
| `resume.png` | **继续按钮** (暂停时显示) | 100x100 | PNG (显示在人物中间) |
| `start_btn.png` | **开始按钮** (右上角) | 50x50 | PNG图标 |

## 2. 菜单图标 (Menu Icons) - 手绘风格
**存放目录 / Directory:** `assets/menu/`
*注意：用户指定所有右键菜单图标均需为手绘风格。*

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `pause.png` | **暂停/继续**菜单项图标 | 32x32 | PNG 手绘风格 |
| `stop.png` | **结束**菜单项图标 | 32x32 | PNG 手绘风格 |
| `reset.png` | **重置**菜单项图标 | 32x32 | PNG 手绘风格 |
| `setting.png` | **设置**菜单项图标 | 32x32 | PNG 手绘风格 |
| `pin.png` | **置顶**图标 (切换状态) | 32x32 | PNG 手绘风格 |
| `voice.png` | **声音**开关图标 (通用) | 32x32 | PNG 手绘风格 |
| `exit.png` | **退出**菜单项图标 | 32x32 | PNG 手绘风格 |

## 3. 手写数字 (Handwritten Digits)
**存放目录 / Directory:** `assets/digits/`
*如果缺少这些文件，软件将回退使用系统默认字体显示时间。*

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `0.png` ~ `9.png` | 数字 0 到 9 | 高度一致 (如 80px) | PNG透明背景 |
| `colon.png` | 冒号 (:) | 与数字高度匹配 | PNG透明背景 |

## 4. 核心音效 (Core Sounds)
**存放目录 / Directory:** `sounds/`
*这些是必须的基础提示音。*

| 文件名 (Filename) | 描述 (Description) | 格式 (Format) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `start.mp3` | **开始工作**时的提示音 | MP3 | |
| `end.mp3` | **工作结束**时的提示音 | MP3 | |
| `rest_start.mp3` | **开始休息**时的提示音 | MP3 | |
| `interval.mp3` | **每N分钟**的默认提示音 | MP3 | (可选) 原名 ten.mp3 |
| `resume.mp3` | **暂停后继续**的默认提示音 | MP3 | (可选) |
| `exit.mp3` | **退出程序**时的提示音 | MP3 | (可选) |

## 5. 随机语音池 (Random Voice Pools)
**存放目录 / Directory:** `sounds/random/`
*这些是可选的，用于增加趣味性。软件会在对应事件发生时，从文件夹中随机抽取一个播放。*

| 目录名 (Folder) | 描述 (Description) | 内容 |
| :--- | :--- | :--- |
| `start/` | **开始工作**时的随机语音 | 放入多个 `.mp3` 文件 |
| `end/` | **工作结束**时的随机语音 | 放入多个 `.mp3` 文件 |
| `interval/` | **每N分钟**的整点报时/提醒 | 放入多个 `.mp3` 文件 |
| `resume/` | **暂停后继续**时的随机语音 | 放入多个 `.mp3` 文件 |
| `exit/` | **退出程序**时的随机语音 | 放入多个 `.mp3` 文件 |

---

### 云端自动下载说明 (Cloud Download)
如果您配置了云端下载功能，请确保服务器上的文件路径与上述结构完全一致。
例如：`http://your-server.com/sounds/start.mp3`
