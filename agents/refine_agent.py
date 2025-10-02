"""
문서 정제 Agent (3단계 - Refine 시스템)
Need Refine인 텍스트를 정제
"""

import time
import json
from typing import Dict, Any
from datetime import datetime

from state import (
    RefineDocumentState,
    PageRefineResult,
    add_refine_result,
    update_stage
)
from utils.llm_client import LLMClient
from prompts.refine_prompts import (
    REFINE_SYSTEM_PROMPT,
    create_refine_prompt
)


class RefineAgent:
    """
    3단계: 문서 정제 에이전트
    
    역할:
    - Need Refine인 페이지만 정제
    - Solar LLM 기반 텍스트 정제
    - 원본 + 정제본 모두 보존
    """
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def run(self, state: RefineDocumentState) -> RefineDocumentState:
        """문서 정제 실행"""
        
        document_name = state["document_name"]
        extraction_results = state["extraction_results"]
        validation_results = state["refine_validation_results"]
        
        print(f"\n{'='*60}")
        print(f"[REFINE] Document: {document_name}")
        print(f"{'='*60}\n")
        
        # 검증 결과를 딕셔너리로 변환 (빠른 조회)
        validation_dict = {}
        for val_result in validation_results:
            key = f"{val_result.strategy}_{val_result.page_num}"
            validation_dict[key] = val_result
        
        # 모든 추출 전략에 대해 정제
        for extraction_result in extraction_results:
            strategy = extraction_result.strategy
            print(f"[REFINE] Processing strategy: {strategy}")
            
            for page_result in extraction_result.page_results:
                page_num = page_result.page_num
                original_text = page_result.text
                
                # 검증 결과 가져오기
                key = f"{strategy}_{page_num}"
                validation_result = validation_dict.get(key)
                
                if not validation_result:
                    print(f"  Page {page_num}: Validation result not found, skipping")
                    continue
                
                # Need Refine인 경우만 정제
                if validation_result.need_refine:
                    refine_result = self._refine_page(
                        page_text=original_text,
                        page_num=page_num,
                        strategy=strategy,
                        issues=validation_result.issues
                    )
                    state = add_refine_result(state, refine_result)
                    print(f"  Page {page_num}: Refined ({len(refine_result.refine_actions)} actions)")
                else:
                    # No Refine인 경우 원본 그대로 기록
                    refine_result = PageRefineResult(
                        page_num=page_num,
                        extraction_id=f"{strategy}_{page_num}",
                        strategy=strategy,
                        original_text=original_text,
                        refined_text=None,  # 정제하지 않음
                        need_refine=False,
                        refined=False,
                        processing_time_ms=0.0,
                        llm_cost_usd=0.0
                    )
                    state = add_refine_result(state, refine_result)
                    print(f"  Page {page_num}: Skipped (No Refine needed)")
        
        # 통계 출력
        total_pages = len(state["refine_results"])
        refined_count = sum(1 for r in state["refine_results"] if r.refined)
        skipped_count = total_pages - refined_count
        
        print(f"\n[SUMMARY] Refine completed")
        print(f"  Total pages: {total_pages}")
        print(f"  Refined: {refined_count}")
        print(f"  Skipped: {skipped_count}")
        print()
        
        # 단계 업데이트
        state["current_stage"] = "refine_complete"
        
        return state
    
    def _refine_page(
        self,
        page_text: str,
        page_num: int,
        strategy: str,
        issues: Dict[str, bool]
    ) -> PageRefineResult:
        """페이지 정제"""
        
        start_time = time.time()
        
        try:
            # 프롬프트 생성
            user_prompt = create_refine_prompt(page_text, page_num, issues)
            
            # LLM 호출
            response = self.llm_client.chat(
                system_prompt=REFINE_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.5,  # 적절한 temperature로 자연스럽게 정제
                response_format="json"
            )
            
            # 응답 파싱
            response_text = response.get("content", "{}")
            llm_result = json.loads(response_text)
            
            refined_text = llm_result.get("refined_text", page_text)
            refine_actions = llm_result.get("refine_actions", [])
            improvements = llm_result.get("improvements", {})
            
            # 비용 계산
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            llm_cost = self.llm_client.calculate_cost(prompt_tokens, completion_tokens)
            
            # 통계 계산
            character_diff = len(refined_text) - len(page_text)
            
            # 결과 생성
            refine_result = PageRefineResult(
                page_num=page_num,
                extraction_id=f"{strategy}_{page_num}",
                strategy=strategy,
                original_text=page_text,
                refined_text=refined_text,
                need_refine=True,
                refined=True,
                refine_actions=refine_actions,
                character_diff=character_diff,
                improvements=improvements,
                llm_response=response,
                processing_time_ms=(time.time() - start_time) * 1000,
                llm_cost_usd=llm_cost,
                timestamp=datetime.now()
            )
            
            return refine_result
            
        except Exception as e:
            print(f"[ERROR] Refine failed for page {page_num}: {e}")
            
            # 에러 시 원본 그대로 반환
            return PageRefineResult(
                page_num=page_num,
                extraction_id=f"{strategy}_{page_num}",
                strategy=strategy,
                original_text=page_text,
                refined_text=None,
                need_refine=True,
                refined=False,
                processing_time_ms=(time.time() - start_time) * 1000,
                llm_cost_usd=0.0,
                metadata={"error": str(e)}
            )

