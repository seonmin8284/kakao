from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import openai
from dotenv import load_dotenv
import os
from typing import Dict, Any, List
import uuid
from difflib import get_close_matches
import uvicorn
import re

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# 저장소 (실제 운영에서는 DB나 Redis 사용)
GPT_RESPONSES: Dict[str, str] = {}
USER_INPUTS: Dict[str, str] = {}
USER_SLOT_STATE: Dict[str, Dict[str, str]] = {}
SHRUNK_RESPONSES: Dict[str, str] = {}

# 서비스 카테고리 데이터
SERVICE_CATEGORIES = {
    "시각화_대시보드": {
        "기획_요구사항_정의": {
            "features": ["분석 목적 및 주요 KPI 정의", "사용자 요구 정리", "데이터 시각화 방향 수립"],
            "cost": 400000
        },
        "데이터_수집_전처리": {
            "features": ["내부/외부 데이터 수집", "데이터 정제 및 가공", "Power BI/Tableau 적재"],
            "cost": 800000
        },
        "대시보드_프로토타입_제작": {
            "features": ["핵심 KPI 위주의 시각화 모듈 개발", "피드백 반영 구조 구성"],
            "cost": 1000000
        },
        "사용자_맞춤형_기능_추가": {
            "features": ["필터", "Drill-Down", "권한별 뷰", "주간/월간 리포트 자동화"],
            "cost": 1000000
        },
        "자동화_운영_연동": {
            "features": ["데이터 자동 업데이트", "배치 스케줄링(Airflow)", "알림/리포트 자동화"],
            "cost": 1000000
        }
    },
    "AI_챗봇": {
        "기획_조사": {
            "features": ["요구사항 분석", "유즈케이스 정의", "경쟁 분석", "AI 활용방안 설계"],
            "cost": 500000
        },
        "데이터_수집_전처리": {
            "features": ["크롤링", "정제", "레이블링", "토크나이징", "이미지/음성/텍스트 데이터셋 구성"],
            "cost": 500000
        },
        "AI_모델_개발": {
            "API고도화": {
                "features": ["음성/이미지/언어 생성 또는 인식 모델 개발", "프롬프트 엔지니어링"],
                "cost": 2000000
            },
            "파인튜닝": {
                "features": ["오픈소스 LLM (LLaMA, Mistral 등) Fine-tuning", "데이터 기반 학습 스크립트 구성"],
                "cost": 3000000
            }
        },
        "모델_평가_개선": {
            "features": ["정확도/정밀도/F1 Score", "실제 QA 시나리오 성능 평가", "실패 케이스 분석"],
            "cost": 1500000
        },
        "플랫폼_MVP_구현": {
            "features": ["백엔드 API", "챗봇 UI(웹/앱)", "인증/권한 시스템", "대화 흐름 구현"],
            "cost": 3000000
        },
        "운영_자동화_모니터링": {
            "features": ["모델 재학습 파이프라인", "로그 수집", "성능 모니터링 대시보드"],
            "cost": 1000000
        }
    },
    "데이터_엔지니어링": {
        "요구사항_정의_설계": {
            "features": ["수집 대상 정의", "스키마 설계", "파이프라인 구조 설계"],
            "cost": 500000
        },
        "데이터_수집_모듈_개발": {
            "features": ["Public API", "웹 크롤링", "DB 추출 등 데이터 수집 자동화 구현"],
            "cost": 500000
        },
        "데이터_처리_정제": {
            "features": ["결측치 처리", "중복 제거", "포맷 변환", "컬럼 정리 등 전처리 로직 개발"],
            "cost": 500000
        },
        "저장_적재_자동화": {
            "features": ["정제 데이터의 저장 (SQL, Data Lake, Warehouse 등) 및 버전 관리"],
            "cost": 500000
        },
        "파이프라인_자동화": {
            "features": ["Apache Airflow", "Python 스케줄러", "CI/CD 등 활용한 자동화 구성"],
            "cost": 700000
        },
        "모니터링_오류_알림": {
            "features": ["실패 로그 수집", "작업 성공 여부 시각화", "슬랙/메일 알림 연동"],
            "cost": 500000
        }
    },
    "웹_플랫폼": {
        "기획_요구사항_정의": {
            "features": ["고객 요구사항 분석", "핵심 기능 도출", "경쟁 벤치마킹", "플랫폼 구조 설계", "기술 스택 선정"],
            "cost": 1000000
        },
        "프론트엔드_개발": {
            "features": ["사용자 UI/UX 구현 (React/Vue 기반)", "반응형 디자인 적용"],
            "cost": 2000000
        },
        "백엔드_개발": {
            "features": ["API 서버", "인증 시스템", "DB 연동", "알림 시스템 등 구현"],
            "cost": 3000000
        },
        "운영자_관리_시스템": {
            "features": ["관리자 페이지", "권한 관리", "사용자/데이터 모니터링 기능"],
            "cost": 2000000
        },
        "배포_통합_유지보수": {
            "features": ["도메인 연동", "서버 배포", "초기 오류 대응 및 유지보수 가이드 제공"],
            "cost": 1000000
        }
    },
    "디지털_이미지_툴": {
        "기획": {
            "features": ["사용자 기능 정의", "툴 아키텍처 설계"],
            "cost": 800000
        },
        "툴_개발": {
            "features": ["이미지 업로드/편집/저장", "필터 적용 기능", "내보내기 기능"],
            "cost": 2000000
        }
    }
}

