import wave
import struct
import math
import os

def generate_tone(filename, duration=3.0, frequency=440.0):
    sample_rate = 44100
    n_frames = int(duration * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        data = []
        for i in range(n_frames):
            t = i / sample_rate
            value = int(32767.0 * math.sin(2 * math.pi * frequency * t))
            data.append(struct.pack('<h', value))
            
        wav_file.writeframes(b''.join(data))
    print(f"Generated: {filename}")

def main():
    # Find or create test source directory
    base_dir = os.getcwd()
    test_dir = os.path.join(base_dir, "test_audio_source")
    
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
        print(f"Created directory: {test_dir}")
    
    # Generate 5 test files with different tones
    frequencies = [261.63, 293.66, 329.63, 349.23, 392.00] # C4, D4, E4, F4, G4
    for i, freq in enumerate(frequencies):
        fname = f"test_voice_{i+1}.wav"
        fpath = os.path.join(test_dir, fname)
        generate_tone(fpath, frequency=freq)
        
    print(f"Done. Files are in {test_dir}")

if __name__ == "__main__":
    main()
