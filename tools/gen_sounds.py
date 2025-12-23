import asyncio
import os
import edge_tts

# 语音配置
VOICE = "zh-CN-XiaoxiaoNeural"

# 默认单一文件
DEFAULTS = {
    "sounds/start.mp3": "开始工作了，打起精神来！",
    "sounds/end.mp3": "工作结束啦，辛苦了，快休息一下吧。",
    "sounds/rest_start.mp3": "休息时间开始，放松眼睛和肩膀哦。",
    "sounds/interval.mp3": "时间过得很快，注意保持专注哦。",
    "sounds/resume.mp3": "休息结束，欢迎回来，继续加油！",
    "sounds/exit.mp3": "再见啦，期待下次见面！",
}

# 随机池扩充
RANDOM_POOLS = {
    "start": [
        "新的番茄钟开始了，加油！",
        "专注当下，开始工作吧。",
        "准备好了吗？让我们开始专注。",
        "又是一个新的开始，保持高效哦。",
        "深呼吸，进入心流状态。",
    ],
    "end": [
        "番茄钟结束了，休息一下吧。",
        "太棒了，你完成了一个番茄钟。",
        "休息时间到，站起来活动活动。",
        "工作暂停，享受你的休息时间。",
        "这一阶段完成了，去喝杯水吧。",
    ],
    "interval": [
        "已经过去一段时间了，还在专注吗？",
        "保持节奏，你做得很好。",
        "喝口水，继续保持专注。",
        "不要分心哦，正在计时中。",
        "坚持就是胜利，继续加油。",
    ],
    "resume": [
        "休息结束，让我们回到工作中。",
        "充电完毕，继续开始吧。",
        "回到专注模式，加油。",
        "下一段旅程开始了。",
        "好了，收心，继续干活。",
    ],
    "exit": [
        "拜拜，下次见！",
        "程序即将关闭，祝你生活愉快。",
        "今天辛苦了，好好休息哦。",
        "记得明天也要来打卡哦，再见。",
        "关闭中，我们下次再会。",
    ]
}

async def generate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    print(f"正在使用语音: {VOICE} 生成测试音频...")
    
    # 1. 生成默认音频
    for rel_path, text in DEFAULTS.items():
        full_path = os.path.join(base_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        print(f"生成默认 {rel_path} : {text}")
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(full_path)
        
    # 2. 生成随机池音频
    for cat, texts in RANDOM_POOLS.items():
        for i, text in enumerate(texts, 1):
            rel_path = f"sounds/random/{cat}/{i}.mp3"
            full_path = os.path.join(base_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            print(f"生成随机 {rel_path} : {text}")
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(full_path)

if __name__ == "__main__":
    try:
        asyncio.run(generate())
        print("所有音频生成完毕！")
    except Exception as e:
        print(f"生成失败: {e}")
