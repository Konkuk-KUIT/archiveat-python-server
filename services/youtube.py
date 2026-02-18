import yt_dlp
from faster_whisper import WhisperModel
import os
import shutil
from youtube_transcript_api import YouTubeTranscriptApi
import logging
import psutil

logger = logging.getLogger(__name__)

def log_memory_usage(stage=""):
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    logger.info(f"[{stage}] Memory Usage: {mem_info.rss / 1024 / 1024:.2f} MB")

class YouTubeProcessor:
    def __init__(self, model_size="base"):
        """
        Faster Whisper 모델 초기화
        """
        logger.info(f"--- 시스템 초기화: Faster Whisper {model_size} 모델 로드 중 ---")
        
        # 다운로드 폴더 생성
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        # [추가] 환경 변수로부터 cookies.txt 생성 (GitHub Actions 등 CI/CD 환경 지원)
        cookies_env = os.environ.get('COOKIES_TXT')
        if cookies_env:
            try:
                # 환경 변수 내용은 줄바꿈 처리가 되어 있을 수 있음
                # 만약 JSON 형태가 아니라 Netscape 포맷 텍스트라면 그대로 저장
                with open('cookies.txt', 'w', encoding='utf-8') as f:
                    f.write(cookies_env)
                logger.info("✅ Created cookies.txt from COOKIES_TXT environment variable.")
            except Exception as e:
                logger.error(f"❌ Failed to create cookies.txt from environment variable: {e}")

        # 모델 로드 (CPU 최적화 설정)
        self.model = WhisperModel(
            model_size, 
            device="cpu", 
            compute_type="int8"
        )
        logger.info(f"✅ Faster Whisper {model_size} 모델 로드 완료!")
        
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
            'overwrites': True,   # 덮어쓰기 허용
            'cachedir': False     # [수정 4] 캐시 사용 안 함 (포맷 오류 방지)
        }
        
        # [디버깅] 쿠키 파일 경로 및 존재 여부 확인
        cookie_path = os.path.abspath('cookies.txt')
        if os.path.exists('cookies.txt'):
            logger.info(f"✅ Found cookies.txt at: {cookie_path}")
            # 파일 크기도 로그에 남기면, 빈 파일이 생성되는지 확인 가능
            logger.info(f"   (Size: {os.path.getsize(cookie_path)} bytes)")
        else:
            logger.warning(f"⚠️ cookies.txt NOT found at: {cookie_path}. Authentication might fail.")

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
        logger.info(f"Processing YouTube URL: {url}")
        log_memory_usage("Start Processing")
        try:
            # 1. 영상 정보 추출 (다운로드 X)
            # [수정 5] 포맷 오류 시 재시도 로직 추가
            video_info = None
            try:
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    video_info = ydl.extract_info(url, download=False)
            except Exception as e:
                # "Requested format is not available" 오류 발생 시, 포맷 제한을 풀고 재시도
                if "Requested format is not available" in str(e):
                    logger.warning("⚠️ 지정된 포맷(bestaudio)을 찾을 수 없어, 기본 포맷(best)으로 재시도합니다.")
                    fallback_opts = self.ydl_opts.copy()
                    fallback_opts['format'] = 'best' # 포맷 제한 해제
                    with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                        video_info = ydl.extract_info(url, download=False)
                else:
                    raise e

            if not video_info:
                raise Exception("Failed to extract video info")

            video_id = video_info.get('id')
            
            video_data = {
                "title": video_info.get('title'),
                "duration": video_info.get('duration'),
                "description": video_info.get('description'),
                "thumbnail_url": video_info.get('thumbnail'),
                "channel": video_info.get('uploader'),
                "video_id": video_id,
            }

            # 2. 공식 자막 우선 시도
            logger.info(f"--- '{video_data['title']}' 공식 자막 확인 중 ---")
            official_text = self._get_official_transcript(video_id)

            if official_text:
                logger.info("✅ 공식 자막 추출 성공!")
                video_data["transcript"] = official_text
            else:
                # 3. 자막 없으면 Whisper 실행
                logger.warning("⚠️ 공식 자막 없음/차단됨. Faster Whisper 음성 인식을 시작합니다...")
                
                # 오디오 다운로드 실행
                logger.info(f"Downloading audio for video {video_id}...")
                
                # 다운로드 시에도 동일하게 재시도 로직 적용 필요할 수 있음
                # 하지만 일단 기존 옵션으로 시도 (오디오 필요하므로)
                # 만약 위에서 fallback으로 넘어갔다면, 여기서도 fallback 옵션을 써야 할 수도 있음.
                # 하지만 extract_info(download=False)는 모든 포맷을 보지만, download=True는 포맷을 지정해야 함.
                
                with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                    try:
                        ydl.download([url])
                    except Exception as e:
                        if "Requested format is not available" in str(e):
                             logger.warning("⚠️ 다운로드 중 포맷 오류. 기본 포맷(best)으로 재시도 (오디오가 없을 수 있음)")
                             fallback_opts = self.ydl_opts.copy()
                             fallback_opts['format'] = 'best'
                             with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                                 fallback_ydl.download([url])
                        else:
                            raise e
                
                # [수정 3] 파일 경로 동적 계산 (temp_audio.mp3 사용 안 함)
                # yt-dlp는 다운로드 후 .mp3로 변환하므로 파일명 예측
                filename = f"{video_id}.mp3"
                file_path = os.path.join(self.download_dir, filename)
                abs_file_path = os.path.abspath(file_path)

                # 파일 존재 확인
                if not os.path.exists(abs_file_path):
                    # 만약 .mp3가 아니라 원본 포맷(예: .m4a, .webm)으로 받아졌을 수 있음 (fallback 시)
                    # 다운로드 폴더 내의 해당 video_id로 시작하는 파일을 찾아봄
                    found_files = [f for f in os.listdir(self.download_dir) if f.startswith(video_id)]
                    if found_files:
                        logger.info(f"⚠️ mp3 변환이 안 되었을 수 있음. 발견된 파일 사용: {found_files[0]}")
                        abs_file_path = os.path.join(self.download_dir, found_files[0])
                    else:
                        logger.error(f"Audio file not found at {abs_file_path}")
                        raise FileNotFoundError(f"오디오 파일을 찾을 수 없습니다: {abs_file_path}")

                # Faster Whisper transcribe
                logger.info("Starting Whisper transcription...")
                log_memory_usage("Before Transcribe")
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
                
                logger.info(f"✅ 음성 인식 완료! (언어: {info.language}, 확률: {info.language_probability:.2f})")
                log_memory_usage("After Transcribe")

            return video_data

        except Exception as e:
            logger.error(f"Error processing YouTube video: {e}", exc_info=True)
            return {"error": str(e)}

if __name__ == "__main__":
    # 테스트 실행 시에도 로그 보이게 설정
    logging.basicConfig(level=logging.INFO)
    processor = YouTubeProcessor()
    # 테스트용 URL
    result = processor.process("https://www.youtube.com/watch?v=7nvUzO_-P0I")
    
    import pprint
    pprint.pprint(result)