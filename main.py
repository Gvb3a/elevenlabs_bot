import os
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, InputMediaAudio

from colorama import init, Fore, Style
from dotenv import load_dotenv
from os import remove

from api import can_make_request, tts, text_to_sound
from sql import sql_check, sql_message, sql_select, sql_quota


load_dotenv()
init()

bot_token = os.getenv('BOT_TOKEN')

bot = Bot(token=bot_token)
dp = Dispatcher()
storage = MemoryStorage()


class FSM(StatesGroup):
    # default_state - tts. User sends text and receives tts
    sound_effects = State()  # Гser sends the text and receives the generated sound
    dubbing = State() # user sends mp3/mp4 file or link
    # TODO: if the user sends a file and cancels dubbing, the file should be deleted
    dubbing_select_language = State() # language selection is required after sending a file/link for dubbing.



@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    name = message.from_user.full_name
    username = message.from_user.username
    id = message.from_user.id 

    with open('messages.json', 'r') as file:
        start_message = json.load(file)['start message']

    await message.answer(text=start_message, parse_mode='Markdown')

    print(f'Start command by {name}')
    sql_check(name=name, username=username, id=id)
    sql_message(name=name, id=id, message='Start command', character=0)


@dp.message(F.text, StateFilter(default_state))  # TTS
async def tts_message_hadler(message: Message, state: FSMContext) -> None:
    name = message.from_user.full_name
    username = message.from_user.username
    id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

    print(f'Start TTS ({text}) by {name}')

    sql_check(name=name, username=username, id=id)
    voice = sql_select(variable='voice', id=id)
    model = sql_select('model', id)
    remaining_characters = sql_quota(id=id)

    
    character = len(text) if model != 'eleven_turbo_v2_5' else len(text)//2

    if not can_make_request(character, remaining_characters):
        await message.answer('You can\'t make an enquiry')
        return
    
    await message.answer('Just a second...')

    file_name = tts(text=text, voice=voice, model=model)

    await bot.delete_message(chat_id=chat_id, message_id=message.message_id+1)

    caption = f'Voice: {voice}\nCharacter: {character}\nRemaining: {remaining_characters-character}'

    await message.answer_voice(voice=FSInputFile(file_name), caption=caption)

    remove(file_name)

    sql_message(name=name, id=id, message=f'tts: {text}, voice: {voice}, model: {model}', character=character)

    print(f'{Fore.GREEN}Finish TTS by {name}{Style.RESET_ALL}. text: {text}')


if __name__ == '__main__':
    print(f'{Fore.GREEN}ElevenLabs bot launched{Style.RESET_ALL}') 
    dp.run_polling(bot, skip_updates=True)