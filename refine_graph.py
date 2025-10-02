"""
문서 정제(Refine) 시스템 LangGraph 워크플로우
"""

from langgraph.graph import StateGraph, END
from state import RefineDocumentState

# 에이전트 임포트
from agents.basic_extraction_agent import BasicExtractionAgent
from agents.refine_validation_agent import RefineValidationAgent
from agents.refine_agent import RefineAgent
from agents.refine_report_agent import RefineReportAgent


def create_refine_graph():
    """문서 정제 시스템 그래프 생성"""
    
    # 그래프 생성
    workflow = StateGraph(RefineDocumentState)
    
    # 에이전트 인스턴스 생성
    extraction_agent = BasicExtractionAgent()
    refine_validation_agent = RefineValidationAgent()
    refine_agent = RefineAgent()
    refine_report_agent = RefineReportAgent()
    
    # 노드 추가
    workflow.add_node("extract", extraction_agent.run)
    workflow.add_node("refine_validate", refine_validation_agent.run)
    workflow.add_node("refine", refine_agent.run)
    workflow.add_node("report", refine_report_agent.run)
    
    # 엣지 추가
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "refine_validate")
    workflow.add_edge("refine_validate", "refine")
    workflow.add_edge("refine", "report")
    workflow.add_edge("report", END)
    
    # 그래프 컴파일
    app = workflow.compile()
    
    return app


def visualize_refine_graph():
    """그래프 시각화 (선택적)"""
    try:
        from IPython.display import Image, display
        
        app = create_refine_graph()
        
        # Mermaid 다이어그램 생성
        print("Refine System Graph:")
        print(app.get_graph().draw_mermaid())
        
        # PNG 이미지 생성 (graphviz 설치 필요)
        try:
            img = app.get_graph().draw_mermaid_png()
            display(Image(img))
        except Exception as e:
            print(f"PNG generation failed: {e}")
            print("Install graphviz to generate PNG: pip install graphviz")
    
    except ImportError:
        print("IPython not available. Cannot visualize graph.")


if __name__ == "__main__":
    # 그래프 생성 테스트
    print("Creating Refine System Graph...")
    app = create_refine_graph()
    print("✓ Graph created successfully!")
    
    # 그래프 구조 출력
    print("\nGraph Structure:")
    print(app.get_graph().draw_mermaid())
    
    # 시각화 시도
    visualize_refine_graph()

