# 文件夹结构与语音放置指南 (Folder Structure & Sound Placement Guide)

本文档详细说明了应用程序的文件夹结构，以及如何添加自定义语音、图标和配置。

## 📂 目录总览

```text
Pomodoro_Widget/
├── assets/                  # 图片资源
│   ├── icons/               # [新增] 应用图标文件夹 (支持节日/季节动态图标)
│   ├── digits/              # 时间数字图片 (0-9)
│   ├── menu/                # 菜单按钮图片
│   └── ...                  # 其他界面图片 (idle.png, start_btn.png 等)
│
├── sounds/                  # 语音资源 (全量打包)
│   ├── start.mp3            # 默认开始语音 (必需)
│   ├── rest.mp3             # 默认休息语音 (必需)
│   ├── ...                  # 其他基础语音
│   │
│   ├── random/              # 随机语音池 (用于替换默认语音)
│   │   ├── start/           # "开始工作" 的随机语音
│   │   ├── rest/            # "休息一下" 的随机语音
│   │   ├── work_end/        # "工作结束" 的随机语音
│   │   └── ...
│   │
│   └── holidays/            # 特殊节日语音 (优先级最高)
│       ├── birthday/        # 生日专属
│       ├── christmas/       # 圣诞节专属
│       └── ...
│
├── calendar_config.json     # 季节与节日配置文件
├── settings.json            # 用户设置 (自动生成)
└── Pomodoro.exe             # 主程序
```

---

## 🎵 语音系统说明 (Voice System)

现在的语音系统分为三个层级，优先级依次递增：

### 1. 基础/季节语音 (Basic & Seasonal)
- **位置**: `sounds/random/{分类}/`
- **说明**: 
  - 这是日常使用的语音池。
  - 您可以直接放入 `.mp3` 或 `.wav` 文件。
  - **季节限定**: 如果您想添加特定季节的语音，请在分类下建立季节文件夹。
    - 例如: `sounds/random/start/winter/` (冬天的开始语音)
    - 季节 ID 请参考 `calendar_config.json` (spring, summer, autumn, winter 等)。

### 2. 特殊节日氛围 (Special Holidays - Ambience)
- **位置**: `sounds/holidays/{节日ID}/`
- **说明**: 
  - 当检测到特定节日（如生日、圣诞）时，**所有的** 语音播放（开始、休息、结束）都会从这里额外抽取音效进行混合。
  - **作用**: 营造全天候的节日氛围（如背景音乐、欢呼声）。
  - **示例**: `sounds/holidays/birthday/party_noise.mp3`

### 3. 节日问候 (Holiday Greetings - One-time)
- **位置**: `sounds/holidays/{节日ID}/greeting/`
- **说明**: 
  - 节日当天**第一次**打开软件时播放。
  - **作用**: 专属的节日祝福。
  - **示例**: `sounds/holidays/birthday/greeting/happy_birthday.mp3`

---

## 🖼️ 动态图标系统 (Dynamic Icons)

程序支持根据节日和季节自动更换应用图标。请将图标放入 `assets/icons/` 文件夹。

| 优先级 | 类型 | 文件名示例 | 说明 |
| :--- | :--- | :--- | :--- |
| **1 (最高)** | 节日/生日 | `birthday.png`<br>`christmas.png` | 对应 `calendar_config.json` 中的节日 ID |
| **2** | 季节 | `winter.png`<br>`spring.png` | 对应 `calendar_config.json` 中的季节 ID |
| **3 (默认)** | 默认 | `default.png`<br>`icon.png` | 没有任何特殊日子时显示 |

---

## 💡 离线与外置资源说明 (Offline & External Resources)

程序采用 **"内置优先 + 外置覆盖"** 的策略，为您提供最大的灵活性。

1.  **内置资源 (默认)**: 
    - 即使没有 `assets` 或 `sounds` 文件夹，程序也能正常运行。
    - 所有核心图片和语音都已打包在 `Pomodoro.exe` 内部。

2.  **外置资源 (自定义/Mod)**:
    - 如果您在 `Pomodoro.exe` 旁边放置了 `assets` 或 `sounds` 文件夹，程序会**优先读取**这里面的文件。
    - **用途**:
      - **下载语音**: 云端下载的语音会保存在外置的 `cloud` 文件夹中。
      - **更换图标**: 如果您想测试新图标，只需在 `assets/icons/` 放一张图片，无需重新打包程序。
      
**总结**: 
- 对于普通用户：**只有语音**需要下载（会自动生成外置 `cloud` 文件夹）。
- 对于开发者/DIY玩家：您可以随意创建外置文件夹来覆盖内置资源。
## ⚙️ 配置文件 (Configuration)

### calendar_config.json
此文件已内置于程序中，用于定义季节和节日逻辑。
**注意**: 普通用户无需修改此文件。如果您是开发者或需要测试新节日，可以在 `Pomodoro.exe` 同级目录下创建一个同名文件进行覆盖。

```json
{
    "seasons": [
        { "id": "winter", "months": [12, 1, 2] }
    ],
    "holidays": [
        { "id": "my_holiday", "month": 5, "days": [20, 21] }
    ]
}
```
添加后，只需在 `sounds/holidays/my_holiday` 放语音，或在 `assets/icons/my_holiday.png` 放图标，即可生效。
