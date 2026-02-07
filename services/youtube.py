import yt_dlp
from faster_whisper import WhisperModel
import os
import shutil
from youtube_transcript_api import YouTubeTranscriptApi

class YouTubeProcessor:
    def __init__(self, model_size="base"):
        """
        Faster Whisper 모델 초기화
        """
        print(f"--- 시스템 초기화: Faster Whisper {model_size} 모델 로드 중 ---")
        
        # 다운로드 폴더 생성
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        # 모델 로드 (CPU 최적화 설정)
        self.model = WhisperModel(
            model_size, 
            device="cpu", 
            compute_type="int8"
        )
        print(f"✅ Faster Whisper {model_size} 모델 로드 완료!")
        
        # [수정 1] FFmpeg 경로 명시 (환경 변수 문제 방지)
        ffmpeg_path = os.environ.get('FFMPEG_PATH') or shutil.which('ffmpeg')
        
        # [수정 2] yt-dlp 옵션 최적화
        self.ydl_opts = {
            'format': 'bestaudio/best',
            # 다운로드 폴더에 "영상ID.mp3"로 저장 (이름 중복 방지)
            'outtmpl': os.path.join(self.download_dir, '%(id)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'ffmpeg_location': ffmpeg_path, # 명시적 경로 설정
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None, # 쿠키 자동 감지
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'add_header': [
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: en-us,en;q=0.5',
            ],
            'no_continue': True, # 이어받기 금지 (오류 방지)
            'overwrites': True   # 덮어쓰기 허용
        }

    def _get_official_transcript(self, video_id):
        """유튜브 공식/자동 생성 자막 추출 시도"""
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_transcript(['ko', 'en'])
            data = transcript.fetch()
            return " ".join([item['text'] for item in data])
        except Exception:
            return None

    def process(self, url):
        try:
            # 1. 영상 정보 추출 (다운로드 X)
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                
                video_data = {
                    "title": info.get('title'),
                    "duration": info.get('duration'),
                    "description": info.get('description'),
                    "thumbnail_url": info.get('thumbnail'),
                    "channel": info.get('uploader'),
                    "video_id": video_id,
                }

                # 2. 공식 자막 우선 시도
                print(f"--- '{video_data['title']}' 공식 자막 확인 중 ---")
                official_text = self._get_official_transcript(video_id)

                if official_text:
                    print("✅ 공식 자막 추출 성공!")
                    video_data["transcript"] = official_text
                else:
                    # 3. 자막 없으면 Whisper 실행
                    print("⚠️ 공식 자막 없음/차단됨. Faster Whisper 음성 인식을 시작합니다...")
                    
                    # 오디오 다운로드 실행
                    ydl.download([url])
                    
                    # [수정 3] 파일 경로 동적 계산 (temp_audio.mp3 사용 안 함)
                    # yt-dlp는 다운로드 후 .mp3로 변환하므로 파일명 예측
                    filename = f"{video_id}.mp3"
                    file_path = os.path.join(self.download_dir, filename)
                    abs_file_path = os.path.abspath(file_path)

                    # 파일 존재 확인
                    if not os.path.exists(abs_file_path):
                        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {abs_file_path}")

                    # Faster Whisper transcribe
                    segments, info = self.model.transcribe(
                        abs_file_path, # 절대 경로 사용
                        language="ko",
                        beam_size=5,
                        vad_filter=True,
                    )
                    
                    transcript_text = " ".join([segment.text for segment in segments])
                    video_data["transcript"] = transcript_text
                    
                    # 사용 완료된 오디오 파일 삭제 (청소)
                    if os.path.exists(abs_file_path):
                        os.remove(abs_file_path)
                    
                    print(f"✅ 음성 인식 완료! (언어: {info.language}, 확률: {info.language_probability:.2f})")

                return video_data

        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    processor = YouTubeProcessor()
    # 테스트용 URL
    result = processor.process("https://www.youtube.com/watch?v=7nvUzO_-P0I")
    
    import pprint
    pprint.pprint(result)