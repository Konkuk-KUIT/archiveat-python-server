# Python Server API Reference

> **Base URL**: `http://localhost:8000`

Java 서버와 Python 서버 간 내부 통신용 API 문서입니다.

---

## 📋 목차

- [Health Check](#health-check)
- [YouTube 요약 API](#youtube-요약-api)
- [Naver News 요약 API](#naver-news-요약-api)
- [공통 응답 형식](#공통-응답-형식)
- [자동 생성 문서](#자동-생성-문서)

---

## Health Check

서버 상태 확인용 엔드포인트

### `GET /health`

**Response**
```json
{
  "status": "healthy",
  "message": "Python server is running"
}
```

---

## YouTube 요약 API

YouTube 영상의 자막/음성을 추출하고 Gemini AI로 요약 및 분류

### `POST /api/v1/summarize/youtube`

**Request Body**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID"
}
```

**Response**
```json
{
  "video_info": {
    "title": "영상 제목",
    "thumbnail_url": "https://i.ytimg.com/vi/VIDEO_ID/maxresdefault.webp",
    "content_url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "channel": "채널명",
    "duration": 720
  },
  "analysis": {
    "category": "IT/과학",
    "topic": "인공지능",
    "small_card_summary": "20자 내외 한 줄 요약",
    "medium_card_summary": "2~3문장으로 핵심 내용 요약",
    "newsletter_summary": [
      {
        "title": "소제목1",
        "content": "문단 내용1"
      },
      {
        "title": "소제목2",
        "content": "문단 내용2"
      },
      {
        "title": "소제목3",
        "content": "문단 내용3"
      }
    ]
  }
}
```

**처리 시간**: 약 2-3분
- 자막 추출/음성 인식: 30초 ~ 2분
- Gemini AI 분석: 3-7초

**자막 처리 우선순위**
1. **공식 자막** (한국어/영어) - 가장 빠름
2. **Faster Whisper STT** - 자막 없을 때 음성 인식

---

## Naver News 요약 API

네이버 뉴스 및 일반 웹 콘텐츠를 크롤링하고 Gemini AI로 요약 및 분류

### `POST /api/v1/summarize/naver-news`

**Request Body**
```json
{
  "url": "https://n.news.naver.com/mnews/article/629/0000461258",
  "user_memo": "삼성전자"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | ✅ | 크롤링할 URL (네이버 뉴스, 티스토리, 브런치, 일반 웹) |
| `user_memo` | string | ❌ | 사용자 메모 (분류 우선순위에 활용) |

**Response**
```json
{
  "article_info": {
    "title": "기사 제목",
    "thumbnail_url": "https://example.com/image.jpg",
    "content_url": "https://n.news.naver.com/...",
    "word_count": 2847
  },
  "analysis": {
    "category": "경제",
    "topic": "주식/투자",
    "small_card_summary": "20자 내외 한 줄 요약",
    "medium_card_summary": "2~3문장으로 핵심 내용 요약",
    "newsletter_summary": [
      {
        "title": "소제목1",
        "content": "문단 내용1"
      },
      {
        "title": "소제목2",
        "content": "문단 내용2"
      },
      {
        "title": "소제목3",
        "content": "문단 내용3"
      }
    ]
  }
}
```

**처리 시간**: 약 10-15초
- 웹 크롤링: 1-3초
- Gemini AI 분석: 5-10초

**지원 도메인**
- ✅ 네이버 뉴스 (`news.naver.com`, `n.news.naver.com`)
- ✅ 티스토리 (`*.tistory.com`)
- ✅ 브런치 (`brunch.co.kr`)
- ✅ 일반 웹사이트 (readability 방식)

---

## 공통 응답 형식

### `video_info` vs `article_info`

| Field | YouTube | Naver News |
|-------|---------|------------|
| `video_info` | ✅ 있음 | ❌ `null` |
| `article_info` | ❌ `null` | ✅ 있음 |
| `analysis` | ✅ 공통 | ✅ 공통 |

### 카테고리 & 토픽 분류

**카테고리 5개**
- `IT/과학`, `국제`, `경제`, `문화`, `생활`

**토픽 (카테고리별)**

| 카테고리 | 토픽 |
|---------|------|
| **IT/과학** | 인공지능, 백엔드/인프라, 프론트/모바일, 데이터/보안, 테크 트렌드, 기타 |
| **국제** | 지정학/외교, 미국/중국, 글로벌 비즈니스, 기후/에너지, 기타 |
| **경제** | 주식/투자, 부동산, 가상 화폐, 창업/스타트업, 브랜드/마케팅, 거시경제, 기타 |
| **문화** | 영화/OTT, 음악, 도서/아티클, 팝컬쳐/트렌드, 공간/플레이스, 디자인/예술, 기타 |
| **생활** | 주니어/취업, 업무 생산성, 리더십/조직, 심리/마인드, 건강/리빙, 기타 |

### 요약 구조

```typescript
{
  small_card_summary: string;      // 20자 내외 한 줄 요약
  medium_card_summary: string;     // 2~3문장 요약
  newsletter_summary: [            // 3개의 상세 요약 블록
    { title: string, content: string },
    { title: string, content: string },
    { title: string, content: string }
  ]
}
```

---

## 에러 응답

**HTTP 400 Bad Request**
```json
{
  "detail": "Crawling failed: timeout"
}
```

**HTTP 500 Internal Server Error**
```json
{
  "detail": "LLM analysis failed: API quota exceeded"
}
```

---

## 자동 생성 문서

FastAPI 자동 생성 문서 (Python 서버 실행 중일 때):

### **Swagger UI** (대화형)
```
http://localhost:8000/docs
```
- "Try it out" 버튼으로 실시간 테스트 가능
- Request/Response 스키마 자동 표시

### **ReDoc** (읽기 전용)
```
http://localhost:8000/redoc
```
- 깔끔한 읽기 전용 문서
- PDF 출력에 적합

### **OpenAPI JSON**
```
http://localhost:8000/openapi.json
```
- OpenAPI 3.0 스펙
- Postman, Insomnia 등에 import 가능

---

## 사용 예시

### cURL

**YouTube 요약**
```bash
curl -X POST http://localhost:8000/api/v1/summarize/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

**Naver News 요약**
```bash
curl -X POST http://localhost:8000/api/v1/summarize/naver-news \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://n.news.naver.com/mnews/article/629/0000461258",
    "user_memo": "삼성전자"
  }'
```

### Java (WebClient)

```java
// YouTube 요약
pythonClientService.requestYouTubeSummary(contentUrl)
    .thenAccept(response -> {
        System.out.println("Title: " + response.getVideoInfo().getTitle());
        System.out.println("Category: " + response.getAnalysis().getCategoryName());
    });

// Naver News 요약
pythonClientService.requestNaverNewsSummary(contentUrl, userMemo)
    .thenAccept(response -> {
        System.out.println("Title: " + response.getArticleInfo().getTitle());
        System.out.println("Word Count: " + response.getArticleInfo().getWordCount());
    });
```

---

## 기술 스택

- **FastAPI** v0.115.6 - 웹 프레임워크
- **Gemini AI** (flash-latest) - LLM 분석
- **Faster Whisper** (tiny) - YouTube STT
- **BeautifulSoup4** - 웹 크롤링
- **yt-dlp** - YouTube 데이터 추출

---

## 참고 문서

- [Naver News 크롤링 가이드](NAVER_NEWS_GUIDE.md)
- [도메인 분류 가이드](../archiveat-java-server/DOMAIN_CLASSIFICATION_GUIDE.md)
