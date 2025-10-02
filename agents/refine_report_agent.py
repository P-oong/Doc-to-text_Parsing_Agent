"""
정제 리포트 생성 Agent (4단계 - Refine 시스템)
원본 vs 정제본 비교 리포트 생성
"""

import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from state import (
    RefineDocumentState,
    RefineReport,
    set_refine_report
)
import config


class RefineReportAgent:
    """
    4단계: 정제 리포트 생성 에이전트
    
    역할:
    - refine_report.json 생성
    - refine_log_YYYYMMDD_HHMMSS.csv 생성
    - 정제 전/후 비교 통계
    """
    
    def run(self, state: RefineDocumentState) -> RefineDocumentState:
        """정제 리포트 생성"""
        
        document_name = state["document_name"]
        validation_results = state["refine_validation_results"]
        refine_results = state["refine_results"]
        
        print(f"\n{'='*60}")
        print(f"[REFINE REPORT] Document: {document_name}")
        print(f"{'='*60}\n")
        
        # 통계 계산
        total_pages = len(refine_results)
        pages_need_refine = sum(1 for r in validation_results if r.need_refine)
        pages_refined = sum(1 for r in refine_results if r.refined)
        pages_skipped = total_pages - pages_refined
        
        # 비용/시간 계산
        total_processing_time = sum(r.processing_time_ms for r in validation_results)
        total_processing_time += sum(r.processing_time_ms for r in refine_results)
        
        total_llm_cost = sum(r.llm_cost_usd for r in validation_results)
        total_llm_cost += sum(r.llm_cost_usd for r in refine_results)
        
        # 리포트 객체 생성
        report = RefineReport(
            document_name=document_name,
            strategy=state["extraction_results"][0].strategy if state["extraction_results"] else "unknown",
            total_pages=total_pages,
            pages_need_refine=pages_need_refine,
            pages_refined=pages_refined,
            pages_skipped=pages_skipped,
            validation_results=validation_results,
            refine_results=refine_results,
            total_processing_time_ms=total_processing_time,
            total_llm_cost_usd=total_llm_cost,
            timestamp=datetime.now()
        )
        
        # JSON 리포트 저장
        json_path = self._save_json_report(report, document_name)
        report.report_json_path = json_path
        print(f"[SAVED] JSON report: {json_path}")
        
        # CSV 로그 저장
        csv_path = self._save_csv_log(report, document_name)
        report.report_csv_path = csv_path
        print(f"[SAVED] CSV log: {csv_path}")
        
        # 통계 출력
        print(f"\n[STATISTICS]")
        print(f"  Total pages: {total_pages}")
        print(f"  Pages need refine: {pages_need_refine}")
        print(f"  Pages refined: {pages_refined}")
        print(f"  Pages skipped: {pages_skipped}")
        print(f"  Total processing time: {total_processing_time:.0f}ms")
        print(f"  Total LLM cost: ${total_llm_cost:.4f}")
        print()
        
        # 상태에 리포트 저장
        state = set_refine_report(state, report)
        state["current_stage"] = "complete"
        
        return state
    
    def _save_json_report(self, report: RefineReport, document_name: str) -> str:
        """JSON 리포트 저장"""
        
        # 출력 디렉토리 생성
        output_dir = config.REPORTS_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 파일명: {document_name}_refine_report.json
        safe_name = document_name.replace('.pdf', '').replace(' ', '_')
        json_path = output_dir / f"{safe_name}_refine_report.json"
        
        # 리포트 데이터 구성
        report_data = {
            "document_name": report.document_name,
            "strategy": report.strategy,
            "timestamp": report.timestamp.isoformat(),
            
            "statistics": {
                "total_pages": report.total_pages,
                "pages_need_refine": report.pages_need_refine,
                "pages_refined": report.pages_refined,
                "pages_skipped": report.pages_skipped,
                "refine_rate": f"{(report.pages_refined / report.total_pages * 100) if report.total_pages > 0 else 0:.1f}%"
            },
            
            "costs": {
                "total_processing_time_ms": report.total_processing_time_ms,
                "total_llm_cost_usd": report.total_llm_cost_usd
            },
            
            "validation_results": [
                {
                    "page_num": v.page_num,
                    "strategy": v.strategy,
                    "need_refine": v.need_refine,
                    "issues": v.issues,
                    "confidence": v.confidence,
                    "reason": v.reason
                }
                for v in report.validation_results
            ],
            
            "refine_results": [
                {
                    "page_num": r.page_num,
                    "strategy": r.strategy,
                    "need_refine": r.need_refine,
                    "refined": r.refined,
                    "refine_actions": r.refine_actions,
                    "character_diff": r.character_diff,
                    "improvements": r.improvements,
                    "original_length": len(r.original_text) if r.original_text else 0,
                    "refined_length": len(r.refined_text) if r.refined_text else 0
                }
                for r in report.refine_results
            ]
        }
        
        # JSON 파일 저장
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        return str(json_path)
    
    def _save_csv_log(self, report: RefineReport, document_name: str) -> str:
        """CSV 로그 저장"""
        
        # 출력 디렉토리 생성
        output_dir = config.TABLES_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 타임스탬프 포함 파일명
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = document_name.replace('.pdf', '').replace(' ', '_')
        csv_path = output_dir / f"{safe_name}_refine_log_{timestamp}.csv"
        
        # CSV 데이터 구성
        rows = []
        
        # 검증 결과와 정제 결과를 매칭
        refine_dict = {r.page_num: r for r in report.refine_results}
        
        for val_result in report.validation_results:
            page_num = val_result.page_num
            refine_result = refine_dict.get(page_num)
            
            row = {
                "page_num": page_num,
                "strategy": val_result.strategy,
                "need_refine": "Yes" if val_result.need_refine else "No",
                "refined": "Yes" if (refine_result and refine_result.refined) else "No",
                
                # 발견된 문제들
                "line_break_errors": "Yes" if val_result.issues.get("line_break_errors") else "No",
                "header_footer_noise": "Yes" if val_result.issues.get("header_footer_noise") else "No",
                "mixed_content": "Yes" if val_result.issues.get("mixed_content") else "No",
                "encoding_errors": "Yes" if val_result.issues.get("encoding_errors") else "No",
                "paragraph_structure": "Yes" if val_result.issues.get("paragraph_structure") else "No",
                
                "confidence": f"{val_result.confidence:.2f}",
                "reason": val_result.reason,
                
                # 정제 작업 내용
                "refine_actions": ", ".join(refine_result.refine_actions) if refine_result else "",
                "character_diff": refine_result.character_diff if refine_result else 0,
                
                # 원본/정제본 텍스트 미리보기
                "original_preview": (refine_result.original_text[:100] + "...") if refine_result and refine_result.original_text else "",
                "refined_preview": (refine_result.refined_text[:100] + "...") if refine_result and refine_result.refined_text else "",
                
                # 비용/시간
                "validation_time_ms": f"{val_result.processing_time_ms:.0f}",
                "refine_time_ms": f"{refine_result.processing_time_ms:.0f}" if refine_result else "0",
                "validation_cost_usd": f"${val_result.llm_cost_usd:.6f}",
                "refine_cost_usd": f"${refine_result.llm_cost_usd:.6f}" if refine_result else "$0.000000"
            }
            
            rows.append(row)
        
        # CSV 파일 저장
        if rows:
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
        
        return str(csv_path)

