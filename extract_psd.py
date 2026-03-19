"""
extract_psd.py
--------------
포토샵(.psd) 파일에서 레이어 데이터를 완전하게 추출합니다.
- 텍스트: 폰트명, 크기, 색상, 정렬, 굵기, 기울기, 줄간격
- 이미지/색상 레이어: PNG 내보내기 + fill 색상
- 그룹: 재귀적 계층 구조 보존
- 블렌드 모드, 불투명도, 좌표, 크기 등 Figma 재현에 필요한 모든 속성
"""

import os
import json
import traceback
from psd_tools import PSDImage
from psd_tools.constants import BlendMode, Tag

BLEND_MODE_MAP = {
    BlendMode.NORMAL: "NORMAL",
    BlendMode.MULTIPLY: "MULTIPLY",
    BlendMode.SCREEN: "SCREEN",
    BlendMode.OVERLAY: "OVERLAY",
    BlendMode.DARKEN: "DARKEN",
    BlendMode.LIGHTEN: "LIGHTEN",
    BlendMode.COLOR_DODGE: "COLOR_DODGE",
    BlendMode.COLOR_BURN: "COLOR_BURN",
    BlendMode.HARD_LIGHT: "HARD_LIGHT",
    BlendMode.SOFT_LIGHT: "SOFT_LIGHT",
    BlendMode.DIFFERENCE: "DIFFERENCE",
    BlendMode.EXCLUSION: "EXCLUSION",
    BlendMode.HUE: "HUE",
    BlendMode.SATURATION: "SATURATION",
    BlendMode.COLOR: "COLOR",
    BlendMode.LUMINOSITY: "LUMINOSITY",
    BlendMode.DISSOLVE: "DISSOLVE",
}


def color_to_hex(r, g, b):
    """RGB 값을 Figma용 hex 문자열로 변환."""
    return "#{:02x}{:02x}{:02x}".format(int(r), int(g), int(b))


def color_to_figma_rgb(r, g, b, a=255):
    """RGB/A 값을 Figma API용 0-1 범위 딕셔너리로 변환."""
    return {
        "r": round(r / 255.0, 4),
        "g": round(g / 255.0, 4),
        "b": round(b / 255.0, 4),
        "a": round(a / 255.0, 4),
    }


def extract_text_style(layer):
    """텍스트 레이어에서 상세 스타일 정보를 추출합니다."""
    text_data = {"content": "", "styles": []}
    try:
        text_data["content"] = layer.text or ""
    except Exception:
        pass

    try:
        engine_data = layer.engine_dict
        if not engine_data:
            return text_data

        # 기본 스타일 수집
        style_sheets = engine_data.get("ResourceDict", {}).get("ParagraphSheetSet", [{}])
        run_data = engine_data.get("EngineDict", {}).get("StyleRun", {})
        run_list = run_data.get("RunArray", []) if run_data else []

        for run in run_list:
            sh = run.get("StyleSheet", {}).get("StyleSheetData", {})
            font_name = "Unknown"
            try:
                font_idx = sh.get("Font", 0)
                fonts = engine_data.get("ResourceDict", {}).get("FontSet", [])
                if fonts and font_idx < len(fonts):
                    font_name = fonts[font_idx].get("Name", "Unknown")
            except Exception:
                pass

            fill_color = None
            try:
                fc = sh.get("FillColor", {}).get("Values", [1, 0, 0, 0])
                if len(fc) >= 4:
                    # [A, R, G, B] 형식 (0-1 범위의 float)
                    fill_color = color_to_figma_rgb(
                        fc[1] * 255, fc[2] * 255, fc[3] * 255, fc[0] * 255
                    )
            except Exception:
                pass

            text_style = {
                "font_family": font_name,
                "font_size": sh.get("FontSize", 16),
                "bold": sh.get("FauxBold", False),
                "italic": sh.get("FauxItalic", False),
                "underline": sh.get("Underline", False),
                "strikethrough": sh.get("Strikethrough", False),
                "letter_spacing": sh.get("Tracking", 0),
                "line_height": sh.get("Leading", None),
                "color": fill_color,
            }
            text_data["styles"].append(text_style)

        # 문단 정렬 추출
        para_run = engine_data.get("EngineDict", {}).get("ParagraphRun", {})
        para_list = para_run.get("RunArray", []) if para_run else []
        alignments = []
        align_map = {0: "LEFT", 1: "RIGHT", 2: "CENTER", 3: "JUSTIFIED"}
        for para in para_list:
            psh = para.get("ParagraphSheet", {}).get("Properties", {})
            alignments.append(align_map.get(psh.get("Justification", 0), "LEFT"))
        text_data["alignments"] = alignments

    except Exception as e:
        text_data["parse_error"] = str(e)

    return text_data


