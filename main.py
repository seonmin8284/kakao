from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai  # GPT 호출 예시

app = FastAPI()

# 🔸 카카오가 보내는 데이터 형식
class KakaoRequest(BaseModel):
    userRequest: dict

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request):
    body = await request.json()
    utterance = body["userRequest"]["utterance"]

    # 🔹 GPT 응답 받아오기 (예시용 dummy 응답)
    gpt_response = f"'{utterance}'에 대한 답변입니다."

    # 🔸 카카오 응답 형식
    response_json = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": gpt_response
                    }
                }
            ]
        }
    }
    return JSONResponse(content=response_json)
