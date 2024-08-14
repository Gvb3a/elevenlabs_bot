import os
import json

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, FSInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from colorama import init, Fore, Style
from dotenv import load_dotenv
from os import remove
from datetime import datetime

from time import sleep

from api import can_make_request, voices, tts, text_to_sound, next_character_count_reset
from sql import sql_check, sql_message, sql_select, sql_quota, sql_change, defult_monthly_quota


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

    sql_message(name=name, username=username, id=id, message='Start command', character=0)


@dp.message(Command('setting'))
async def command_setting_handler(message: Message) -> None:
    name = message.from_user.full_name
    username = message.from_user.username
    id = message.from_user.id 
    sql_message(name=name, username=username, id=id, message='Setting command', character=0)

    remaining = sql_quota(id)
    voice = sql_select('voice', id)
    model = sql_select('model', id)
    character_count = sql_select('character_count', id)

    with open('messages.json', 'r') as file:
        text = json.load(file)['models'][model]
        full_model_name = text['full_name']  # Example: Eleven Multilingual v2
        model_button_name = text['switch']  # Example: Switch to a cheaper model
        full_model_description = text['description']


    delta = (next_character_count_reset() - datetime.now())
    resets = f'resets in {delta.days} days' if delta.days > 0 else f'resets in {delta.seconds//3600} hour and {delta.seconds // 60 % 60} minuts'
    text = f'Name: {name}\nID: {id}\nTotal characters: {character_count}\n\nCharacter quota ({resets}) \nTotal: {defult_monthly_quota}\nRemaining: {remaining}\n\nVoice: {voice}\nModel: {full_model_name}\n{full_model_description}'
    
    change_voice = [InlineKeyboardButton(text='Change voice', callback_data='change_voice')]
    change_model = [InlineKeyboardButton(text=model_button_name, callback_data='change_model')]
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[change_voice, change_model])
    await message.answer(text=text, reply_markup=inline_keyboard)


@dp.callback_query(F.data == 'change_voice')
async def inline_text(callback: CallbackQuery):
    await callback.answer(text='In development')


@dp.callback_query(F.data == 'change_model')
async def inline_text(callback: CallbackQuery):
    name = callback.from_user.full_name
    username = callback.from_user.username
    id = callback.from_user.id 
    message_id = callback.message.message_id
    chat_id = callback.message.chat.id

    sql_message(name=name, username=username, id=id, message='change_model callback', character=0)

    remaining = sql_quota(id)
    voice = sql_select('voice', id)
    model = sql_select('model', id)
    character_count = sql_select('character_count', id)

    with open('messages.json', 'r') as file:
        text = json.load(file)['models']
        
        new_model = 'eleven_multilingual_v2' if model == 'eleven_turbo_v2_5' else 'eleven_turbo_v2_5' 
        
        sql_change(variable='model', new_value=new_model, id=id)
        
        text = text[new_model]

        full_model_name = text['full_name']
        full_model_description = text['description']
        model_button_name = text['switch']


    delta = (next_character_count_reset() - datetime.now())
    resets = f'resets in {delta.days} days' if delta.days > 0 else f'resets in {delta.seconds//3600} hour and {delta.seconds // 60 % 60} minuts'
    text = f'Name: {name}\nID: {id}\nTotal characters: {character_count}\n\nCharacter quota ({resets}) \nTotal: {defult_monthly_quota}\nRemaining: {remaining}\n\nVoice: {voice}\nModel: {full_model_name}\n{full_model_description}'
    
    change_voice = [InlineKeyboardButton(text='Change voice', callback_data='change_voice')]
    change_model = [InlineKeyboardButton(text=model_button_name, callback_data='change_model')]
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[change_voice, change_model])

    await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=inline_keyboard)
    await callback.answer()



@dp.message(F.text, StateFilter(default_state))  # TTS
async def tts_message_hadler(message: Message, state: FSMContext) -> None:
    name = message.from_user.full_name
    username = message.from_user.username
    id = message.from_user.id
    chat_id = message.chat.id
    text = message.text

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

    sql_message(name=name, username=username, id=id, message=f'tts: {text}, voice: {voice}, model: {model}', character=character)


if __name__ == '__main__':
    print(f'{Fore.GREEN}ElevenLabs bot launched{Style.RESET_ALL}') 
    dp.run_polling(bot, skip_updates=True)