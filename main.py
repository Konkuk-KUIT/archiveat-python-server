import asyncio # [추가] 비동기 처리를 위한 모듈
import os
import logging
import sys

# 로깅 설정
# Uvicorn 실행 시 로그가 보이지 않는 문제 해결을 위해 stdout 핸들러 명시적 추가
# 루트 로커에 핸들러를 추가하여 services 등 모든 모듈의 로그가 출력되도록 함
# root_logger = logging.getLogger()
# root_logger.setLevel(logging.INFO)

# # 기본 핸들러가 없을 경우에만 추가 (중복 방지)
# if not root_logger.handlers:
#     handler = logging.StreamHandler(sys.stdout)
#     handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
#     root_logger.addHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True
)

logger = logging.getLogger(__name__)

def setup_cookies():
    """GitHub Secrets에서 전달된 COOKIES_TXT 환경변수를 파일로 저장합니다."""
    cookies_content = os.getenv("COOKIES_TXT")
    
    # 현재 작업 디렉토리 기준 절대 경로 설정
    cookie_path = os.path.join(os.getcwd(), "cookies.txt")
    
    if cookies_content:
        logger.info(f"🍪 COOKIES_TXT environment variable found. Length: {len(cookies_content)}")
        try:
            with open(cookie_path, "w", encoding="utf-8") as f:
                f.write(cookies_content)
            logger.info(f"✅ Created cookies.txt from environment variable at: {cookie_path}")
            
            # 파일 내용 앞부분만 살짝 찍어서 확인
            with open(cookie_path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
                logger.info(f"   First line of cookies.txt: {first_line[:50]}...")
                
        except Exception as e:
            logger.error(f"❌ Failed to create cookies.txt: {e}")
    else:
        logger.warning("⚠️ COOKIES_TXT environment variable is missing. YouTube processing might fail.")

# [수정 3] 서비스 임포트 및 초기화 전에 쿠키 설정을 먼저 실행!!
setup_cookies()


from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    SummarizeYoutubeRequest,
    SummarizeGenericRequest,
    SummarizeNaverNewsRequest,
    SummarizeTistoryRequest,
    PythonSummaryResponse,
    HealthResponse,
    VideoInfo,
    ArticleInfo,
    Analysis,
    NewsletterSummaryBlock
)
from services.youtube import YouTubeProcessor
from services.summarizer import GeminiSummarizer
from services.naver_news import NaverNewsProcessor
from services.tistory import TistoryProcessor

# 외부 라이브러리(httpx 등) 로그가 너무 시끄러우면 레벨 조정
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(
    title="Archiveat Python Server",
    description="LLM-powered content summarization service using Gemini AI",
    version="1.0.0"
)

# CORS 설정 - Java 서버에서 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000", "http://127.0.0.1:8000", "http://localhost:8000"],  # 프로덕션에서는 구체적인 origin 지정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
# Whisper tiny 모델: 가장 빠른 음성 인식 (정확도는 낮지만 속도 우선)
yt_processor = YouTubeProcessor(model_size="tiny")
summarizer = GeminiSummarizer()
naver_processor = NaverNewsProcessor()
tistory_processor = TistoryProcessor()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """헬스체크 엔드포인트"""
    return HealthResponse(
        status="healthy",
        message="Python server is running"
    )


