from fastapi import FastAPI, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import openai
from typing import Optional, Dict, Any
from sentence_transformers import SentenceTransformer, util
import numpy as np

# SentenceBERT 모델 로드
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

# 서비스 카테고리 및 기능 정의
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

def get_service_cost(category: str, service: str) -> int:
    """서비스 카테고리와 세부 서비스에 대한 비용을 반환"""
    try:
        if category in SERVICE_CATEGORIES and service in SERVICE_CATEGORIES[category]:
            return SERVICE_CATEGORIES[category][service]["cost"]
    except:
        return 0
    return 0

def get_service_features(category: str, service: str) -> list:
    """서비스 카테고리와 세부 서비스의 기능 목록을 반환"""
    try:
        if category in SERVICE_CATEGORIES and service in SERVICE_CATEGORIES[category]:
            return SERVICE_CATEGORIES[category][service]["features"]
    except:
        return []
    return []

# 프로젝트 데이터
PROJECT_TO_OUTPUTS = {
    "고객센터 챗봇": ["AI 챗봇", "관리자 페이지"],
    "뉴스 요약 시스템": ["리포트 자동화", "대시보드"],
    "운세 서비스": ["AI 챗봇", "사용자 프론트", "데이터 수집", "백엔드"],
    "병원 예약 시스템": ["웹사이트", "백엔드", "관리자 페이지"],
    "전자상거래 플랫폼": ["웹사이트", "프론트엔드", "백엔드", "결제 시스템"],
    "온라인 교육 플랫폼": ["프론트엔드", "백엔드", "동영상 업로드 시스템"],
    "부동산 정보 포털": ["지도 연동", "데이터 수집", "시각화"],
    "날씨 정보 서비스": ["API 연동", "시각화", "프론트엔드"],
    "AI 면접 시스템": ["AI 챗봇", "녹화 기능", "관리자 페이지"],
    "자동차 정비 예약 시스템": ["웹사이트", "예약 모듈", "관리자 페이지"],
    "헬스케어 데이터 분석": ["데이터 수집", "정제", "리포트"],
    "영화 추천 시스템": ["추천 알고리즘", "프론트엔드", "백엔드"],
    "음악 스트리밍 앱": ["프론트엔드", "백엔드", "플레이어 UI"],
    "AI 문서 요약기": ["AI 모델", "백엔드", "리포트 자동화"],
    "가계부 앱": ["프론트엔드", "시각화", "백엔드"],
    "설문조사 시스템": ["프론트엔드", "백엔드", "통계 리포트"],
    "이력서 생성기": ["템플릿 엔진", "프론트엔드", "리포트 자동화"],
    "영어 학습 챗봇": ["AI 챗봇", "프론트엔드", "데이터 수집"],
    "고객 피드백 분석 시스템": ["텍스트 분석", "시각화", "리포트"],
    "전자책 구독 플랫폼": ["결제 시스템", "뷰어", "프론트엔드"],
    "전자도서관 관리 시스템": ["검색 기능", "대여 시스템", "관리자 페이지"],
    "식단 추천 서비스": ["추천 알고리즘", "사용자 프론트", "데이터 수집"],
    "SNS 분석 대시보드": ["API 연동", "시각화", "리포트 자동화"],
    "중고거래 플랫폼": ["프론트엔드", "백엔드", "결제 시스템"],
    "AI 음성비서": ["음성인식", "AI 챗봇", "백엔드"],
    "스포츠 기록 앱": ["프론트엔드", "데이터 입력", "시각화"],
    "교통정보 통합 플랫폼": ["API 연동", "지도 서비스", "시각화"],
    "기업 인트라넷 포털": ["관리자 페이지", "프론트엔드", "문서 관리"],
    "재무 보고 시스템": ["리포트 자동화", "KPI", "Power BI"],
    "생산 공정 모니터링 시스템": ["시각화", "데이터 수집", "모니터링"],
    "학원 스케줄 관리 앱": ["프론트엔드", "달력 기능", "백엔드"],
    "전자투표 시스템": ["인증 기능", "백엔드", "프론트엔드"],
    "AI 번역기": ["AI 모델", "프론트엔드", "백엔드"],
    "재택근무 출퇴근 시스템": ["위치 기반", "프론트엔드", "백엔드"],
    "AI 상담 챗봇": ["AI 챗봇", "상담 시나리오", "로그 저장"],
    "문서 검색 엔진": ["검색 인덱싱", "백엔드", "프론트엔드"],
    "보안 모니터링 대시보드": ["모니터링", "시각화", "알림 기능"],
    "물류 추적 시스템": ["지도 연동", "백엔드", "프론트엔드"],
    "AI 면접 평가 시스템": ["AI 챗봇", "영상 녹화", "리포트"],
    "청구서 자동화 시스템": ["리포트 자동화", "PDF 생성기", "프론트엔드"],
    "사내 게시판 시스템": ["프론트엔드", "글쓰기 기능", "관리자 페이지"],
    "디지털 명함 서비스": ["프론트엔드", "QR 생성", "관리자 페이지"],
    "AI 출결 관리 시스템": ["얼굴인식", "백엔드", "시각화"],
    "세무 리포트 생성기": ["리포트", "정제", "PDF 출력"],
    "HR 인재 추천 시스템": ["추천 알고리즘", "관리자 페이지", "리포트"],
    "온라인 투표 플랫폼": ["프론트엔드", "투표 모듈", "백엔드"],
    "마이데이터 기반 건강관리": ["데이터 수집", "시각화", "AI 분석"],
    "기업 경쟁사 분석 도구": ["크롤링", "리포트", "대시보드"],
    "상담 일정 예약 플랫폼": ["프론트엔드", "캘린더", "알림"],
    "중소기업 재무 리포트 자동화": ["정제", "리포트 자동화", "시각화"],
    "AI 자소서 코치": ["AI 챗봇", "자연어 분석", "프론트엔드"],
    "전자계약 서비스": ["문서 생성", "서명 기능", "관리자 페이지"],
    "AI 코딩 도우미": ["AI 모델", "코드 편집기", "프론트엔드"],
    "온라인 출석 체크 시스템": ["QR 체크인", "백엔드", "시각화"],
    "전자공시 분석 플랫폼": ["크롤링", "텍스트 분석", "리포트"],
    "투자자 정보 제공 서비스": ["리포트", "대시보드", "알림"],
    "스타트업 포트폴리오 공유 서비스": ["프론트엔드", "리포트", "PDF 출력"],
    "앱 사용 데이터 분석 시스템": ["파이프라인", "시각화", "KPI"],
    "경진대회 평가 시스템": ["프론트엔드", "점수 계산", "리포트"],
    "AI 음성 상담 시스템": ["음성인식", "AI 챗봇", "대화 기록"],
    "AI 이미지 분석 서비스": ["이미지 업로드", "AI 모델", "리포트"],
    "라이브 커머스 플랫폼": ["스트리밍", "결제 시스템", "프론트엔드"],
    "디지털 서명 서비스": ["문서 업로드", "서명 기능", "백엔드"],
    "전자민원 처리 시스템": ["접수 기능", "백엔드", "리포트"],
    "스타일 추천 서비스": ["추천 알고리즘", "프론트엔드", "데이터 수집"],
    "지역 상권 분석 서비스": ["지도 시각화", "데이터 수집", "리포트"],
    "투표 기반 커뮤니티 앱": ["프론트엔드", "투표 모듈", "백엔드"],
    "AI 보도자료 생성기": ["AI 모델", "리포트", "PDF 출력"],
    "요약형 뉴스 제공 앱": ["크롤링", "요약 모델", "프론트엔드"],
    "채팅 기반 일정 공유 앱": ["프론트엔드", "대화 모듈", "캘린더 연동"],
    "운동 기록 관리 앱": ["프론트엔드", "데이터 수집", "시각화"],
    "리걸테크 문서 분석기": ["자연어 처리", "AI 모델", "프론트엔드"],
    "부모-자녀 일정 공유 앱": ["프론트엔드", "캘린더", "알림 기능"],
    "투자 시뮬레이터": ["프론트엔드", "계산 로직", "시각화"],
    "직원 평가 시스템": ["리포트", "KPI", "관리자 페이지"],
    "건강보험 자동 계산기": ["입력 폼", "계산기", "리포트"],
    "명함 OCR 인식기": ["OCR 모델", "프론트엔드", "리포트"],
    "스마트 팩토리 모니터링": ["센서 데이터", "시각화", "모니터링"],
    "스마트팜 대시보드": ["IoT 연동", "시각화", "리포트"],
    "공공데이터 분석 플랫폼": ["데이터 수집", "시각화", "KPI"],
    "도서 추천 플랫폼": ["추천 모델", "프론트엔드", "관리자 페이지"],
    "회의록 요약 시스템": ["음성 인식", "텍스트 요약", "리포트"],
    "이력 자동 채우기 시스템": ["OCR", "백엔드", "리포트"],
    "사진 기반 검색 엔진": ["이미지 분석", "검색 기능", "프론트엔드"],
    "비대면 상담 플랫폼": ["AI 챗봇", "프론트엔드", "영상 기능"],
    "멘토링 매칭 시스템": ["매칭 알고리즘", "프론트엔드", "알림"],
    "마케팅 퍼널 분석 도구": ["KPI", "대시보드", "리포트"],
    "AI 성적 분석기": ["리포트", "시각화", "AI 분석"],
    "지출 분석 시스템": ["데이터 수집", "카테고리 분류", "시각화"],
    "고객 이탈 예측 시스템": ["AI 모델", "백엔드", "리포트"],
    "직원 복지 관리 포털": ["프론트엔드", "설문 기능", "리포트"],
    "심리상담 AI 챗봇": ["AI 챗봇", "대화 저장", "프론트엔드"],
    "음식 알레르기 필터링 앱": ["입력 기능", "추천 시스템", "프론트엔드"],
    "지역 기반 퀘스트 앱": ["위치 기반", "프론트엔드", "백엔드"],
    "기부 캠페인 플랫폼": ["프론트엔드", "결제 시스템", "리포트"],
    "여행 일정 공유 앱": ["프론트엔드", "달력 기능", "지도 연동"]
}

