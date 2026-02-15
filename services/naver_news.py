import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse
import re
import logging
import random
import time

logger = logging.getLogger(__name__)

# 실제 브라우저 User-Agent 목록 (최신 버전 기준)
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]

# 429 재시도 설정
_MAX_RETRIES = 3
_BASE_DELAY = 2  # 초


class NaverNewsProcessor:
    """
    네이버 뉴스 및 일반 웹 콘텐츠 크롤러
    
    네이버 뉴스는 특화된 파싱을 사용하고,
    일반 URL은 readability를 사용하여 본문 추출
    """
    
    def __init__(self):
        # Session 사용 — 쿠키 자동 관리 + 커넥션 재활용
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        })

    def _get_with_retry(self, url: str) -> requests.Response:
        """429 에러 시 exponential backoff로 재시도"""
        for attempt in range(_MAX_RETRIES + 1):
            # 매 요청마다 User-Agent 랜덤 교체
            self.session.headers["User-Agent"] = random.choice(_USER_AGENTS)
            # 네이버 뉴스에는 Referer 추가 (요청 단위)
            extra_headers = {}
            if "naver.com" in url:
                extra_headers["Referer"] = "https://search.naver.com/search.naver"

            response = self.session.get(url, timeout=15, headers=extra_headers)

            if response.status_code == 429:
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** attempt) + random.uniform(0, 1)
                    logger.warning(f"429 Too Many Requests, retrying in {delay:.1f}s (attempt {attempt + 1}/{_MAX_RETRIES})")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"429 Too Many Requests after {_MAX_RETRIES} retries: {url}")
                    response.raise_for_status()

            response.raise_for_status()
            return response

        # Should not reach here, but just in case
        raise requests.exceptions.RequestException("Max retries exceeded")

    def process(self, url: str) -> dict:
        """
        URL에서 콘텐츠를 크롤링하고 제목, 본문 추출
        
        Args:
            url: 크롤링할 URL
            
        Returns:
            dict: {
                "type": "NAVER_NEWS" or "GENERAL",
                "url": str,
                "title": str,
                "content": str,
                "thumbnail_url": str (선택사항)
            }
        """
        try:
            logger.info(f"Fetching content from: {url}")
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return {"type": "ERROR", "error": "Invalid URL scheme"}

            response = self._get_with_retry(url)
            response.encoding = 'utf-8'  # 명시적으로 UTF-8 인코딩 설정
            html = response.text
            
            # 네이버 뉴스인지 확인
            if "news.naver.com" in url or "n.news.naver.com" in url:
                return self._parse_naver_news(html, url)
            else:
                return self._parse_general(html, url)
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout while fetching {url}")
            return {
                "type": "ERROR",
                "url": url,
                "title": "Timeout Error",
                "content": "요청 시간이 초과되었습니다.",
                "error": "timeout"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return {
                "type": "ERROR",
                "url": url,
                "title": "Request Error",
                "content": f"콘텐츠를 가져올 수 없습니다: {str(e)}",
                "error": str(e)
            }
        except Exception as e:
            logger.exception(f"Unexpected error processing {url}")
            return {
                "type": "ERROR",
                "url": url,
                "title": "Processing Error",
                "content": f"처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e)
            }
    
    def _parse_naver_news(self, html: str, url: str) -> dict:
        """네이버 뉴스 전용 파서"""
        soup = BeautifulSoup(html, "html.parser")
        
        # 제목 추출
        title_tag = soup.select_one("#title_area span") or soup.select_one("h2#title_area")
        title = title_tag.text.strip() if title_tag else "제목 없음"
        
        # 썸네일 추출 (향상된 로직)
        thumbnail_url = None
        
        # 1. Open Graph 이미지 (가장 확실함)
        og_image = soup.select_one("meta[property='og:image']")
        if og_image and og_image.get("content"):
            thumbnail_url = og_image.get("content")
            
        # 2. 본문 내 첫 번째 이미지 (HTML 구조 기반)
        if not thumbnail_url:
            # 사용자가 제공한 구조: #img1 (lazy loading 고려 data-src 확인)
            img_tag = soup.select_one("#img1") 
            if img_tag:
                 thumbnail_url = img_tag.get("data-src") or img_tag.get("src")
        
        # 3. .end_photo_org 내부 이미지
        if not thumbnail_url:
            img_tag = soup.select_one(".end_photo_org img")
            if img_tag:
                thumbnail_url = img_tag.get("data-src") or img_tag.get("src")

        # 4. 일반적인 본문 이미지 (fallback)
        if not thumbnail_url:
            img_tag = soup.select_one("#dic_area img") or soup.select_one("article img")
            if img_tag:
                thumbnail_url = img_tag.get("data-src") or img_tag.get("src")
        
        # 본문 추출
        content_area = soup.select_one("#dic_area") or soup.select_one("article#dic_area")
        
        if content_area:
            # 불필요한 태그 제거 (이미지 설명, 광고 등)
            for tag in content_area.select(".end_photo_org, .img_desc, .nbd_im_w, "
                                          "script, iframe, style, .ad_area"):
                tag.decompose()
            
            # 텍스트 추출 및 정리
            text = content_area.get_text("\n")
            content = re.sub(r'\n+', '\n', text).strip()
            content = re.sub(r' +', ' ', content)  # 연속 공백 제거
        else:
            content = "본문을 찾을 수 없습니다."
            logger.warning(f"Content area not found for {url}")
        
        return {
            "type": "NAVER_NEWS",
            "url": url,
            "title": title,
            "content": content,
            "thumbnail_url": thumbnail_url
        }
    
    def _parse_general(self, html: str, url: str) -> dict:
        """일반 웹페이지 파서 (readability 사용)"""
        try:
            doc = Document(html)
            title = doc.title()
            summary_html = doc.summary()
            
            # HTML을 텍스트로 변환
            soup = BeautifulSoup(summary_html, "html.parser")
            
            # 썸네일 추출 (첫 번째 이미지)
            thumbnail_url = None
            img_tag = soup.find("img")
            if img_tag and img_tag.get("src"):
                thumbnail_url = img_tag.get("src")
            
            # 텍스트 추출 및 정리
            text = soup.get_text("\n")
            content = re.sub(r'\n+', '\n', text).strip()
            content = re.sub(r' +', ' ', content)
            
            return {
                "type": "GENERAL",
                "url": url,
                "title": title,
                "content": content,
                "thumbnail_url": thumbnail_url
            }
        except Exception as e:
            logger.exception(f"Readability parsing failed for {url}")
            return {
                "type": "ERROR",
                "url": url,
                "title": "Parse Error",
                "content": f"본문 추출 실패: {str(e)}",
                "error": str(e)
            }


if __name__ == "__main__":
    # 테스트 코드
    processor = NaverNewsProcessor()
    
    # 네이버 뉴스 예시
    test_url = "https://n.news.naver.com/article/421/0008745941?cds=news_media_pc&type=editn"
    result = processor.process(test_url)
    
    print(f"Type: {result['type']}")
    print(f"Title: {result['title']}")
    print(f"Content (first 500 chars): {result['content'][:500]}...")
    if result.get('thumbnail_url'):
        print(f"Thumbnail: {result['thumbnail_url']}")
