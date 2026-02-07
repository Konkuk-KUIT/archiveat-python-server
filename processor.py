from services.youtube import YouTubeProcessor
from services.naver_news import NaverNewsProcessor
from services.summarizer import GeminiSummarizer
import pprint

class ArchiveatProcessor:
    def __init__(self):
        # Whisper tiny 모델: 가장 빠른 음성 인식
        self.yt_processor = YouTubeProcessor(model_size="tiny")
        self.naver_news_processor = NaverNewsProcessor()
        self.summarizer = GeminiSummarizer()

    def execute_youtube_flow(self, url):
        """
        유튜브 URL로부터 정보를 추출하고 요약/분류를 수행하는 전체 흐름을 제어합니다.
        """
        print(f"\n[1/2] 유튜브 데이터 추출 시작: {url}")
        # 1. 유튜브 로직 실행 (제목, 자막 등 추출)
        video_data = self.yt_processor.process(url)

        # 에러 발생 시 즉시 반환
        if "error" in video_data:
            return video_data

        print("[2/2] Gemini AI 분석 및 요약 시작...")
        # 2. 요약 엔진 실행 (분류 및 3단계 요약)
        # 제목과 자막을 함께 넘김
        analysis_result = self.summarizer.summarize_content(
            video_data["title"], 
            video_data["description"] + "\n" + video_data["transcript"]
        )

        # 3. 데이터 결합
        # 자바 백엔드의 'newsletters' 테이블 구조와 1:1로 매칭되도록 최종 딕셔너리를 구성
        final_result = {
            "video_info": {
                "title": video_data["title"],
                "thumbnail_url": video_data["thumbnail_url"],
                "content_url": url,
                "channel": video_data["channel"],
                "duration": video_data["duration"]
            },
            "analysis": analysis_result # category, topic, 3종 summary 포함
        }

        return final_result

    def execute_naver_news_flow(self, url):
        """
        네이버 뉴스 및 일반 웹 URL로부터 정보를 추출하고 요약/분류를 수행합니다.
        """
        print(f"\n[1/2] 웹 콘텐츠 크롤링 시작: {url}")
        # 1. 네이버 뉴스/일반 웹 크롤링 실행
        article_data = self.naver_news_processor.process(url)

        # 에러 발생 시 즉시 반환
        if article_data.get("type") == "ERROR":
            return {"error": article_data.get("error", "Unknown error")}

        print("[2/2] Gemini AI 분석 및 요약 시작...")
        # 2. 요약 엔진 실행
        analysis_result = self.summarizer.summarize_content(
            article_data["title"],
            article_data["content"]
        )

        # 3. 데이터 결합
        final_result = {
            "article_info": {
                "title": article_data["title"],
                "thumbnail_url": article_data.get("thumbnail_url"),
                "content_url": url,
                "word_count": len(article_data["content"])  # 글자 수 계산
            },
            "analysis": analysis_result
        }

        return final_result

if __name__ == "__main__":
    app = ArchiveatProcessor()
    
    # 테스트용 유튜브 링크
    test_url = "https://www.youtube.com/watch?v=4I8fWk0k7Y8"
    
    final_output = app.execute_youtube_flow(test_url)
    
    print("\n" + "="*50)
    print("최종 분석 결과 (DB 저장용)")
    print("="*50)
    pprint.pprint(final_output)
