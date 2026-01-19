import yt_dlp
import os

def download_audio_only(url):
    # [Insight] Whisper는 영상이 필요 없습니다. 
    # 오디오만 받으면 용량이 1/10로 줄어들어 처리 속도가 비약적으로 빨라집니다.
    ydl_opts = {
        'format': 'bestaudio/best',  # 가장 좋은 음질의 오디오를 선택
        'postprocessors': [{         # 다운로드 후 수행할 작업 설정
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',  # 파일 형식을 mp3로 변환
            'preferredquality': '192', # 음질 설정
        }],
        'outtmpl': 'downloaded_audio.%(ext)s', # 저장될 파일 이름 규칙
        'quiet': False,               # 진행 상황을 보기 위해 False로 설정
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"--- 오디오 추출 시작: {url} ---")
            ydl.download([url])
            print(f"✅ 추출 완료: downloaded_audio.mp3")
            return "downloaded_audio.mp3"
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        return None

if __name__ == "__main__":
    # test
    test_url = "https://www.youtube.com/watch?v=BboE9i7TwzM"
    download_audio_only(test_url)