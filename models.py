from pydantic import BaseModel, HttpUrl
from typing import List, Optional


# Request Models
class SummarizeYoutubeRequest(BaseModel):
    url: str


class SummarizeGenericRequest(BaseModel):
    title: str
    content: str


class SummarizeNaverNewsRequest(BaseModel):
    url: str
    user_memo: Optional[str] = None  # 사용자 메모 (분류 우선순위에 활용)


class SummarizeTistoryRequest(BaseModel):
    url: str
    user_memo: Optional[str] = None  # 사용자 메모 (분류 우선순위에 활용)


class SummarizeCollectionRequest(BaseModel):
    # 각 뉴스레터의 제목과 요약(small_card_summary 등)을 리스트로 전달받음
    newsletters: List[str] 


class CollectionSummaryResponse(BaseModel):
    small_card_summary: str
    medium_card_summary: str


# Response Models
class VideoInfo(BaseModel):
    title: str
    thumbnail_url: str
    content_url: str
    channel: str
    duration: int  # 초 단위


class ArticleInfo(BaseModel):
    title: str
    thumbnail_url: Optional[str] = None
    content_url: str
    word_count: int  # 글자 수


class NewsletterSummaryBlock(BaseModel):
    title: str
    content: str


class Analysis(BaseModel):
    category: str
    topic: str
    small_card_summary: str
    medium_card_summary: str
    newsletter_summary: List[NewsletterSummaryBlock]


class PythonSummaryResponse(BaseModel):
    video_info: Optional[VideoInfo] = None
    article_info: Optional[ArticleInfo] = None
    analysis: Analysis


class HealthResponse(BaseModel):
    status: str
    message: str
