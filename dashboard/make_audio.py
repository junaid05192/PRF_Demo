import os
import subprocess

def generate_voiceover():
    workspace_dir = "/Users/junaidalam/Documents/D/claude-workspace/project-prf/dashboard"
    video_path = os.path.join(workspace_dir, "flocksense_demo.webm")
    output_path = os.path.join(workspace_dir, "flocksense_demo_voiceover.mp4")
    
    sections = [
        {
            "text": "This is FlockSense — a real-time monitoring dashboard for commercial broiler sheds. It combines radar, temperature and humidity sensors, and AI analysis to give farm managers a live view of flock health, litter condition, and shed environment — all in one place.",
            "delay_ms": 0
        },
        {
            "text": "The centrepiece is a live 3D model of the shed. Each tile represents one pen. Right now we're looking at Activity — green means the birds are moving normally, amber is moderate, red is an alert zone. You can switch layers instantly — here's Litter Condition, showing saturation levels across the floor. Temperature. Humidity. And Clustering — which flags abnormal bird pile-ups that often precede a health event. On the horizon, three additional layers are in beta: a Welfare Index that composites all signals into a single bird wellbeing score, FCR — feed conversion ratio estimated per pen — and an Approximate Weight layer derived from the radar point cloud. Early results are tracking within 2% of manual weigh-ins.",
            "delay_ms": 15000
        },
        {
            "text": "The sidebar gives you the key numbers at a glance. Flock Activity Index is 84 — trending up. Litter is 78% friable. Shed temperature averaging 29.4 degrees. Weight proxy is tracking 1.7% above the Ross 308 breed standard at Day 18. And right now there are 3 active alerts — one critical.",
            "delay_ms": 45000
        },
        {
            "text": "The Bird Health tab goes deeper. This activity chart shows Zone 4L declining sharply over 7 days — from 80 down to 48 today, well below every other zone. The clustering heatmap confirms early-morning pile-ups intensifying through the week. And the pre-mortality risk grid flags which pens need a walkthrough — right now, Zone 4L Row 3 is on monitor status.",
            "delay_ms": 60000
        },
        {
            "text": "Shed Operations shows the litter floor map — a top-down view of every pen coloured by FPD risk score. Zone 2R is flagged in red with a score of 7.2 — the system is recommending a drinker line inspection. Below that, the fault log shows AI-generated recommended actions for every environmental event in the last 24 hours.",
            "delay_ms": 80000
        },
        {
            "text": "Finally, the AI Assistant lets farm managers ask plain-language questions about their flock. Everything runs on-site — a Raspberry Pi 4 at the edge — with 6 radar nodes and 12 climate sensors online. FlockSense turns raw sensor data into decisions, faster.",
            "delay_ms": 100000
        }
    ]
    
    temp_files = []
    print("Generating voiceover audio segments using edge-tts...")
    for idx, sec in enumerate(sections):
        temp_file = os.path.join(workspace_dir, f"sec{idx}.mp3")
        temp_files.append(temp_file)
        
        # Use edge-tts with a high-quality neural voice to produce MP3 files
        cmd = ["edge-tts", "--voice", "en-US-AndrewNeural", "--text", sec["text"], "--write-media", temp_file]
        print(f"Generating segment {idx}...")
        subprocess.run(cmd, check=True)
        
    print("All segments generated successfully.")
    
    # Construct FFmpeg command to delay and mix the audio tracks
    # We delay each input using the 'adelay' filter and then combine them using 'amix'
    filter_complex = ""
    for idx, sec in enumerate(sections):
        delay = sec["delay_ms"]
        # adelay takes delays per channel, e.g., '15000|15000' for stereo
        filter_complex += f"[{idx}:a]adelay={delay}|{delay}[a{idx}];"
        
    mix_inputs = "".join([f"[a{i}]" for i in range(len(sections))])
    filter_complex += f"{mix_inputs}amix=inputs={len(sections)}:duration=longest[outa]"
    
    mixed_audio_path = os.path.join(workspace_dir, "mixed_voiceover.m4a")
    
    ffmpeg_mix_cmd = ["ffmpeg", "-y"]
    for f in temp_files:
        ffmpeg_mix_cmd.extend(["-i", f])
    ffmpeg_mix_cmd.extend(["-filter_complex", filter_complex, "-map", "[outa]", "-c:a", "aac", mixed_audio_path])
    
    print("Mixing audio segments with FFmpeg...")
    subprocess.run(ffmpeg_mix_cmd, check=True)
    print(f"Mixed voiceover saved to: {mixed_audio_path}")
    
    # Merge mixed audio with original video
    print("Merging audio with video and encoding to H.264/MP4...")
    ffmpeg_merge_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", mixed_audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_path
    ]
    subprocess.run(ffmpeg_merge_cmd, check=True)
    print(f"Merged video with voiceover saved to: {output_path}")
    
    # Cleanup temp files
    print("Cleaning up temporary audio files...")
    for f in temp_files:
        try:
            os.remove(f)
        except Exception:
            pass
    try:
        os.remove(mixed_audio_path)
    except Exception:
        pass
        
    print("Finished voiceover process successfully!")

if __name__ == "__main__":
    generate_voiceover()
