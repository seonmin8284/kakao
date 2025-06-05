from sentence_transformers import SentenceTransformer, util
from typing import Dict, List, Any, Tuple
import asyncio

# 글로벌 변수로 결과 저장
ANALYSIS_RESULTS: Dict[str, str] = {}

# 모델 로딩
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

SIMILARITY_THRESHOLD = 0.75

# 프로젝트 데이터는 main.py에서 가져올 예정
PROJECT_TO_OUTPUTS: Dict[str, List[str]] = {}
SERVICE_CATEGORIES: Dict[str, Dict[str, Any]] = {}

async def find_similar_project(query: str) -> Tuple[str, float]:
    query_embedding = model.encode(query)
    max_similarity = 0
    best_match = None
    
    for project, features in PROJECT_TO_OUTPUTS.items():
        text = f"{project} - {', '.join(features)}"
        similarity = util.pytorch_cos_sim(query_embedding, model.encode(text)).item()
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = project
    
    return best_match, max_similarity

def extract_outputs_from_text(text: str) -> List[str]:
    matched = []
    all_outputs = set(sum(PROJECT_TO_OUTPUTS.values(), []))
    for output in all_outputs:
        if output.lower().replace("_", "") in text.lower().replace(" ", ""):
            matched.append(output)
    return matched

async def process_utterance_async(user_id: str, utterance: str):
    """비동기로 사용자 입력을 처리하고 결과를 저장하는 함수"""
    try:
        # 서비스 카테고리 우선 매칭
        for category in SERVICE_CATEGORIES.keys():
            if category.replace("_", " ").lower() in utterance.lower():
                services = SERVICE_CATEGORIES[category]
                total_cost = sum(s["cost"] for s in services.values() if isinstance(s, dict) and "cost" in s)
                response_text = f"[{category.replace('_', ' ')} 서비스 상세 견적]\n\n"
                
                # 각 단계별 상세 정보
                for name, info in services.items():
                    if isinstance(info, dict) and "features" in info:
                        response_text += f"\n▶ {name.replace('_', ' ')}\n"
                        response_text += f"- 비용: {info['cost']:,}원\n"
                        response_text += "- 주요 기능:\n"
                        for f in info["features"]:
                            response_text += f"  · {f}\n"
                        if "outputs" in info:
                            response_text += "- 산출물:\n"
                            for o in info["outputs"]:
                                response_text += f"  · {o}\n"
                
                response_text += f"\n💰 총 견적: {total_cost:,}원"
                ANALYSIS_RESULTS[user_id] = response_text
                return

        # 키워드 기반 매칭
        matched_outputs = extract_outputs_from_text(utterance)
        if matched_outputs:
            matched_projects = [
                proj for proj, outs in PROJECT_TO_OUTPUTS.items()
                if all(output in outs for output in matched_outputs)
            ]
            if matched_projects:
                response_text = "🎯 요청하신 기능을 포함하는 프로젝트 목록입니다:\n\n"
                for proj in matched_projects[:3]:
                    response_text += f"📌 {proj}\n"
                    response_text += "주요 기능:\n"
                    for output in PROJECT_TO_OUTPUTS[proj]:
                        response_text += f"- {output}\n"
                    response_text += "\n"
            else:
                response_text = f"❌ 요청하신 기능({', '.join(matched_outputs)})을 포함하는 프로젝트를 찾지 못했습니다."
        else:
            # BERT 유사도 기반 매칭
            similar_project, similarity = await find_similar_project(utterance)
            if similarity >= SIMILARITY_THRESHOLD:
                features = PROJECT_TO_OUTPUTS[similar_project]
                response_text = f"💡 유사한 프로젝트를 찾았습니다 (유사도: {similarity:.2%}):\n\n"
                response_text += f"프로젝트: {similar_project}\n\n기능 목록:\n"
                for f in features:
                    response_text += f"✓ {f}\n"
            else:
                response_text = "🔍 다음 중 어떤 종류의 서비스를 찾으시나요?\n\n"
                for cat in SERVICE_CATEGORIES:
                    response_text += f"• {cat.replace('_', ' ')}\n"

        ANALYSIS_RESULTS[user_id] = response_text

    except Exception as e:
        ANALYSIS_RESULTS[user_id] = f"분석 중 오류가 발생했습니다: {str(e)}"

def set_project_data(project_data: Dict[str, List[str]], service_categories: Dict[str, Dict[str, Any]]):
    """프로젝트 데이터 설정 함수"""
    global PROJECT_TO_OUTPUTS, SERVICE_CATEGORIES
    PROJECT_TO_OUTPUTS = project_data
    SERVICE_CATEGORIES = service_categories 