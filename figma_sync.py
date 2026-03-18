import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

FIGMA_API_URL = "https://api.figma.com/v1"

class FigmaAutomator:
    def __init__(self, token=None, team_id=None):
        self.headers = {"X-Figma-Token": token or os.getenv("FIGMA_TOKEN")}
        self.team_id = team_id

    def create_new_file(self, name):
        # ⚠️ Figma REST API는 현재 '새 파일 생성' 직접 호출을 지원하지 않을 수 있음
        # 보통 기존 파일 ID를 받거나 프로젝트 ID를 기반으로 생성함
        print(f"Creating file '{name}' via API (Project ID required)...")
        # 임시로 기존 파일 ID를 사용하는 방식 추천
        return "YOUR_FILE_ID"

    def apply_auto_layout(self, frame_id, direction="VERTICAL", padding=20, spacing=10):
        """
        피그마 프레임에 오토레이아웃 속성을 적용합니다.
        """
        payload = {
            "layoutMode": direction, # "HORIZONTAL" or "VERTICAL"
            "itemSpacing": spacing,
            "paddingLeft": padding,
            "paddingRight": padding,
            "paddingTop": padding,
            "paddingBottom": padding
        }
        # Figma Plugin API와 달리 REST API는 POST /files/:key/nodes로 업데이트함
        # ⚠️ 참고: REST API는 읽기 전용 속성이 많아 실제 적용은 오토레이아웃 '설정' 보다는 
        # 처음 생성 시 좌표와 크기를 정확히 계산하는 것이 핵심입니다.
        pass

    def guess_layout_direction(self, children):
        """
        자식 요소들의 배치를 분석하여 가로/세로 오토레이아웃 방향을 추측합니다.
        """
        if len(children) < 2:
            return "VERTICAL"
            
        # x, y 좌표 변화 분석
        x_diffs = [abs(children[i+1]['left'] - children[i]['left']) for i in range(len(children)-1)]
        y_diffs = [abs(children[i+1]['top'] - children[i]['top']) for i in range(len(children)-1)]
        
        if sum(x_diffs) > sum(y_diffs):
            return "HORIZONTAL"
        return "VERTICAL"

    def sync_to_figma(self, metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            layers = json.load(f)
            
        print(f"Syncing {len(layers)} layers to Figma...")
        # 1. 그룹화 구조 파악
        # 2. 오토레이아웃 추측 및 적용
        # 3. 레이어 생성 API 호출
        
        # ⚠️ 실제 구현 시 각 레이어의 타입(Text, Slice 등)에 맞춰 적절한 노드 생성 필요
        # 현재는 로직 설계 단계입니다.

if __name__ == "__main__":
    # automator = FigmaAutomator("YOUR_FIGMA_TOKEN")
    # automator.sync_to_figma("output_assets/metadata.json")
    pass