# 산출물 관련 키워드
SANCHUL_ENTRIES = [
    "웹", "웹사이트", "챗봇", "ETL", "시스템", "앱", "사이트", "MVP", "UI", "대시보드",
    "API", "관리자 페이지", "리포트", "보고서", "자동화", "안드로이드", "IOS", "웹앱", "프로그램","윈도우", "맥"
]

SANCHUL_SYNONYMS = [kw.lower() for kw in SANCHUL_ENTRIES]  # 소문자 비교용 리스트

# 주제 관련 키워드
JUJAE_ENTRIES = [
    "에너지", "전기", "교육", "심리", "사주", "건강", "병원", "진료", "의료", "정신건강",
    "강의", "학습", "수강", "튜터링", "금융", "송금", "자산", "투자", "보험", "쇼핑몰",
    "마켓", "결제", "리뷰", "추천", "음성인식", "이미지 생성", "챗GPT", "메신저",
    "채팅", "협업", "일정", "CRM", "ERP", "워크플로우", "프로젝트 관리", "계약서",
    "보고서", "PDF 요약", "예약", "매칭", "미용실", "상담", "자가 진단", "습관 관리",
    "행정", "민원", "정책", "배송", "택시", "물류", "탄소배출",
    # 교육/발달 관련 키워드 추가
    "지능", "경계선 지능", "특수교육", "발달", "인지", "읽기", "학습장애", "언어", "아동", "프로그램"
]

JUJAE_SYNONYMS = [kw.lower() for kw in JUJAE_ENTRIES]  # 소문자 비교용 리스트

def match_similar_slot_lightweight(text: str, slot_type: str) -> str:
    """문자열 유사도 기반으로 가장 유사한 주제 또는 산출물을 반환"""
    candidates = SANCHUL_ENTRIES if slot_type == "산출물" else JUJAE_ENTRIES
    matches = get_close_matches(text, candidates, n=1, cutoff=0.5)  # cutoff 값을 0.5로 낮춤
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

def normalize_period(text: str) -> str:
    """기간 입력을 표준 형식으로 정규화"""
    if "개월" in text or "달" in text:
        number = ''.join(filter(str.isdigit, text))
        return f"{number}개월"
    elif "주" in text:
        number = ''.join(filter(str.isdigit, text))
        return f"{number}주"
    return text.strip()

