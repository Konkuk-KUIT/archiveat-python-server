import os
from google import genai
from dotenv import load_dotenv
import json

load_dotenv()

class GeminiSummarizer:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(".env 파일에 GEMINI_API_KEY가 설정되지 않았습니다.")
            
        self.client = genai.Client(api_key=api_key)
        self.model_id = "gemini-flash-latest" # 모델명 명시 (flash-latest보다 안정적일 수 있음)

    def summarize_content(self, title, content):
        """
        [범용 모듈] 제목과 본문을 입력받아 서비스 규격에 맞는 JSON을 반환합니다.
        """
        category_map = {
            "IT/과학": ["인공지능", "백엔드/인프라", "프론트/모바일", "데이터/보안", "테크 트렌드", "기타"],
            "국제": ["지정학/외교", "미국/중국", "글로벌 비즈니스", "기후/에너지", "기타"],
            "경제": ["주식/투자", "부동산", "가상 화폐", "창업/스타트업", "브랜드/마케팅", "거시경제", "기타"],
            "문화": ["영화/OTT", "음악", "도서/아티클", "팝컬쳐/트렌드", "공간/플레이스", "디자인/예술", "기타"],
            "생활": ["주니어/취업", "업무 생산성", "리더십/조직", "심리/마인드", "건강/리빙", "기타"]
        }

        # [수정 포인트] f-string 내에서 JSON 예시는 중괄호 2개({{ }}) 사용, 변수는 1개({ }) 사용
        prompt = f"""
        당신은 전문 콘텐츠 분석가입니다. 제공된 콘텐츠의 제목과 내용을 분석하여 다음 JSON 형식으로만 답변하세요.
        서론이나 마크다운(```json) 없이 순수 JSON만 반환하세요.
        
        ### ★필수 반환 필드 및 포맷 (정확히 지킬 것)★:
        {{
            "category": "아래 분류 규칙의 카테고리 중 하나",
            "topic": "아래 분류 규칙의 토픽 중 하나",
            "small_card_summary": "20자 내외의 아주 짧은 한 줄 요약",
            "medium_card_summary": "핵심 내용 위주의 2~3문장 요약",
            "newsletter_summary": [
                {{
                    "title": "소제목1",
                    "content": "문단 내용1"
                }},
                {{
                    "title": "소제목2",
                    "content": "문단 내용2"
                }},
                {{
                    "title": "소제목3",
                    "content": "문단 내용3"
                }}
            ]
        }}

        ### 분류 규칙:
        1. 카테고리 선택지: {list(category_map.keys())}
        2. 토픽 선택지: {category_map} (해당 카테고리에 맞는 토픽 선택)

        ### 입력 데이터:
        [콘텐츠 제목]: {title}
        [콘텐츠 원문]: {content}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            return json.loads(response.text)
        except Exception as e:
            # 에러 발생 시 로그 출력
            print(f"Gemini API Error: {str(e)}")
            return {"error": str(e)}

    def summarize_collection(self, newsletters):
        """
        뉴스레터 목록(제목+요약)을 입력받아 컬렉션용 요약(Small/Medium Card)을 생성합니다.
        """
        prompt = f"""
        당신은 전문 에디터입니다. 아래 제공된 {len(newsletters)}개의 뉴스레터 요약본들을 바탕으로, 이들을 하나로 묶는 컬렉션(모음집)의 제목과 설명을 작성해주세요.
        
        ### 입력 데이터(뉴스레터 목록):
        {json.dumps(newsletters, ensure_ascii=False, indent=2)}

        ### ★필수 반환 필드 및 조건 (정확히 지킬 것)★:
        JSON 형식으로만 응답하세요.

        {{
            "small_card_summary": "컬렉션의 실질적인 제목 역할. 3~4단어로 핵심을 관통하는 문구 (예: '생산성을 높이는 툴', '개발자 커리어 조언')",
            "medium_card_summary": "어떤 뉴스레터들을 위주로 모았는지, 이 컬렉션이 독자에게 어떤 가치를 주는지 설명하는 1개의 자연스러운 문장 (예: '실무에서 바로 쓸 수 있는 생산성 도구들과 활용법을 모았습니다.')"
        }}
        """

        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt,
                config={
                    'response_mime_type': 'application/json'
                }
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Gemini API Error (Collection): {str(e)}")
            return {"error": str(e)}

if __name__ == "__main__":
    summarizer = GeminiSummarizer()
    # 테스트 데이터
    test_title = "연봉 1억 개발자가 말하는 업무 생산성 도구 TOP 3"
    test_content = "노션, 슬랙, 그리고 최근에는 리니어(Linear)를 활용하여 프로젝트를 관리합니다. 효율적인 협업은 조직의 성장에 필수적입니다."
    
    result = summarizer.summarize_content(test_title, test_content)
    
    import pprint
    pprint.pprint(result)