"""
Tistory 블로그 크롤러
- Tistory URL에서 og:title, og:description, og:image, article:published_time 추출
- 본문은 div.entry-content, div.contents_style 등에서 추출
"""
import urllib.request
import re
import html
import logging

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---- utils ----
_ESCAPE_RE = re.compile(r"\\([\\\"'abfnrtv])")
_ESCAPE_MAP = {
    "\\": "\\",
    '"': '"',
    "'": "'",
    "a": "\a",
    "b": "\b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
}


def remove_escape(text: str) -> str:
    if text is None:
        return ""

    # HTML entity만 우선 처리 (&amp; -> &)
    s = html.unescape(text)

    # \n, \t 같은 "백슬래시 이스케이프"가 실제로 있을 때만 처리
    if "\\" in s:
        def _repl(m):
            ch = m.group(1)
            return _ESCAPE_MAP.get(ch, m.group(0))
        s = _ESCAPE_RE.sub(_repl, s)

    # unicode_escape 디코딩은 기본적으로 하지 말자 (한글 깨짐 유발 가능)
    if "\\u" in s or "\\x" in s:
        try:
            s = s.encode("utf-8").decode("unicode_escape")
        except Exception:
            pass

    return s


class TistoryProcessor:
    """
    Tistory 블로그 전용 크롤러
    링크를 받아 본문을 추출하고, 기존 응답 형식(article_info + analysis)에 맞게 반환
    """

    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                     "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

    def process(self, url: str) -> dict:
        """
        Tistory URL에서 메타 정보와 본문 추출

        Returns:
            dict: {
                "title": str,
                "content": str,
                "thumbnail_url": str (선택),
                "description": str (선택),
                "published_time": str (선택),
                "error": str (에러 시만)
            }
        """
        try:
            logger.info(f"Fetching Tistory content from: {url}")

            req = urllib.request.Request(url, headers=self.headers)
            resp = urllib.request.urlopen(req, timeout=10)
            raw = resp.read()

            charset = resp.headers.get_content_charset() or "utf-8"
            html_text = raw.decode(charset, errors="replace")
            soup = BeautifulSoup(html_text, "html.parser")

            # 메타 정보 추출
            title = self._get_meta_content(soup, "og:title")
            description = self._get_meta_content(soup, "og:description")
            thumbnail_url = self._get_meta_content(soup, "og:image")
            published_time = self._get_meta_content(soup, "article:published_time")

            # 본문 추출 (Tistory 레이아웃 다양성 대응)
            content = self._extract_content(soup)

            if not content:
                logger.warning(f"Content area not found for {url}")

            return {
                "title": title or "제목 없음",
                "content": content or "본문을 찾을 수 없습니다.",
                "thumbnail_url": thumbnail_url or None,
                "description": description or "",
                "published_time": published_time or "",
            }

        except urllib.error.URLError as e:
            logger.error(f"URL error for {url}: {e}")
            return {
                "title": "",
                "content": "",
                "thumbnail_url": None,
                "error": str(e.reason) if hasattr(e, "reason") else str(e),
            }
        except Exception as e:
            logger.exception(f"Unexpected error processing Tistory {url}")
            return {
                "title": "",
                "content": "",
                "thumbnail_url": None,
                "error": str(e),
            }

    def _get_meta_content(self, soup: BeautifulSoup, property_name: str) -> str:
        """meta property에서 content 추출"""
        tag = soup.find("meta", property=property_name)
        return tag["content"] if tag and tag.has_attr("content") else ""

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Tistory 본문 영역 추출 (여러 레이아웃 대응)"""
        node = (
            soup.select_one("div.entry-content")
            or soup.select_one("div.contents_style")
            or soup.select_one("div.article_view")
            or soup.select_one("article")
        )
        if node is None:
            return ""
        return remove_escape(node.get_text(separator="\n", strip=True))