def normalize_budget(text: str) -> str:
    """사용자가 입력한 금액 문자열을 숫자로 정규화"""
    # 금액 단위가 명시되지 않으면 무시
    if not any(unit in text for unit in ["원", "만원", "천원", "억", "조"]):
        return ""
    
    # 단위별 승수 정의
    multipliers = {
        "조": 1000000000000,
        "억": 100000000,
        "만원": 10000,
        "천원": 1000,
        "원": 1
    }
    
    text = text.replace(",", "")
    
    # 숫자와 단위를 모두 포함하는 패턴 매칭
    for unit, multiplier in multipliers.items():
        if unit in text:
            match = re.search(r"(\d+)\s*" + unit, text)
            if match:
                amount = int(match.group(1)) * multiplier
                return f"{amount:,}원"
    
    # 단순 숫자 추출 (단위가 '원'인 경우)
    if "원" in text:
        match = re.search(r"(\d+)", text)
        if match:
            amount = int(match.group(1))
            return f"{amount:,}원"
            
    return ""

def is_valid_period(text: str) -> bool:
    """기간 입력의 유효성을 검사하고 정규화를 시도합니다."""
    text = text.strip()
    if not is_valid_slot_answer(text):  # 기본 유효성 검사
        return False
    
    # 정규화 시도
    normalized = normalize_period(text)
    return any(unit in normalized for unit in ["개월", "주"])

def infer_primary_category(topic: str, output: str) -> str:
    """사용자 입력을 기반으로 가장 적합한 서비스 카테고리를 추론합니다."""
    output = output.lower()
    topic = topic.lower()
    
    # 웹 플랫폼 관련 키워드
    if any(kw in output for kw in ["앱", "웹", "사이트", "플랫폼", "관리자", "ui", "페이지"]):
        return "웹_플랫폼"
    
    # AI 챗봇 관련 키워드
    elif any(kw in output for kw in ["챗봇", "ai", "대화", "질의응답"]) or \
         any(kw in topic for kw in ["대화", "상담", "응답", "질문"]):
        return "AI_챗봇"
    
    # 데이터/시각화 관련 키워드
    elif any(kw in output for kw in ["대시보드", "시각화", "분석", "리포트"]) or \
         any(kw in topic for kw in ["데이터", "분석", "통계", "현황"]):
        return "시각화_대시보드"
    
    # 기본값은 웹 플랫폼
    return "웹_플랫폼"

def infer_all_categories(topic: str, output: str) -> List[str]:
    """여러 산출물에 기반하여 적합한 서비스 카테고리 목록 추론"""
    topic = topic.lower()
    output = output.lower()
    categories = set()

    # 웹/앱 관련
    if any(kw in output for kw in ["앱", "웹", "사이트", "플랫폼"]):
        categories.add("웹_플랫폼")

    # 챗봇 관련
    if any(kw in output for kw in ["챗봇", "대화", "AI"]):
        categories.add("AI_챗봇")

    # 시각화/데이터 분석
    if any(kw in output for kw in ["분석", "대시보드", "리포트"]):
        categories.add("시각화_대시보드")

    # 이미지 툴 (향후 필요시 SERVICE_CATEGORIES에 정의 필요)
    if any(kw in output for kw in ["디자인", "이미지", "프로그램"]):
        categories.add("디지털_이미지_툴")

    # SNS 마케팅 운영 (향후 필요시 SERVICE_CATEGORIES에 정의 필요)
    if any(kw in output for kw in ["틱톡", "유튜브", "페이스북", "인스타"]):
        categories.add("SNS_운영")

    # 최소 1개 이상의 카테고리 보장
    if not categories:
        categories.add("웹_플랫폼")  # 기본값

    return list(categories)

def build_prompt_multicategory(user_input: str, service_categories: dict, categories: List[str], expected_budget: str = "", topic: str = "", period: str = "") -> str:
    # 구조화된 입력 정보 표시
    prompt = "🧾 사용자가 입력한 정보:\n"
    prompt += f"- 주제: {topic}\n"
    prompt += f"- 산출물: {user_input}\n"
    prompt += f"- 기간: {period}\n"
    prompt += f"- 예상 예산: {expected_budget}\n\n"
    
    prompt += f"💡 사용자가 요청한 주요 서비스 범주는 `{', '.join(categories)}`입니다.\n\n"
    
    prompt += "🧾 각 카테고리에 대해 빠짐없이 견적을 제시해 주세요. 일부 항목 누락 없이 전체 범위를 고려해 주세요.\n"
    prompt += "⚠️ 각 카테고리는 독립된 프로젝트 단위로 보고, 개별 견적을 제시해 주세요.\n\n"
    prompt += "우리 회사는 다음과 같은 서비스 카테고리를 제공합니다:\n"

    for category in categories:
        if category not in service_categories:
            continue
        prompt += f"\n📂 {category.replace('_', ' ')}\n"
        for step, content in service_categories[category].items():
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

    prompt += "\n다음 형식으로 각 카테고리에 대해 개별적으로 답변해 주세요:\n\n"
    
    # 예시 형식 추가
    prompt += """📂 [카테고리명]
- 필요한 단계: [금액]원
- 예상 기간: [기간]

이런 형식으로 각 카테고리별 견적을 제시한 후,

💰 총 합계: [전체 금액]원
"""

    return prompt

