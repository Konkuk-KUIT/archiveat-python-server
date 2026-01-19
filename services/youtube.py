import yt_dlp
import whisper
import os
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeProcessor:
    def __init__(self, model_size="base"):
        print(f"--- 시스템 초기화: Whisper {model_size} 모델 로드 중 ---")
        self.model = whisper.load_model(model_size)
        
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': 'temp_audio.%(ext)s',
            'quiet': True,
            'no_warnings': True,
        }

    def _get_official_transcript(self, video_id):
        """[1순위] 유튜브 공식/자동 생성 자막 추출 시도"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            # 한국어, 영어 등 가능한 모든 언어 중 가장 적절한 것을 선택
            transcript = transcript_list.find_transcript(['ko', 'en'])
            data = transcript.fetch()
            return " ".join([item['text'] for item in data])
        except Exception:
            # 자막이 없거나 차단된 경우 None 반환
            return None

    def process(self, url):
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False) # 일단 정보만 먼저 추출
                video_id = info.get('id')
                
                video_data = {
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "description": info.get('description'),
                    "thumbnail_url": info.get('thumbnail'),
                    "channel": info.get('uploader'),
                    "video_id": video_id,
                }

                # [Insight] 1순위: 공식 자막 시도
                print(f"--- '{video_data['title']}' 공식 자막 확인 중 ---")
                official_text = self._get_official_transcript(video_id)

                if official_text:
                    print("✅ 공식 자막 추출 성공!")
                    video_data["transcript"] = official_text
                else:
                    # [Insight] 2순위: 공식 자막 실패 시 Whisper(음성 인식) 실행
                    print("⚠️ 공식 자막 없음/차단됨. Whisper 음성 인식을 시작합니다...")
                    ydl.download([url]) # 오디오 다운로드 실행
                    result = self.model.transcribe("temp_audio.mp3", fp16=False)
                    video_data["transcript"] = result['text']
                    
                    if os.path.exists("temp_audio.mp3"):
                        os.remove("temp_audio.mp3")
                    print("✅ 음성 인식 완료!")

                return video_data

        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    processor = YouTubeProcessor()
    # 1. 자막이 있는 영상으로 먼저 테스트해보세요.
    result = processor.process("https://www.youtube.com/watch?v=7nvUzO_-P0I")
    
    import pprint
    pprint.pprint(result)