"""
Custom Split Tool 테스트 스크립트
"""

import sys
from pathlib import Path

# 현재 디렉토리를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

from tools.custom_split_tool import CustomSplitTool
import config


def test_tool_initialization():
    """도구 초기화 테스트"""
    print("\n" + "="*60)
    print("[TEST 1] Custom Split Tool 초기화")
    print("="*60)
    
    try:
        tool = CustomSplitTool()
        print(f"[OK] CustomSplitTool 로드 성공")
        print(f"     DPI 설정: {tool.settings['dpi']}")
        return tool
    except Exception as e:
        print(f"[ERROR] 초기화 실패: {e}")
        return None


def test_with_pdf(tool, pdf_path: str):
    """실제 PDF 파일로 테스트"""
    print("\n" + "="*60)
    print(f"[TEST 2] PDF 파일 처리 테스트")
    print("="*60)
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        print(f"[SKIP] 파일 없음: {pdf_path}")
        return
    
    print(f"[INFO] 파일: {pdf_file.name}")
    
    try:
        # 더미 페이지 데이터 생성
        dummy_pages = [
            {
                "page": 1,
                "source": "test",
                "text": "테스트 텍스트",
                "bbox": [],
                "width": 0,
                "height": 0
            }
        ]
        
        print(f"[INFO] 처리 시작...")
        result = tool.process(dummy_pages, str(pdf_file))
        
        print(f"[OK] 처리 완료")
        print(f"     원본 페이지 수: {len(dummy_pages)}")
        print(f"     결과 페이지 수: {len(result)}")
        
        if len(result) > len(dummy_pages):
            print(f"     [분할 발생] {len(result) - len(dummy_pages)}개 페이지 추가됨")
        
        # 첫 페이지 정보 출력
        if result:
            first_page = result[0]
            print(f"\n     첫 페이지 정보:")
            print(f"     - 소스: {first_page.get('source', 'N/A')}")
            print(f"     - 텍스트 길이: {len(first_page.get('text', ''))}")
            print(f"     - bbox 개수: {len(first_page.get('bbox', []))}")
            print(f"     - 크기: {first_page.get('width', 0):.1f} x {first_page.get('height', 0):.1f}")
        
    except Exception as e:
        print(f"[ERROR] 처리 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("\n" + "="*60)
    print("Custom Split Tool 테스트")
    print("="*60)
    
    # 1. 초기화 테스트
    tool = test_tool_initialization()
    if not tool:
        return
    
    # 2. PDF 파일 테스트 (data/input 폴더에서 찾기)
    input_dir = Path(__file__).parent / "data" / "input"
    
    if input_dir.exists():
        pdf_files = list(input_dir.glob("*.pdf"))
        if pdf_files:
            print(f"\n[INFO] 발견된 PDF 파일: {len(pdf_files)}개")
            # 첫 번째 파일로 테스트
            test_with_pdf(tool, str(pdf_files[0]))
        else:
            print(f"\n[SKIP] {input_dir}에 PDF 파일이 없습니다")
    else:
        print(f"\n[SKIP] {input_dir} 폴더가 없습니다")
    
    print("\n" + "="*60)
    print("[완료] 테스트 종료")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()

