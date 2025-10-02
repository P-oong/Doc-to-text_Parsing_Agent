"""
Upstage Document Parse Tool
Upstage Document Parsing API를 사용한 문서 파싱
"""

import requests
import os
import json
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
            print(f"[INFO] Upstage Document Parse 시작: {pdf_path.name}")
            
            # PDF 파일을 바이너리로 읽기
            with open(pdf_path, 'rb') as f:
                files = {"document": f}
                headers = {"Authorization": f"Bearer {self.api_key}"}
                
                # API 파라미터 (document-parse 모델 사용)
                # base64_encoding은 JSON 배열 문자열로 전달
                data = {
                    "ocr": "auto",  # OCR 자동 감지
                    "model": "document-parse"  # stable alias
                }
                
                print(f"[INFO] API 호출 중... (최대 120초 대기)")
                
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
                
                print(f"[INFO] API 응답 수신 완료")
            
            # 응답 구조 확인
            if "elements" in result:
                print(f"[INFO] elements 개수: {len(result['elements'])}")
            else:
                print(f"[WARNING] API 응답에 'elements' 필드가 없습니다. 응답 키: {list(result.keys())}")
            
            # 응답 파싱
            pages = self._parse_upstage_response(result)
            
            print(f"[INFO] 파싱 완료: {len(pages)}개 페이지")
            
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
        if "elements" in response and len(response["elements"]) > 0:
            # 엘리먼트 기반 파싱
            page_texts = {}
            page_bboxes = {}
            page_tables = {}
            
            print(f"[DEBUG] 처리할 elements: {len(response['elements'])}개")
            
            for idx, element in enumerate(response["elements"]):
                page_num = element.get("page", 1)
                category = element.get("category", "text")
                element_id = element.get("id", idx)
                
                if page_num not in page_texts:
                    page_texts[page_num] = []
                    page_bboxes[page_num] = []
                    page_tables[page_num] = []
                
                # content 객체에서 텍스트 추출 (markdown → text → html 순)
                content_obj = element.get("content", {})
                
                # content가 문자열인 경우도 처리
                if isinstance(content_obj, str):
                    text = content_obj
                elif isinstance(content_obj, dict):
                    text = (
                        content_obj.get("markdown") or 
                        content_obj.get("text") or 
                        content_obj.get("html", "")
                    )
                else:
                    text = ""
                
                # 텍스트가 있으면 추가
                if text and text.strip():
                    page_texts[page_num].append(text)
                    
                    # 바운딩 박스 추가 (coordinates는 4개의 점 [{x, y}, {x, y}, {x, y}, {x, y}] 형식)
                    if "coordinates" in element:
                        try:
                            coords = element["coordinates"]
                            if isinstance(coords, list) and len(coords) >= 4:
                                # 좌표가 dict 리스트인 경우
                                if isinstance(coords[0], dict):
                                    x_coords = [c.get("x", 0) for c in coords if "x" in c]
                                    y_coords = [c.get("y", 0) for c in coords if "y" in c]
                                    
                                    if x_coords and y_coords:
                                        page_bboxes[page_num].append({
                                            "x0": min(x_coords),
                                            "y0": min(y_coords),
                                            "x1": max(x_coords),
                                            "y1": max(y_coords),
                                            "text": text[:100]  # 텍스트 일부만 저장
                                        })
                                # 좌표가 숫자 리스트인 경우 [x0, y0, x1, y1]
                                elif isinstance(coords[0], (int, float)):
                                    page_bboxes[page_num].append({
                                        "x0": coords[0],
                                        "y0": coords[1],
                                        "x1": coords[2],
                                        "y1": coords[3],
                                        "text": text[:100]
                                    })
                        except Exception as e:
                            print(f"[WARNING] 좌표 파싱 오류 (element {element_id}): {e}")
                
                # 표 정보 추출
                if category == "table":
                    page_tables[page_num].append({
                        "category": "table",
                        "text": text[:200],  # 표 내용 일부
                        "has_base64": "base64_encoding" in element
                    })
            
            # 페이지별로 정리
            for page_num in sorted(page_texts.keys()):
                page_text = "\n\n".join(page_texts[page_num])
                print(f"[DEBUG] 페이지 {page_num}: {len(page_text)} 문자, {len(page_bboxes[page_num])} bbox, {len(page_tables[page_num])} tables")
                
                pages.append({
                    "page": page_num,
                    "text": page_text,
                    "bbox": page_bboxes[page_num],
                    "tables": page_tables[page_num],
                    "width": 0,
                    "height": 0
                })
        
        # 응답이 비어있는 경우
        if not pages:
            print("[WARNING] 파싱된 페이지가 없습니다. 빈 페이지를 반환합니다.")
            # 실제 페이지 수를 확인해서 빈 페이지들을 생성
            if "usage" in response and "pages" in response["usage"]:
                total_pages = response["usage"]["pages"]
                pages = [
                    {
                        "page": i,
                        "text": "",
                        "bbox": [],
                        "tables": [],
                        "width": 0,
                        "height": 0
                    }
                    for i in range(1, total_pages + 1)
                ]
            else:
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
        # 기본 테스트 파일 경로 (이스케이프 문제 방지를 위해 raw string 사용)
        test_pdf = r"C:\Users\Admin\agentserver\data\input\카카오뱅크_20240508_한화투자증권.pdf"
    
    test_path = Path(test_pdf)
    
    if test_path.exists():
        try:
            print("="*80)
            print("Upstage Document Parse Tool 테스트")
            print("="*80)
            
            tool = UpstageDocumentParseTool()
            result = tool.extract(test_path)
            
            print("\n" + "="*80)
            print("[OK] Upstage Document Parse extraction completed")
            print("="*80)
            print(f"총 페이지 수: {len(result['pages'])}")
            
            # 전체 통계
            total_text_length = sum(len(p['text']) for p in result['pages'])
            total_bboxes = sum(len(p['bbox']) for p in result['pages'])
            total_tables = sum(len(p['tables']) for p in result['pages'])
            
            print(f"총 텍스트 길이: {total_text_length:,} 문자")
            print(f"총 bbox 개수: {total_bboxes}")
            print(f"총 표 개수: {total_tables}")
            
            if result['pages']:
                print(f"\n첫 번째 페이지 미리보기:")
                first_page = result['pages'][0]
                print(f"  페이지 번호: {first_page['page']}")
                print(f"  텍스트 길이: {len(first_page['text'])} 문자")
                if first_page['text']:
                    preview = first_page['text'][:300].replace('\n', ' ')
                    print(f"  텍스트 샘플: {preview}...")
                else:
                    print(f"  ⚠️ 텍스트가 비어있습니다!")
                print(f"  Bbox 개수: {len(first_page['bbox'])}")
                print(f"  표 개수: {len(first_page['tables'])}")
            
            print("\n" + "="*80)
        except Exception as e:
            print(f"\n[ERROR] 테스트 실패: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[ERROR] 테스트 파일을 찾을 수 없습니다: {test_pdf}")

