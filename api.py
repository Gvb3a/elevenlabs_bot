import requests
import os
from typing import Optional
from moviepy.editor import AudioFileClip, VideoFileClip
import time
from elevenlabs.client import ElevenLabs
import moviepy.editor as mpe
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ELEVENLABS_API_KEY")
if not api_key:
    raise ValueError("ELEVENLABS_API_KEY environment variable not found. "
                     "Please set the API key in your environment variables.")


async def tts(voice_id, text, file_name):
    CHUNK_SIZE = 1024  # Size of chunks to read/write at a time

    tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }

    response = requests.post(tts_url, headers=headers, json=data, stream=True)

    if response.ok:
        with open(file_name, "wb") as f:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                f.write(chunk)
        return True
    else:
        return response.text




async def dubbing(target_language: str, file_name: str) -> (bool, str):

    if file_name.split('.')[-1] == 'mp3':
        name = file_name.split('.')[0]  # abc.mp3 -> abc
    else:
        return False, 'Now dubbing only supports mp3 files'

    audio_file = f"{name}.mp3"
    video_file = f"{name}.mp4"

    audio = mpe.AudioFileClip(audio_file)
    video = mpe.ColorClip(size=(64, 64), color=(0, 0, 0), duration=audio.duration)

    final_clip = video.set_audio(audio)
    final_clip.write_videofile(video_file, fps=4, codec="libx264", audio_codec="aac")



    result = create_dub_from_file(
        video_file,  # Input file path
        'video/mp4',  # File format
        'auto',
        'en'
    )
    if result:
        video = VideoFileClip(result)
        audio = video.audio
        audio.write_audiofile(f'{name} - dubbing to {target_language}.mp3', codec='pcm_s16le')
        video.close()
        return True, f"Dubbing was successful! File saved at: {result}"
    else:
        return False, "Dubbing failed or timed out."


client = ElevenLabs(api_key=api_key)


def download_dubbed_file(dubbing_id: str, language_code: str) -> str:
    dir_path = f"data/{dubbing_id}"
    os.makedirs(dir_path, exist_ok=True)

    file_path = f"{dir_path}/{language_code}.mp4"
    with open(file_path, "wb") as file:
        for chunk in client.dubbing.get_dubbed_file(dubbing_id, language_code):
            file.write(chunk)

    return file_path


def wait_for_dubbing_completion(dubbing_id: str) -> bool:

    MAX_ATTEMPTS = 180
    CHECK_INTERVAL = 15

    for _ in range(MAX_ATTEMPTS):
        metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)
        if metadata.status == "dubbed":
            return True
        elif metadata.status == "dubbing":
            print(
                "Dubbing in progress... Will check status again in",
                CHECK_INTERVAL,
                "seconds.",
            )
            time.sleep(CHECK_INTERVAL)
        else:
            print("Dubbing failed:", metadata.error_message)
            return False

    print("Dubbing timed out")
    return False


def create_dub_from_file(
    input_file_path: str,
    file_format: str,
    source_language: str,
    target_language: str
) -> Optional[str]:
    if not os.path.isfile(input_file_path):
        raise FileNotFoundError(f"The input file does not exist: {input_file_path}")

    with open(input_file_path, "rb") as audio_file:
        response = client.dubbing.dub_a_video_or_an_audio_file(
            file=(os.path.basename(input_file_path), audio_file, file_format),
            target_lang=target_language,
            mode="automatic",
            source_lang='auto',
            num_speakers=0,
            watermark=True,
        )

    dubbing_id = response.dubbing_id
    if wait_for_dubbing_completion(dubbing_id):
        output_file_path = download_dubbed_file(dubbing_id, target_language)
        return output_file_path
    else:
        return None