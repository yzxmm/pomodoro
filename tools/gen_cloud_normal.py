import asyncio
import os
import edge_tts

# Voice configuration
VOICE = "zh-CN-XiaoxiaoNeural"

# Content definition
# 5 categories, 5 sentences each
SOUNDS = {
    "start": [
        "开始专注了，请保持安静。",
        "新的番茄钟开始了，加油。",
        "准备好进入工作状态了吗？",
        "让我们开始这段专注时光。",
        "计时开始，祝你效率倍增。"
    ],
    "end": [
        "番茄钟结束，休息一下吧。",
        "你完成了一个番茄钟，真棒。",
        "时间到，站起来活动活动。",
        "休息时间，放松眼睛。",
        "这段工作完成了，去喝杯水吧。"
    ],
    "interval": [
        "已经过去一半时间了，保持专注。",
        "注意坐姿，继续加油。",
        "深呼吸，回到当下的任务。",
        "别走神哦，还在计时呢。",
        "保持节奏，你做得很好。"
    ],
    "resume": [
        "休息结束，回到工作中来吧。",
        "充电完成，继续开始。",
        "欢迎回来，开始下一个番茄钟。",
        "让我们继续刚才的任务。",
        "收心了，准备开始工作。"
    ],
    "exit": [
        "退出程序，下次见。",
        "今天辛苦了，再见。",
        "祝你度过愉快的一天。",
        "关闭番茄钟，拜拜。",
        "期待下次和你一起专注。"
    ]
}

async def generate():
    # Base directory is pomodoro_git/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Target directory is pomodoro_git/cloud
    cloud_dir = os.path.join(base_dir, "cloud")
    
    print(f"Generating normal cloud sounds to: {cloud_dir}")
    print(f"Voice: {VOICE}")
    
    tasks = []
    
    for category, sentences in SOUNDS.items():
        # Place directly in the category folder (no 'normal' subfolder)
        target_subdir = os.path.join(cloud_dir, category)
        os.makedirs(target_subdir, exist_ok=True)
        
        for i, text in enumerate(sentences, 1):
            filename = f"{i}.mp3"
            full_path = os.path.join(target_subdir, filename)
            
            print(f"Generating {category}/{filename}: {text}")
            try:
                communicate = edge_tts.Communicate(text, VOICE)
                await communicate.save(full_path)
                await asyncio.sleep(1) # Add delay to avoid rate limiting
            except Exception as e:
                print(f"Error generating {full_path}: {e}")
                
    # await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(generate())
        print("All normal cloud sounds generated successfully!")
    except Exception as e:
        print(f"Generation failed: {e}")
