from rotulai.agents.decisor import DecisorAgent
from rotulai.agents.revisor import ReviewerAgent
from rotulai.db.postgres_client import save_analysis_result
from rotulai.schemas import AnalysisResult, LabelInput


def analyze_label(label: LabelInput, persist: bool = True) -> AnalysisResult:
    decisor = DecisorAgent()
    revisor = ReviewerAgent()

    findings = decisor.route(label)
    verdict = revisor.review(label, findings)

    result = AnalysisResult(label=label, findings=findings, verdict=verdict)

    if persist:
        save_analysis_result(result)

    return result