def call_gpt_full_estimate(user_input: str, topic: str, output: str, expected_budget: str, period: str) -> str:
    """전체 견적만 요청 (🔄 축소 제안 제외)"""
    prompt = build_prompt_multicategory(
        user_input, SERVICE_CATEGORIES,
        infer_all_categories(topic, output),
        expected_budget, topic, period
    )
    # 프롬프트에서 축소 제안 안내 삭제
    prompt = re.sub(r"\n*만약 총 합계.*?축소안도 함께 제시해 주세요\.", "", prompt, flags=re.DOTALL)

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "당신은 IT 견적 전문가입니다."},
                  {"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1200
    )
    return response.choices[0].message.content

def call_gpt_shrunk_only(full_prompt: str, user_budget: str = "") -> str:
    """축소 제안만 GPT에 요청 (사용자 예산이 너무 낮을 경우, 최소 구성 견적 제안)"""
    prompt = ""

    # 예산 파싱 (숫자만 추출)
    min_reasonable_budget = 300_000  # 최소 수용 가능한 견적
    user_budget_value = 0
    match = re.search(r"([\d,]+)", user_budget.replace(",", ""))
    if match:
        user_budget_value = int(match.group(1))

    # 예산이 너무 낮은 경우 GPT 안내 추가
    if user_budget_value < min_reasonable_budget:
        prompt += f"❗ 사용자의 입력 예산이 {user_budget}으로 너무 낮습니다. 현실적으로 가능한 최소한의 구성 견적을 안내해 주세요.\n"
        prompt += "예산이 부족한 상황에서도 필수적인 기능만으로 구성해 주시고, 그에 맞는 적절한 비용을 제시해 주세요.\n\n"
    else:
        prompt += f"❗️예산을 반드시 지켜주세요: 최대 {user_budget} 이하로 작성되어야 합니다.\n\n"

    prompt += "🛠 아래는 사용자가 요청한 서비스 범위입니다. 최소 기능 중심의 '🔄 축소 제안'만 작성해주세요.\n\n"
    prompt += full_prompt
    prompt += "\n\n🔄 축소 제안:\n[카테고리별 축소 견적 형식으로 작성해 주세요.]"

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system", 
            "content": "당신은 IT 견적 전문가입니다. 사용자의 예산이 너무 낮을 경우, 현실적으로 가능한 최소 구성을 제안하고, 그렇지 않은 경우 예산 이하로 견적을 작성해야 합니다."
        }, {
            "role": "user", 
            "content": prompt
        }],
        temperature=0.7,
        max_tokens=800
    )
    return response.choices[0].message.content.strip()

