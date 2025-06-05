from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 기능 키워드와 엑셀 기준 금액 매핑
FEATURE_COSTS = {
    "기획": 100_0000,
    "설계": 100_0000,
    "프론트": 200_0000,
    "프론트엔드": 200_0000,
    "UI": 200_0000,
    "백엔드": 300_0000,
    "서버": 300_0000,
    "관리자": 200_0000,
    "운영자": 200_0000,
    "모니터링": 200_0000,
    "배포": 100_0000,
    "유지보수": 100_0000
}

def estimate_cost_from_text(text: str):
    total = 0
    matched = []

    for keyword, cost in FEATURE_COSTS.items():
        if keyword in text:
            total += cost
            matched.append((keyword, cost))

    return total, matched

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    body = await request.json()
    utterance = body.get("userRequest", {}).get("utterance", "")
    user_id = body.get("userRequest", {}).get("user", {}).get("id", "unknown")

    # 견적 계산
    total, matched = estimate_cost_from_text(utterance)

    if not matched:
        message = "죄송해요! 요청하신 항목을 정확히 인식하지 못했어요. 다시 한번 상세히 입력해 주세요."
    else:
        details = "\n".join([f"- {k}: {v:,}원" for k, v in matched])
        message = (
            f"🧾 사용자({user_id})님의 요청 기준 예상 견적입니다.\n\n"
            f"{details}\n\n"
            f"💰 총 예상 견적: {total:,}원\n\n"
            "상세한 상담을 원하시면 연락처를 남겨주세요 😊"
        )

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": message
                    }
                }
            ]
        }
    }

    return JSONResponse(content=response)
