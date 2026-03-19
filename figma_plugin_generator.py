"""
figma_plugin_generator.py
--------------------------
layout_analyzer.py 가 주석을 달아준 레이어 트리를 읽어
Figma Plugin API 로 실행 가능한 JavaScript 코드를 자동 생성합니다.

핵심 변경:
- 부모-자식 좌표를 상대좌표로 변환 (PSD 절대좌표 → Figma 상대좌표)
- 텍스트 폰트 로딩 개선 (다중 폴백)
- Auto Layout은 선택적 적용
"""

import json
import base64
import os
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────────────────────────────────────

def js_str(s: str) -> str:
    """파이썬 문자열을 안전한 JS 문자열 리터럴로 변환."""
    return json.dumps(str(s), ensure_ascii=False)


def js_color(c: Optional[dict]) -> str:
    """Figma RGB 딕셔너리를 JS 객체 리터럴로 변환."""
    if not c:
        return "{r:0, g:0, b:0, a:1}"
    return "{{r:{r}, g:{g}, b:{b}, a:{a}}}".format(**c)


def image_to_base64(path: str) -> Optional[str]:
    """이미지 파일을 Base64 문자열로 인코딩."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# 레이어 → JS 코드 생성 (상대좌표 버전)
# ──────────────────────────────────────────────────────────────────────────────

def gen_frame(layer: dict, var: str, parent_var: str, lines: list,
              parent_x: int = 0, parent_y: int = 0):
    """Frame 노드 생성 코드 (Auto Layout 포함). 좌표는 부모 기준 상대좌표."""
    h = layer.get("layout_hints", {})
    # 상대좌표로 변환
    rel_x = layer.get("x", 0) - parent_x
    rel_y = layer.get("y", 0) - parent_y
    w = layer.get("width", 100)
    ht = layer.get("height", 100)
    name = layer.get("name", "Frame")
    opacity = layer.get("opacity", 1.0)
    blend = layer.get("blend_mode", "NORMAL")

    lines.append(f"  const {var} = figma.createFrame();")
    lines.append(f"  {var}.name = {js_str(name)};")
    lines.append(f"  {var}.x = {rel_x};")
    lines.append(f"  {var}.y = {rel_y};")
    lines.append(f"  {var}.resize({max(w,1)}, {max(ht,1)});")
    lines.append(f"  {var}.opacity = {opacity};")
    lines.append(f"  {var}.blendMode = {js_str(blend)};")
    lines.append(f"  {var}.fills = [];")  # 기본 배경 제거
    lines.append(f"  {var}.clipsContent = false;")  # 자식 잘림 방지

    # Auto Layout
    if h.get("auto_layout"):
        direction = h.get("layout_direction", "VERTICAL")
        lines.append(f"  {var}.layoutMode = {js_str(direction)};")
        lines.append(f"  {var}.itemSpacing = {h.get('item_spacing', 0)};")
        lines.append(f"  {var}.paddingTop = {h.get('padding_top', 0)};")
        lines.append(f"  {var}.paddingBottom = {h.get('padding_bottom', 0)};")
        lines.append(f"  {var}.paddingLeft = {h.get('padding_left', 0)};")
        lines.append(f"  {var}.paddingRight = {h.get('padding_right', 0)};")
        lines.append(f"  {var}.primaryAxisSizingMode = {js_str('AUTO' if h.get('v_sizing') == 'HUG' else 'FIXED')};")
        lines.append(f"  {var}.counterAxisSizingMode = {js_str('AUTO' if h.get('h_sizing') == 'HUG' else 'FIXED')};")
        lines.append(f"  {var}.clipsContent = true;")  # Auto Layout은 clipping 사용

    lines.append(f"  {parent_var}.appendChild({var});")


def gen_text(layer: dict, var: str, parent_var: str, lines: list,
             parent_x: int = 0, parent_y: int = 0):
    """Text 노드 생성 코드. 폰트 로딩 개선 버전."""
    text_data = layer.get("text_data", {})
    content = text_data.get("content", layer.get("name", ""))
    styles = text_data.get("styles", [{}])
    first_style = styles[0] if styles else {}
    alignments = text_data.get("alignments", ["LEFT"])
    alignment = alignments[0] if alignments else "LEFT"

    font_family = first_style.get("font_family", "Inter")
    font_size = first_style.get("font_size", 16)
    is_bold = first_style.get("bold", False)
    is_italic = first_style.get("italic", False)
    letter_spacing = first_style.get("letter_spacing", 0)
    line_height = first_style.get("line_height")
    color = first_style.get("color")
    opacity = layer.get("opacity", 1.0)
    # 상대좌표로 변환
    rel_x = layer.get("x", 0) - parent_x
    rel_y = layer.get("y", 0) - parent_y
    w = layer.get("width", 100)
    ht = layer.get("height", 30)
    name = layer.get("name", "Text")

    # Figma 폰트 스타일 결정
    font_style = "Bold Italic" if (is_bold and is_italic) else ("Bold" if is_bold else ("Italic" if is_italic else "Regular"))

    lines.append(f"  const {var} = figma.createText();")
    lines.append(f"  {var}.name = {js_str(name)};")
    lines.append(f"  {var}.x = {rel_x};")
    lines.append(f"  {var}.y = {rel_y};")
    lines.append(f"  {var}.opacity = {opacity};")

    # 폰트 로딩 — 다중 폴백: 원본폰트 → Inter Bold/Regular
    lines.append(f"  let {var}Font = {{ family: {js_str(font_family)}, style: {js_str(font_style)} }};")
    lines.append(f"  try {{")
    lines.append(f"    await figma.loadFontAsync({var}Font);")
    lines.append(f"  }} catch(e1) {{")
    # 폴백 1: 원본 폰트의 Regular 시도
    if font_style != "Regular":
        lines.append(f"    try {{")
        lines.append(f"      {var}Font = {{ family: {js_str(font_family)}, style: 'Regular' }};")
        lines.append(f"      await figma.loadFontAsync({var}Font);")
        lines.append(f"    }} catch(e2) {{")
    # 폴백 2: Inter (같은 스타일)
    lines.append(f"      try {{")
    lines.append(f"        {var}Font = {{ family: 'Inter', style: {js_str(font_style)} }};")
    lines.append(f"        await figma.loadFontAsync({var}Font);")
    lines.append(f"      }} catch(e3) {{")
    # 폴백 3: Inter Regular (최종 폴백)
    lines.append(f"        {var}Font = {{ family: 'Inter', style: 'Regular' }};")
    lines.append(f"        await figma.loadFontAsync({var}Font);")
    lines.append(f"      }}")
    if font_style != "Regular":
        lines.append(f"    }}")
    lines.append(f"  }}")

    lines.append(f"  {var}.fontName = {var}Font;")
    lines.append(f"  {var}.fontSize = {max(font_size, 1)};")
    lines.append(f"  {var}.characters = {js_str(content)};")
    lines.append(f"  {var}.textAlignHorizontal = {js_str(alignment)};")
    lines.append(f"  {var}.letterSpacing = {{ value: {letter_spacing}, unit: 'PIXELS' }};")
    if line_height:
        lines.append(f"  {var}.lineHeight = {{ value: {line_height}, unit: 'PIXELS' }};")
    if color:
        lines.append(f"  {var}.fills = [{{ type: 'SOLID', color: {js_color(color)}, opacity: {color.get('a', 1)} }}];")
    else:
        lines.append(f"  {var}.fills = [{{ type: 'SOLID', color: {{r:0,g:0,b:0}}, opacity: 1 }}];")
    # 크기 조정
    lines.append(f"  {var}.resize({max(w,1)}, {max(ht,1)});")
    lines.append(f"  try {{ {var}.textAutoResize = 'HEIGHT'; }} catch(e) {{}}")
    lines.append(f"  {parent_var}.appendChild({var});")


def gen_image(layer: dict, var: str, parent_var: str, lines: list,
              parent_x: int = 0, parent_y: int = 0):
    """이미지를 Rectangle + Image Fill로 생성하는 코드. 상대좌표 사용."""
    # 상대좌표로 변환
    rel_x = layer.get("x", 0) - parent_x
    rel_y = layer.get("y", 0) - parent_y
    w = max(layer.get("width", 100), 1)
    ht = max(layer.get("height", 100), 1)
    name = layer.get("name", "Image")
    opacity = layer.get("opacity", 1.0)
    blend = layer.get("blend_mode", "NORMAL")
    fill_color = layer.get("fill_color")
    image_path = layer.get("image_path")

    lines.append(f"  const {var} = figma.createRectangle();")
    lines.append(f"  {var}.name = {js_str(name)};")
    lines.append(f"  {var}.x = {rel_x};")
    lines.append(f"  {var}.y = {rel_y};")
    lines.append(f"  {var}.resize({w}, {ht});")
    lines.append(f"  {var}.opacity = {opacity};")
    lines.append(f"  {var}.blendMode = {js_str(blend)};")

    if image_path and os.path.exists(image_path):
        b64 = image_to_base64(image_path)
        if b64:
            lines.append(f"  const {var}Data = agLayerImages[{js_str(layer['id'])}];")
            lines.append(f"  if ({var}Data) {{")
            lines.append(f"    const {var}Hash = figma.createImage(new Uint8Array({var}Data)).hash;")
            lines.append(f"    {var}.fills = [{{ type: 'IMAGE', imageHash: {var}Hash, scaleMode: 'FILL' }}];")
            lines.append(f"  }}")
        else:
            lines.append(f"  {var}.fills = [{{ type: 'SOLID', color: {{r:0.8,g:0.8,b:0.8}}, opacity: 1 }}];")
    elif fill_color:
        lines.append(f"  {var}.fills = [{{ type: 'SOLID', color: {js_color(fill_color)}, opacity: {fill_color.get('a', 1)} }}];")
    else:
        lines.append(f"  {var}.fills = [{{ type: 'SOLID', color: {{r:0.9,g:0.9,b:0.9}}, opacity: 1 }}];")

    lines.append(f"  {parent_var}.appendChild({var});")


# ──────────────────────────────────────────────────────────────────────────────
# 재귀 레이어 트리 → JS 코드 변환
# ──────────────────────────────────────────────────────────────────────────────

_var_counter = [0]

def new_var(prefix="node") -> str:
    _var_counter[0] += 1
    return f"{prefix}_{_var_counter[0]}"


def gen_layer_code(layer: dict, parent_var: str, lines: list,
                   parent_x: int = 0, parent_y: int = 0):
    """레이어 하나를 JS 코드로 변환합니다 (재귀). 부모 좌표를 받아 상대좌표 계산."""
    layer_type = layer.get("type", "image")
    var = new_var(layer_type[:3])

    if layer_type == "group":
        gen_frame(layer, var, parent_var, lines, parent_x, parent_y)
        # 자식들에게 이 그룹의 절대좌표를 전달하여 상대좌표 변환
        group_abs_x = layer.get("x", 0)
        group_abs_y = layer.get("y", 0)
        for child in layer.get("children", []):
            gen_layer_code(child, var, lines, group_abs_x, group_abs_y)
    elif layer_type == "text":
        gen_text(layer, var, parent_var, lines, parent_x, parent_y)
    else:
        gen_image(layer, var, parent_var, lines, parent_x, parent_y)


def generate_plugin_js(psd_data: dict, canvas_frame_name: str = "PSD Import") -> str:
    """
    전체 PSD 데이터를 Figma Plugin 실행 가능한 async IIFE JS 코드로 변환합니다.

    좌표 변환:
    - rootFrame: 뷰포트 중앙에 배치
    - 최상위 레이어: rootFrame 기준 좌표 (PSD 절대좌표 그대로 = rootFrame은 0,0 기준)
    - 중첩 레이어: 부모 그룹의 절대좌표를 빼서 상대좌표로 변환
    """
    global _var_counter
    _var_counter = [0]

    canvas = psd_data.get("canvas", {"width": 1440, "height": 900})
    source_file = os.path.basename(psd_data.get("source_file", "unknown.psd"))
    layer_tree = psd_data.get("layer_tree", [])

    # 이미지 파일들을 플러그인 UI가 전달할 수 있도록 목록 생성
    image_ids = []
    def collect_images(layers):
        for l in layers:
            if l.get("image_path") and os.path.exists(l.get("image_path", "")):
                image_ids.append({"id": l["id"], "path": l["image_path"]})
            for c in l.get("children", []):
                collect_images([c])
    collect_images(layer_tree)

    lines = []
    lines.append("// ============================================================")
    lines.append(f"// Auto-generated by Antigravity Design Automation")
    lines.append(f"// Source: {source_file}")
    lines.append(f"// Canvas: {canvas['width']}x{canvas['height']}")
    lines.append("// ============================================================")
    lines.append("")
    lines.append("(async () => {")
    lines.append("  // agLayerImages: { [layerId]: Uint8Array } - populated by plugin UI")
    lines.append("  const agLayerImages = typeof __agLayerImages !== 'undefined' ? __agLayerImages : {};")
    lines.append("")
    # 최상위 캔버스 프레임
    lines.append("  // Create root canvas frame")
    lines.append(f"  const rootFrame = figma.createFrame();")
    lines.append(f"  rootFrame.name = {js_str(canvas_frame_name + ' — ' + source_file)};")
    lines.append(f"  rootFrame.resize({canvas['width']}, {canvas['height']});")
    lines.append(f"  rootFrame.x = figma.viewport.center.x - {canvas['width'] // 2};")
    lines.append(f"  rootFrame.y = figma.viewport.center.y - {canvas['height'] // 2};")
    lines.append(f"  rootFrame.fills = [{{ type: 'SOLID', color: {{r:1,g:1,b:1}}, opacity: 1 }}];")
    lines.append(f"  rootFrame.clipsContent = true;")  # 루트 프레임은 캔버스 크기로 클리핑
    lines.append("")

    # 레이어 트리 순회 — 최상위 레이어의 부모좌표는 0,0 (캔버스 원점)
    for layer in reversed(layer_tree):
        gen_layer_code(layer, "rootFrame", lines, 0, 0)

    lines.append("")
    lines.append("  figma.currentPage.selection = [rootFrame];")
    lines.append("  figma.viewport.scrollAndZoomIntoView([rootFrame]);")
    lines.append("")
    lines.append("  figma.ui.postMessage({ type: 'done', layerCount: " +
                 str(sum(1 for _ in _flatten_layers(layer_tree))) + " });")
    lines.append("})();")

    return "\n".join(lines)


def _flatten_layers(layers):
    for l in layers:
        yield l
        if l.get("children"):
            yield from _flatten_layers(l["children"])


def save_plugin_js(psd_data: dict, output_path: str = "output_assets/figma_plugin_code.js",
                   canvas_frame_name: str = "PSD Import"):
    """JS 코드를 파일로 저장합니다."""
    js_code = generate_plugin_js(psd_data, canvas_frame_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_code)
    print(f"[figma_plugin_generator] Plugin code saved → {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "output_assets/metadata.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = save_plugin_js(data, "output_assets/figma_plugin_code.js")
    print(f"Generated: {out}")
