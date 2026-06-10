import os
import time
import json
import subprocess
from playwright.sync_api import sync_playwright

def get_audio_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, text=True, check=True)
    return float(res.stdout.strip())

def main():
    workspace_dir = "/Users/junaidalam/Documents/D/claude-workspace/project-prf/dashboard"
    video_path = os.path.join(workspace_dir, "flocksense_demo_raw.webm")
    output_mp4 = os.path.join(workspace_dir, "flocksense_demo_voiceover.mp4")
    mixed_audio_path = os.path.join(workspace_dir, "mixed_voiceover.m4a")
    
    sections = [
        {
            "name": "intro",
            "text": "This is FlockSense — a real-time monitoring dashboard for commercial broiler sheds. It combines radar, temperature and humidity sensors, and AI analysis to give farm managers a live view of flock health, litter condition, and shed environment — all in one place."
        },
        {
            "name": "layers",
            "text": "The centrepiece is a live 3D model of the shed. Each tile represents one pen. Right now we're looking at Activity — green means the birds are moving normally, amber is moderate, red is an alert zone. You can switch layers instantly — here's Litter Condition, showing saturation levels across the floor. Temperature. Humidity. And Clustering — which flags abnormal bird pile-ups that often precede a health event. On the horizon, three additional layers are in beta: a Welfare Index that composites all signals into a single bird wellbeing score, FCR — feed conversion ratio estimated per pen — and an Approximate Weight layer derived from the radar point cloud. Early results are tracking within 2% of manual weigh-ins."
        },
        {
            "name": "sidebar",
            "text": "The sidebar gives you the key numbers at a glance. Flock Activity Index is 84 — trending up. Litter is 78% friable. Shed temperature averaging 29.4 degrees. Weight proxy is tracking 1.7% above the Ross 308 breed standard at Day 18. And right now there are 3 active alerts — one critical."
        },
        {
            "name": "health",
            "text": "The Bird Health tab goes deeper. This activity chart shows Zone 4L declining sharply over 7 days — from 80 down to 48 today, well below every other zone. The clustering heatmap confirms early-morning pile-ups intensifying through the week. And the pre-mortality risk grid flags which pens need a walkthrough — right now, Zone 4L Row 3 is on monitor status."
        },
        {
            "name": "ops",
            "text": "Shed Operations shows the litter floor map — a top-down view of every pen coloured by FPD risk score. Zone 2R is flagged in red with a score of 7.2 — the system is recommending a drinker line inspection. Below that, the fault log shows AI-generated recommended actions for every environmental event in the last 24 hours."
        },
        {
            "name": "ai",
            "text": "Finally, the AI Assistant lets farm managers ask plain-language questions about their flock. Everything runs on-site — a Raspberry Pi 4 at the edge — with 6 radar nodes and 12 climate sensors online. FlockSense turns raw sensor data into decisions, faster."
        }
    ]
    
    # -------------------------------------------------------------
    # 1. Generate Voiceover MP3s using edge-tts
    # -------------------------------------------------------------
    print("Step 1: Generating voiceovers with edge-tts...")
    temp_audio_files = []
    durations = []
    
    for idx, sec in enumerate(sections):
        temp_file = os.path.join(workspace_dir, f"sec_{idx}.mp3")
        temp_audio_files.append(temp_file)
        
        # Use edge-tts with Andrew's natural neural voice
        # We use a speed rate of +12% for a natural yet engaging presentation pace
        cmd = [
            "edge-tts",
            "--voice", "en-US-AndrewNeural",
            "--rate", "+12%",
            "--text", sec["text"],
            "--write-media", temp_file
        ]
        print(f"Generating audio for: {sec['name']}")
        subprocess.run(cmd, check=True)
        
        # Measure duration
        dur = get_audio_duration(temp_file)
        durations.append(dur)
        print(f"  Duration: {dur:.2f} seconds")
        
    # Calculate sequential start delays
    delays = [0.0]
    for i in range(len(durations) - 1):
        delays.append(delays[-1] + durations[i])
        
    print("\nCalculated timeline offsets:")
    for idx, sec in enumerate(sections):
        print(f"  Section {idx} ({sec['name']}): Start: {delays[idx]:.2f}s | Duration: {durations[idx]:.2f}s")
        
    # -------------------------------------------------------------
    # 2. Record visual demo with Playwright timed to audio durations
    # -------------------------------------------------------------
    print("\nStep 2: Recording dashboard demo timed to speech durations...")
    file_url = f"file://{os.path.join(workspace_dir, 'index.html')}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=workspace_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        page.goto(file_url)
        page.wait_for_load_state("networkidle")
        
        # Inject Three.js element coordinates helpers & Fake Visual Cursor
        page.evaluate("""() => {
            window.getCoords = function(idx) {
                if (!window.camera || !window.renderer || !window.penMeshes) return null;
                const mesh = window.penMeshes[idx];
                const vector = new THREE.Vector3();
                mesh.getWorldPosition(vector);
                vector.project(window.camera);
                const canvas = window.renderer.domElement;
                const x = (vector.x * 0.5 + 0.5) * canvas.clientWidth;
                const y = (-(vector.y * 0.5) + 0.5) * canvas.clientHeight;
                const rect = canvas.getBoundingClientRect();
                return { x: rect.left + x, y: rect.top + y };
            }
            
            // Inject fake visual cursor
            const cursor = document.createElement('div');
            cursor.id = 'demo-cursor';
            cursor.style.position = 'fixed';
            cursor.style.width = '40px';
            cursor.style.height = '40px';
            cursor.style.borderRadius = '50%';
            cursor.style.backgroundColor = 'rgba(255, 193, 7, 0.4)'; // Amber
            cursor.style.border = '2px solid rgba(255, 193, 7, 1)';
            cursor.style.pointerEvents = 'none';
            cursor.style.zIndex = '999999';
            cursor.style.transition = 'left 0.4s cubic-bezier(0.22, 1, 0.36, 1), top 0.4s cubic-bezier(0.22, 1, 0.36, 1), transform 0.1s ease, background-color 0.1s ease';
            cursor.style.transform = 'translate(-50%, -50%)'; // center on mouse
            cursor.style.left = '50%';
            cursor.style.top = '50%';
            document.body.appendChild(cursor);

            document.addEventListener('mousemove', (e) => {
                cursor.style.left = e.clientX + 'px';
                cursor.style.top = e.clientY + 'px';
            });
            document.addEventListener('mousedown', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(0.6)';
                cursor.style.backgroundColor = 'rgba(255, 193, 7, 0.8)';
            });
            document.addEventListener('mouseup', () => {
                cursor.style.transform = 'translate(-50%, -50%) scale(1)';
                cursor.style.backgroundColor = 'rgba(255, 193, 7, 0.4)';
            });
        }""")
        
        time.sleep(2) # Stabilize initial load
        
        start_time = time.time()
        
        def wait_until(target_sec):
            elapsed = time.time() - start_time
            rem = target_sec - elapsed
            if rem > 0:
                page.wait_for_timeout(rem * 1000)
                
        # --- [0] INTRO ---
        dur_intro = durations[0]
        print(f"Recording INTRO (duration: {dur_intro:.2f}s)...")
        box = page.locator("#shed-container").bounding_box()
        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        
        steps = 100
        for i in range(steps):
            page.mouse.move(start_x - i * 3.5, start_y)
            wait_until(((dur_intro - 1.5) / steps) * (i + 1))
            
        page.mouse.up()
        wait_until(delays[1])
        
        # --- [1] LAYERS ---
        dur_layers = durations[1]
        print(f"Recording LAYERS (duration: {dur_layers:.2f}s)...")
        
        def hover_clustering():
            coords = page.evaluate("window.getCoords(15)")
            if coords: page.mouse.move(coords["x"], coords["y"])
                
        actions = [
            lambda: page.click('button.layer-btn[data-layer="litter"]'),
            lambda: page.click('button.layer-btn[data-layer="temperature"]'),
            lambda: page.click('button.layer-btn[data-layer="humidity"]'),
            lambda: page.click('button.layer-btn[data-layer="clustering"]'),
            hover_clustering,
            lambda: page.click('button.layer-btn[data-layer="welfare"]'),
            lambda: page.click('button.layer-btn[data-layer="fcr"]'),
            lambda: page.click('button.layer-btn[data-layer="weight"]'),
            lambda: page.click('button.layer-btn[data-layer="activity"]')
        ]
        
        for i, act in enumerate(actions):
            act()
            wait_until(delays[1] + (dur_layers / len(actions)) * (i + 1))
            
        wait_until(delays[2])
        
        # --- [2] SIDEBAR ---
        dur_sidebar = durations[2]
        print(f"Recording SIDEBAR (duration: {dur_sidebar:.2f}s)...")
        cards = page.query_selector_all('.kpi-sidebar .kpi-card')
        for i, card in enumerate(cards):
            card.scroll_into_view_if_needed()
            wait_until(delays[2] + (dur_sidebar / max(1, len(cards))) * (i + 1))
            
        wait_until(delays[3])
        
        # --- [3] BIRD HEALTH ---
        dur_health = durations[3]
        print(f"Recording BIRD HEALTH (duration: {dur_health:.2f}s)...")
        
        def health_act_1(): page.click('button[data-tab="birdhealth"]')
        def health_act_2():
            chart_box = page.locator('#activity-chart').bounding_box()
            if chart_box: page.mouse.move(chart_box["x"] + chart_box["width"] * 0.78, chart_box["y"] + chart_box["height"] * 0.75)
        def health_act_3(): page.locator('#clustering-canvas').scroll_into_view_if_needed()
        def health_act_4():
            monitor_cell = page.locator('#premort-cell-15')
            monitor_cell.scroll_into_view_if_needed()
        def health_act_5():
            monitor_cell = page.locator('#premort-cell-15')
            cell_box = monitor_cell.bounding_box()
            if cell_box: page.mouse.move(cell_box["x"] + cell_box["width"]/2, cell_box["y"] + cell_box["height"]/2)
            
        health_actions = [health_act_1, health_act_2, health_act_3, health_act_4, health_act_5]
        for i, act in enumerate(health_actions):
            act()
            wait_until(delays[3] + (dur_health / len(health_actions)) * (i + 1))
            
        wait_until(delays[4])
        
        # --- [4] OPERATIONS ---
        dur_ops = durations[4]
        print(f"Recording OPERATIONS (duration: {dur_ops:.2f}s)...")
        
        def ops_act_1(): page.click('button[data-tab="operations"]')
        def ops_act_2():
            svg_pen = page.locator('#svg-pen-31')
            svg_pen.scroll_into_view_if_needed()
            pen_box = svg_pen.bounding_box()
            if pen_box: page.mouse.move(pen_box["x"] + pen_box["width"]/2, pen_box["y"] + pen_box["height"]/2)
        def ops_act_3(): page.locator('.fault-table').scroll_into_view_if_needed()
        def ops_act_4():
            active_row = page.locator('.fault-table tr:has-text("ACTIVE")')
            row_box = active_row.bounding_box()
            if row_box: page.mouse.move(row_box["x"] + row_box["width"]/2, row_box["y"] + row_box["height"]/2)
            
        ops_actions = [ops_act_1, ops_act_2, ops_act_3, ops_act_4]
        for i, act in enumerate(ops_actions):
            act()
            wait_until(delays[4] + (dur_ops / len(ops_actions)) * (i + 1))
            
        wait_until(delays[5])
        
        # --- [5] AI ASSISTANT ---
        dur_ai = durations[5]
        print(f"Recording AI ASSISTANT (duration: {dur_ai:.2f}s)...")
        
        def ai_act_1(): page.click('button[data-tab="ai"]')
        def ai_act_2(): page.click('button.quick-chip:has-text("What is the current FPD risk")')
        def ai_act_3(): page.click('#ai-bubble')
        def ai_act_4():
            page.evaluate("""() => {
                const overlay = document.createElement('div');
                overlay.style.position = 'fixed';
                overlay.style.inset = '0';
                overlay.style.background = 'black';
                overlay.style.zIndex = '999999';
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 1.5s ease-in-out';
                document.body.appendChild(overlay);
                setTimeout(() => { overlay.style.opacity = '1'; }, 50);
            }""")
            
        ai_actions = [ai_act_1, ai_act_2, ai_act_3, ai_act_4]
        for i, act in enumerate(ai_actions):
            act()
            wait_until(delays[5] + (dur_ai / len(ai_actions)) * (i + 1))
            
        wait_until(delays[5] + dur_ai)
        
        # Get recorded video path
        video_filename = page.video.path()
        context.close()
        browser.close()
        
    # Copy temporary recorded video to our workspace raw path
    print(f"Video recorded to: {video_filename}")
    subprocess.run(["cp", video_filename, video_path], check=True)
    
    # -------------------------------------------------------------
    # 3. Mix audio tracks sequentially
    # -------------------------------------------------------------
    print("\nStep 3: Mixing audio segments with FFmpeg...")
    filter_complex = ""
    for idx, sec in enumerate(sections):
        delay_ms = int(delays[idx] * 1000)
        filter_complex += f"[{idx}:a]adelay={delay_ms}|{delay_ms}[a{idx}];"
        
    mix_inputs = "".join([f"[a{i}]" for i in range(len(sections))])
    filter_complex += f"{mix_inputs}amix=inputs={len(sections)}:duration=longest[outa]"
    
    ffmpeg_mix_cmd = ["ffmpeg", "-y"]
    for f in temp_audio_files:
        ffmpeg_mix_cmd.extend(["-i", f])
    ffmpeg_mix_cmd.extend(["-filter_complex", filter_complex, "-map", "[outa]", "-c:a", "aac", mixed_audio_path])
    subprocess.run(ffmpeg_mix_cmd, check=True)
    
    # -------------------------------------------------------------
    # 4. Merge video and audio into final MP4
    # -------------------------------------------------------------
    print("\nStep 4: Merging visual and mixed audio into final H.264 MP4...")
    ffmpeg_merge_cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", mixed_audio_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-map", "0:v:0",
        "-map", "1:a:0",
        output_mp4
    ]
    subprocess.run(ffmpeg_merge_cmd, check=True)
    print(f"\nFinal video successfully built at: {output_mp4}")
    
    # -------------------------------------------------------------
    # 5. Cleanup temp files
    # -------------------------------------------------------------
    print("\nCleaning up temporary files...")
    for f in temp_audio_files:
        try:
            os.remove(f)
        except Exception:
            pass
    try:
        os.remove(mixed_audio_path)
        os.remove(video_path)
        os.remove(video_filename) # Playwright temp video
    except Exception:
        pass
        
    print("Success! Complete video generated without overlaps.")

if __name__ == "__main__":
    main()
