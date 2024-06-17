from dotenv import load_dotenv
from re import sub
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state, State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# from .api import tts, dubbing
from api import tts, dubbing

load_dotenv()
bot_token = os.getenv("BOT_TOKEN")
if not bot_token:
    raise ValueError('How are you going to run a bot without a token (https://t.me/BotFather)')


bot = Bot(bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage, bot=bot)


class FSMFillForm(StatesGroup):
    fill_change = State()
    fill_send_input = State()


@dp.message(CommandStart())
async def command_start(message: Message) -> None:
    await message.answer(text=f'Hello {message.from_user.full_name}! This bot is still in development')


@dp.message(Command('help'))
async def command_start(message: Message) -> None:
    pass


@dp.message(Command('voices'))
async def command_start(message: Message) -> None:
    pass


@dp.message(F.text)
async def tts_handler(message: Message) -> None:
    text = message.text
    if len(text) >= 36:
        i = text[:36].rindex(' ')
        file_name = text[:i] if i != -1 else text[:36]
    else:
        file_name = text
    file_name += ' - TTS.mp3'
    file_name = sub(r'[\\/:*?"<>|]', '', file_name)
    voice_id = '21m00Tcm4TlvDq8ikWAM'  # TODO: voice selection
    answer = await tts(voice_id=voice_id, text=text, file_name=file_name)

    if answer == True:
        await message.answer_audio(audio=FSInputFile(file_name))
        os.remove(file_name)
    else:
        await message.answer(f'Error: {answer}')

    print(f'TTS: {text} by {message.from_user.full_name}({message.from_user.username}). {answer}')

audio_list = []
@dp.message(F.audio)
async def audio_handler(message: Message) -> None:
    file_id = message.audio.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path
    file_name = file_path.split('/')[-1]
    await bot.download_file(file_path, file_name)
    global audio_list
    audio_list.append(file_name)

    sts_inline = [InlineKeyboardButton(text='Speech to speech', callback_data=f'choice_sts-{file_name}')]
    dubbing_last_inline = [InlineKeyboardButton(text='Dubbing(last)', callback_data=f'choice_dub(last)-{file_name}')]
    dubbing_inline = [InlineKeyboardButton(text='Dubbing', callback_data=f'choice_dub-{file_name}')]
    await message.answer(text='What you want to do with the audio',
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=[sts_inline, dubbing_last_inline, dubbing_inline]))


@dp.callback_query(F.data[:10] == 'choice_sts')
async def callback_mode(callback: CallbackQuery):
    await callback.answer('In development', show_alert=True)


@dp.callback_query(F.data[:16] == 'choice_dub(last)')
async def callback_mo(callback: CallbackQuery):
    await callback.answer('In development', show_alert=True)


@dp.callback_query(F.data[:10] == 'choice_dub')
async def callback_m(callback: CallbackQuery):
    file_name = callback.data.split('-')[-1]
    languages = [
        ['🇺🇸 English', 'us'], ['🇮🇳 Hindi', 'in'], ['🇵🇹Portuguese', 'pt'], ['🇨🇳 Chinese', 'cn'], ['🇪🇸 Spanish', 'es'],
        ['🇫🇷 French', 'fr'], ['🇩🇪 German', 'de'], ['🇯🇵 Japanese', 'jp'], ['🇦🇪 Arabic', 'ae'], ['🇷🇺 Russian', 'ru'],
        ['🇰🇷 Korean', 'kr'], ['🇮🇩 Indonesian', 'id'], ['🇮🇹 Italian', 'it'], ['🇳🇱 Dutch', 'nl'], ['🇹🇷 Turkish', 'tr'],
        ['🇵🇱 Polish', 'pl'], ['🇸🇪 Swedish', 'se'], ['🇵🇭 Filipino', 'ph'], ['🇲🇾 Malay', 'my'], ['🇷🇴 Romanian', 'ro'],
        ['🇺🇦 Ukrainian', 'ua'], ['🇬🇷 Greek', 'gr'], ['🇨🇿 Czech', 'cz'], ['🇩🇰 Danish', 'dk'], ['🇫🇮 Finnish', 'fi'],
        ['🇧🇬 Bulgarian', 'bg'], ['🇭🇷 Croatian', 'hr'], ['🇸🇰 Slovak', 'sk'], ['🇮🇳 Tamil', 'ta']
    ]

    buttons = [
        InlineKeyboardButton(text=lang[0], callback_data=f"dubbing-{lang[1]}-{file_name}")
        for lang in languages
    ]
    buttons_split = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons_split)
    await callback.message.edit_text('Select target language for dubbing:', reply_markup=keyboard)


@dp.callback_query(F.data[:7] == 'dubbing')
async def callback_m(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    await callback.message.edit_text('Video still processing. Please wait.')
    data = callback.data.split('-')  # dubbing-{target_language}-{file_name}
    target_language = data[1]
    file_name = sub(r'[\\/:*?"<>|]', '', data[2])

    ok, answer = await dubbing(target_language, file_name)
    result_file_name = f'{file_name.split(".")[0]} - dubbing to {target_language}.mp3'
    print(answer)
    await callback.message.delete()
    if ok:
        await bot.send_audio(audio=FSInputFile(result_file_name), chat_id=chat_id)
    else:
        print(answer)




if __name__ == '__main__':
    print('Launch')
    dp.run_polling(bot, skip_updates=True)
