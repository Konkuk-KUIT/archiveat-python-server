"""
네이버 뉴스 크롤링 및 요약 테스트 스크립트

사용법:
1. Python 서버 실행: python -m uvicorn main:app --reload --port 8000
2. 이 스크립트 실행: python test_naver_news.py
"""

from services.naver_news import NaverNewsProcessor
from services.summarizer import GeminiSummarizer
import json


def test_naver_news_crawler():
    """네이버 뉴스 크롤러 단독 테스트"""
    print("\n" + "="*60)
    print("TEST 1: 네이버 뉴스 크롤링")
    print("="*60)
    
    processor = NaverNewsProcessor()
    
    # 네이버 뉴스 URL 예시
    test_urls = [
        "https://n.news.naver.com/mnews/article/629/0000461258",
        # 다른 네이버 뉴스 URL도 추가 가능
    ]
    
    for url in test_urls:
        print(f"\n크롤링 URL: {url}")
        result = processor.process(url)
        
        print(f"Type: {result['type']}")
        print(f"Title: {result['title']}")
        print(f"Content (first 200 chars): {result['content'][:200]}...")
        if result.get('thumbnail_url'):
            print(f"Thumbnail: {result['thumbnail_url']}")
        if result.get('error'):
            print(f"Error: {result['error']}")
        print("-" * 60)


def test_with_summarizer():
    """크롤러 + Gemini 요약 통합 테스트"""
    print("\n" + "="*60)
    print("TEST 2: 네이버 뉴스 크롤링 + Gemini 요약")
    print("="*60)
    
    processor = NaverNewsProcessor()
    summarizer = GeminiSummarizer()
    
    # 테스트 URL
    test_url = "https://n.news.naver.com/mnews/article/629/0000461258"
    user_memo = "반도체 관련주 주가 영향 분석용"  # 사용자 메모 (선택사항)
    
    print(f"\n1. 크롤링 중: {test_url}")
    crawl_result = processor.process(test_url)
    
    if crawl_result.get("error"):
        print(f"❌ 크롤링 실패: {crawl_result['error']}")
        return
    
    print(f"✅ 제목: {crawl_result['title']}")
    print(f"✅ 본문 길이: {len(crawl_result['content'])} characters")
    
    # 사용자 메모가 있으면 본문 앞에 추가
    content_with_memo = crawl_result["content"]
    if user_memo:
        content_with_memo = f"[사용자 메모: {user_memo}]\n\n{content_with_memo}"
        print(f"✅ 사용자 메모: {user_memo}")
    
    print("\n2. Gemini AI 요약 중...")
    analysis_result = summarizer.summarize_content(
        crawl_result["title"],
        content_with_memo
    )
    
    if "error" in analysis_result:
        print(f"❌ 요약 실패: {analysis_result['error']}")
        return
    
    print("\n" + "="*60)
    print("최종 결과 (JSON)")
    print("="*60)
    print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
    print("="*60)
    
    # 주요 필드 출력
    print(f"\n📁 카테고리: {analysis_result.get('category')}")
    print(f"🏷️  토픽: {analysis_result.get('topic')}")
    print(f"📝 짧은 요약: {analysis_result.get('small_card_summary')}")
    print(f"📄 중간 요약: {analysis_result.get('medium_card_summary')}")
    print(f"📰 상세 요약: {len(analysis_result.get('newsletter_summary', []))}개 블록")


def test_general_web():
    """일반 웹사이트 크롤링 테스트"""
    print("\n" + "="*60)
    print("TEST 3: 일반 웹사이트 크롤링 (readability)")
    print("="*60)
    
    processor = NaverNewsProcessor()
    
    # 일반 웹사이트 URL (브런치, 티스토리 등)
    test_url = "https://brunch.co.kr/@jinhoyooephf/64"  # 예시 URL
    
    print(f"\n크롤링 URL: {test_url}")
    result = processor.process(test_url)
    
    print(f"Type: {result['type']}")
    print(f"Title: {result['title']}")
    print(f"Content (first 300 chars): {result['content'][:300]}...")
    if result.get('error'):
        print(f"Error: {result['error']}")


if __name__ == "__main__":
    print("네이버 뉴스 크롤링 및 요약 테스트 시작")
    print("Gemini API 키가 .env 파일에 설정되어 있는지 확인하세요!")
    
    # TEST 1: 크롤러만 테스트
    test_naver_news_crawler()
    
    # TEST 2: 크롤러 + 요약 통합 테스트
    try:
        test_with_summarizer()
    except Exception as e:
        print(f"\n⚠️  요약 테스트 실패: {e}")
        print("Gemini API 키가 설정되어 있는지 확인하세요.")
    
    # TEST 3: 일반 웹사이트 테스트 (선택사항)
    # test_general_web()
    
    print("\n✅ 모든 테스트 완료!")
