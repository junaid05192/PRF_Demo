import os
import time
from playwright.sync_api import sync_playwright

def record_demo():
    dashboard_path = "/Users/junaidalam/Documents/D/claude-workspace/project-prf/dashboard/index.html"
    file_url = f"file://{dashboard_path}"
    video_dir = "/Users/junaidalam/Documents/D/claude-workspace/project-prf/dashboard/videos"
    
    os.makedirs(video_dir, exist_ok=True)
    
    print("Launching Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=video_dir,
            record_video_size={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        print(f"Loading page: {file_url}")
        page.goto(file_url)
        page.wait_for_load_state("networkidle")
        
        # Inject getCoords helper to project 3D coordinates to screen space
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
        }""")
        
        print("Starting video recording...")
        time.sleep(2) # Stabilize
        
        # -------------------------------------------------------------
        # [0:00 – 0:15] — INTRO
        # -------------------------------------------------------------
        print("Step 1: Intro - Slow Orbit camera")
        box = page.locator("#shed-container").bounding_box()
        start_x = box["x"] + box["width"] / 2
        start_y = box["y"] + box["height"] / 2
        
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        
        # Slowly drag left to orbit camera
        steps = 120
        for i in range(steps):
            page.mouse.move(start_x - i * 3.5, start_y)
            page.wait_for_timeout(80) # ~9.6 seconds
            
        page.mouse.up()
        page.wait_for_timeout(2400) # Hold until 15s mark
        
        # -------------------------------------------------------------
        # [0:15 – 0:45] — 3D SHED + LAYERS
        # -------------------------------------------------------------
        print("Step 2: 3D Shed Layers & Tooltip Hover")
        
        # Click Litter
        page.click('button.layer-btn[data-layer="litter"]')
        page.wait_for_timeout(2000)
        
        # Click Temperature
        page.click('button.layer-btn[data-layer="temperature"]')
        page.wait_for_timeout(2000)
        
        # Click Humidity
        page.click('button.layer-btn[data-layer="humidity"]')
        page.wait_for_timeout(2000)
        
        # Click Clustering
        page.click('button.layer-btn[data-layer="clustering"]')
        page.wait_for_timeout(2000)
        
        # Hover Zone 4L (Pen Index 15)
        coords = page.evaluate("window.getCoords(15)")
        if coords:
            page.mouse.move(coords["x"], coords["y"])
            print(f"Hovering Zone 4L at coords: {coords}")
            page.wait_for_timeout(5000)
            
        # Click Welfare Index (BETA)
        page.click('button.layer-btn[data-layer="welfare"]')
        page.wait_for_timeout(3000)
        
        # Click FCR (BETA)
        page.click('button.layer-btn[data-layer="fcr"]')
        page.wait_for_timeout(3000)
        
        # Click Approx. Weight (BETA)
        page.click('button.layer-btn[data-layer="weight"]')
        page.wait_for_timeout(3000)
        
        # Return to Activity
        page.click('button.layer-btn[data-layer="activity"]')
        page.wait_for_timeout(3000)
        
        # -------------------------------------------------------------
        # [0:40 – 1:00] — KPI SIDEBAR
        # -------------------------------------------------------------
        print("Step 3: KPI Sidebar Scroll")
        page.wait_for_timeout(1000)
        
        # Smoothly scroll the KPI sidebar down card by card
        cards = page.query_selector_all('.kpi-sidebar .kpi-card')
        for card in cards:
            card.scroll_into_view_if_needed()
            page.wait_for_timeout(2500)
            
        page.wait_for_timeout(3000) # buffer to complete 20s
        
        # -------------------------------------------------------------
        # [1:00 – 1:20] — BIRD HEALTH TAB
        # -------------------------------------------------------------
        print("Step 4: Bird Health Tab")
        page.click('button[data-tab="birdhealth"]')
        page.wait_for_timeout(2000)
        
        # Hover over the Zone 4L red line dropping on activity chart
        chart_box = page.locator('#activity-chart').bounding_box()
        if chart_box:
            chart_x = chart_box["x"] + chart_box["width"] * 0.78
            chart_y = chart_box["y"] + chart_box["height"] * 0.75
            page.mouse.move(chart_x, chart_y)
        page.wait_for_timeout(4000)
        
        # Scroll down to clustering heatmap
        page.locator('#clustering-canvas').scroll_into_view_if_needed()
        page.wait_for_timeout(4000)
        
        # Scroll to pre-mortality grid and hover amber MONITOR cell (index 15)
        monitor_cell = page.locator('#premort-cell-15')
        monitor_cell.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        
        cell_box = monitor_cell.bounding_box()
        if cell_box:
            page.mouse.move(cell_box["x"] + cell_box["width"]/2, cell_box["y"] + cell_box["height"]/2)
        page.wait_for_timeout(5000)
        
        # -------------------------------------------------------------
        # [1:20 – 1:40] — SHED OPERATIONS TAB
        # -------------------------------------------------------------
        print("Step 5: Shed Operations Tab")
        page.click('button[data-tab="operations"]')
        page.wait_for_timeout(2000)
        
        # Hover over red-highlighted pen in Zone 2R (index 31) on SVG map
        svg_pen = page.locator('#svg-pen-31')
        svg_pen.scroll_into_view_if_needed()
        
        pen_box = svg_pen.bounding_box()
        if pen_box:
            page.mouse.move(pen_box["x"] + pen_box["width"]/2, pen_box["y"] + pen_box["height"]/2)
        page.wait_for_timeout(6000)
        
        # Scroll down to fault log table
        fault_table = page.locator('.fault-table')
        fault_table.scroll_into_view_if_needed()
        page.wait_for_timeout(2000)
        
        # Hover the ACTIVE row
        active_row = page.locator('.fault-table tr:has-text("ACTIVE")')
        row_box = active_row.bounding_box()
        if row_box:
            page.mouse.move(row_box["x"] + row_box["width"]/2, row_box["y"] + row_box["height"]/2)
        page.wait_for_timeout(6000)
        
        # -------------------------------------------------------------
        # [1:40 – 2:00] — AI ASSISTANT + CLOSE
        # -------------------------------------------------------------
        print("Step 6: AI Assistant Tab & Fade to black")
        page.click('button[data-tab="ai"]')
        page.wait_for_timeout(2000)
        
        # Click the quick chip
        page.click('button.quick-chip:has-text("What is the current FPD risk")')
        page.wait_for_timeout(5000)
        
        # Click the floating cyan bubble
        page.click('#ai-bubble')
        page.wait_for_timeout(3000)
        
        # Fade to black overlay
        print("Fading to black...")
        page.evaluate("""() => {
            const overlay = document.createElement('div');
            overlay.style.position = 'fixed';
            overlay.style.inset = '0';
            overlay.style.background = 'black';
            overlay.style.zIndex = '999999';
            overlay.style.opacity = '0';
            overlay.style.transition = 'opacity 2.0s ease-in-out';
            document.body.appendChild(overlay);
            setTimeout(() => { overlay.style.opacity = '1'; }, 50);
        }""")
        page.wait_for_timeout(4000)
        
        print("Closing browser...")
        context.close()
        browser.close()
        
    print("Demo recording successfully completed!")

if __name__ == "__main__":
    record_demo()
