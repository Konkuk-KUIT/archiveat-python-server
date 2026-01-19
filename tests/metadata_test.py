import yt_dlp

def get_youtube_metadata(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

        # [Insight] 'description' 필드가 바로 '더보기'란의 전체 텍스트입니다.
        metadata = {
            "title": info.get('title'),
            "thumbnail": info.get('thumbnail'),
            "duration": info.get('duration'),
            "description": info.get('description') # <-- 추가된 부분
        }
        return metadata

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=BboE9i7TwzM"
    data = get_youtube_metadata(test_url)
    
    print(f"✅ 제목: {data['title']}")
    print(f"✅ 재생 시간: {data['duration']}초")
    print("-" * 30)
    print(f"✅ 영상 설명(앞부분): \n{data['description'][:200]}...")