# 산출물 특성 정의
OUTPUT_TO_FEATURES = {
    "웹사이트": {
        "base_cost": 1000,
        "base_duration": 30,
        "features": {
            "회원관리": {"cost": 300, "duration": 7},
            "결제": {"cost": 500, "duration": 10},
            "관리자페이지": {"cost": 400, "duration": 7}
        }
    },
    "모바일앱": {
        "base_cost": 1500,
        "base_duration": 45,
        "features": {
            "푸시알림": {"cost": 200, "duration": 5},
            "지도": {"cost": 300, "duration": 7},
            "결제": {"cost": 500, "duration": 10}
        }
    }
}

SIMILARITY_THRESHOLD = 0.75

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

def find_similar_project(query: str) -> tuple[str, float]:
    """가장 유사한 프로젝트와 유사도 점수를 반환"""
    query_embedding = model.encode(query)
    max_similarity = 0
    best_match = None
    
    for project, features in PROJECT_TO_OUTPUTS.items():
        # 프로젝트 이름과 기능을 결합하여 임베딩
        project_text = f"{project} - {', '.join(features)}"
        project_embedding = model.encode(project_text)
        similarity = util.pytorch_cos_sim(query_embedding, project_embedding).item()
        
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = project
    
    return best_match, max_similarity

