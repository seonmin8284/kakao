from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sentence_transformers import SentenceTransformer, util

app = FastAPI()
model = SentenceTransformer("paraphrase-MiniLM-L6-v2")

# 💾 간단한 캐시 메모리 저장소
memory_cache = {}

# 가격 테이블
FEATURE_COSTS = {
    "기획": 1000000, "프론트엔드": 2000000, "백엔드": 3000000,
    "운영자": 2000000, "배포": 1000000, "요구사항": 500000,
    "데이터 수집": 500000, "정제": 500000, "적재": 500000,
    "파이프라인": 700000, "모니터링": 500000, "시각화": 1000000,
    "리포트": 1000000, "KPI": 400000, "Power BI": 800000, "Tableau": 800000,
}

# 주제 → 산출물
PROJECT_TO_OUTPUTS = {
    "고객센터 챗봇": ["AI 챗봇", "관리자 페이지"],
    "뉴스 요약 시스템": ["리포트 자동화", "대시보드"],
    "운세 서비스": ["AI 챗봇", "사용자 프론트", "데이터 수집", "백엔드"],
    "병원 예약 시스템": ["웹사이트", "백엔드", "관리자 페이지"],
}

# 산출물 → 기능
OUTPUT_TO_FEATURES = {
    "AI 챗봇": ["기획", "백엔드", "프론트엔드", "배포"],
    "웹사이트": ["기획", "프론트엔드", "백엔드", "배포"],
    "관리자 페이지": ["프론트엔드", "운영자"],
    "대시보드": ["시각화", "KPI", "Tableau"],
    "리포트 자동화": ["리포트", "데이터 수집", "정제"],
    "사용자 프론트": ["프론트엔드"],
    "데이터 수집": ["데이터 수집", "정제", "적재"],
    "백엔드": ["백엔드"],
}

project_keys = list(PROJECT_TO_OUTPUTS.keys())
project_embeddings = model.encode(project_keys, convert_to_tensor=True)

def get_outputs_from_project(utterance: str):
    query_emb = model.encode(utterance, convert_to_tensor=True)
    cos_scores = util.pytorch_cos_sim(query_emb, project_embeddings)
    best_match_idx = int(cos_scores.argmax())
    project = project_keys[best_match_idx]
    return PROJECT_TO_OUTPUTS[project], project

def estimate_from_outputs(outputs):
    total = 0
    matched = []
    for out in outputs:
        features = OUTPUT_TO_FEATURES.get(out, [])
        for feat in features:
            cost = FEATURE_COSTS.get(feat)
            if cost:
                matched.append((feat, cost))
                total += cost
    return total, matched

def build_kakao_response(msg: str):
    return JSONResponse(content={
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": msg}}]
        }
    })

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    body = await request.json()
    utterance = body.get("userRequest", {}).get("utterance", "")
    user_id = body.get("userRequest", {}).get("user", {}).get("id", "unknown")

    # ⛓️ 캐시 초기화
    if user_id not in memory_cache:
        memory_cache[user_id] = {}

    user_data = memory_cache[user_id]

    # 1. 슬롯 채우기 시도
    if "project" not in user_data:
        try:
            outputs, project = get_outputs_from_project(utterance)
            user_data["project"] = project
            user_data["outputs"] = outputs
        except:
            pass

    elif "period" not in user_data:
        if any(word in utterance for word in ["일", "주", "개월", "달"]):
            user_data["period"] = utterance

    # 2. 부족한 슬롯에 따라 되묻기
    if "project" not in user_data:
        return build_kakao_response("어떤 프로젝트를 계획 중이신가요? 예: 고객센터 챗봇, 뉴스 요약 시스템 등")

    if "period" not in user_data:
        return build_kakao_response("예상 개발 기간은 어느 정도인가요? 예: 1개월, 2주 등")

    # 3. 모든 슬롯이 채워졌다면 견적 산정
    total, matched = estimate_from_outputs(user_data["outputs"])
    detail = "\n".join([f"- {k}: {v:,}원" for k, v in matched])
    msg = (
        f"🧾 사용자({user_id})님의 '{user_data['project']}' 프로젝트 예상 견적입니다.\n"
        f"📅 예상 기간: {user_data['period']}\n\n"
        f"{detail}\n\n"
        f"💰 총 견적: {total:,}원입니다.\n정확한 상담을 원하시면 연락처를 남겨주세요 😊"
    )

    # 💬 응답 후 캐시 초기화
    del memory_cache[user_id]
    return build_kakao_response(msg)
