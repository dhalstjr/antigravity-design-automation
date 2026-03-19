"""
run_pipeline.py
---------------
PSD → 피그마 변환 파이프라인의 진입점 (메인 오케스트레이터).

실행 흐름:
  1. PSD 파일 추출   (extract_psd.py)
  2. 레이아웃 분석   (layout_analyzer.py)
  3. Plugin JS 생성  (figma_plugin_generator.py)
  4. n8n 웹훅 POST  (결과 리포트 전송)

사용법:
  python run_pipeline.py input.psd [--output output_assets] [--frame-name "My Design"]
"""

import argparse
import json
import os
import sys
import time
import traceback
import shutil
import requests
from dotenv import load_dotenv

load_dotenv()

from extract_psd import extract_psd_data
from layout_analyzer import analyze_layout
from figma_plugin_generator import save_plugin_js

# ──────────────────────────────────────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────────────────────────────────────

N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "http://localhost:5678/webhook/design-automation-report"
)
PLUGIN_OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output_assets")
FIGMA_FILE_ID = os.getenv("FIGMA_FILE_ID", "")  # 선택 사항: 결과 리포트에 링크 포함용

# 결과 파일명 정의
RESULT_JS_NAME = "01_피그마에_드래그하세요.js"
RESULT_METADATA_NAME = "레이어_분석_데이터.json"
RESULT_REPORT_NAME = "작업_리포트.json"


# ──────────────────────────────────────────────────────────────────────────────
# n8n 리포트 전송
# ──────────────────────────────────────────────────────────────────────────────

def send_n8n_report(report: dict, timeout: int = 5) -> bool:
    """n8n 웹훅으로 결과 리포트를 전송합니다."""
    if not N8N_WEBHOOK_URL or "localhost" not in N8N_WEBHOOK_URL and not N8N_WEBHOOK_URL.startswith("http"):
        print("[n8n] Webhook URL not configured, skipping.")
        return False
    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=report, timeout=timeout)
        if resp.status_code < 400:
            print(f"[n8n] Report sent → HTTP {resp.status_code}")
            return True
        else:
            print(f"[n8n] Report failed → HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print("[n8n] Connection failed (n8n not running?). Report saved locally.")
        return False
    except Exception as e:
        print(f"[n8n] Error sending report: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 파이프라인 실행
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(psd_path: str, output_dir: str, frame_name: str) -> dict:
    """
    전체 파이프라인을 실행하고 결과 딕셔너리를 반환합니다.

    Returns:
        {
          "status": "success" | "error",
          "source_file": str,
          "total_layers": int,
          "plugin_js_path": str,
          "metadata_path": str,
          "figma_link": str,
          "timestamp": str,
          "duration_seconds": float,
          "error": str | None,
        }
    """
    start_time = time.time()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    report = {
        "status": "error",
        "source_file": os.path.abspath(psd_path),
        "total_layers": 0,
        "plugin_js_path": "",
        "metadata_path": "",
        "figma_link": f"https://www.figma.com/file/{FIGMA_FILE_ID}" if FIGMA_FILE_ID else "(파일 ID 미설정)",
        "timestamp": timestamp,
        "duration_seconds": 0.0,
        "error": None,
    }

    try:
        # ── Step 1: PSD 추출 ─────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print(f"[Step 1/3] PSD 레이어 추출 중...")
        psd_data = extract_psd_data(psd_path, output_dir)
        report["total_layers"] = psd_data.get("total_layers", 0)
        metadata_path = os.path.join(output_dir, RESULT_METADATA_NAME)
        report["metadata_path"] = os.path.abspath(metadata_path)
        print(f"  ✅ {report['total_layers']}개 레이어 추출 완료")

        # ── Step 2: 레이아웃 분석 ─────────────────────────────────────────────
        print(f"\n[Step 2/3] 레이아웃 분석 중...")
        analyzed_data = analyze_layout(psd_data)
        # 분석 결과를 메타데이터에 덮어쓰기
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_data, f, indent=2, ensure_ascii=False)
        print(f"  ✅ 오토레이아웃 & 반응형 힌트 분석 완료")

        # ── Step 3: Figma Plugin JS 생성 ──────────────────────────────────────
        print(f"\n[Step 3/3] Figma Plugin 코드 생성 중...")
        js_path = os.path.join(output_dir, RESULT_JS_NAME)
        save_plugin_js(analyzed_data, js_path, frame_name)
        report["plugin_js_path"] = os.path.abspath(js_path)
        print(f"  ✅ Plugin JS 생성 완료: {os.path.join(output_dir, RESULT_JS_NAME)}")
        print(f"     -> 이 파일을 피그마 플러그인에 드래그하세요!")

        report["status"] = "success"

    except Exception as e:
        report["error"] = traceback.format_exc()
        print(f"\n❌ 파이프라인 오류:\n{report['error']}")

    report["duration_seconds"] = round(time.time() - start_time, 2)

    # ── 결과 리포트 JSON 저장 ─────────────────────────────────────────────────
    report_path = os.path.join(output_dir, RESULT_REPORT_NAME)
    os.makedirs(output_dir, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 루트 폴더에도 복사본 생성 (사용자 편의성)
    try:
        shutil.copy2(os.path.join(output_dir, RESULT_JS_NAME), os.path.join(os.getcwd(), RESULT_JS_NAME))
        print(f"  ⭐ 결과물이 루트 폴더에도 생성되었습니다: {RESULT_JS_NAME}")
    except:
        pass

    # ── n8n 웹훅 전송 ────────────────────────────────────────────────────────
    print(f"\n[n8n] 결과 리포트 전송 중...")
    sent = send_n8n_report(report)
    report["n8n_sent"] = sent

    # ── 최종 요약 출력 ────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if report["status"] == "success":
        print(f"🎉 파이프라인 완료!")
        print(f"   레이어 수    : {report['total_layers']}")
        print(f"   소요 시간    : {report['duration_seconds']}초")
        print(f"   Plugin JS   : {report['plugin_js_path']}")
        print(f"   Figma 링크   : {report['figma_link']}")
        print(f"\n👉 다음 단계: Figma에서 'antigravity-figma-plugin' 플러그인을 실행하세요!")
    else:
        print(f"❌ 파이프라인 실패! 오류 내용은 {report_path} 를 확인하세요.")
    print("=" * 60)

    return report


# ──────────────────────────────────────────────────────────────────────────────
# CLI 진입점
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PSD → Figma 자동화 파이프라인")
    parser.add_argument("psd_path", help="변환할 .psd 파일 경로")
    parser.add_argument("--output", default=PLUGIN_OUTPUT_DIR, help="출력 디렉토리 (기본값: output_assets)")
    parser.add_argument("--frame-name", default="PSD Import", help="Figma에 생성될 최상위 프레임 이름")
    args = parser.parse_args()

    if not os.path.exists(args.psd_path):
        print(f"[ERROR] 파일을 찾을 수 없습니다: {args.psd_path}")
        sys.exit(1)

    result = run_pipeline(args.psd_path, args.output, args.frame_name)
    sys.exit(0 if result["status"] == "success" else 1)
