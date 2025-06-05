from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import openai
from dotenv import load_dotenv
import os
from typing import Dict, Any
import uuid
from difflib import get_close_matches

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# 저장소 (실제 운영에서는 DB나 Redis 사용)
GPT_RESPONSES: Dict[str, str] = {}
USER_INPUTS: Dict[str, str] = {}
USER_SLOT_STATE: Dict[str, Dict[str, str]] = {}

# 산출물 관련 키워드
SANCHUL_ENTRIES = [
    "웹", "챗봇", "플랫폼", "ETL", "시스템", "앱", "사이트", "MVP", "UI", "대시보드",
    "API", "관리자 페이지", "리포트", "보고서", "자동화"
]

SANCHUL_SYNONYMS = [kw.lower() for kw in SANCHUL_ENTRIES]  # 소문자 비교용 리스트

# 주제 관련 키워드
JUJAE_ENTRIES = [
    "에너지", "전기", "교육", "심리", "사주", "건강", "병원", "진료", "의료", "정신건강",
    "강의", "학습", "수강", "튜터링", "금융", "송금", "자산", "투자", "보험", "쇼핑몰",
    "마켓", "결제", "리뷰", "추천", "음성인식", "이미지 생성", "챗GPT", "메신저",
    "채팅", "협업", "일정", "CRM", "ERP", "워크플로우", "프로젝트 관리", "계약서",
    "보고서", "PDF 요약", "예약", "매칭", "미용실", "상담", "자가 진단", "습관 관리",
    "행정", "민원", "정책", "배송", "택시", "물류", "탄소배출"
]

JUJAE_SYNONYMS = [kw.lower() for kw in JUJAE_ENTRIES]  # 소문자 비교용 리스트

def match_similar_slot_lightweight(text: str, slot_type: str) -> str:
    """문자열 유사도 기반으로 가장 유사한 주제 또는 산출물을 반환"""
    candidates = SANCHUL_ENTRIES if slot_type == "산출물" else JUJAE_ENTRIES
    matches = get_close_matches(text, candidates, n=1, cutoff=0.6)
    return matches[0] if matches else ""

def is_likely_output(text: str) -> bool:
    """산출물 슬롯에 들어갈 가능성이 높은지 판단"""
    lower_text = text.lower().strip()
    return any(entry in lower_text for entry in SANCHUL_SYNONYMS)

def is_likely_topic(text: str) -> bool:
    """주제 슬롯에 들어갈 가능성이 높은지 판단"""
    lower_text = text.lower().strip()
    return any(entry in lower_text for entry in JUJAE_SYNONYMS)

def is_valid_slot_answer(text: str) -> bool:
    """사용자 입력의 유효성을 검사합니다."""
    text = text.strip()
    if len(text) < 3:
        return False
    lower = text.lower()
    invalid_keywords = ["없", "모르", "모름", "몰라", "글쎄", "무", "잘 몰라", "기억 안", "생각 안"]
    return not any(kw in lower for kw in invalid_keywords)

def build_prompt(user_input: str, service_categories: Dict[str, Any]) -> str:
    """사용자 입력과 서비스 카테고리를 기반으로 GPT 프롬프트를 생성합니다."""
    prompt = f"사용자의 요청:\n\"{user_input}\"\n\n"
    prompt += "우리 회사는 다음과 같은 서비스 카테고리를 제공합니다:\n"

    for category, steps in service_categories.items():
        prompt += f"\n📂 {category.replace('_', ' ')}\n"
        for step, content in steps.items():
            if isinstance(content, dict) and "features" in content:
                cost = content.get("cost", 0)
                features = " / ".join(content["features"])
                prompt += f"  - {step.replace('_', ' ')}: {features} (비용: {cost:,}원)\n"
            elif isinstance(content, dict):
                for substep, subcontent in content.items():
                    if "features" in subcontent:
                        cost = subcontent.get("cost", 0)
                        features = " / ".join(subcontent["features"])
                        prompt += f"  - {step.replace('_', ' ')} > {substep}: {features} (비용: {cost:,}원)\n"

    prompt += "\n다음 형식으로 답변해 주세요:\n"
    prompt += "1. 추천 서비스: 사용자의 요구사항에 가장 적합한 카테고리\n"
    prompt += "2. 필요한 단계: 각 단계별 주요 기능과 비용\n"
    prompt += "3. 예상 기간: 전체 프로젝트 소요 기간\n"
    prompt += "4. 총 견적: 모든 단계의 비용 합계\n"
    prompt += "5. 추가 고려사항: 선택적으로 추가할 수 있는 기능이나 대안\n"
    
    return prompt