@app.post("/api/v1/summarize/youtube", response_model=PythonSummaryResponse)
async def summarize_youtube(request: SummarizeYoutubeRequest):
    """
    YouTube URL을 받아 영상 정보 추출 및 LLM 요약 수행
    
    처리 시간: 약 5-10초
    - YouTube 데이터 추출: 2-3초
    - Gemini LLM 요약: 3-7초
    """
    logger.info(f"Received YouTube summarization request: {request.url}")
    
    try:
        # 1. YouTube 데이터 추출 (Blocking -> Non-blocking)
        logger.info("Extracting YouTube data...")
        # [수정] 동기 함수인 yt_processor.process를 별도 스레드에서 실행
        video_data = await asyncio.to_thread(yt_processor.process, request.url)
        
        if "error" in video_data:
            logger.error(f"YouTube processing error: {video_data['error']}")
            raise HTTPException(status_code=400, detail=video_data["error"])
        
        # 2. Gemini AI 분석 및 요약 (Blocking -> Non-blocking)
        logger.info("Starting Gemini AI analysis...")
        # [수정] 동기 함수인 summarizer.summarize_content를 별도 스레드에서 실행
        analysis_result = await asyncio.to_thread(
            summarizer.summarize_content,
            video_data["title"],
            (video_data.get("description") or "") + "\n" + (video_data.get("transcript") or "")
        )
        
        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")
        
        # 3. 응답 데이터 구성
        video_info = VideoInfo(
            title=video_data["title"],
            thumbnail_url=video_data["thumbnail_url"],
            content_url=request.url,
            channel=video_data["channel"],
            duration=video_data["duration"]
        )
        
        # ... (생략) ...
        
        # newsletter_summary를 Pydantic 모델로 변환
        newsletter_blocks = [
            NewsletterSummaryBlock(title=block.get("title", ""), content=block.get("content", ""))
            for block in analysis_result.get("newsletter_summary", [])
            if isinstance(block, dict)
        ]
        
        analysis = Analysis(
            category=analysis_result.get("category", "기타"),
            topic=analysis_result.get("topic", "기타"),
            small_card_summary=analysis_result.get("small_card_summary", ""),
            medium_card_summary=analysis_result.get("medium_card_summary", ""),
            newsletter_summary=newsletter_blocks
        )
        
        response = PythonSummaryResponse(
            video_info=video_info,
            analysis=analysis
        )
        
        logger.info(f"Successfully processed YouTube URL: {request.url}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing YouTube URL: {request.url}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/summarize/generic", response_model=PythonSummaryResponse)
async def summarize_generic(request: SummarizeGenericRequest):
    """
    일반 텍스트 콘텐츠 요약 (향후 확장용)
    """
    logger.info(f"Received generic summarization request: {request.title}")
    
    try:
        # Gemini AI 분석 (Blocking -> Non-blocking)
        # [수정] 별도 스레드 실행
        analysis_result = await asyncio.to_thread(
            summarizer.summarize_content,
            request.title,
            request.content
        )
        
        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")
        
        # ... (생략) ...
        
        # newsletter_summary를 Pydantic 모델로 변환
        newsletter_blocks = [
            NewsletterSummaryBlock(title=block["title"], content=block["content"])
            for block in analysis_result.get("newsletter_summary", [])
        ]
        
        analysis = Analysis(
            category=analysis_result.get("category", "기타"),
            topic=analysis_result.get("topic", "기타"),
            small_card_summary=analysis_result.get("small_card_summary", ""),
            medium_card_summary=analysis_result.get("medium_card_summary", ""),
            newsletter_summary=newsletter_blocks
        )
        
        response = PythonSummaryResponse(
            video_info=None,
            analysis=analysis
        )
        
        logger.info(f"Successfully processed generic content: {request.title}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing generic content: {request.title}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/summarize/naver-news", response_model=PythonSummaryResponse)
