"""
Tistory 블로그 크롤링 및 요약 테스트 스크립트

사용법:
1. Python 서버 실행: python -m uvicorn main:app --reload --port 8000
2. 이 스크립트 실행: python test_tistory.py
"""

from services.tistory import TistoryProcessor
from services.summarizer import GeminiSummarizer
import json


def test_tistory_crawler():
    """Tistory 크롤러 단독 테스트"""
    print("\n" + "="*60)
    print("TEST 1: Tistory 크롤링")
    print("="*60)

    processor = TistoryProcessor()

    test_urls = [
        "https://realej.tistory.com/433",
        "https://s2house.tistory.com/entry/%EC%86%90%EB%8B%98-%EC%98%AC-%EB%95%8C%EB%A7%88%EB%8B%A4-%EB%AF%BC%EB%A7%9D%ED%96%88%EB%8D%98-%EC%88%98%EC%A0%80%EC%84%B8%ED%8A%B8-%EC%9D%B4%EA%B1%B8%EB%A1%9C-%EB%B0%94%EA%BE%B8%EB%8B%88-%EC%8B%9D%ED%83%81-%EB%B6%84%EC%9C%84%EA%B8%B0%EA%B0%80-%EB%8B%AC%EB%9D%BC%EC%A1%8C%EC%96%B4%EC%9A%94",
    ]

    for url in test_urls:
        print(f"\n크롤링 URL: {url}")
        result = processor.process(url)

        if result.get("error"):
            print(f"Error: {result['error']}")
        else:
            print(f"Title: {result['title']}")
            print(f"Content (first 200 chars): {result['content'][:200]}...")
            if result.get("thumbnail_url"):
                print(f"Thumbnail: {result['thumbnail_url']}")
        print("-" * 60)


def test_with_summarizer():
    """크롤러 + Gemini 요약 통합 테스트"""
    print("\n" + "="*60)
    print("TEST 2: Tistory 크롤링 + Gemini 요약")
    print("="*60)

    processor = TistoryProcessor()
    summarizer = GeminiSummarizer()

    test_url = "https://realej.tistory.com/433"
    user_memo = None  # "맛집 리뷰 관점으로 분류해줘"  # 사용자 메모 (선택사항)

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


def test_another_tistory_url():
    """다른 Tistory URL 형식 테스트 (/entry/ 포함)"""
    print("\n" + "="*60)
    print("TEST 3: Tistory /entry/ 형식 URL 크롤링")
    print("="*60)

    processor = TistoryProcessor()

    test_url = "https://s2house.tistory.com/entry/%EC%86%90%EB%8B%98-%EC%98%AC-%EB%95%8C%EB%A7%88%EB%8B%A4-%EB%AF%BC%EB%A7%9D%ED%96%88%EB%8D%98-%EC%88%98%EC%A0%80%EC%84%B8%ED%8A%B8-%EC%9D%B4%EA%B1%B8%EB%A1%9C-%EB%B0%94%EA%BE%B8%EB%8B%88-%EC%8B%9D%ED%83%81-%EB%B6%84%EC%9C%84%EA%B8%B0%EA%B0%80-%EB%8B%AC%EB%9D%BC%EC%A1%8C%EC%96%B4%EC%9A%94"

    print(f"\n크롤링 URL: {test_url}")
    result = processor.process(test_url)

    if result.get("error"):
        print(f"Error: {result['error']}")
    else:
        print(f"Title: {result['title']}")
        print(f"Content (first 300 chars): {result['content'][:300]}...")
        if result.get("thumbnail_url"):
            print(f"Thumbnail: {result['thumbnail_url']}")


if __name__ == "__main__":
    print("Tistory 블로그 크롤링 및 요약 테스트 시작")
    print("Gemini API 키가 .env 파일에 설정되어 있는지 확인하세요!")

    # TEST 1: 크롤러만 테스트
    test_tistory_crawler()

    # TEST 2: 크롤러 + 요약 통합 테스트
    try:
        test_with_summarizer()
    except Exception as e:
        print(f"\n⚠️  요약 테스트 실패: {e}")
        print("Gemini API 키가 설정되어 있는지 확인하세요.")

    # TEST 3: 다른 Tistory URL 형식 테스트 (선택사항)
    # test_another_tistory_url()

    print("\n✅ 모든 테스트 완료!")
