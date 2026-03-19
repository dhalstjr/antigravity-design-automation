"""
layout_analyzer.py
------------------
PSD 메타데이터를 분석하여 Figma Auto Layout / 반응형 속성을 자동 추론합니다.

주요 기능:
- 자식 레이어 좌표를 분석하여 HORIZONTAL / VERTICAL 방향 결정
- 레이어 간 간격(gap)과 패딩(padding)을 계산
- 레이어가 캔버스 너비/높이에 대해 갖는 비율로 FILL/FIXED/HUG 결정
- 겹치거나 인접한 레이어를 논리적 컨테이너로 그룹화 제안
"""

from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# 1. 레이아웃 방향 감지
# ──────────────────────────────────────────────────────────────────────────────

def guess_layout_direction(children: list) -> str:
    """
    자식 레이어 목록의 좌표 이동량을 비교하여
    HORIZONTAL(가로) 또는 VERTICAL(세로) Auto Layout 방향을 반환합니다.
    """
    if len(children) < 2:
        return "VERTICAL"

    x_diffs = [abs(children[i + 1]["x"] - children[i]["x"]) for i in range(len(children) - 1)]
    y_diffs = [abs(children[i + 1]["y"] - children[i]["y"]) for i in range(len(children) - 1)]

    return "HORIZONTAL" if sum(x_diffs) > sum(y_diffs) else "VERTICAL"


# ──────────────────────────────────────────────────────────────────────────────
# 2. 패딩 및 아이템 간격 계산
# ──────────────────────────────────────────────────────────────────────────────

