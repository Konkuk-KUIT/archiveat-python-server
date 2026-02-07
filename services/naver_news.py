import requests
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)


class NaverNewsProcessor:
    """
    네이버 뉴스 및 일반 웹 콘텐츠 크롤러
    
    네이버 뉴스는 특화된 파싱을 사용하고,
    일반 URL은 readability를 사용하여 본문 추출
    """
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
    
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

            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
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
        
        # 썸네일 추출 (첫 번째 이미지)
        thumbnail_url = None
        img_tag = soup.select_one("#img1") or soup.select_one("article img")
        if img_tag and img_tag.get("src"):
            thumbnail_url = img_tag.get("src")
        
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
