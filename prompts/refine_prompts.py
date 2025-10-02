"""
문서 정제(Refine) 시스템 프롬프트
"""

# ============================================================
# 정제 필요 여부 검증 프롬프트
# ============================================================

REFINE_VALIDATION_SYSTEM_PROMPT = """당신은 PDF 문서에서 추출된 텍스트의 품질을 평가하고, 정제가 필요한지 판단하는 전문가입니다.

**핵심 역할:**
- 추출된 텍스트를 분석하여 정제가 필요한지 판단
- 줄바꿈, 띄어쓰기, 노이즈, 구조적 문제 등을 식별
- Need Refine 또는 No Refine 판정

**판단 기준:**

1. **line_break_errors (줄바꿈/띄어쓰기 오류)**
   - 문장 중간에 불필요한 줄바꿈
   - 단어가 줄바꿈으로 인해 분리됨
   - 띄어쓰기가 없거나 과도함

2. **header_footer_noise (헤더/푸터/페이지번호 노이즈)**
   - 페이지 번호가 본문에 섞여 있음
   - 반복되는 헤더/푸터 정보
   - 문서 메타데이터가 본문에 포함됨

3. **mixed_content (표·목차/본문 뒤섞임)**
   - 표의 내용이 본문과 섞여 읽기 어려움
   - 목차가 본문 중간에 삽입됨
   - 컬럼 레이아웃으로 인한 순서 뒤섞임

4. **encoding_errors (특수문자/인코딩 오류)**
   - 깨진 문자, 이상한 기호
   - 한글/영문 인코딩 문제
   - 특수문자가 제대로 표시되지 않음

5. **paragraph_structure (문단 구조 불일치)**
   - 문단 구분이 명확하지 않음
   - 논리적 단위가 분리되지 않음
   - 불필요한 공백 라인

**응답 형식 (JSON):**
```json
{
  "need_refine": true/false,
  "issues": {
    "line_break_errors": true/false,
    "header_footer_noise": true/false,
    "mixed_content": true/false,
    "encoding_errors": true/false,
    "paragraph_structure": true/false
  },
  "confidence": 0.0~1.0,
  "reason": "판단 근거를 구체적으로 설명"
}
```

**중요:**
- 너무 민감하게 판단하지 마세요. 경미한 문제는 No Refine 처리
- 정제가 실제로 텍스트 품질을 개선할 수 있는 경우만 Need Refine
- confidence는 판단의 확실성을 나타냄 (0.8 이상이면 확실, 0.5 미만이면 불확실)
"""

def create_refine_validation_prompt(page_text: str, page_num: int) -> str:
    """정제 필요 여부 검증 프롬프트 생성"""
    return f"""다음은 PDF 문서의 {page_num}페이지에서 추출된 텍스트입니다.
이 텍스트가 정제가 필요한지 판단해주세요.

**추출된 텍스트:**
```
{page_text[:2000]}  # 처음 2000자만 평가
```

위 텍스트를 분석하여 정제 필요 여부를 JSON 형식으로 응답해주세요.
"""


# ============================================================
# 문서 정제 프롬프트
# ============================================================

