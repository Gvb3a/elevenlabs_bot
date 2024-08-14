from elevenlabs.client import ElevenLabs
from elevenlabs import save


from colorama import Fore, Style, init
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from time import sleep

import os
from datetime import datetime



init()
load_dotenv()

eleven_api_key = os.getenv('ELEVEN_API_KEY')
detect_api_key = os.getenv('DETECT_LANGUAGE_API')


client = ElevenLabs(
    api_key=eleven_api_key
)


def can_make_request(characters: int, remaining: int):

    admin = dict(client.user.get())
    subscription = dict(admin['subscription'])

    if subscription['character_limit'] - subscription['character_count'] < characters:
        print(f'{Fore.RED}Lack of character{Style.RESET_ALL}')
        return False
    
    if remaining - characters < 0:
        return False

    return True


def next_character_count_reset():
    admin = dict(client.user.get())
    subscription = dict(admin['subscription'])
    next_character_count_reset_unix = subscription['next_character_count_reset_unix']
    return datetime.fromtimestamp(next_character_count_reset_unix)  # unix -> datetime


def voices(current_voice):
    voices = dict(client.voices.get_all())['voices']
    result = {}

    for voice in voices:
        voice = dict(voice)
        voice_name = voice['name'] + (' ✅\n' if voice['name'] == current_voice else '\n')
        labels = ', '.join(voice['labels'].values()) + '\n'
        description = voice['description'] if voice['description'] is not None else ''
        result[voice['preview_url']] = f"{voice_name}{labels}{description}"

    return result


def tts(text: str, voice: str = 'Alice', model: str ='eleven_turbo_v2_5'):
    try:
        
        file_name = 'tts - ' + ''.join(letter for letter in text[:64] if letter.isalnum() or letter==' ') + '.mp3'

        audio = client.generate(
            text=text,
            voice=voice,
            model=model
            )
        
        save(audio=audio, filename=file_name)

        return file_name
    
    except Exception as e:
        print(f'{Fore.RED}tts error: {e}{Style.RESET_ALL}')
        return False
        
    

def text_to_sound(text: str, file_name: str = 'sound.mp3', duration_seconds: float = None, prompt_influence: float = 0.3):
    try:
        start_time = datetime.now()
        print(f'Start text_to_sound. text: {text}, file_name: {file_name}, duration_seconds: {duration_seconds}, prompt_influence: {prompt_influence}')

        text = GoogleTranslator(source='auto', target='en').translate(text)

        audio = client.text_to_sound_effects.convert(
            text=text,
            duration_seconds=duration_seconds,
            prompt_influence=prompt_influence
        )

        save(audio, file_name)
        print(f'{Fore.GREEN}Finish text_to_sound{Style.RESET_ALL}. text: {text}, time: {datetime.now()-start_time}')
        return file_name
    
    except Exception as e:
        print(f'{Fore.RED}text_to_sound: {e}{Style.RESET_ALL}')
        return False
    

def audio_isolate(input_file_path: str):
    try:
        start_time = datetime.now()
        print(f'Start audio_isolate. input_file_path: {input_file_path}')

        with open(input_file_path, 'rb') as file:
            audio = client.audio_isolation.audio_isolation(audio=(os.path.basename(input_file_path), file, 'audio/mpeg'))
            save(audio=audio, filename=f'audio isolation - {input_file_path}')
        
        print(f'{Fore.GREEN}Finish audio_isolate{Style.RESET_ALL}. time: {datetime.now()-start_time}')
        return input_file_path
    
    except Exception as e:
        print(f'{Fore.RED}audio_isolate: {e}{Style.RESET_ALL}')
        return False
    

def wait_for_dubbing_completion(dubbing_id: str) -> bool:
    # Waits for the dubbing process to complete by periodically checking the status.
    MAX_ATTEMPTS = 200
    CHECK_INTERVAL = 10  # In seconds

    for _ in range(MAX_ATTEMPTS):
        metadata = client.dubbing.get_dubbing_project_metadata(dubbing_id)

        if metadata.status == "dubbed":
            return True
        
        elif metadata.status == "dubbing":
            print(f'dubbing')
            sleep(CHECK_INTERVAL)

        else:
            print(f"{Fore.RED}Dubbing({dubbing_id}) failed: {metadata.error_message}{Style.RESET_ALL}")
            return False

    print(f"{Fore.RED}Dubbing({dubbing_id}) timed out{Style.RESET_ALL}")
    return False


def download_dubbed_file(file_name: str, dubbing_id: str, language_code: str) -> str:
    # Downloads the dubbed file for a given dubbing ID and language code.
    with open(file_name, "wb") as file:
        for chunk in client.dubbing.get_dubbed_file(dubbing_id, language_code):
            file.write(chunk)
    return file_name


def create_dub_from_file(file_name: str, target_language: str):  # returs output file path
    # Dubs an audio or video file from one language to another and saves the output.
    print(f'Start create_dub_from_file. file_name: {file_name}, target_language: {target_language}')

    with open(file_name, "rb") as audio_file:
        response = client.dubbing.dub_a_video_or_an_audio_file(
            file=(os.path.basename(file_name), audio_file, "audio/mpeg"),
            target_lang=target_language,
            watermark=True
        )

    dubbing_id = response.dubbing_id
    try:
        print(response.expected_duration_sec)
        print(response.model_computed_fields)
        print(response.model_config)
        print(response.model_fields)
        print(response.__pretty__)

    except Exception as e:
        print(e)
        
    print(f'create_dub_from_file: {dubbing_id}({file_name})')

    if wait_for_dubbing_completion(dubbing_id):
        output_file_path = download_dubbed_file(file_name=f'dubbed_{target_language} - {file_name}', dubbing_id=dubbing_id, language_code=target_language)
        print(f'{Fore.GREEN}Finish create_dub_from_file{Style.RESET_ALL}. output_file_path: {output_file_path}, dubbing_id: {dubbing_id}')
        return output_file_path
    else:
        return False