def calculate_spacing(parent: dict, children: list) -> dict:
    """
    부모 레이어와 자식 레이어들의 좌표를 분석하여
    Figma Auto Layout에 필요한 padding 및 itemSpacing 값을 계산합니다.
    """
    if not children:
        return {"padding_top": 0, "padding_right": 0, "padding_bottom": 0, "padding_left": 0, "item_spacing": 0}

    parent_x = parent.get("x", 0)
    parent_y = parent.get("y", 0)
    parent_w = parent.get("width", 1)
    parent_h = parent.get("height", 1)

    child_lefts   = [c["x"] for c in children]
    child_tops    = [c["y"] for c in children]
    child_rights  = [c["x"] + c["width"] for c in children]
    child_bottoms = [c["y"] + c["height"] for c in children]

    padding_left   = max(0, min(child_lefts) - parent_x)
    padding_top    = max(0, min(child_tops) - parent_y)
    padding_right  = max(0, (parent_x + parent_w) - max(child_rights))
    padding_bottom = max(0, (parent_y + parent_h) - max(child_bottoms))

    # 아이템 간격: 인접 레이어 쌍의 간격 중 최솟값 (가장 촘촘한 부분)
    direction = guess_layout_direction(children)
    gaps = []
    sorted_children = sorted(children, key=lambda c: c["x"] if direction == "HORIZONTAL" else c["y"])
    for i in range(len(sorted_children) - 1):
        if direction == "HORIZONTAL":
            gap = sorted_children[i + 1]["x"] - (sorted_children[i]["x"] + sorted_children[i]["width"])
        else:
            gap = sorted_children[i + 1]["y"] - (sorted_children[i]["y"] + sorted_children[i]["height"])
        if gap >= 0:
            gaps.append(gap)

    item_spacing = round(min(gaps)) if gaps else 0

    return {
        "padding_top": round(padding_top),
        "padding_right": round(padding_right),
        "padding_bottom": round(padding_bottom),
        "padding_left": round(padding_left),
        "item_spacing": item_spacing,
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3. 반응형 크기 속성 결정 (FILL / FIXED / HUG)
# ──────────────────────────────────────────────────────────────────────────────

FILL_THRESHOLD = 0.85  # 부모 크기의 85% 이상이면 FILL로 간주

def get_sizing_mode(layer: dict, parent: Optional[dict], canvas: dict) -> dict:
    """
    레이어의 가로/세로 크기 모드를 결정합니다.
    - FILL  : 부모(또는 캔버스)에 비해 매우 큰 경우 → 부모를 채움
    - HUG   : 그룹이며 자식이 있을 경우 → 내용에 맞게 줄어듦
    - FIXED : 나머지 → 고정 크기
    """
    ref_w = parent["width"] if parent else canvas["width"]
    ref_h = parent["height"] if parent else canvas["height"]

    layer_w = layer.get("width", 0)
    layer_h = layer.get("height", 0)
    is_group = layer.get("type") == "group"
    has_children = bool(layer.get("children"))

    h_mode = "FILL" if (ref_w > 0 and layer_w / ref_w >= FILL_THRESHOLD) else (
        "HUG" if (is_group and has_children) else "FIXED"
    )
    v_mode = "FILL" if (ref_h > 0 and layer_h / ref_h >= FILL_THRESHOLD) else (
        "HUG" if (is_group and has_children) else "FIXED"
    )

    return {"h_sizing": h_mode, "v_sizing": v_mode}


# ──────────────────────────────────────────────────────────────────────────────
# 4. 전체 레이어 트리에 Auto Layout 정보 주입
# ──────────────────────────────────────────────────────────────────────────────

def _overlap_ratio(children: list) -> float:
    """자식 레이어 쌍 중 겹치는 비율을 반환합니다 (0.0 ~ 1.0)."""
    if len(children) < 2:
        return 0.0
    total_pairs = len(children) * (len(children) - 1) // 2
    overlap_count = 0
    for i in range(len(children)):
        for j in range(i + 1, len(children)):
            a, b = children[i], children[j]
            if (a["x"] < b["x"] + b["width"] and a["x"] + a["width"] > b["x"] and
                a["y"] < b["y"] + b["height"] and a["y"] + a["height"] > b["y"]):
                overlap_count += 1
    return overlap_count / total_pairs if total_pairs > 0 else 0.0


def annotate_layout(layer_tree: list, canvas: dict, parent: Optional[dict] = None) -> list:
    """
    레이어 트리를 순회하면서 각 레이어에 layout_hints 를 추가합니다.
    Auto Layout은 자식이 2개 이상이고 겹침이 30% 이하일 때 적용합니다.
    """
    annotated = []
    for layer in layer_tree:
        sizing = get_sizing_mode(layer, parent, canvas)
        children = layer.get("children", [])

        hints = {
            "h_sizing": sizing["h_sizing"],
            "v_sizing": sizing["v_sizing"],
        }

        if children and len(children) >= 2:
            direction = guess_layout_direction(children)
            overlap = _overlap_ratio(children)

            # 겹침 비율이 30% 이하이면 Auto Layout 적용
            if overlap <= 0.3:
                spacing = calculate_spacing(layer, children)
                hints.update({
                    "auto_layout": True,
                    "layout_direction": direction,
                    **spacing,
                })
            else:
                hints["auto_layout"] = False

            # 자식 재귀 처리
            layer = dict(layer)
            layer["children"] = annotate_layout(children, canvas, parent=layer)
        else:
            hints["auto_layout"] = False

        layer = dict(layer)
        layer["layout_hints"] = hints
        annotated.append(layer)

    return annotated


def analyze_layout(psd_data: dict) -> dict:
    """
    extract_psd.py 의 결과물(psd_data)에 layout 정보를 추가하여 반환합니다.
    """
    canvas = psd_data["canvas"]
    annotated_tree = annotate_layout(psd_data["layer_tree"], canvas)
    return {**psd_data, "layer_tree": annotated_tree, "layout_analyzed": True}


if __name__ == "__main__":
    import json, sys
    path = sys.argv[1] if len(sys.argv) > 1 else "output_assets/metadata.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    result = analyze_layout(data)
    out_path = path.replace("metadata.json", "metadata_with_layout.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[layout_analyzer] Done → {out_path}")
