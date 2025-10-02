"""
정제 필요 여부 검증 Agent (2단계 - Refine 시스템)
문서가 정제가 필요한지 판단
"""

import time
import json
from typing import Dict, Any
from datetime import datetime

from state import (
    RefineDocumentState,
    PageRefineValidationResult,
    add_refine_validation_result,
    update_stage
)
from utils.llm_client import LLMClient
from prompts.refine_prompts import (
    REFINE_VALIDATION_SYSTEM_PROMPT,
    create_refine_validation_prompt
)


class RefineValidationAgent:
    """
    2단계: 정제 필요 여부 검증 에이전트
    
    역할:
    - 추출된 텍스트가 정제가 필요한지 판단
    - Solar LLM 기반 검증
    - Need Refine / No Refine 판정
    """
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def run(self, state: RefineDocumentState) -> RefineDocumentState:
        """정제 필요 여부 검증 실행"""
        
        document_name = state["document_name"]
        extraction_results = state["extraction_results"]
        
        print(f"\n{'='*60}")
        print(f"[REFINE VALIDATION] Document: {document_name}")
        print(f"{'='*60}\n")
        
        # 모든 추출 전략에 대해 검증
        for extraction_result in extraction_results:
            strategy = extraction_result.strategy
            print(f"[VALIDATION] Checking strategy: {strategy}")
            
            for page_result in extraction_result.page_results:
                page_num = page_result.page_num
                text = page_result.text
                
                # 텍스트가 너무 짧으면 정제 불필요
                if len(text.strip()) < 50:
                    validation_result = PageRefineValidationResult(
                        page_num=page_num,
                        extraction_id=f"{strategy}_{page_num}",
                        strategy=strategy,
                        need_refine=False,
                        issues={},
                        confidence=1.0,
                        reason="텍스트가 너무 짧아 정제 불필요",
                        processing_time_ms=0.0,
                        llm_cost_usd=0.0
                    )
                    state = add_refine_validation_result(state, validation_result)
                    print(f"  Page {page_num}: No Refine (too short)")
                    continue
                
                # LLM으로 정제 필요 여부 판단
                validation_result = self._validate_page(
                    page_text=text,
                    page_num=page_num,
                    strategy=strategy
                )
                
                state = add_refine_validation_result(state, validation_result)
                
                status = "Need Refine" if validation_result.need_refine else "No Refine"
                print(f"  Page {page_num}: {status} (conf: {validation_result.confidence:.2f})")
        
        # 통계 출력
        total_pages = len(state["refine_validation_results"])
        need_refine_count = sum(1 for r in state["refine_validation_results"] if r.need_refine)
        no_refine_count = total_pages - need_refine_count
        
        print(f"\n[SUMMARY] Validation completed")
        print(f"  Total pages: {total_pages}")
        print(f"  Need Refine: {need_refine_count}")
        print(f"  No Refine: {no_refine_count}")
        print()
        
        # 단계 업데이트
        state["current_stage"] = "refine_validation_complete"
        
        return state
    
    def _validate_page(
        self,
        page_text: str,
        page_num: int,
        strategy: str
    ) -> PageRefineValidationResult:
        """페이지별 정제 필요 여부 검증"""
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            user_prompt = create_refine_validation_prompt(page_text, page_num)
            
            # LLM 호출
            response = self.llm_client.chat(
                system_prompt=REFINE_VALIDATION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,  # 낮은 temperature로 일관성 있는 판단
                response_format="json"
            )
            
            # 응답 파싱
            response_text = response.get("content", "{}")
            llm_result = json.loads(response_text)
            
            # 비용 계산
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            llm_cost = self.llm_client.calculate_cost(prompt_tokens, completion_tokens)
            
            # 결과 생성
            validation_result = PageRefineValidationResult(
                page_num=page_num,
                extraction_id=f"{strategy}_{page_num}",
                strategy=strategy,
                need_refine=llm_result.get("need_refine", False),
                issues=llm_result.get("issues", {}),
                confidence=llm_result.get("confidence", 0.0),
                reason=llm_result.get("reason", ""),
                llm_response=response,
                processing_time_ms=(time.time() - start_time) * 1000,
                llm_cost_usd=llm_cost,
                timestamp=datetime.now()
            )
            
            return validation_result
            
        except Exception as e:
            print(f"[ERROR] Validation failed for page {page_num}: {e}")
            
            # 에러 시 기본값 (정제 불필요로 처리)
            return PageRefineValidationResult(
                page_num=page_num,
                extraction_id=f"{strategy}_{page_num}",
                strategy=strategy,
                need_refine=False,
                issues={},
                confidence=0.0,
                reason=f"검증 실패: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
                llm_cost_usd=0.0,
                metadata={"error": str(e)}
            )

