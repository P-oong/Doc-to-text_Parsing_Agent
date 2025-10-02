"""
시스템 설정 테스트
"""

import sys
from pathlib import Path

print("="*60)
print("Doc-to-Text 시스템 설정 테스트")
print("="*60)
print()

# 1. Python 버전 확인
print(f"1. Python 버전: {sys.version}")
print()

# 2. 필수 모듈 확인
print("2. 필수 모듈 확인:")
required_modules = [
    "langgraph",
    "langchain",
    "pdfplumber",
    "paddleocr",
    "requests",
    "pandas",
    "PIL"
]

missing_modules = []
for module in required_modules:
    try:
        __import__(module)
        print(f"   [OK] {module}")
    except ImportError:
        print(f"   [X] {module} - 설치 필요")
        missing_modules.append(module)

print()

# 3. .env 파일 확인
print("3. 환경 변수 파일:")
import config

env_file = config.PROJECT_ROOT / ".env"
env_example = config.PROJECT_ROOT / "env.example"

if env_file.exists():
    print(f"   [OK] .env 파일 존재")
else:
    print(f"   [X] .env 파일 없음")
    if env_example.exists():
        print(f"       -> env.example을 .env로 복사하세요: copy env.example .env")
    else:
        print(f"       -> .env 파일을 생성하고 SOLAR_API_KEY를 설정하세요")

print()

# 4. 디렉토리 구조 확인
print("4. 디렉토리 구조:")

dirs_to_check = [
    ("입력", config.INPUT_DIR),
    ("출력", config.OUTPUT_DIR),
    ("임시", config.TEMP_DIR),
    ("리포트", config.REPORTS_DIR),
    ("테이블", config.TABLES_DIR),
]

for name, path in dirs_to_check:
    if path.exists():
        print(f"   [OK] {name}: {path}")
    else:
        print(f"   [X] {name}: {path} - 디렉토리 없음")

print()

# 5. 설정 확인
print("5. 주요 설정:")
if config.SOLAR_API_KEY:
    key_preview = config.SOLAR_API_KEY[:10] + "..." if len(config.SOLAR_API_KEY) > 10 else config.SOLAR_API_KEY
    print(f"   [OK] Solar API Key: {key_preview}")
else:
    print(f"   [X] Solar API Key: 미설정 - .env 파일을 확인하세요")
print(f"   - Solar Model: {config.SOLAR_MODEL}")
print(f"   - Paddle GPU: {config.PADDLE_USE_GPU}")
print(f"   - 지원 형식: {', '.join(config.SUPPORTED_FORMATS)}")

print()

# 6. 테스트 파일 확인
print("6. 입력 파일:")
from utils.file_utils import get_input_files

input_files = get_input_files()
if input_files:
    for f in input_files[:5]:  # 최대 5개만 표시
        print(f"   - {f.name}")
    if len(input_files) > 5:
        print(f"   ... 외 {len(input_files)-5}개")
else:
    print("   (없음) - data/input/에 PDF 파일을 넣어주세요")

print()
print("="*60)

if missing_modules:
    print("[경고] 누락된 모듈 설치:")
    print(f"   pip install {' '.join(missing_modules)}")
    print()
else:
    print("[OK] 모든 설정 완료!")
    print()

print("="*60)