def extract_fill_color(layer):
    """레이어에서 단색 fill 색상을 추출합니다 (Shape/Solid Color 레이어)."""
    try:
        for effect in (layer.tagged_blocks or {}).values():
            pass
    except Exception:
        pass

    # Solid Color 레이어 추출 시도
    try:
        blocks = layer.tagged_blocks
        if blocks:
            # 솔리드 컬러 태그 확인
            for key in [Tag.SOLID_COLOR_SHEET_SETTING, "SoCo", "luni"]:
                try:
                    block = blocks.get(key)
                    if block and hasattr(block, "data"):
                        d = block.data
                        if hasattr(d, "color"):
                            c = d.color
                            return color_to_figma_rgb(c.red, c.green, c.blue)
                except Exception:
                    pass
    except Exception:
        pass
    return None


def get_blend_mode(layer):
    """레이어 블렌드 모드를 Figma 호환 문자열로 반환합니다."""
    try:
        return BLEND_MODE_MAP.get(layer.blend_mode, "NORMAL")
    except Exception:
        return "NORMAL"


def process_layers(layers, output_dir, parent_name=None, z_index_counter=None):
    """레이어 목록을 재귀적으로 처리하여 구조화된 데이터를 반환합니다."""
    if z_index_counter is None:
        z_index_counter = [0]

    result = []
    # psd-tools는 레이어를 위→아래 순으로 반환 (Figma와 동일)
    for layer in layers:
        z_index_counter[0] += 1
        current_z = z_index_counter[0]

        # 레이어 타입 결정
        layer_kind = str(layer.kind) if hasattr(layer, "kind") else "unknown"
        is_group = layer.is_group() if hasattr(layer, "is_group") else False
        is_text = layer_kind in ("type", "TypeLayer") or "type" in layer_kind.lower()
        is_shape = layer_kind in ("shape", "ShapeLayer") or "shape" in layer_kind.lower()

        layer_info = {
            "id": f"layer_{current_z}",
            "name": layer.name or f"Layer {current_z}",
            "type": "group" if is_group else ("text" if is_text else ("shape" if is_shape else "image")),
            "psd_kind": layer_kind,
            "parent": parent_name,
            "z_index": current_z,
            # 좌표 및 크기
            "x": layer.left,
            "y": layer.top,
            "width": max(layer.width, 1),
            "height": max(layer.height, 1),
            # 표시 속성
            "visible": layer.visible,
            "opacity": round(layer.opacity / 255.0, 4) if layer.opacity <= 255 else 1.0,
            "blend_mode": get_blend_mode(layer),
        }

        # 텍스트 레이어 상세 정보
        if is_text:
            layer_info["text_data"] = extract_text_style(layer)

        # 솔리드 색상 추출
        fill_color = extract_fill_color(layer)
        if fill_color:
            layer_info["fill_color"] = fill_color

        # 그룹 레이어: 하위 레이어 재귀 처리
        if is_group:
            layer_info["children"] = process_layers(
                layer, output_dir, parent_name=layer.name, z_index_counter=z_index_counter
            )
        else:
            # 이미지 레이어: PNG 내보내기
            try:
                if layer.width > 0 and layer.height > 0:
                    img = layer.composite()
                    if img:
                        safe_name = "".join(
                            c if c.isalnum() or c in "-_" else "_" for c in layer.name
                        )
                        img_path = os.path.join(output_dir, f"layer_{current_z}_{safe_name}.png")
                        img.save(img_path)
                        layer_info["image_path"] = os.path.abspath(img_path)
            except Exception as e:
                layer_info["image_export_error"] = str(e)

        result.append(layer_info)
    return result


def extract_psd_data(psd_path, output_dir="output_assets"):
    """
    PSD 파일을 완전하게 분석하고 output_dir에 메타데이터와 이미지를 저장합니다.

    Returns:
        dict: 추출된 전체 PSD 데이터 (레이어 트리 포함)
    """
    os.makedirs(output_dir, exist_ok=True)

    print(f"[extract_psd] Loading: {psd_path}")
    psd = PSDImage.open(psd_path)

    canvas_info = {
        "width": psd.width,
        "height": psd.height,
        "color_mode": str(psd.color_mode),
        "version": psd.version,
    }
    print(f"[extract_psd] Canvas: {psd.width}x{psd.height}, mode={psd.color_mode}")

    layers = process_layers(psd, output_dir)

    result = {
        "source_file": os.path.abspath(psd_path),
        "canvas": canvas_info,
        "total_layers": sum(1 for _ in _flatten_layers(layers)),
        "layer_tree": layers,
    }

    metadata_path = os.path.join(output_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[extract_psd] Done! {result['total_layers']} layers → {metadata_path}")
    return result


def _flatten_layers(layers):
    """레이어 트리를 평탄하게 이터레이션합니다."""
    for layer in layers:
        yield layer
        if layer.get("children"):
            yield from _flatten_layers(layer["children"])


if __name__ == "__main__":
    import sys
    psd_path = sys.argv[1] if len(sys.argv) > 1 else "sample.psd"
    if not os.path.exists(psd_path):
        print(f"[ERROR] File not found: {psd_path}")
        print("Usage: python extract_psd.py <path/to/file.psd>")
        sys.exit(1)
    extract_psd_data(psd_path, "output_assets")
