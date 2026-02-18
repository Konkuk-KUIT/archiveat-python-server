
import os
import sys

# Change working directory to the script's directory
# This ensures that 'cookies.txt' and 'services/' are found correctly regardless of execution path
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

from services.youtube import YouTubeProcessor
from services.summarizer import GeminiSummarizer
import yt_dlp
import json

def test_youtube_cookies_and_summary():
    print(f"📂 Current Working Directory: {os.getcwd()}")
    print("🍪 Testing YouTube Cookies Configuration & LLM Summarization...")

    # 1. Check cookies.txt existence
    if not os.path.exists("cookies.txt"):
        print("❌ Error: 'cookies.txt' not found in current directory.")
        print("   Please place the 'cookies.txt' file in the same folder as this script.")
        return

    print("✅ 'cookies.txt' found.")

    # 2. Initialize Processor & Summarizer
    try:
        processor = YouTubeProcessor()
        summarizer = GeminiSummarizer()
    except Exception as e:
        print(f"❌ Error initializing processors: {e}")
        return

    # 3. Verify cookiefile option
    cookie_opt = processor.ydl_opts.get('cookiefile')
    if cookie_opt == 'cookies.txt':
        print(f"✅ YouTubeProcessor configured to use cookies: '{cookie_opt}'")
    else:
        print(f"❌ Error: 'cookiefile' option is NOT set to 'cookies.txt'. Current: {cookie_opt}")
        return

    # 4. Process Video (Extract Info + Transcript)
    test_url = "https://www.youtube.com/watch?v=7nvUzO_-P0I" 
    print(f"\n🔄 Processing URL: {test_url}")
    
    try:
        # This will download audio, transcribe (if needed), or get official captions
        # AND it uses the session/cookies from ydl_opts
        video_data = processor.process(test_url)
        
        if "error" in video_data:
            print(f"❌ Error processing video: {video_data['error']}")
            return

        print(f"✅ Video Title: {video_data['title']}")
        print(f"✅ Transcript Length: {len(video_data.get('transcript', ''))} chars")

    except Exception as e:
        print(f"❌ Exception during video processing: {e}")
        return

    # 5. Summarize with Gemini
    print("\n🧠 Generating AI Summary (this might take a few seconds)...")
    
    try:
        # Combine description and transcript for better context, similar to processor.py
        full_content = (video_data.get('description', '') or '') + "\n\n" + (video_data.get('transcript', '') or '')
        
        analysis_result = summarizer.summarize_content(
            video_data['title'],
            full_content
        )

        if "error" in analysis_result:
            print(f"❌ Summarization failed: {analysis_result['error']}")
            return

        print("\n" + "="*60)
        print("🎉 Final Result (JSON)")
        print("="*60)
        print(json.dumps(analysis_result, indent=2, ensure_ascii=False))
        print("="*60)
        
        # Summary Highlights
        print(f"\n📁 Category: {analysis_result.get('category')}")
        print(f"🏷️  Topic: {analysis_result.get('topic')}")
        print(f"📝 Small Summary: {analysis_result.get('small_card_summary')}")
        print(f"📰 Newsletter Blocks: {len(analysis_result.get('newsletter_summary', []))} blocks")

    except Exception as e:
        print(f"❌ Exception during summarization: {e}")

if __name__ == "__main__":
    test_youtube_cookies_and_summary()
