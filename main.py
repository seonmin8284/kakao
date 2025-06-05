from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai  # GPT 호출 예시
from typing import Optional, Dict, Any

app = FastAPI()

class UserProperties(BaseModel):
    properties: Dict[str, Any] = {}

class User(BaseModel):
    id: str
    type: str
    properties: Dict[str, Any] = {}

class BlockInfo(BaseModel):
    id: str
    name: str

class UserRequest(BaseModel):
    timezone: str
    params: Dict[str, Any]
    block: BlockInfo
    utterance: str
    lang: Optional[str]
    user: User

class BotInfo(BaseModel):
    id: str
    name: str

class ActionParams(BaseModel):
    name: str
    clientExtra: Optional[str]
    params: Dict[str, Any]
    id: str
    detailParams: Dict[str, Any]

class KakaoRequest(BaseModel):
    intent: BlockInfo
    userRequest: UserRequest
    bot: BotInfo
    action: ActionParams

@app.post("/kakao/webhook")
async def kakao_webhook(request: KakaoRequest):
    # 사용자 발화 추출
    utterance = request.userRequest.utterance
    user_id = request.userRequest.user.id

    # 🔹 GPT 응답 받아오기 (예시용 dummy 응답)
    gpt_response = f"사용자({user_id})의 질문 '{utterance}'에 대한 답변입니다."

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
