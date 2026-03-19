"""
web_app.py
----------
PSD → Figma 자동화 파이프라인 웹 서버 + Figma Plugin API 백엔드.

실행:
  python web_app.py

브라우저: http://localhost:5000
Figma Plugin: /api/convert 엔드포인트로 PSD 업로드 → JS + 이미지 JSON 응답
"""

import os
import sys
import json
import time
import base64
import shutil
import traceback
from datetime import datetime
from flask import Flask, request, render_template, send_from_directory, jsonify, send_file
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

# 같은 폴더의 모듈 임포트
sys.path.insert(0, os.path.dirname(__file__))
from extract_psd import extract_psd_data
from layout_analyzer import analyze_layout
from figma_plugin_generator import save_plugin_js

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB limit

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output_assets")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# CORS 허용 (Figma Plugin iframe → localhost 요청)
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# n8n 관련
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/design-automation-report")


def send_n8n_report(report):
    """n8n 웹훅으로 결과 리포트를 전송합니다."""
    try:
        import requests
        resp = requests.post(N8N_WEBHOOK_URL, json=report, timeout=5)
        return resp.status_code < 400
    except Exception:
        return False


# ──────────────────────────────────────────────────────────────────────────────
# 라우트
# ──────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_and_run():
    """PSD 파일 업로드 → 파이프라인 실행 → JSON 결과 반환."""
    if "psd_file" not in request.files:
        return jsonify({"status": "error", "message": "PSD 파일을 선택해주세요."}), 400

    file = request.files["psd_file"]
    if not file.filename:
        return jsonify({"status": "error", "message": "파일 이름이 비어 있습니다."}), 400

    frame_name = request.form.get("frame_name", "PSD Import")
    original_name = file.filename

    # 한글 파일명 안전 처리
    safe_name = secure_filename(original_name) or f"upload_{int(time.time())}.psd"
    if not safe_name.lower().endswith(".psd"):
        safe_name += ".psd"

    # 작업별 고유 폴더 생성
    job_id = f"job_{int(time.time())}_{os.getpid()}"
    job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    psd_path = os.path.join(job_upload_dir, safe_name)
    file.save(psd_path)

    start_time = time.time()
    report = {
        "status": "error",
        "source_file": original_name,
        "job_id": job_id,
        "total_layers": 0,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "duration_seconds": 0,
        "steps": [],
        "error": None,
    }

    try:
        # ── Step 1: PSD 추출 ──────────────────────────────
        report["steps"].append({"step": 1, "name": "PSD 레이어 추출", "status": "running"})
        psd_data = extract_psd_data(psd_path, job_output_dir)
        report["total_layers"] = psd_data.get("total_layers", 0)
        report["steps"][-1]["status"] = "done"
        report["steps"][-1]["detail"] = f"{report['total_layers']}개 레이어 추출"

        # ── Step 2: 레이아웃 분석 ──────────────────────────
        report["steps"].append({"step": 2, "name": "레이아웃 분석", "status": "running"})
        analyzed_data = analyze_layout(psd_data)
        metadata_path = os.path.join(job_output_dir, "레이어_분석_데이터.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_data, f, indent=2, ensure_ascii=False)
        report["steps"][-1]["status"] = "done"
        report["steps"][-1]["detail"] = "오토레이아웃 & 반응형 분석 완료"

        # ── Step 3: Figma Plugin JS 생성 ───────────────────
        report["steps"].append({"step": 3, "name": "Figma Plugin 코드 생성", "status": "running"})
        js_path = os.path.join(job_output_dir, "01_피그마에_드래그하세요.js")
        save_plugin_js(analyzed_data, js_path, frame_name)
        report["steps"][-1]["status"] = "done"
        report["steps"][-1]["detail"] = "Plugin JS 생성 완료"

        report["status"] = "success"

        # 결과 파일 목록
        result_files = []
        for fname in os.listdir(job_output_dir):
            fpath = os.path.join(job_output_dir, fname)
            if os.path.isfile(fpath):
                result_files.append({
                    "name": fname,
                    "size": os.path.getsize(fpath),
                    "download_url": f"/download/{job_id}/{fname}"
                })
        report["result_files"] = result_files

    except Exception as e:
        report["error"] = str(e)
        report["traceback"] = traceback.format_exc()
        if report["steps"]:
            report["steps"][-1]["status"] = "error"

    report["duration_seconds"] = round(time.time() - start_time, 2)

    # 리포트 JSON 저장
    report_path = os.path.join(job_output_dir, "pipeline_report.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # n8n 전송
    n8n_sent = send_n8n_report(report)
    report["n8n_sent"] = n8n_sent

    return jsonify(report)


@app.route("/api/convert", methods=["POST", "OPTIONS"])
def api_convert():
    """
    Figma Plugin 전용 API.
    PSD 업로드 → JS 코드 + Base64 이미지 응답.
    피그마 플러그인이 이 응답을 받아 바로 실행합니다.
    """
    if request.method == "OPTIONS":
        return "", 200

    if "psd_file" not in request.files:
        return jsonify({"status": "error", "message": "PSD 파일을 선택해주세요."}), 400

    file = request.files["psd_file"]
    if not file.filename:
        return jsonify({"status": "error", "message": "파일 이름이 비어 있습니다."}), 400

    frame_name = request.form.get("frame_name", "PSD Import")
    original_name = file.filename
    safe_name = secure_filename(original_name) or f"upload_{int(time.time())}.psd"
    if not safe_name.lower().endswith(".psd"):
        safe_name += ".psd"

    job_id = f"job_{int(time.time())}_{os.getpid()}"
    job_upload_dir = os.path.join(UPLOAD_DIR, job_id)
    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    psd_path = os.path.join(job_upload_dir, safe_name)
    file.save(psd_path)

    try:
        # Step 1: PSD 추출
        psd_data = extract_psd_data(psd_path, job_output_dir)
        total_layers = psd_data.get("total_layers", 0)

        # Step 2: 레이아웃 분석
        analyzed_data = analyze_layout(psd_data)

        # Step 3: Figma Plugin JS 생성
        from figma_plugin_generator import generate_plugin_js
        js_code = generate_plugin_js(analyzed_data, frame_name)

        # Step 4: 이미지 파일들을 Base64로 인코딩
        # 키: layer_ID (예: layer_1) — figma_plugin_generator.py 와 일치시킴
        layer_images = {}
        for fname in os.listdir(job_output_dir):
            if fname.lower().endswith(".png"):
                fpath = os.path.join(job_output_dir, fname)
                # 파일명: layer_1_레이어이름.png → layer_1 추출
                base = fname.replace(".png", "").replace(".PNG", "")
                parts = base.split("_", 2)  # ['layer', '1', '레이어이름']
                layer_id = f"{parts[0]}_{parts[1]}" if len(parts) >= 2 else base
                with open(fpath, "rb") as img_f:
                    layer_images[layer_id] = base64.b64encode(img_f.read()).decode("ascii")

        return jsonify({
            "status": "success",
            "source_file": original_name,
            "total_layers": total_layers,
            "plugin_js": js_code,
            "layer_images": layer_images,
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route("/download/<job_id>/<filename>")
def download_file(job_id, filename):
    """결과 파일 다운로드."""
    safe_job = secure_filename(job_id)
    safe_file = secure_filename(filename) or filename
    directory = os.path.join(OUTPUT_DIR, safe_job)
    return send_from_directory(directory, safe_file, as_attachment=True)


@app.route("/download-all/<job_id>")
def download_all(job_id):
    """모든 결과 파일을 ZIP으로 다운로드."""
    safe_job = secure_filename(job_id)
    job_dir = os.path.join(OUTPUT_DIR, safe_job)
    if not os.path.isdir(job_dir):
        return jsonify({"error": "Job not found"}), 404

    zip_path = os.path.join(OUTPUT_DIR, f"{safe_job}")
    shutil.make_archive(zip_path, "zip", job_dir)
    return send_file(zip_path + ".zip", as_attachment=True,
                     download_name=f"antigravity_result_{safe_job}.zip")


# ──────────────────────────────────────────────────────────────────────────────
# 서버 실행
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("WEB_PORT", 5000))
    print("=" * 60)
    print(f"  Antigravity Design Automation Web Server")
    print(f"  http://localhost:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=True)