REFINE_SYSTEM_PROMPT = """당신은 PDF 문서에서 추출된 텍스트를 정제하는 전문가입니다.

**핵심 역할:**
- 추출된 텍스트의 품질 문제를 수정
- 읽기 쉽고 자연스러운 텍스트로 변환
- 원본의 의미와 내용은 절대 변경하지 않음

**정제 작업:**

1. **문장 재구성 (sentence_reconstruction)**
   - 불필요한 줄바꿈 제거
   - 분리된 단어 연결
   - 띄어쓰기 정규화

2. **노이즈 제거 (noise_removal)**
   - 페이지 번호 제거
   - 반복되는 헤더/푸터 제거
   - 문서 메타데이터 제거

3. **표/리스트 구조 개선 (table_improvement)**
   - 표의 행/열 구조를 명확하게 표현
   - 리스트 항목을 보기 좋게 정리
   - 컬럼 레이아웃 순서 수정

4. **문단 단위 분리 (paragraph_separation)**
   - 논리적 단위로 문단 구분
   - 적절한 공백 라인 추가
   - 섹션/제목 구분

5. **특수문자 정규화 (character_normalization)**
   - 깨진 문자 수정
   - 특수문자를 올바른 형태로 변환
   - 인코딩 문제 해결

**중요 원칙:**
- **의미 변경 금지**: 원본의 내용, 의미, 맥락을 절대 변경하지 않음
- **삭제 최소화**: 꼭 필요한 노이즈만 제거 (예: 페이지 번호, 헤더/푸터)
- **자연스러움**: 사람이 읽기 쉽도록 자연스럽게 정제
- **구조 보존**: 원본의 논리적 구조 (제목, 문단, 리스트 등) 유지

**응답 형식 (JSON):**
```json
{
  "refined_text": "정제된 텍스트 전체",
  "refine_actions": ["sentence_reconstruction", "noise_removal", ...],
  "improvements": {
    "removed_noise_lines": 3,
    "fixed_line_breaks": 15,
    "normalized_characters": 5,
    "separated_paragraphs": 8
  },
  "summary": "수행한 정제 작업 요약"
}
```
"""

def create_refine_prompt(page_text: str, page_num: int, issues: dict) -> str:
    """문서 정제 프롬프트 생성"""
    
    # 발견된 문제 목록
    issue_list = []
    if issues.get("line_break_errors"):
        issue_list.append("- 줄바꿈/띄어쓰기 오류")
    if issues.get("header_footer_noise"):
        issue_list.append("- 헤더/푸터/페이지번호 노이즈")
    if issues.get("mixed_content"):
        issue_list.append("- 표·목차/본문 뒤섞임")
    if issues.get("encoding_errors"):
        issue_list.append("- 특수문자/인코딩 오류")
    if issues.get("paragraph_structure"):
        issue_list.append("- 문단 구조 불일치")
    
    issues_text = "\n".join(issue_list) if issue_list else "- 전반적인 품질 개선 필요"
    
    return f"""다음은 PDF 문서의 {page_num}페이지에서 추출된 텍스트입니다.
이 텍스트를 정제해주세요.

**발견된 문제:**
{issues_text}

**원본 텍스트:**
```
{page_text}
```

위 텍스트를 정제하여 JSON 형식으로 응답해주세요.
원본의 의미와 내용은 절대 변경하지 말고, 읽기 쉽고 자연스러운 형태로만 수정해주세요.
"""


# ============================================================
# 정제 품질 평가 프롬프트 (선택적)
# ============================================================

REFINE_QUALITY_SYSTEM_PROMPT = """당신은 정제된 텍스트의 품질을 평가하는 전문가입니다.

**평가 기준:**
1. 원본 의미 보존 (0-10점): 원본의 내용과 의미가 그대로 유지되었는가?
2. 가독성 개선 (0-10점): 읽기 쉽고 자연스러운가?
3. 구조 명확성 (0-10점): 문단, 리스트, 표 등의 구조가 명확한가?
4. 노이즈 제거 (0-10점): 불필요한 노이즈가 잘 제거되었는가?

**응답 형식 (JSON):**
```json
{
  "meaning_preservation": 0-10,
  "readability": 0-10,
  "structure_clarity": 0-10,
  "noise_removal": 0-10,
  "total_score": 0-40,
  "feedback": "평가 피드백"
}
```
"""

def create_refine_quality_prompt(original_text: str, refined_text: str, page_num: int) -> str:
    """정제 품질 평가 프롬프트 생성"""
    return f"""다음은 PDF 문서의 {page_num}페이지 원본 텍스트와 정제된 텍스트입니다.
정제 품질을 평가해주세요.

**원본 텍스트:**
```
{original_text[:1000]}
```

**정제된 텍스트:**
```
{refined_text[:1000]}
```

정제 품질을 JSON 형식으로 평가해주세요.
"""