async def summarize_naver_news(request: SummarizeNaverNewsRequest):
    """
    네이버 뉴스 또는 일반 웹 콘텐츠 요약
    """
    logger.info(f"Received Naver news summarization request: {request.url}")
    
    try:
        # 1. 웹 크롤링 (Blocking -> Non-blocking)
        logger.info("Crawling web content...")
        # [수정] 별도 스레드 실행
        crawl_result = await asyncio.to_thread(naver_processor.process, request.url)
        
        if crawl_result.get("error"):
            logger.error(f"Crawling error: {crawl_result['error']}")
            raise HTTPException(status_code=400, detail=f"Crawling failed: {crawl_result['error']}")
        
        # 2. Gemini AI 분석 및 요약 (Blocking -> Non-blocking)
        logger.info("Starting Gemini AI analysis...")
        
        content_with_memo = crawl_result["content"]
        if request.user_memo:
            content_with_memo = f"[사용자 메모: {request.user_memo}]\n\n{content_with_memo}"
            logger.info(f"User memo provided: {request.user_memo}")
        
        # [수정] 별도 스레드 실행
        analysis_result = await asyncio.to_thread(
            summarizer.summarize_content,
            crawl_result["title"],
            content_with_memo
        )
        
        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")
        
        # ... (생략) ...
        
        # newsletter_summary를 Pydantic 모델로 변환
        newsletter_blocks = [
            NewsletterSummaryBlock(title=block["title"], content=block["content"])
            for block in analysis_result.get("newsletter_summary", [])
        ]
        
        analysis = Analysis(
            category=analysis_result.get("category", "기타"),
            topic=analysis_result.get("topic", "기타"),
            small_card_summary=analysis_result.get("small_card_summary", ""),
            medium_card_summary=analysis_result.get("medium_card_summary", ""),
            newsletter_summary=newsletter_blocks
        )
        
        # article_info 구성
        article_info = ArticleInfo(
            title=crawl_result["title"],
            thumbnail_url=crawl_result.get("thumbnail_url"),
            content_url=request.url,
            word_count=len(crawl_result["content"])
        )
        
        response = PythonSummaryResponse(
            video_info=None,
            article_info=article_info,
            analysis=analysis
        )
        
        logger.info(f"Successfully processed Naver news: {request.url}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing Naver news: {request.url}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/summarize/tistory", response_model=PythonSummaryResponse)
async def summarize_tistory(request: SummarizeTistoryRequest):
    """
    Tistory 블로그 URL을 받아 본문을 긁어오고 Gemini AI로 요약하여 응답
    """
    logger.info(f"Received Tistory summarization request: {request.url}")

    try:
        # 1. Tistory 크롤링 (Blocking -> Non-blocking)
        logger.info("Crawling Tistory content...")
        # [수정] 별도 스레드 실행
        crawl_result = await asyncio.to_thread(tistory_processor.process, request.url)

        if crawl_result.get("error"):
            logger.error(f"Tistory crawling error: {crawl_result['error']}")
            raise HTTPException(status_code=400, detail=f"Crawling failed: {crawl_result['error']}")

        # 2. Gemini AI 분석 및 요약 (Blocking -> Non-blocking)
        logger.info("Starting Gemini AI analysis...")

        content_with_memo = crawl_result["content"]
        if request.user_memo:
            content_with_memo = f"[사용자 메모: {request.user_memo}]\n\n{content_with_memo}"
            logger.info(f"User memo provided: {request.user_memo}")

        # [수정] 별도 스레드 실행
        analysis_result = await asyncio.to_thread(
            summarizer.summarize_content,
            crawl_result["title"],
            content_with_memo
        )

        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")

        # ... (생략) ...

        # 3. 응답 데이터 구성
        newsletter_blocks = [
            NewsletterSummaryBlock(title=block["title"], content=block["content"])
            for block in analysis_result.get("newsletter_summary", [])
        ]

        analysis = Analysis(
            category=analysis_result.get("category", "기타"),
            topic=analysis_result.get("topic", "기타"),
            small_card_summary=analysis_result.get("small_card_summary", ""),
            medium_card_summary=analysis_result.get("medium_card_summary", ""),
            newsletter_summary=newsletter_blocks
        )

        article_info = ArticleInfo(
            title=crawl_result["title"],
            thumbnail_url=crawl_result.get("thumbnail_url"),
            content_url=request.url,
            word_count=len(crawl_result["content"]),
        )

        response = PythonSummaryResponse(
            video_info=None,
            article_info=article_info,
            analysis=analysis
        )

        logger.info(f"Successfully processed Tistory: {request.url}")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing Tistory: {request.url}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=None)
