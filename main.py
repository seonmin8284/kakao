from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import openai
from dotenv import load_dotenv
import os
from typing import Dict, Any
import uuid

# 환경 변수 로드
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

# 결과 저장소 (실제 운영에서는 DB나 Redis 사용)
GPT_RESPONSES: Dict[str, str] = {}
USER_INPUTS: Dict[str, str] = {}  # 사용자 입력 저장소

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
    }
}

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
        utterance = body.get("userRequest", {}).get("utterance", "")
        
        # 견적 결과 확인 요청 처리
        if utterance.startswith("견적 결과 확인:"):
            user_id = utterance.split("견적 결과 확인:")[-1].strip()
            return await get_result(user_id)
        
        # 파라미터 추출
        action_params = body.get("action", {}).get("params", {})
        print("[DEBUG] action_params:", action_params)

        topic = action_params.get("주제") or action_params.get("$주제", "")
        duration = action_params.get("기간") or action_params.get("$기간", "")

            
        user_id = str(uuid.uuid4())
        
        # 사용자의 요청 프롬프트 구성
        user_input = f"""
프로젝트 주제: {topic}
예상 기간: {duration}
        """.strip()
        
        # GPT 요청 비동기 실행
        background_tasks.add_task(process_gpt, user_id, user_input)
        
        return JSONResponse(content={
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {
                        "text": f"📝 요청을 접수했어요!\n몇 초 후 결과를 확인해주세요.\n주제: {topic}기간: {duration}\n👉 확인: /result/{user_id}"
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
