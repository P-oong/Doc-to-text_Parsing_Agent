"""
메인 실행 파일
LangGraph 기반 문서 파싱 시스템
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent))

import config
from state import create_initial_document_state, create_initial_refine_state
from graph import create_processing_graph
from refine_graph import create_refine_graph
from utils.file_utils import ensure_directories, get_input_files


def run_strategy_mode(input_files: List[Path], args) -> List[Dict]:
    """파싱 전략 선택 모드 실행"""
    
    print(f"\n{'*'*80}")
    print(f"SYSTEM A: OCR/Parsing Strategy Selection")
    print(f"{'*'*80}\n")
    
    # LangGraph 그래프 생성
    graph = create_processing_graph()
    
    results = []
    
    for idx, file_path in enumerate(input_files, 1):
        print(f"\n{'#'*80}")
        print(f"[{idx}/{len(input_files)}] {file_path.name}")
        print(f"{'#'*80}\n")
        
        # 초기 상태 생성
        state = create_initial_document_state(str(file_path))
        
        try:
            # 그래프 실행
            final_state = graph.invoke(state)
            
            # 결과 저장
            results.append({
                "mode": "strategy",
                "file": file_path.name,
                "status": final_state["current_stage"],
                "final_selection": final_state.get("final_selection"),
                "error_count": len(final_state.get("error_log", []))
            })
            
            # 결과 출력
            print(f"\n{'='*80}")
            if final_state["current_stage"] == "completed":
                print(f"[OK] Processing completed: {file_path.name}")
                if final_state.get("final_selection"):
                    selection = final_state["final_selection"]
                    print(f"   Final strategy: {selection.selected_strategy}")
                    print(f"   Score: {selection.S_total:.3f}")
            else:
                print(f"[FAIL] Processing failed: {file_path.name}")
                print(f"   Status: {final_state['current_stage']}")
                print(f"   Errors: {len(final_state.get('error_log', []))}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"[FATAL ERROR] {file_path.name}")
            print(f"   {str(e)}")
            print(f"{'='*80}\n")
            
            import traceback
            traceback.print_exc()
            
            results.append({
                "mode": "strategy",
                "file": file_path.name,
                "status": "fatal_error",
                "final_selection": None,
                "error_count": 1
            })
    
    return results


def run_refine_mode(input_files: List[Path], args) -> List[Dict]:
    """문서 정제 모드 실행"""
    
    print(f"\n{'*'*80}")
    print(f"SYSTEM B: Document Refine")
    print(f"{'*'*80}\n")
    
    # LangGraph 그래프 생성
    graph = create_refine_graph()
    
    results = []
    
    for idx, file_path in enumerate(input_files, 1):
        print(f"\n{'#'*80}")
        print(f"[{idx}/{len(input_files)}] {file_path.name}")
        print(f"{'#'*80}\n")
        
        # 초기 상태 생성
        state = create_initial_refine_state(str(file_path), file_path.name)
        
        try:
            # 그래프 실행
            final_state = graph.invoke(state)
            
            # 결과 저장
            refine_report = final_state.get("refine_report")
            
            results.append({
                "mode": "refine",
                "file": file_path.name,
                "status": final_state["current_stage"],
                "pages_refined": refine_report.pages_refined if refine_report else 0,
                "total_pages": refine_report.total_pages if refine_report else 0,
                "error_count": len(final_state.get("error_log", []))
            })
            
            # 결과 출력
            print(f"\n{'='*80}")
            if final_state["current_stage"] == "complete":
                print(f"[OK] Refine completed: {file_path.name}")
                if refine_report:
                    print(f"   Total pages: {refine_report.total_pages}")
                    print(f"   Pages refined: {refine_report.pages_refined}")
                    print(f"   Pages skipped: {refine_report.pages_skipped}")
                    print(f"   LLM cost: ${refine_report.total_llm_cost_usd:.4f}")
            else:
                print(f"[FAIL] Refine failed: {file_path.name}")
                print(f"   Status: {final_state['current_stage']}")
                print(f"   Errors: {len(final_state.get('error_log', []))}")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"\n{'='*80}")
            print(f"[FATAL ERROR] {file_path.name}")
            print(f"   {str(e)}")
            print(f"{'='*80}\n")
            
            import traceback
            traceback.print_exc()
            
            results.append({
                "mode": "refine",
                "file": file_path.name,
                "status": "fatal_error",
                "pages_refined": 0,
                "total_pages": 0,
                "error_count": 1
            })
    
    return results


def main():
    """메인 함수"""
    
    # 인자 파싱
    parser = argparse.ArgumentParser(
        description="LangGraph 기반 Doc-to-Text 멀티 에이전트 시스템"
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["strategy", "refine", "both"],
        default="strategy",
        help="실행 모드: strategy (파싱 전략 선택), refine (문서 정제), both (둘 다)"
    )
    
    parser.add_argument(
        "--input",
        type=str,
        help="입력 PDF 파일 경로"
    )
    
    parser.add_argument(
        "--input-dir",
        type=str,
        help="입력 PDF 디렉토리 경로"
    )
    
    parser.add_argument(
        "--stage",
        type=str,
        choices=["extraction", "validation", "judge", "all"],
        default="all",
        help="실행할 단계 (strategy 모드에서만 사용, 기본값: all)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="디버그 모드"
    )
    
    args = parser.parse_args()
    
    # 디버그 모드 설정
    if args.debug:
        config.DEBUG_MODE = True
    
    # 디렉토리 생성
    ensure_directories()
    
    # 입력 파일 가져오기
    if args.input:
        input_files = [Path(args.input)]
    elif args.input_dir:
        input_files = get_input_files(args.input_dir)
    else:
        # 기본 입력 디렉토리
        input_files = get_input_files()
    
    if not input_files:
        print("❌ 처리할 파일이 없습니다.")
        print(f"입력 디렉토리: {config.INPUT_DIR}")
        print(f"지원 형식: {config.SUPPORTED_FORMATS}")
        return
    
    print(f"\n{'='*80}")
    print(f"Doc-to-Text Multi-Agent System")
    print(f"{'='*80}")
    print(f"[INFO] Mode: {args.mode}")
    print(f"[INFO] Input Files: {len(input_files)}")
    if args.mode == "strategy":
        print(f"[INFO] Stage: {args.stage}")
    print(f"{'='*80}\n")
    
    # 모드에 따라 처리
    results = []
    
    if args.mode == "strategy":
        results = run_strategy_mode(input_files, args)
    elif args.mode == "refine":
        results = run_refine_mode(input_files, args)
    elif args.mode == "both":
        print("[INFO] Running both modes sequentially...\n")
        strategy_results = run_strategy_mode(input_files, args)
        refine_results = run_refine_mode(input_files, args)
        results = strategy_results + refine_results
    
    # 전체 결과 요약
    print(f"\n{'='*80}")
    print(f"[SUMMARY] Processing Results")
    print(f"{'='*80}")
    
    completed = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] != "completed")
    
    print(f"[OK] Success: {completed}")
    print(f"[FAIL] Failed: {failed}")
    print(f"[TOTAL] Total: {len(results)}")
    
    print(f"\n[OUTPUT] Output locations:")
    print(f"   - Reports: {config.REPORTS_DIR}")
    print(f"   - Tables: {config.TABLES_DIR}")
    print(f"   - Logs: {config.LOG_FILE}")
    
    print(f"\n{'='*80}")
    print(f"[DONE] All processing completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN] User interrupted\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Exception occurred: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

