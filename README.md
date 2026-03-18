# 안티그래비티 디자인 자동화

포토샵(.psd) 파일을 피그마(Figma)로 자동 변환하고, 레이어를 분리한 뒤 오토레이아웃(Auto-layout)을 자동으로 적용하는 자동화 파이프라인입니다.

## 사용 방법

### 1. 환경 설정
```bash
pip install psd-tools pillow requests
```

### 2. PSD 레이어 추출
```bash
python extract_psd.py
```
- 포토샵 파일의 모든 레이어를 분석하고 PNG 이미지와 메타데이터(JSON)로 내보냅니다.

### 3. 피그마 동기화
```bash
python figma_sync.py
```
- 추출된 데이터를 기반으로 피그마에 레이어를 자동 생성하고 오토레이아웃을 적용합니다.
- 실행 전 `FIGMA_TOKEN` 환경 변수를 설정해야 합니다.

## 파일 구조
```
안티그래비티/
├── extract_psd.py   # PSD 레이어 추출 스크립트
├── figma_sync.py    # 피그마 API 동기화 및 오토레이아웃 적용
└── output_assets/   # 변환된 레이어 이미지 및 메타데이터 (자동 생성)
```
