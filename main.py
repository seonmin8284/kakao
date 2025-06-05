from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from sentence_transformers import SentenceTransformer, util
import os
from tasks import process_utterance_async, set_project_data, ANALYSIS_RESULTS

# 모델 로딩
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 서비스 및 프로젝트 데이터 (카테고리 기준 견적 산정)
SERVICE_CATEGORIES = {
    "시각화_대시보드": {
        "기획_요구사항_정의": {
            "features": ["분석 목적 및 주요 KPI 정의", "사용자 요구 정리", "데이터 시각화 방향 수립"],
            "outputs": ["대시보드 기획서", "KPI 정의서", "와이어프레임"],
            "cost": 400000
        },
        "데이터_수집_전처리": {
            "features": ["내부/외부 데이터 수집", "데이터 정제 및 가공", "Power BI/Tableau 적재"],
            "outputs": ["전처리된 데이터셋", "테이블 구조 설계"],
            "cost": 800000
        },
        "대시보드_프로토타입_제작": {
            "features": ["핵심 KPI 위주의 시각화 모듈 개발", "피드백 반영 구조 구성"],
            "outputs": ["초기 대시보드 MVP", "페이지별 기능 설명서"],
            "cost": 1000000
        },
        "사용자_맞춤형_기능_추가": {
            "features": ["필터", "Drill-Down", "권한별 뷰", "주간/월간 리포트 자동화"],
            "outputs": ["사용자 인터랙션 기능 적용된 완성형 대시보드"],
            "cost": 1000000
        },
        "자동화_운영_연동": {
            "features": ["데이터 자동 업데이트", "배치 스케줄링(Airflow)", "알림/리포트 자동화"],
            "outputs": ["자동 리포트 PDF", "Airflow DAG", "메일 발송 연동"],
            "cost": 1000000
        },
        "관리자_교육_전달": {
            "features": ["사용자 가이드 작성", "관리자 교육 세션", "유지보수 문서 전달"],
            "outputs": ["운영 매뉴얼", "대시보드 사용법 PDF"],
            "cost": 0
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
        },
        "교육_전달": {
            "features": ["관리자 및 사용자 매뉴얼 제공", "유지보수 가이드", "기술 이전"],
            "cost": 0
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
        },
        "문서화_전달": {
            "features": ["전체 데이터 흐름도", "운영 가이드", "유지보수 문서 제공"],
            "cost": 0
        }
    },
    "플랫폼": {
        "기획_요구사항_정의": {
            "features": ["고객 요구사항 분석", "핵심 기능 도출", "경쟁 벤치마킹", "플랫폼 구조 설계", "기술 스택 선정", "클라우드 인프라 초안 수립"],
            "cost": 1000000
        },
        "플랫폼_프론트엔드_개발": {
            "features": ["사용자 UI/UX 구현 (React/Vue 기반)", "반응형 디자인 적용"],
            "cost": 2000000
        },
        "플랫폼_백엔드_개발": {
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

# 프로젝트 데이터 설정
PROJECT_TO_OUTPUTS = {
    "대시보드 개발": ["데이터 시각화", "실시간 모니터링", "KPI 대시보드"],
    "AI 챗봇 구축": ["자연어 처리", "대화 시스템", "API 연동"],
    "데이터 파이프라인": ["ETL 프로세스", "데이터 웨어하우스", "자동화 스크립트"],
    "웹 플랫폼 개발": ["프론트엔드", "백엔드", "데이터베이스"]
}

# 초기 데이터 설정
set_project_data(PROJECT_TO_OUTPUTS, SERVICE_CATEGORIES)

SIMILARITY_THRESHOLD = 0.75

app = FastAPI()

# Pydantic 스키마 정의
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

# 기능 유사도 매칭
def find_similar_project(query: str) -> tuple[str, float]:
    query_embedding = model.encode(query)
    max_similarity = 0
    best_match = None
    for project, features in PROJECT_TO_OUTPUTS.items():
        text = f"{project} - {', '.join(features)}"
        similarity = util.pytorch_cos_sim(query_embedding, model.encode(text)).item()
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = project
    return best_match, max_similarity

# 산출물 키워드 기반 추출
def extract_outputs_from_text(text: str) -> list[str]:
    matched = []
    all_outputs = set(sum(PROJECT_TO_OUTPUTS.values(), []))
    for output in all_outputs:
        if output.lower().replace("_", "") in text.lower().replace(" ", ""):
            matched.append(output)
    return matched

@app.post("/kakao/webhook")
async def kakao_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    utterance = body.get("userRequest", {}).get("utterance", "")
    user_id = body.get("userRequest", {}).get("user", {}).get("id", "")
    
    # 1. 즉시 응답
    initial_response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "문의 주셔서 감사합니다. 최적의 견적을 산출 중입니다. 잠시만 기다려주세요! 🤖✨"
                    }
                }
            ],
            "quickReplies": [
                {
                    "messageText": "견적 결과 확인",
                    "action": "message",
                    "label": "견적 결과 확인"
                }
            ]
        }
    }
    
    # 2. 백그라운드 처리 시작
    background_tasks.add_task(process_utterance_async, user_id, utterance)
    
    return JSONResponse(content=initial_response)

@app.get("/kakao/result/{user_id}")
async def get_analysis_result(user_id: str):
    """분석 결과 조회 API"""
    result = ANALYSIS_RESULTS.get(user_id, "아직 분석이 완료되지 않았습니다. 잠시 후 다시 시도해주세요.")
    
    response = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": result
                    }
                }
            ],
            "quickReplies": [
                {
                    "messageText": "새로운 견적 문의",
                    "action": "message",
                    "label": "새로운 견적 문의"
                }
            ]
        }
    }
    
    return JSONResponse(content=response)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
