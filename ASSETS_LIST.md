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
| `resume.png` | 图片 | **继续按钮** (暂停时显示) | 窗口短边的30% | 显示在正中央，用于暂停后恢复 |
| `start_btn.png` | 图片 | **开始按钮** (右上角) | 窗口短边的37.5% | 自动缩放，建议原图200x200 |
| `time_bg.png` | 图片 | **时间背景** | 建议 150x40+ | 显示在时间数字下方，**随字体大小缩放** |
| `help.png` | 图片 | **首次启动帮助图** | 建议 800x600+ | `assets/help.png` 或 `help.jpg` |
| `icon.png` | 图片 | **默认应用图标** | 256x256 | 用于托盘和窗口 |

### 1.1 节日与季节专属图片 (Holiday & Season Specific Images)
| 文件夹路径 (Path) | 类型 (Type) | 描述 (Description) | 备注 (Note) |
| :--- | :--- | :--- | :--- |
| `assets/holidays/{id}/icon.png` | 图片 | **节日专属图标** | 节日当天自动切换 |
| `assets/seasons/{id}/icon.png` | 图片 | **季节专属图标** | 对应季节自动切换 |

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

## 4. 音频系统 (Audio System)
音频资源可存放在本地 `sounds/` 目录或云端同步目录 `cloud/`。程序启动时会自动合并这两个目录的内容。

### 4.1 基础分类 (Basic Categories)
**存放路径:** `sounds/{category}/` 或 `cloud/{category}/`

| 分类文件夹 (Folder) | 描述 (Description) | 触发时机 (Trigger) |
| :--- | :--- | :--- |
| `start/` | 专注开始 | 点击开始按钮，开始工作计时 |
| `end/` | 休息开始 | 工作计时结束，进入休息状态 |
| `interval/` | 专注中途提醒 | 工作期间达到设定的间隔时间 (10/15/30min) |
| `resume/` | 恢复工作 | 暂停后点击继续按钮，或休息结束进入新一轮工作 |
| `exit/` | 退出程序 | 通过菜单或作弊码退出软件 |

### 4.2 节日与季节语音 (Holiday & Season Voices)
**存放路径:** `sounds/holidays/` 或 `sounds/seasons/`

| 路径格式 (Path Pattern) | 描述 (Description) | 备注 (Note) |
| :--- | :--- | :--- |
| `holidays/{id}/greeting/` | **节日问候** | 节日当天**首次启动**时必播 |
| `holidays/{id}/{category}/` | **节日专属事件** | 节日当天**首次触发**对应事件时必播 |
| `seasons/{id}/{category}/` | **季节专属事件** | 对应季节内与基础语音等概率混合采样 |

### 4.3 播放逻辑 (Playback Logic)
1. **采样池**: 对应分类下的所有文件组成一个采样池。
2. **随机播放**: 若文件夹内有多个文件，随机抽取一个播放。
3. **优先级**: 
   - 节日当天：`greeting` 首次启动必播；各分类 `category` 当天首次触发必播。
   - 之后：基础语音、节日语音、当前季节语音混合随机采样。
4. **格式支持**: 推荐使用 `.mp3` 或 `.wav` 格式。

---
### 云端资源说明 (Cloud Resources)
`cloud/` 目录结构必须与 `sounds/` 完全一致。用户收到的分发包仅包含 `exe` 和 `sounds/`，应用首次运行后会自动生成 `cloud/` 目录。
