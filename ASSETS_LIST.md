# 资源文件清单 / Asset Requirements List

此文档列出了软件正式运行所需的全部资源文件。请按照以下目录结构准备您的正式素材。
This document lists all the resource files required for the official release. Please prepare your assets according to the directory structure below.

## 1. 核心动画与图片 (Core Animations & Images)
**存放目录 / Directory:** `assets/`

| 文件名/文件夹 (File/Folder) | 类型 (Type) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- | :--- |
| `idle.png` | 图片 | **待机**状态静帧 (Start) | 400x400+ | 软件启动/调整时间时的默认状态 |
| `paused.png` | 图片 | **暂停**状态静帧 | 400x400+ | 倒计时暂停时显示 |
| `idle/` | **文件夹** | **工作**状态动画序列 | 400x400+ | 放入 `0.png`... (倒计时进行中播放) |
| `paused/` | **文件夹** | **休息**状态动画序列 | 400x400+ | 放入 `0.png`... (休息时间进行中播放) |
| `resume.png` | 图片 | **继续按钮** (暂停时显示) | 窗口短边的30% | 显示在右上角，用于暂停后恢复 |
| `start_btn.png` | 图片 | **开始按钮** (右上角) | 窗口短边的37.5% | 自动缩放，建议原图200x200 |
| `time_bg.png` | 图片 | **时间背景** | 建议 150x40+ | 显示在时间数字下方，**随字体大小缩放** |

## 2. 菜单图标 (Menu Icons) - 手绘风格
**存放目录 / Directory:** `assets/menu/`
*注意：右键菜单的所有图标均需为手绘风格。*

| 文件名 (Filename) | 类型 (Type) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- | :--- |
| `menu/check.png` | 图片 | 菜单选中状态图标 | 24x24 | 通用勾选图标 |
| `menu/pause.png` | 图片 | **暂停**按钮 | 32x32 | 菜单第一排 |
| `menu/pin.png` | 图片 | **置顶**按钮 | 32x32 | 菜单第一排 |
| `menu/exit.png` | 图片 | **退出**按钮 | 32x32 | 菜单第一排 |
| `menu/interval_0.png` | 图片 | **间隔语音关闭**状态 | 自定义 | 菜单中间，显示当前状态 |
| `menu/interval_10.png` | 图片 | **间隔语音10分钟**状态 | 自定义 | 菜单中间，显示当前状态 |
| `menu/interval_15.png` | 图片 | **间隔语音15分钟**状态 | 自定义 | 菜单中间，显示当前状态 |
| `menu/interval_30.png` | 图片 | **间隔语音30分钟**状态 | 自定义 | 菜单中间，显示当前状态 |
| `menu/exit_voice.png` | 图片 | **退出语音**按钮 | 自定义 | 菜单底部，点击切换 |
| `menu/update.png` | 图片 | **检查更新**按钮 | 自定义 | 菜单底部，点击切换 |
| `menu/menu_bg.png` | 图片 | **菜单背景图** | 建议 200x200+ | 菜单的底图（自动平铺或拉伸） |

## 3. 手写数字 (Handwritten Digits)
**存放目录 / Directory:** `assets/digits/`
*如果缺少这些文件，软件将回退使用系统默认字体。*

| 文件名 (Filename) | 描述 (Description) | 推荐尺寸 (Size) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `0.png` ~ `9.png` | 数字 0-9 | 高度约 80px | PNG透明背景 |
| `colon.png` | 冒号 (:) | 与数字高度匹配 | PNG透明背景 |
| `infinite.png` | 无穷符号 (∞) | 与数字高度匹配 | PNG透明背景 (用于本轮结束自动退出时的休息时间显示) |

## 4. 音效资源 (Sound Assets)
**存放目录 / Directory:** `sounds/`

所有音效文件都存放在 `sounds` 目录下对应的分类文件夹中。

### 基础结构
你可以直接放入单个文件，或者创建文件夹放入多个文件（程序会随机播放）。

| 分类 (Category) | 文件夹路径 (Folder Path) | 备用单文件 (Legacy Single File) | 描述 (Description) |
| :--- | :--- | :--- | :--- |
| **开始工作** | `sounds/start/` | `sounds/start.mp3` | 开始工作提示音 |
| **工作结束** | `sounds/end/` | `sounds/end.mp3` | 工作结束提示音 |
| **定时提醒** | `sounds/interval/` | `sounds/interval.mp3` | 间隔提醒 (如每10分钟) |
| **继续工作** | `sounds/resume/` | `sounds/resume.mp3` | 暂停后继续工作 |
| **退出程序** | `sounds/exit/` | `sounds/exit.mp3` | 退出程序提示音 |

*注：如果文件夹中有多个文件，每次触发时会随机播放其中一个。如果文件夹为空，会尝试寻找同名的 `.mp3` 单文件。*

### 高级用法 (季节与标签)
你可以在分类文件夹中创建子文件夹来实现季节或标签分类：

- **季节/节日**: `sounds/start/winter/`
- **标签**: `sounds/start/tags/miku/` (使用 `POMODORO_TAG=miku` 激活)

---
### 云端资源 (Cloud Resources)
如果启用了云端更新，请确保远程仓库 (`pomodoro-assets`) 保持相同的目录结构。
