from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 통합된 기능명과 견적
FEATURE_COSTS = {
    "기획": 1000000,
    "프론트엔드": 2000000,
    "백엔드": 3000000,
    "운영자": 2000000,
    "배포": 1000000,
    "요구사항": 500000,
    "데이터 수집": 500000,
    "정제": 500000,
    "적재": 500000,
    "파이프라인": 700000,
    "모니터링": 500000,
    "시각화": 1000000,
    "리포트": 1000000,
    "KPI": 400000,
    "Power BI": 800000,
    "Tableau": 800000,
}

def estimate_cost_from_text(text: str):
    total = 0
    matched = []
    for keyword, cost in FEATURE_COSTS.items():
        if keyword.lower() in text.lower():
            total += cost
            matched.append((keyword, cost))
    return total, matched

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    body = await request.json()
    utterance = body.get("userRequest", {}).get("utterance", "")
    user_id = body.get("userRequest", {}).get("user", {}).get("id", "unknown")

    total, matched = estimate_cost_from_text(utterance)

    if not matched:
        message = "죄송해요! 어떤 기능을 원하시는지 인식하지 못했어요. 예: 프론트엔드, 백엔드, 데이터 수집 등으로 다시 입력해 주세요."
    else:
        details = "\n".join([f"- {k}: {v:,}원" for k, v in matched])
        message = (
            f"🧾 사용자({user_id})님의 요청 기준 예상 견적입니다.\n\n"
            f"{details}\n\n"
            f"💰 총 예상 견적: {total:,}원\n\n"
            "정확한 상담을 원하시면 연락처를 남겨주세요 😊"
        )

    return JSONResponse(content={
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": message}}]
        }
    })