# process_gpt 함수 수정
async def process_gpt(user_id: str, user_input: str, topic: str = "", output: str = "", expected_budget: str = "", period: str = ""):
    USER_INPUTS[user_id] = user_input
    GPT_RESPONSES[user_id] = "⏳ 요청을 처리 중입니다. 잠시만 기다려주세요..."
    
    # 전체 견적만 먼저 생성
    full_response = call_gpt_full_estimate(user_input, topic, output, expected_budget, period)
    GPT_RESPONSES[user_id] = full_response

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    """카카오톡 웹훅 엔드포인트"""
    # 변수 초기화
    user_id = ""
    utterance = ""
    params = {}
    detail_params = {}

    try:
        body = await request.json()
        user_id = body.get("userRequest", {}).get("user", {}).get("id", str(uuid.uuid4()))
        utterance = body.get("userRequest", {}).get("utterance", "")
        
        # 파라미터 추출 (상세 파라미터 우선, 없으면 일반 파라미터 사용)
        params = body.get("action", {}).get("params", {})
        detail_params = body.get("action", {}).get("detailParams", {})
        
        # 견적 결과 확인 요청 처리
        if utterance.startswith("견적 결과 확인:"):
            result_user_id = utterance.split("견적 결과 확인:")[-1].strip()
            return await get_result(result_user_id)
            
        # 축소 견적 확인 요청 처리
        if utterance.startswith("축소 견적 확인:"):
            shrunk_user_id = utterance.split("축소 견적 확인:")[-1].strip()
            return await get_shrunk_result(shrunk_user_id)

        # 새로운 견적 문의 시 상태 초기화
        if utterance == "새로운 견적 문의":
            USER_SLOT_STATE.pop(user_id, None)
            USER_INPUTS.pop(user_id, None)
            GPT_RESPONSES.pop(user_id, None)
        
        # 슬롯 필링 중인지 여부 확인
        in_slot_filling = user_id in USER_SLOT_STATE and any(
            USER_SLOT_STATE[user_id].get(slot, "") == "" for slot in ["주제", "산출물", "기간", "예상_견적"]
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
    
        # 기존 상태 없으면 초기화
        if user_id not in USER_SLOT_STATE:
            USER_SLOT_STATE[user_id] = {"주제": "", "산출물": "", "기간": "", "예상_견적": "", "retry_count": 0}
            
        user_state = USER_SLOT_STATE[user_id]
        
        # 토큰화 및 전처리
        tokens = utterance.replace(",", " ").replace("을", "").replace("를", "").split()
        tokens = [t.strip().lower() for t in tokens]
        
        # 주제가 비어 있으면 토큰에서 매칭 시도
        if user_state["주제"] == "":
            for token in tokens:
                if is_likely_topic(token):
                    user_state["주제"] = token
                    break
            if user_state["주제"] == "":
                topic_match = match_similar_slot_lightweight(utterance, "주제")
                if topic_match:
                    user_state["주제"] = topic_match
                else:
                    return JSONResponse(content={
                        "version": "2.0",
                        "template": {
                            "outputs": [{
                                "simpleText": {
                                    "text": "📝 프로젝트 주제를 알려주세요! (예: 쇼핑몰, 교육 플랫폼 등)"
                                }
                            }]
                        }
                    })
        
        # 산출물이 비어 있으면 여러 토큰에서 추출
        if user_state["산출물"] == "":
            matched_outputs = [entry for entry in SANCHUL_SYNONYMS if entry in utterance.lower()]
            if matched_outputs:
                user_state["산출물"] = ", ".join(sorted(set(matched_outputs)))
            else:
                output_match = match_similar_slot_lightweight(utterance, "산출물")
                if output_match:
                    user_state["산출물"] = output_match
                else:
                    return JSONResponse(content={
                        "version": "2.0",
                        "template": {
                            "outputs": [{
                                "simpleText": {
                                    "text": "📦 어떤 산출물을 원하시나요? (예: 웹사이트, 앱, 관리자 페이지 등)"
                                }
                            }]
                        }
                    })
        
        # 기간 입력이 없으면 요청
        if user_state["기간"] == "":
            if is_valid_period(utterance):
                user_state["기간"] = normalize_period(utterance)
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": "⌛ 예상 개발 기간을 알려주세요! (예: 2개월, 3주 등)"
                            }
                        }]
                    }
                })

        # 예상 견적 슬롯 추가
        if "예상_견적" not in user_state:
            user_state["예상_견적"] = ""

        # 견적 결과 응답에 포함되었을 경우 추출해서 저장
        if user_state["예상_견적"] == "" and utterance.startswith("견적 결과 확인:"):
            gpt_result = GPT_RESPONSES.get(user_id, "")
            if "총 견적" in gpt_result:
                lines = gpt_result.splitlines()
                for line in lines:
                    if "총 견적" in line:
                        user_state["예상_견적"] = line.strip()
                        break

        # 견적이 비어 있으면 다시 물어보기
        if user_state["예상_견적"] == "":
            normalized = normalize_budget(utterance)
            if normalized:
                user_state["예상_견적"] = normalized
            else:
                return JSONResponse(content={
                    "version": "2.0",
                    "template": {
                        "outputs": [{
                            "simpleText": {
                                "text": "💰 대략 어느 정도의 예산을 생각하고 계신가요? (예: 100만원, 2000만원 등)"
                            }
                        }]
                    }
                })
        
        # 상세 파라미터가 있는 경우 우선 적용
        for slot in ["주제", "산출물", "기간", "예상_견적"]:
            if slot in detail_params and detail_params[slot].get("origin"):
                user_state[slot] = detail_params[slot]["origin"]
            elif slot in params:
                user_state[slot] = params.get(slot) or params.get(f"${slot}", "")
        
        # 모든 슬롯이 채워진 경우에만 GPT 요청 처리
        if user_state["주제"] != "" and user_state["산출물"] != "" and user_state["기간"] != "" and user_state["예상_견적"] != "":
            user_input_parts = [
                f"🖋 주제: {user_state['주제']}",
                f"🧾 산출물: {user_state['산출물']}",
                f"🕒 기간: {user_state['기간']}",
                f"💰 예산: {user_state['예상_견적']}"
            ]
            user_input = "\n".join(user_input_parts)
            
            USER_INPUTS[user_id] = user_input
            background_tasks.add_task(
                process_gpt,
                user_id,
                user_input,
                user_state["주제"],
                user_state["산출물"],
                user_state["예상_견적"],
                user_state["기간"]
            )
            
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
    
    # quick_replies 초기화를 먼저 수행
    quick_replies = [{
        "messageText": "새로운 견적 문의",
        "action": "message",
        "label": "새로운 견적 문의"
    }]

    # 입력 정보가 있으면 축소 견적 버튼 추가
    if user_id in USER_INPUTS:
        quick_replies.append({
            "messageText": f"축소 견적 확인:{user_id}",
            "action": "message",
            "label": "축소 견적만 보기"
        })
    
    return {
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {
                    "text": f"{response_text}\n\n🗂️ 입력 정보:\n{user_input}"
                }
            }],
            "quickReplies": quick_replies
        }
    }

