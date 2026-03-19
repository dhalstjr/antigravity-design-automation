# 🚀 Antigravity Design Automation

포토샵(`.psd`) 파일을 **Figma 레이어**로 자동 변환하고, **Auto Layout · 반응형 레이아웃 · 텍스트 스타일**을 자동 적용하는 완전 자동화 파이프라인입니다. 변환 완료 후 **n8n**을 통해 Discord로 결과를 알림으로 보냅니다.

---

## 🏗️ 전체 아키텍처

```
PSD 파일
  │
  ▼
[extract_psd.py]          ← 레이어 전체 추출 (텍스트·색상·이미지·그룹·블렌드)
  │  metadata.json
  ▼
[layout_analyzer.py]      ← Auto Layout 방향·패딩·간격·반응형 sizing 분석
  │  metadata.json (업데이트)
  ▼
[figma_plugin_generator.py] ← Figma Plugin JavaScript 코드 자동 생성
  │  output_assets/figma_plugin_code.js
  ▼
[antigravity-figma-plugin]  ← Figma 내에서 플러그인 실행 → 레이어 생성
  │
  ▼
[n8n Webhook]             ← 결과 리포트 수신 → Discord 알림 발송
```

---

## ⚡ 빠른 시작

### 1. 환경 설정

```powershell
cd antigravity-design-automation
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 열어 FIGMA_TOKEN, N8N_WEBHOOK_URL 설정
```

### 2. 파이프라인 실행

```powershell
python run_pipeline.py path/to/your/design.psd
# 선택 옵션:
python run_pipeline.py design.psd --output my_output --frame-name "My App Design"
```

실행 결과:
- `output_assets/metadata.json` — 레이어 트리 + Auto Layout 힌트
- `output_assets/layer_*.png` — 이미지 레이어 PNG
- `output_assets/figma_plugin_code.js` — **Figma Plugin 실행 코드** (핵심)
- `output_assets/pipeline_report.json` — 요약 리포트

### 3. Figma 플러그인 등록 (최초 1회)

1. **Figma Desktop App** 실행
2. 메뉴: **Plugins → Development → Import plugin from manifest...**
3. `antigravity-figma-plugin/manifest.json` 파일 선택
4. 이후: **Plugins → Development → Antigravity PSD Importer** 로 실행

### 4. Figma에서 임포트

1. 플러그인 UI에서 `output_assets/figma_plugin_code.js` 드래그 앤 드롭
2. (선택) `output_assets/*.png` 이미지 파일들도 함께 선택
3. **⚡ Figma에 임포트** 버튼 클릭
4. 레이어가 Figma 캔버스에 자동 생성됩니다!

### 5. n8n 알림 설정

1. n8n이 실행 중인지 확인 (`http://localhost:5678`)
2. `n8n_report_workflow.json` 을 n8n에 임포트 (Workflows → Import)
3. Discord 웹훅 URL을 워크플로우 노드에 입력
4. Webhook Path `design-automation-report` 를 활성화

---

## 📁 파일 구조

```
antigravity-design-automation/
├── run_pipeline.py              ← 메인 오케스트레이터 (여기서 실행!)
├── extract_psd.py               ← PSD 레이어 추출 엔진
├── layout_analyzer.py           ← Auto Layout / 반응형 분석
├── figma_plugin_generator.py    ← Figma Plugin JS 코드 생성기
├── demonstrate_pipeline.py      ← Mock 데모 (PSD 없이 테스트)
├── antigravity-figma-plugin/    ← Figma Plugin 패키지
│   ├── manifest.json
│   ├── code.js
│   └── ui.html
├── n8n_report_workflow.json     ← n8n 워크플로우 (임포트용)
├── requirements.txt
├── .env.example
└── output_assets/               ← 자동 생성 (gitignore됨)
    ├── metadata.json
    ├── figma_plugin_code.js
    ├── layer_*.png
    └── pipeline_report.json
```

---

## 🎨 변환되는 레이어 종류

| PSD 레이어 타입 | Figma 변환 결과 | 지원 속성 |
|---|---|---|
| Text Layer | Text 노드 | 폰트·크기·색상·정렬·굵기·기울기·줄간격 |
| Group Layer | Frame + Auto Layout | HORIZONTAL/VERTICAL·패딩·간격·반응형 sizing |
| Pixel/Image Layer | Rectangle + Image Fill | PNG 이미지 삽입 |
| Solid Color Layer | Rectangle + Solid Fill | 색상값 정확 재현 |
| 모든 레이어 공통 | — | 불투명도·블렌드 모드·좌표·크기·레이어명 |

---

## 🔑 환경 변수

| 변수 | 필수 | 설명 |
|---|---|---|
| `FIGMA_TOKEN` | 선택 | Figma Personal Access Token (향후 API 기능용) |
| `N8N_WEBHOOK_URL` | 선택 | n8n 웹훅 URL (알림용) |
| `FIGMA_FILE_ID` | 선택 | 결과 리포트에 포함될 Figma 파일 링크 |
| `OUTPUT_DIR` | 선택 | 출력 디렉토리 (기본값: `output_assets`) |
