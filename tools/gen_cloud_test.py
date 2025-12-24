import asyncio
import os
import edge_tts

# 语音配置
VOICE = "zh-CN-XiaoxiaoNeural"

# 云端测试文件
SOUNDS = {
    "start/online_1.mp3": "这是云端语音测试一，来自互联网的声音。",
    "start/online_2.mp3": "这是云端语音测试二，下载成功了吗？",
    "start/online_3.mp3": "这是云端语音测试三，祝你工作愉快。",
    
    "end/online_1.mp3": "云端休息语音一，休息一下吧。",
    "end/online_2.mp3": "云端休息语音二，要注意劳逸结合。",
    "end/online_3.mp3": "云端休息语音三，喝口水休息片刻。",
    
    "interval/online_1.mp3": "云端提醒语音一，专注时间到了。",
    "interval/online_2.mp3": "云端提醒语音二，继续保持专注。",
    "interval/online_3.mp3": "云端提醒语音三，你做得很好。",
    
    "resume/online_1.mp3": "云端恢复语音一，回来继续工作吧。",
    "resume/online_2.mp3": "云端恢复语音二，让我们继续努力。",
    "resume/online_3.mp3": "云端恢复语音三，保持这个节奏。",
    
    "exit/online_1.mp3": "云端退出语音一，再见。",
    "exit/online_2.mp3": "云端退出语音二，下次见。",
    "exit/online_3.mp3": "云端退出语音三，工作辛苦了。",
}

async def generate():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(base_dir, "cloud")
    
    print(f"正在生成云端测试音频到: {target_dir}")
    
    for rel_path, text in SOUNDS.items():
        full_path = os.path.join(target_dir, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        print(f"生成 {rel_path} : {text}")
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(full_path)

if __name__ == "__main__":
    try:
        asyncio.run(generate())
        print("云端测试音频生成完毕！")
    except Exception as e:
        print(f"生成失败: {e}")
