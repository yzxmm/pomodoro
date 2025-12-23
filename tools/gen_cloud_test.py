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
