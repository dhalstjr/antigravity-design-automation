"""
단위 테스트: layout_analyzer + figma_plugin_generator
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))

from layout_analyzer import analyze_layout
from figma_plugin_generator import generate_plugin_js

mock_data = {
    "source_file": "mock_design.psd",
    "canvas": {"width": 1440, "height": 900, "color_mode": "RGB", "version": 1},
    "total_layers": 4,
    "layer_tree": [
        {
            "id": "layer_1", "name": "Container", "type": "group",
            "x": 0, "y": 0, "width": 1440, "height": 900,
            "visible": True, "opacity": 1.0, "blend_mode": "NORMAL",
            "children": [
                {
                    "id": "layer_2", "name": "Title", "type": "text",
                    "x": 60, "y": 80, "width": 600, "height": 60,
                    "visible": True, "opacity": 1.0, "blend_mode": "NORMAL",
                    "text_data": {
                        "content": "Hello Figma",
                        "styles": [{"font_family": "Inter", "font_size": 48, "bold": True,
                                    "color": {"r": 0.1, "g": 0.1, "b": 0.1, "a": 1.0}}],
                        "alignments": ["LEFT"]
                    }
                },
                {
                    "id": "layer_3", "name": "Subtitle", "type": "text",
                    "x": 60, "y": 160, "width": 500, "height": 30,
                    "visible": True, "opacity": 1.0, "blend_mode": "NORMAL",
                    "text_data": {
                        "content": "\uc790\ub3d9\ud654 \ud30c\uc774\ud504\ub77c\uc778",
                        "styles": [{"font_family": "Inter", "font_size": 24,
                                    "color": {"r": 0.4, "g": 0.4, "b": 0.4, "a": 1.0}}],
                        "alignments": ["LEFT"]
                    }
                },
                {
                    "id": "layer_4", "name": "Background", "type": "image",
                    "x": 0, "y": 0, "width": 1440, "height": 900,
                    "visible": True, "opacity": 1.0, "blend_mode": "NORMAL",
                    "fill_color": {"r": 0.98, "g": 0.98, "b": 1.0, "a": 1.0}
                }
            ]
        }
    ]
}

# ─── 1. Layout Analysis ───────────────────────────────
print("=== Layout Analysis ===")
analyzed = analyze_layout(mock_data)
layer_0 = analyzed["layer_tree"][0]
hints = layer_0["layout_hints"]
print(f"Direction  : {hints.get('layout_direction', 'N/A')}")
print(f"H-Sizing   : {hints.get('h_sizing')}")
print(f"V-Sizing   : {hints.get('v_sizing')}")
print(f"Padding    : T={hints.get('padding_top')} R={hints.get('padding_right')} B={hints.get('padding_bottom')} L={hints.get('padding_left')}")
print(f"Item Sp.   : {hints.get('item_spacing')}")

assert hints.get("layout_direction") == "VERTICAL", "Expected VERTICAL layout"
assert hints.get("h_sizing") == "FILL", "Expected FILL h_sizing for full-width container"

# ─── 2. JS Generation ────────────────────────────────
print("\n=== Plugin JS Generation ===")
js = generate_plugin_js(analyzed)
lines = js.splitlines()
print(f"Generated  : {len(lines)} lines of JavaScript")
print(f"createFrame: {'createFrame' in js}")
print(f"createText : {'createText' in js}")
print(f"layoutMode : {'layoutMode' in js}")
print(f"FILL sizing: {'FILL' in js}")

assert "createFrame" in js
assert "createText" in js
assert "layoutMode" in js
assert "FILL" in js

# 파일로 저장
os.makedirs("output_assets", exist_ok=True)
with open("output_assets/test_plugin_code.js", "w", encoding="utf-8") as f:
    f.write(js)
print(f"\nSaved to   : output_assets/test_plugin_code.js")
print("\n\u2705 ALL CHECKS PASSED!")