def extract_features(query: str) -> list[str]:
    """사용자 입력에서 필요한 기능들을 추출"""
    # 실제 구현에서는 NER이나 키워드 매칭을 사용할 수 있습니다
    features = []
    for output_type in OUTPUT_TO_FEATURES.values():
        for feature in output_type["features"]:
            if feature in query.lower():
                features.append(feature)
    return features

def calculate_estimate(output_type: str, features: list[str]) -> dict:
    """견적 계산"""
    if output_type not in OUTPUT_TO_FEATURES:
        return None
        
    base = OUTPUT_TO_FEATURES[output_type]
    total_cost = base["base_cost"]
    total_duration = base["base_duration"]
    
    for feature in features:
        if feature in base["features"]:
            total_cost += base["features"][feature]["cost"]
            total_duration += base["features"][feature]["duration"]
            
    return {
        "cost": f"{total_cost}만원",
        "duration": f"{total_duration}일"
    }

@app.post("/kakao/webhook")
async def kakao_webhook(request: KakaoRequest):
    utterance = request.userRequest.utterance
    user_id = request.userRequest.user.id
    
    # 1단계: 서비스 카테고리 매칭
    for category in SERVICE_CATEGORIES.keys():
        if category.replace("_", " ").lower() in utterance.lower():
            services = SERVICE_CATEGORIES[category]
            total_cost = sum(service["cost"] for service in services.values() if isinstance(service, dict) and "cost" in service)
            
            response_text = f"[{category.replace('_', ' ')} 서비스 견적]\n\n"
            response_text += "주요 단계:\n"
            
            for service_name, service_info in services.items():
                if isinstance(service_info, dict) and "features" in service_info:
                    response_text += f"\n▶ {service_name.replace('_', ' ')}\n"
                    response_text += f"- 비용: {service_info['cost']:,}원\n"
                    response_text += "- 주요 기능:\n"
                    for feature in service_info["features"]:
                        response_text += f"  · {feature}\n"
            
            response_text += f"\n총 견적: {total_cost:,}원"
            break
    else:
        # 2단계: 프로젝트 매칭
        similar_project, similarity = find_similar_project(utterance)
        
        if similarity >= SIMILARITY_THRESHOLD and similar_project:
            features = PROJECT_TO_OUTPUTS[similar_project]
            response_text = f"비슷한 프로젝트를 찾았습니다!\n\n"
            response_text += f"프로젝트: {similar_project}\n"
            response_text += f"필요한 기능:\n"
            for feature in features:
                response_text += f"- {feature}\n"
        else:
            response_text = "다음 중 어떤 종류의 서비스를 찾으시나요?\n\n"
            for category in SERVICE_CATEGORIES.keys():
                response_text += f"- {category.replace('_', ' ')}\n"

    response_json = {
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
    return JSONResponse(content=response_json)

if __name__ == "__main__":
    import uvicorn
    import os
    
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
