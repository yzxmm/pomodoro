图标放置指南 (Icon Placement Guide)

请将您的应用图标（.png 格式）放入此文件夹。

命名规则：
1. 默认图标：
   - icon.png 或 default.png

2. 节日图标 (优先级最高)：
   - birthday.png (生日)
   - christmas.png (圣诞节)
   - new_year.png (元旦)
   - (对应 calendar_config.json 中的 holidays id)

3. 季节图标 (优先级第二)：
   - spring.png (春)
   - summer.png (夏)
   - autumn.png (秋)
   - winter.png (冬)
   - (对应 calendar_config.json 中的 seasons id)

程序会自动根据当前日期和节日加载对应的图标。
无需重启程序，设置生日或日期变更后会自动刷新。
