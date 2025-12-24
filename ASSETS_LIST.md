# 资源文件清单 / Asset Requirements List

此文档列出了软件正式运行所需的全部资源文件。请按照以下目录结构准备您的正式素材。
This document lists all the resource files required for the official release. Please prepare your assets according to the directory structure below.

## 1. 核心动画与图片 (Core Animations & Images)
**存放目录 / Directory:** `assets/`

| 文件名/文件夹 (File/Folder) | 类型 (Type) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- | :--- |
| `idle/` | **文件夹** | **待机/工作状态**动画序列 | 400x400+ | 放入 `0.png`, `1.png`, `2.png`... (按文件名排序播放) |
| `paused/` | **文件夹** | **休息/暂停状态**动画序列 | 400x400+ | 放入 `0.png`, `1.png`, `2.png`... (按文件名排序播放) |
| `idle.png` | 图片 | (备用) **待机/工作**静帧 | 400x400+ | 如果 `idle/` 文件夹不存在或为空，将使用此图 |
| `paused.png` | 图片 | (备用) **休息/暂停**静帧 | 400x400+ | 如果 `paused/` 文件夹不存在或为空，将使用此图 |
| `resume.png` | 图片 | **继续按钮** (暂停时显示) | 100x100 | 显示在人物中间 |
| `start_btn.png` | 图片 | **开始按钮** (右上角) | 50x50 | 图标 |

## 2. 菜单图标 (Menu Icons) - 手绘风格
**存放目录 / Directory:** `assets/menu/`
*注意：右键菜单的所有图标均需为手绘风格。*

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `check.png` | **选中状态** (对勾) | 20x20 | **新增** 用于指示开关状态 (如"置顶"、"退出语音") |
| `pause.png` | **暂停** | 32x32 | |
| `stop.png` | **结束** | 32x32 | |
| `reset.png` | **重置** | 32x32 | |
| `setting.png` | **设置** | 32x32 | (预留) |
| `pin.png` | **置顶** | 32x32 | (仅作图标展示，可选) |
| `voice.png` | **声音** | 32x32 | (仅作图标展示，可选) |
| `exit.png` | **退出** | 32x32 | |

## 3. 手写数字 (Handwritten Digits)
**存放目录 / Directory:** `assets/digits/`
*如果缺少这些文件，软件将回退使用系统默认字体。*

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `0.png` ~ `9.png` | 数字 0-9 | 高度约 80px | PNG透明背景 |
| `colon.png` | 冒号 (:) | 与数字高度匹配 | PNG透明背景 |

## 4. 核心音效 (Core Sounds)
**存放目录 / Directory:** `sounds/`

| 文件名 (Filename) | 描述 (Description) | 格式 |
| :--- | :--- | :--- |
| `start.mp3` | **开始工作**提示音 | MP3 |
| `end.mp3` | **工作结束**提示音 | MP3 |
| `rest_start.mp3` | **开始休息**提示音 | MP3 |
| `interval.mp3` | **定时提醒** (如每10分钟) | MP3 |
| `resume.mp3` | **继续工作**提示音 | MP3 |
| `exit.mp3` | **退出程序**提示音 | MP3 |

## 5. 随机语音池 (Random Voice Pools)
**存放目录 / Directory:** `sounds/random/`
*在对应目录下放入多个 `.mp3` 文件，软件将随机播放。*

- `start/` : 开始工作
- `end/` : 工作结束
- `interval/` : 定时提醒 (间隔语音)
- `resume/` : 继续工作
- `exit/` : 退出程序

---
### 云端资源 (Cloud Resources)
如果启用了云端更新，请确保远程仓库 (`pomodoro-assets`) 保持相同的目录结构。
