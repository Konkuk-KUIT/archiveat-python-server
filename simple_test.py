from services.naver_news import NaverNewsProcessor

processor = NaverNewsProcessor()
result = processor.process("https://n.news.naver.com/mnews/article/629/0000461258")

print(f"Type: {result['type']}")
print(f"Title: {result['title']}")
print(f"Content (first 300 chars): {result['content'][:300]}...")
if result.get('thumbnail_url'):
    print(f"Thumbnail: {result['thumbnail_url']}")
if result.get('error'):
    print(f"Error: {result['error']}")