def call_gpt_for_estimate(user_input: str) -> str:
    """GPT API를 호출하여 견적 응답을 생성합니다."""
    try:
        prompt = build_prompt(user_input, SERVICE_CATEGORIES)
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 또는 "gpt-3.5-turbo"
            messages=[
                {
                    "role": "system", 
                    "content": "당신은 IT 프로젝트 견적 전문가입니다. 친절하고 전문적으로 상담해주세요. 이모지를 적절히 활용하여 답변하되, 형식은 반드시 지정된 대로 작성해주세요."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=700
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ 죄송합니다. 견적 산출 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.\n\n오류 내용: {str(e)}"

# 비동기 GPT 요청 처리
async def process_gpt(user_id: str, user_input: str):
    USER_INPUTS[user_id] = user_input
    GPT_RESPONSES[user_id] = "⏳ 요청을 처리 중입니다. 잠시만 기다려주세요..."
    GPT_RESPONSES[user_id] = call_gpt_for_estimate(user_input)

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    """카카오톡 웹훅 엔드포인트"""
    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", str(uuid.uuid4()))
        utterance = body.get("userRequest", {}).get("utterance", "")
        
        # 견적 결과 확인 요청 처리
        if utterance.startswith("견적 결과 확인:"):
            result_user_id = utterance.split("견적 결과 확인:")[-1].strip()
            return await get_result(result_user_id)
            
        # 새로운 견적 문의 시 상태 초기화
        if utterance == "새로운 견적 문의":
            USER_SLOT_STATE.pop(user_id, None)
            USER_INPUTS.pop(user_id, None)
            GPT_RESPONSES.pop(user_id, None)
        
        # 슬롯 필링 중인지 여부 확인
        in_slot_filling = user_id in USER_SLOT_STATE and any(
            USER_SLOT_STATE[user_id].get(slot, "") == "" for slot in ["주제", "산출물", "기간"]
        )
        
        # 처리 가능 여부 확인 → 슬롯 필링 중이면 검사 건너뜀
        if not in_slot_filling and not any(keyword in utterance for keyword in ["포트폴리오", "가격", "견적", "비용", "프로젝트", "개발", "제작"]):
            return JSONResponse(content={
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": "죄송합니다. 저는 포트폴리오 확인과 견적 상담만 도와드릴 수 있어요. 😅\n\n다음과 같은 내용을 문의해주세요:\n- 프로젝트 견적 문의\n- 포트폴리오 확인\n- 개발 비용 상담"
                        }
                    }],
                    "quickReplies": [{
                        "messageText": "새로운 견적 문의",
                        "action": "message",
                        "label": "견적 문의하기"
                    }]
                }
            })
    
        # 파라미터 추출 (상세 파라미터 우선, 없으면 일반 파라미터 사용)
        params = body.get("action", {}).get("params", {})
        detail_params = body.get("action", {}).get("detailParams", {})
        
        print("[DEBUG] params:", params)
        print("[DEBUG] detail_params:", detail_params)
        
        # 기존 상태 없으면 초기화
        if user_id not in USER_SLOT_STATE:
            USER_SLOT_STATE[user_id] = {"주제": "", "산출물": "", "기간": "", "retry_count": 0}
            
        # 단어 기반 슬롯 추론 + 유사도 보완
        if USER_SLOT_STATE[user_id]["산출물"] == "":
            if is_likely_output(utterance):
                USER_SLOT_STATE[user_id]["산출물"] = utterance
            else:
                match = match_similar_slot_lightweight(utterance, "산출물")
                if match:
                    USER_SLOT_STATE[user_id]["산출물"] = match

        elif USER_SLOT_STATE[user_id]["주제"] == "":
            if is_likely_topic(utterance):
                USER_SLOT_STATE[user_id]["주제"] = utterance
            else:
                match = match_similar_slot_lightweight(utterance, "주제")
                if match:
                    USER_SLOT_STATE[user_id]["주제"] = match

        elif USER_SLOT_STATE[user_id]["기간"] == "" and any(keyword in utterance for keyword in ["일", "개월", "주", "달", "년"]):
            USER_SLOT_STATE[user_id]["기간"] = utterance
            
        # 파라미터 업데이트 (상세 파라미터 우선, 일반 파라미터, 발화 순)
        for slot in ["주제", "산출물", "기간"]:
            if slot in detail_params and detail_params[slot].get("origin"):
                USER_SLOT_STATE[user_id][slot] = detail_params[slot]["origin"]
            elif slot in params:
                USER_SLOT_STATE[user_id][slot] = params.get(slot) or params.get(f"${slot}", "")
            elif USER_SLOT_STATE[user_id][slot] == "":  # 아직도 비어있으면
                # 이전에 해당 슬롯을 요청했었다면, 현재 발화를 해당 슬롯의 값으로 사용
                last_requested_slot = USER_SLOT_STATE[user_id].get("last_requested_slot")
                if last_requested_slot == slot and is_valid_slot_answer(utterance):
                    USER_SLOT_STATE[user_id][slot] = utterance
                
        user_state = USER_SLOT_STATE[user_id]
        
        # 미입력된 슬롯 확인
        missing_slots = [k for k, v in user_state.items() if not v and k != "last_requested_slot" and k != "retry_count"]
        
        if missing_slots:
            USER_SLOT_STATE[user_id]["retry_count"] += 1
            
            # 3회 이상 실패 시 전체 초기화
            if USER_SLOT_STATE[user_id]["retry_count"] >= 3:
                USER_SLOT_STATE.pop(user_id, None)
                USER_INPUTS.pop(user_id, None)
                GPT_RESPONSES.pop(user_id, None)
                
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": "⚠️ 여러 번 정보를 정확히 받지 못했어요. 처음부터 다시 진행해 주세요!"
                            }
                        }],
                        "quickReplies": [{
                            "messageText": "새로운 견적 문의",
                            "action": "message",
                            "label": "처음부터 다시"
                        }]
                    }
                })
            
            # 첫 요청 또는 일부만 입력된 경우 → 남은 항목 묶어서 물어보기
            USER_SLOT_STATE[user_id]["last_requested_slot"] = missing_slots[0]
            
            # 질문 텍스트 생성
            slot_labels = {"주제": "프로젝트 주제", "산출물": "원하시는 산출물", "기간": "예상 개발 기간"}
            requested_fields = [slot_labels[slot] for slot in missing_slots]
            field_text = "와 ".join(requested_fields) if len(requested_fields) == 2 else ", ".join(requested_fields)
            
            # 이전 입력이 유효하지 않은 경우 안내 메시지 추가
            last_slot = USER_SLOT_STATE[user_id].get("last_requested_slot")
            invalid_input_msg = "\n\n❗ 죄송하지만 이해하기 어려운 답변이에요. 조금 더 구체적으로 말씀해 주세요." if last_slot and not is_valid_slot_answer(utterance) else ""
            
            return JSONResponse(content={
                "version": "2.0",
                "template": {
                    "outputs": [{
                        "simpleText": {
                            "text": f"📝 {field_text}을(를) 알려주세요!{invalid_input_msg}"
                        }
                    }]
                }
            })
           
        
        # GPT 요청 비동기 처리
        background_tasks.add_task(process_gpt, user_id)
        
        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"📝 모든 정보를 받았어요! 몇 초 후 결과를 확인해주세요.\n\n👉 확인: /result/{user_id}"
                    } 
                }],
                "quickReplies": [{
                    "messageText": f"견적 결과 확인:{user_id}",
                    "action": "message",
                    "label": "견적 결과 확인"
                }]
            }
        })
        
    except Exception as e:
        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"⚠️ 요청 처리 중 오류가 발생했습니다.\n잠시 후 다시 시도해주세요.\n\n오류 내용: {str(e)}"
                    }
                }]
            }
        })

@app.get("/result/{user_id}")
async def get_result(user_id: str):
    """결과 조회 엔드포인트"""
    response_text = GPT_RESPONSES.get(user_id, "❌ 존재하지 않는 요청 ID이거나 아직 처리 중입니다.")
    user_input = USER_INPUTS.get(user_id, "입력 정보가 없습니다.")
    
    # 결과 조회 후 상태 초기화 (선택사항)
    USER_SLOT_STATE.pop(user_id, None)
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"{response_text}\n\n🗂️ 입력 정보:\n{user_input}"
                }
            }],
            "quickReplies": [{
                "messageText": "새로운 견적 문의",
                "action": "message",
                "label": "새로운 견적 문의"
            }]
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}
