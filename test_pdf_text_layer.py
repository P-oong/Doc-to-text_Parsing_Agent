"""
PDF 텍스트 레이어 확인 스크립트
"""
import pdfplumber
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "data/input/카카오뱅크_20240508_한화투자증권.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        print(f"[INFO] PDF File: {pdf_path}")
        print(f"[INFO] Total Pages: {len(pdf.pages)}")
        print()
        
        # 첫 페이지 텍스트 추출
        page1 = pdf.pages[0]
        text = page1.extract_text()
        
        if text and len(text.strip()) > 0:
            print("[OK] Text layer found!")
            print(f"[INFO] First page text length: {len(text)} characters")
            print()
            print("[SAMPLE] First 300 characters:")
            print("-" * 60)
            print(text[:300])
            print("-" * 60)
            print()
            print("[RESULT] This PDF can be parsed with pdfplumber!")
        else:
            print("[FAIL] No text layer found!")
            print("[INFO] This is likely a scanned/image-based PDF")
            print("[SOLUTION] This PDF requires OCR processing")
            
except Exception as e:
    print(f"[ERROR] {str(e)}")

