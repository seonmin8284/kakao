from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 🔹 키워드 기반 견적 산정 함수
def estimate_cost_and_duration(text: str):
    base_cost = 0
    urgent = False

    if "예약" in text:
        base_cost += 300000
    if "GPT" in text or "AI" in text:
        base_cost += 250000
    if "관리자" in text:
        base_cost += 350000
    if "카카오" in text or "톡" in text:
        base_cost += 200000
    if "3일" in text or "5일" in text or "급하게" in text:
        urgent = True

    total_cost = int(base_cost * 1.2) if urgent else base_cost
    days = 5 if urgent else 10

    return total_cost, days

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    body = await request.json()
    utterance = body.get("userRequest", {}).get("utterance", "")
    user_id = body.get("userRequest", {}).get("user", {}).get("id", "unknown")

    # 🔸 견적 계산
    cost, duration = estimate_cost_and_duration(utterance)

    response_text = (
        f"사용자({user_id})의 요청을 확인했습니다.\n\n"
        f"📌 예상 견적: 약 {cost:,}원\n"
        f"⏱️ 예상 소요 기간: 약 {duration}일\n\n"
        f"정확한 상담을 원하시면 연락처를 남겨주세요 😊"
    )

    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": response_text
                    }
                }
            ]
        }
    }

    return JSONResponse(content=response)
