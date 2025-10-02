"""
Upstage Document Parse Tool
Upstage Document Parsing API를 사용한 문서 파싱
"""

import requests
import os
from pathlib import Path
from typing import Dict, List, Any, Union


class UpstageDocumentParseTool:
    """
    Upstage Document Parsing API 기반 문서 파싱
    
    특징:
    - 문서 구조 인식 (제목, 문단, 표 등)
    - 레이아웃 분석
    - 고급 파싱 기능
    """
    
    def __init__(self):
        self.api_key = os.getenv("SOLAR_API_KEY")
        if not self.api_key:
            raise ValueError("SOLAR_API_KEY not found in environment variables")
        
        # 올바른 API 엔드포인트
        self.api_url = "https://api.upstage.ai/v1/document-digitization"
    
    def get_version(self) -> str:
        """도구 버전 반환"""
        return "upstage-document-parse-v1"
    
    def extract(self, pdf_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Upstage Document Parse API로 PDF 추출
        
        Args:
            pdf_path: PDF 파일 경로
            
        Returns:
            {
                "pages": [
                    {
                        "page": 1,
                        "text": "추출된 텍스트",
                        "bbox": [...],
                        "tables": [...]
                    }
                ],
                "settings": {...}
            }
        """
        
        if not isinstance(pdf_path, Path):
            pdf_path = Path(pdf_path)
        
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # PDF 파일을 바이너리로 읽기
            with open(pdf_path, 'rb') as f:
                files = {"document": f}
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                # API 파라미터 (document-parse 모델 사용)
                data = {
                    "ocr": "auto",  # OCR 자동 감지
                    "model": "document-parse",  # stable alias
                    "base64_encoding": "['figure', 'chart', 'table', 'equation']",
                    "merge_multipage_tables": "true"
                }
                
                # API 호출
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    files=files,
                    data=data,
                    timeout=120  # 문서 파싱은 시간이 걸릴 수 있음
                )
                
                response.raise_for_status()
                result = response.json()
            
            # 응답 파싱
            pages = self._parse_upstage_response(result)
            
            return {
                "pages": pages,
                "settings": {
                    "api": "upstage-document-parse",
                    "version": self.get_version(),
                    "ocr": "auto"
                }
            }
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Upstage Document Parse API error: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] Upstage Document Parse processing error: {e}")
            raise
    
    def _parse_upstage_response(self, response: Dict) -> List[Dict]:
        """
        Upstage Document Parse API 응답을 표준 형식으로 변환
        
        Args:
            response: Upstage API 응답
            
        Returns:
            페이지 리스트
        """
        pages = []
        
        # Document Parse API 응답 구조: elements 배열
        if "elements" in response:
            # 엘리먼트 기반 파싱
            page_texts = {}
            page_bboxes = {}
            page_tables = {}
            
            for element in response["elements"]:
                page_num = element.get("page", 1)
                category = element.get("category", "")
                
                if page_num not in page_texts:
                    page_texts[page_num] = []
                    page_bboxes[page_num] = []
                    page_tables[page_num] = []
                
                # content 객체에서 텍스트 추출 (markdown → text → html 순)
                content_obj = element.get("content", {})
                text = (
                    content_obj.get("markdown") or 
                    content_obj.get("text") or 
                    content_obj.get("html", "")
                )
                
                # 텍스트가 있으면 추가
                if text and text.strip():
                    page_texts[page_num].append(text)
                    
                    # 바운딩 박스 추가
                    if "coordinates" in element:
                        coords = element["coordinates"]
                        if isinstance(coords, list) and len(coords) >= 4:
                            # 좌표가 리스트 형태인 경우: [x, y, width, height]
                            page_bboxes[page_num].append({
                                "x0": coords[0].get("x", 0) if isinstance(coords[0], dict) else coords[0],
                                "y0": coords[0].get("y", 0) if isinstance(coords[0], dict) else coords[1],
                                "x1": coords[2].get("x", 0) if isinstance(coords[2], dict) else coords[2],
                                "y1": coords[2].get("y", 0) if isinstance(coords[2], dict) else coords[3],
                                "text": text[:100]  # 텍스트 일부만 저장
                            })
                
                # 표 정보 추출
                if category == "table":
                    # 표는 이미 markdown이나 text로 변환되어 있음
                    # 추가 메타데이터만 저장
                    page_tables[page_num].append({
                        "category": "table",
                        "text": text[:200],  # 표 내용 일부
                        "has_base64": "base64_encoding" in element
                    })
            
            # 페이지별로 정리
            for page_num in sorted(page_texts.keys()):
                pages.append({
                    "page": page_num,
                    "text": "\n\n".join(page_texts[page_num]),  # 요소 간 구분을 위해 더블 줄바꿈
                    "bbox": page_bboxes[page_num],
                    "tables": page_tables[page_num],
                    "width": 0,
                    "height": 0
                })
        
        # 응답이 비어있는 경우 기본값 반환
        if not pages:
            pages = [{
                "page": 1,
                "text": "",
                "bbox": [],
                "tables": [],
                "width": 0,
                "height": 0
            }]
        
        return pages
    
    def process(self, pages: List[Dict], document_path: str) -> List[Dict]:
        """
        폴백 처리용 메서드 (문서 파싱 재실행은 비효율적이므로 원본 반환)
        
        Args:
            pages: 페이지 데이터 리스트
            document_path: 문서 경로
            
        Returns:
            처리된 페이지 리스트 (원본 그대로)
        """
        # 문서 파싱을 폴백으로 재실행하는 것은 비효율적이므로
        # 이미 추출된 결과를 그대로 반환
        return pages


if __name__ == "__main__":
    # 테스트
    import sys
    
    if len(sys.argv) > 1:
        test_pdf = sys.argv[1]
    else:
        test_pdf = "C:\Users\Admin\agentserver\data\input\카카오뱅크_20240508_한화투자증권.pdf"
    
    if Path(test_pdf).exists():
        try:
            tool = UpstageDocumentParseTool()
            result = tool.extract(test_pdf)
            
            print(f"[OK] Upstage Document Parse extraction completed")
            print(f"Pages: {len(result['pages'])}")
            
            if result['pages']:
                first_page = result['pages'][0]
                print(f"\nFirst page preview:")
                print(f"  Text length: {len(first_page['text'])} chars")
                print(f"  Text sample: {first_page['text'][:200]}...")
                print(f"  Bbox count: {len(first_page['bbox'])}")
                print(f"  Tables: {len(first_page['tables'])}")
        except Exception as e:
            print(f"[ERROR] Test failed: {e}")
    else:
        print(f"[ERROR] Test file not found: {test_pdf}")

