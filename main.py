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
    "모바일앱_플랫폼": {
        "기획_요구사항_정의": {
            "features": [
                "앱 사용자 흐름 설계",
                "기능 목록 정의",
                "앱 구조 및 와이어프레임 설계"
            ],
            "outputs": ["앱 기획서", "앱 구조도", "기능 정의서"],
            "cost": 1000000
        },
        "프론트엔드_개발": {
            "features": [
                "Flutter 기반 앱 UI 구현",
                "Riverpod 등 상태관리 적용",
                "iOS/Android 동시 대응"
            ],
            "outputs": ["iOS/Android 앱 UI 모듈"],
            "cost": 2000000
        },
        "기능_API_연동": {
            "features": [
                "로그인 및 인증 기능",
                "서버 API 연동 (FastAPI 등)",
                "Firebase 연동"
            ],
            "outputs": ["기능 구현 코드", "API 문서"],
            "cost": 1000000
        },
        "모바일_기능_특화": {
            "features": [
                "FCM 푸시 알림",
                "카메라 / 갤러리 접근",
                "인앱 기능 연동"
            ],
            "outputs": ["알림 연동 코드", "디바이스 연동 기능"],
            "cost": 1000000
        },
        "테스트_QA": {
            "features": [
                "안드로이드 및 iOS 실기기 테스트",
                "버그 수정 및 QA 리포트 작성"
            ],
            "outputs": ["테스트 보고서", "버그 수정 내역"],
            "cost": 800000
        },
        "앱_스토어_배포": {
            "features": [
                "Google Play 및 Apple Store 배포 등록",
                "앱 심사 대응"
            ],
            "outputs": ["등록 완료 링크", "스토어 설명 및 이미지"],
            "cost": 300000
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
    
    # 모바일 앱 관련 키워드
    if any(kw in output for kw in ["앱", "ios", "안드로이드", "모바일"]):
        return "모바일앱_플랫폼"
    
    # 웹 플랫폼 관련 키워드
    elif any(kw in output for kw in ["웹", "사이트", "플랫폼", "관리자", "ui", "페이지"]):
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
    if any(kw in output for kw in ["웹", "사이트", "플랫폼"]):
        categories.add("웹_플랫폼")

    # 모바일 앱 관련
    if any(kw in output for kw in ["앱", "ios", "안드로이드", "모바일"]):
        categories.add("모바일앱_플랫폼")

    # 챗봇 관련
    if any(kw in output for kw in ["챗봇", "대화", "ai"]):
        categories.add("AI_챗봇")

    # 시각화/데이터 분석
    if any(kw in output for kw in ["분석", "대시보드", "리포트"]):
        categories.add("시각화_대시보드")

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
    
    # 중복 제거하면서 순서 유지
    unique_categories = list(dict.fromkeys(categories))
    prompt += f"💡 사용자가 요청한 주요 서비스 범주는 `{', '.join(unique_categories)}`입니다.\n\n"
    
    prompt += "🧾 각 카테고리에 대해 빠짐없이 견적을 제시해 주세요. 일부 항목 누락 없이 전체 범위를 고려해 주세요.\n"
    prompt += "⚠️ 각 카테고리는 독립된 프로젝트 단위로 보고, 개별 견적을 제시해 주세요.\n"
    prompt += "\n💡 동일한 카테고리명(`📂 웹 플랫폼`)은 한 번만 출력하고, 그 아래에 모든 단계와 금액을 나열해 주세요.\n"
    prompt += "\n💡 각 카테고리별 비용 총합(소계)을 마지막 줄에 `💰 소계: ...원` 형식으로 표시해 주세요.\n\n"
    prompt += "우리 회사는 다음과 같은 서비스 카테고리를 제공합니다:\n"

    # 중복 제거된 카테고리로 순회
    for category in unique_categories:
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
💰 소계: [카테고리 총 금액]원

이런 형식으로 각 카테고리별 견적을 제시한 후,

💰 총 합계: [전체 금액]원
"""

    return prompt

def call_gpt_estimate_fitting_budget(user_input: str, topic: str, output: str, expected_budget: str, period: str) -> str:
    """예산에 맞춘 견적을 바로 생성 (GPT 1회 호출로 처리)"""
    prompt = build_prompt_multicategory(
        user_input, SERVICE_CATEGORIES,
        infer_all_categories(topic, output),
        expected_budget, topic, period
    )

    min_reasonable_budget = 300_000
    budget_value = 0
    match = re.search(r"(\d+)", expected_budget.replace(",", ""))
    if match:
        budget_value = int(match.group(1))

    # 예산 부족시 우선순위 기반 축소안 요청
    if budget_value < min_reasonable_budget:
        prompt = (
            f"❗ 사용자의 입력 예산이 {expected_budget}으로 제한적입니다.\n"
            "예산이 부족한 경우, 다음 원칙에 따라 우선순위 기반으로 축소안을 설계해 주세요:\n\n"
            "1️⃣ 핵심 기능 우선: 서비스의 핵심 가치를 전달할 수 있는 필수 기능을 우선 포함\n"
            "2️⃣ MVP 중심: 최소 기능 제품(MVP) 구성에 필요한 단계만 우선 선택\n"
            "3️⃣ 단계별 축소: 각 단계에서 필수적인 기능만 남기고 부가 기능은 제외\n"
            "4️⃣ 우선순위 제시: 제외된 기능들은 향후 업그레이드 항목으로 별도 안내\n\n"
            + prompt
        )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system", 
            "content": "당신은 IT 견적 전문가입니다. 예산이 제한적인 경우, 우선순위를 고려하여 실현 가능한 최소 범위의 견적을 제시해야 합니다."
        }, {
            "role": "user", 
            "content": prompt
        }],
        temperature=0.7,
        max_tokens=1400
    )
    return response.choices[0].message.content

# 비동기 GPT 요청 처리
async def process_gpt(user_id: str, user_input: str, topic: str = "", output: str = "", expected_budget: str = "", period: str = ""):
    USER_INPUTS[user_id] = user_input
    GPT_RESPONSES[user_id] = "⏳ 요청을 처리 중입니다. 잠시만 기다려주세요..."

    response = call_gpt_estimate_fitting_budget(user_input, topic, output, expected_budget, period)
    GPT_RESPONSES[user_id] = response

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
                            "text": "죄송합니다. 저는 팀 소개 및 포트폴리오 확인과 견적 상담만 도와드릴 수 있어요. 😅\n\n다음과 같은 내용을 문의해주세요:\n- 프로젝트 견적 문의\n- 포트폴리오 확인\n- 개발 비용 상담"
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
    
    quick_replies = [{
        "messageText": "새로운 견적 문의",
        "action": "message",
        "label": "새로운 견적 문의"
    }]

    
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


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {"status": "healthy"}

# 직접 실행 시 서버 구동
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Railway나 Fly.io 환경변수 대응
    uvicorn.run(app, host="0.0.0.0", port=port)
