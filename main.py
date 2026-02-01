from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import (
    SummarizeYoutubeRequest,
    SummarizeGenericRequest,
    SummarizeNaverNewsRequest,
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
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Archiveat Python Server",
    description="LLM-powered content summarization service using Gemini AI",
    version="1.0.0"
)

# CORS 설정 - Java 서버에서 호출 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],  # 프로덕션에서는 구체적인 origin 지정 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 서비스 초기화
# Whisper tiny 모델: 가장 빠른 음성 인식 (정확도는 낮지만 속도 우선)
yt_processor = YouTubeProcessor(model_size="tiny")
summarizer = GeminiSummarizer()
naver_processor = NaverNewsProcessor()


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
        # 1. YouTube 데이터 추출
        logger.info("Extracting YouTube data...")
        video_data = yt_processor.process(request.url)
        
        if "error" in video_data:
            logger.error(f"YouTube processing error: {video_data['error']}")
            raise HTTPException(status_code=400, detail=video_data["error"])
        
        # 2. Gemini AI 분석 및 요약
        logger.info("Starting Gemini AI analysis...")
        analysis_result = summarizer.summarize_content(
            video_data["title"],
            video_data["description"] + "\n" + video_data["transcript"]
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
    
    YouTube가 아닌 블로그, 기사 등의 텍스트 콘텐츠 처리
    """
    logger.info(f"Received generic summarization request: {request.title}")
    
    try:
        # Gemini AI 분석
        analysis_result = summarizer.summarize_content(
            request.title,
            request.content
        )
        
        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")
        
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
            video_info=None,  # 일반 텍스트는 video_info 없음
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
    
    처리 시간: 약 5-10초
    - 웹 크롤링: 2-3초
    - Gemini LLM 요약: 3-7초
    
    사용자 메모를 활용하여 콘텐츠를 분류하고 요약합니다.
    메모가 있으면 본문보다 메모의 의도를 우선시하여 카테고리/토픽을 결정합니다.
    """
    logger.info(f"Received Naver news summarization request: {request.url}")
    
    try:
        # 1. 웹 크롤링 (네이버 뉴스 또는 일반 웹)
        logger.info("Crawling web content...")
        crawl_result = naver_processor.process(request.url)
        
        if crawl_result.get("error"):
            logger.error(f"Crawling error: {crawl_result['error']}")
            raise HTTPException(status_code=400, detail=f"Crawling failed: {crawl_result['error']}")
        
        # 2. Gemini AI 분석 및 요약
        logger.info("Starting Gemini AI analysis...")
        
        # 사용자 메모가 있으면 본문 앞에 추가하여 분류에 활용
        content_with_memo = crawl_result["content"]
        if request.user_memo:
            content_with_memo = f"[사용자 메모: {request.user_memo}]\n\n{content_with_memo}"
            logger.info(f"User memo provided: {request.user_memo}")
        
        analysis_result = summarizer.summarize_content(
            crawl_result["title"],
            content_with_memo
        )
        
        if "error" in analysis_result:
            logger.error(f"Gemini analysis error: {analysis_result['error']}")
            raise HTTPException(status_code=500, detail=f"LLM analysis failed: {analysis_result['error']}")
        
        # 3. 응답 데이터 구성
        # video_info는 None (뉴스/웹 콘텐츠는 영상이 아님)
        
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
        
        # article_info 구성 (Naver News/일반 웹용)
        article_info = ArticleInfo(
            title=crawl_result["title"],
            thumbnail_url=crawl_result.get("thumbnail_url"),
            content_url=request.url,
            word_count=len(crawl_result["content"])  # 글자 수 계산
        )
        
        response = PythonSummaryResponse(
            video_info=None,  # 뉴스/웹 콘텐츠는 video_info 없음
            article_info=article_info,  # article_info 추가!
            analysis=analysis
        )
        
        logger.info(f"Successfully processed Naver news: {request.url}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing Naver news: {request.url}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
