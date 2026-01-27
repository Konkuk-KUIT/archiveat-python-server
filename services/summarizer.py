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
        self.model_id = "gemini-flash-latest" 

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

        # 프롬프트
        prompt = f"""
        당신은 전문 콘텐츠 분석가입니다. 제공된 콘텐츠의 제목과 내용을 분석하여 다음 JSON 형식으로만 답변하세요.
        
        ### 분류 규칙:
        1. 아래 카테고리 중 딱 하나를 선택: {list(category_map.keys())}
        2. 해당 카테고리의 토픽 중 하나 선택 (없으면 '기타'): {category_map}

        ### 요약 규칙 (ERD 필드명 준수):
        1. small_card_summary: 20자 내외의 아주 짧은 한 줄 요약
        2. medium_card_summary: 핵심 내용 위주의 2~3문장 요약
        3. newsletter_summary: 상세 요약. 반드시 '3개의 객체'를 가진 리스트여야 하며, 각 객체는 'title'(소제목)과 'content'(문단 내용)를 포함해야 함.

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
            return {"error": str(e)}

if __name__ == "__main__":
    summarizer = GeminiSummarizer()
    # 블로그나 기사 형태의 테스트 데이터
    test_title = "연봉 1억 개발자가 말하는 업무 생산성 도구 TOP 3"
    test_content = "노션, 슬랙, 그리고 최근에는 리니어(Linear)를 활용하여 프로젝트를 관리합니다. 효율적인 협업은 조직의 성장에 필수적입니다."
    
    result = summarizer.summarize_content(test_title, test_content)
    
    import pprint
    pprint.pprint(result)