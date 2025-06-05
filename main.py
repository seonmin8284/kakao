from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from sentence_transformers import SentenceTransformer, util
import os

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

# 이하 기존 코드 동일

# 모델 로딩
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 서비스 및 프로젝트 데이터 생략 (이전 코드와 동일하므로 생략 가능)
# SERVICE_CATEGORIES, PROJECT_TO_OUTPUTS, OUTPUT_TO_FEATURES 정의 부분을 그대로 둬야 합니다

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
async def kakao_webhook(request: KakaoRequest):
    utterance = request.userRequest.utterance

    # 서비스 카테고리 우선 매칭
    for category in SERVICE_CATEGORIES.keys():
        if category.replace("_", " ").lower() in utterance.lower():
            services = SERVICE_CATEGORIES[category]
            total_cost = sum(s["cost"] for s in services.values() if isinstance(s, dict) and "cost" in s)
            response_text = f"[{category.replace('_', ' ')} 서비스 견적]\n\n주요 단계:\n"
            for name, info in services.items():
                if isinstance(info, dict) and "features" in info:
                    response_text += f"\n▶ {name.replace('_', ' ')}\n- 비용: {info['cost']:,}원\n- 주요 기능:\n"
                    for f in info["features"]:
                        response_text += f"  · {f}\n"
            response_text += f"\n총 견적: {total_cost:,}원"
            break
    else:
        matched_outputs = extract_outputs_from_text(utterance)
        if matched_outputs:
            matched_projects = [
                proj for proj, outs in PROJECT_TO_OUTPUTS.items()
                if all(output in outs for output in matched_outputs)
            ]
            if matched_projects:
                response_text = "입력하신 기능을 포함하는 프로젝트입니다:\n\n"
                for proj in matched_projects[:3]:
                    response_text += f"- {proj}\n"
            else:
                response_text = f"요청하신 기능({', '.join(matched_outputs)})을 포함하는 프로젝트를 찾지 못했습니다."
        else:
            # Fallback to BERT 유사도
            similar_project, similarity = find_similar_project(utterance)
            if similarity >= SIMILARITY_THRESHOLD:
                features = PROJECT_TO_OUTPUTS[similar_project]
                response_text = f"비슷한 프로젝트를 찾았습니다:\n\n프로젝트: {similar_project}\n기능:\n"
                for f in features:
                    response_text += f"- {f}\n"
            else:
                response_text = "다음 중 어떤 종류의 서비스를 찾으시나요?\n\n"
                for cat in SERVICE_CATEGORIES:
                    response_text += f"- {cat.replace('_', ' ')}\n"

    return JSONResponse(content={
        "version": "2.0",
        "template": {
            "outputs": [{
                "simpleText": {"text": response_text}
            }]
        }
    })

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