@app.get("/shrunk_result/{user_id}")
async def get_shrunk_result(user_id: str):
    """축소 견적은 버튼 눌렀을 때 GPT 다시 호출"""
    if user_id not in USER_INPUTS:
        return {"version": "2.0", "template": {"outputs": [{"simpleText": {"text": "❌ 입력 정보가 없습니다."}}]}}

    user_input = USER_INPUTS[user_id]
    # 기존 full prompt 재활용
    topic = USER_SLOT_STATE.get(user_id, {}).get("주제", "")
    output = USER_SLOT_STATE.get(user_id, {}).get("산출물", "")
    budget = USER_SLOT_STATE.get(user_id, {}).get("예상_견적", "")
    period = USER_SLOT_STATE.get(user_id, {}).get("기간", "")

    # 캐시된 축소 견적이 있으면 재사용
    if user_id in SHRUNK_RESPONSES and SHRUNK_RESPONSES[user_id]:
        shrunk_only_text = SHRUNK_RESPONSES[user_id]
    else:
        full_prompt = build_prompt_multicategory(user_input, SERVICE_CATEGORIES, infer_all_categories(topic, output), budget, topic, period)
        shrunk_only_text = call_gpt_shrunk_only(full_prompt, user_budget=budget)
        SHRUNK_RESPONSES[user_id] = shrunk_only_text  # 캐싱

    return {
        "version": "2.0",
        "template": {
            "outputs": [{"simpleText": {"text": shrunk_only_text}}],
            "quickReplies": [{
                "messageText": f"견적 결과 확인:{user_id}",
                "action": "message",
                "label": "전체 견적 보기"
            }]
        }
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

# 직접 실행 시 서버 구동
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Railway나 Fly.io 환경변수 대응
    uvicorn.run(app, host="0.0.0.0", port=port)
