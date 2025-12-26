# 项目交接文档 (To: Home Trae)

**背景**: 用户希望在家里的电脑上继续开发番茄钟项目，重点是使用 Qt Designer 可视化调整右键菜单布局。

## 一、 最近开发进度总结 (Context)
这几天我们主要完成了以下功能改进和 Bug 修复：

### 1. 核心交互优化
*   **空格键控制**: 实现了空格键全状态控制（空闲->开始，工作中->暂停，暂停->继续）。
    *   *技术细节*: 解决了焦点丢失问题，在点击按钮或暂停后强制 `setFocus()`。
*   **Alt 键切换调整模式**:
    *   仅在**空闲/暂停**且**窗口激活**时生效。
    *   切换调整 **工作时间** 和 **休息时间**。
    *   休息模式下，若开启“自动退出”，时间显示为 **∞ (infinite.png)**。
*   **窗口大小适配**:
    *   **智能初始化**: 首次启动高度设为屏幕高度的 35%。
    *   **Shift + 滚轮**: 实现了整体窗口缩放（移除了右下角难用的调整手柄）。

### 2. UI/UX 细节
*   **时间牌稳定性**: 修复了时间牌数字忽大忽小的问题（强制固定比例，不再随内容缩放）。
*   **暂停按钮**: 移至右上角，尺寸调整为短边的 30%，更易点击。
*   **右键菜单**:
    *   修复了背景不显示和白框问题。
    *   布局调整：功能图标在第一排，设置项在下方。
    *   样式优化：检查更新按钮改为“图片+对勾”形式。

### 3. 工程化
*   **打包**: 使用 PyInstaller 打包测试通过。
*   **资源**: 更新了 `ASSETS_LIST.md`，增加了 `infinite.png` 等手绘资源需求。

---

## 二、 下一步任务：Qt Designer 可视化布局
用户想尝试使用 Qt Designer 来调整右键菜单 (`image_menu.py`) 的布局，以替代目前繁琐的手写代码。

### 1. 启动 Designer
告诉用户在终端运行以下命令启动设计器：
```powershell
pyside6-designer
```
*(如果找不到命令，引导用户在 `.venv/Lib/site-packages/PySide6/designer.exe` 寻找)*

### 2. 创建菜单模板
1.  启动后，选择新建 **Widget** (或者 **Frame**)。
2.  **设置属性** (右侧属性栏):
    *   `objectName`: `ContextMenu`
    *   `minimumWidth`: `250`
    *   `styleSheet`: (复制现有的 CSS 样式，例如 `border-image: url(...)`，或者暂时留空)

### 3. 布局实战 (Grid Layout)
指导用户使用 **Grid Layout** 复刻现有布局：
*   **拖拽控件**: 从左侧 `Widget Box` 拖入 `Push Button`。
*   **应用布局**: 选中窗体空白处，点击工具栏上的 **Grid Layout** 图标 (九宫格形状)。
*   **排列按钮**:
    *   **第一排 (功能区)**: `暂停`, `置顶`, `间隔`, `退出` (放在 Row 0, Col 0-3)
    *   **第二排 (检查更新)**: `检查更新` (放在 Row 1, Col 0, 拖动边缘使其跨越 4 列 -> `rowSpan: 1`, `columnSpan: 4`)
    *   **第三排 (退出语音)**: `退出语音` (放在 Row 2, Col 0, 同样跨越 4 列)

### 4. 导出与集成
设计完成后保存为 `menu.ui`。

**方案 A: 编译成 Python 代码 (推荐，轻量化)**
运行命令：
```powershell
pyside6-uic menu.ui -o ui_menu.py
```
然后修改 `image_menu.py`，导入这个类并继承它，替换原本的手写 `setup_ui`。

**方案 B: 直接加载 (快速测试)**
```python
from PySide6.QtUiTools import QUiLoader
# ...
loader = QUiLoader()
self.ui = loader.load("menu.ui", self)
```

### 5. 关键提示
*   记得把按钮的 `objectName` 改成有意义的名字 (如 `btn_pause`, `btn_exit`)，方便代码调用。
*   图片资源在 Designer 里可能显示不出来 (路径问题)，告诉用户不用担心，代码里 `resolve_asset` 会处理好。

