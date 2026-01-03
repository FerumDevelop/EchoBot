# user.py
import asyncio
import re
import os
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from difflib import SequenceMatcher
from aiogram import Bot, types
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, InputPaidMediaPhoto
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database
import keyboards

class RateLimiter:
    def __init__(self):
        self.user_timestamps: Dict[int, float] = {}
        self.cooldown = 1.0
        
    def can_send(self, user_id: int) -> bool:
        current_time = time.time()
        last_time = self.user_timestamps.get(user_id, 0)
        if current_time - last_time < self.cooldown:
            return False
        self.user_timestamps[user_id] = current_time
        return True

def is_admin(user_id):
    user = database.get_user(user_id)
    return bool(user and (user['is_admin'] or user['is_creator'] or user['is_coowner']))

def is_creator(user_id):
    user = database.get_user(user_id)
    return bool(user and user['is_creator'])

def is_coowner(user_id):
    user = database.get_user(user_id)
    return bool(user and user['is_coowner'])

async def send_captcha(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    
    builder = InlineKeyboardBuilder()
    emojis = ["🚗", "🚕", "🚙", "🚌", "🚎", "🏎️"]
    correct_index = 0
    
    for i, emoji in enumerate(emojis):
        if i == correct_index:
            builder.button(text=emoji, callback_data=f"captcha_correct:{user_id}")
        else:
            builder.button(text=emoji, callback_data=f"captcha_wrong:{user_id}")
    
    builder.adjust(3)
    
    await bot.send_message(
        user_id,
        "Докажите, что вы не бот!\n\nВыберите красную, не спортивную машинку",
        reply_markup=builder.as_markup()
    )

async def handle_start(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    language_code = message.from_user.language_code or 'ru'
    first_name = message.from_user.first_name or ""
    
    user = database.get_user(user_id)
    
    if not user:
        database.cursor.execute('''
            INSERT INTO users (user_id, language_code, created_at, last_active, captcha_passed)
            VALUES (?, ?, ?, ?, 0)
        ''', (user_id, language_code, datetime.now(), datetime.now()))
        await send_captcha(message, bot)
        return
    
    if not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    if first_name:
        encrypted_name = database.encrypt_text(first_name)
        database.update_user(user_id, {'encrypted_name': encrypted_name})
    
    if message.from_user.username:
        encrypted_username = database.encrypt_text(message.from_user.username)
        database.update_user(user_id, {'encrypted_username': encrypted_username})
    
    await message.answer("Добро пожаловать!\n\nКанал: @FerumEchoAll\nПомощь с ботом: /help\nУсловия пользования: /privacy\nОстались вопросы? @FerumSupport", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_captcha_callback(query: types.CallbackQuery, bot: Bot):
    data = query.data.split(":")
    action = data[0]
    user_id = int(data[1])
    
    if query.from_user.id != user_id:
        await query.answer("Это не ваша капча!")
        return
    
    if action == "captcha_correct":
        database.update_user(user_id, {'captcha_passed': 1})
        
        user = database.get_user(user_id)
        if user and user['user_id'] == int(os.getenv('CREATOR_ID', '8326355672')):
            database.update_user(user_id, {'is_creator': 1})
        
        try:
            await query.message.delete()
        except:
            pass
        
        await query.answer("Капча пройдена!")
        await bot.send_message(
            user_id,
            "Добро пожаловать!\n\nКанал: @FerumEchoAll\nПомощь с ботом: /help\nУсловия пользования: /privacy\nОстались вопросы? @FerumSupport", 
            reply_markup=keyboards.create_system_keyboard()
        )
    else:
        await query.answer("Неправильный выбор! Попробуйте еще раз /start")

async def send_rules(message: types.Message, bot: Bot):
    user = database.get_user(message.from_user.id)
    if not user or not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    photo_path = 'data/img/rules.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await bot.send_photo(
            message.from_user.id,
            photo,
            caption="Правила бота:\n\n1. Уважение\n— Никаких оскорблений, дискриминации\n\n2. По делу\n— Без эротического контента\n— Без спама / флуда / ЦП\n\nПожаловаться на пользователя можно командой /report [reason]",
            reply_markup=keyboards.create_system_keyboard()
        )
    else:
        await message.answer("Правила бота:\n\n1. Уважение\n— Никаких оскорблений, дискриминации\n\n2. По делу\n— Без эротического контента\n— Без спама / флуда / ЦП\n\nПожаловаться на пользователя можно командой /report [reason]",
                             reply_markup=keyboards.create_system_keyboard())

async def handle_tag(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    args = message.text.split()
    
    if len(args) > 1:
        tag_text = ' '.join(args[1:])
        if not database.validate_tag_text(tag_text):
            await message.answer("Тэг содержит запрещенные символы или пустой! Разрешенные символы: кириллица, латиница, цифры, пробелы и некоторые спецсимволы.", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
        
        if tag_text.upper() in ['SYSTEM', 'DELETED', 'REPLY', 'MENTION', 'BLESSED', 'ADMIN', 'CREATOR', 'OWNER', 'CO-OWNER']:
            await message.answer("Ставить тэг в виде системных сообщений - мошенничество!", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
        database.update_user(user_id, {'tag_text': tag_text})
        await message.answer(f"{tag_text}, рад знакомству!", reply_markup=keyboards.create_system_keyboard())
        return
    
    if user and (user['is_creator'] or user['is_admin'] or user['is_coowner']):
        builder = InlineKeyboardBuilder()
        
        tag_status = "✅" if user['tag_enabled'] else "❌"
        admin_tag_status = "✅" if user['admin_tag_enabled'] else "❌"
        creator_tag_status = "✅" if user['creator_tag_enabled'] else "❌"
        
        builder.button(text=f"{tag_status} Подпись", callback_data=f"togtag:{user_id}")
        
        if user['is_admin'] or user['is_coowner']:
            builder.button(text=f"{admin_tag_status} Метка Админ", callback_data=f"togadmintag:{user_id}")
        
        if user['is_creator']:
            builder.button(text=f"{creator_tag_status} Метка Создатель", callback_data=f"togcreatortag:{user_id}")
        
        builder.adjust(1)
        await message.answer("Настройки тэгов", reply_markup=builder.as_markup())
    else:
        new_status = 0 if user['tag_enabled'] else 1
        database.update_user(user_id, {'tag_enabled': new_status})
        status_text = "Подпись включена" if new_status else "Подпись выключена"
        await message.answer(status_text, reply_markup=keyboards.create_system_keyboard())

async def handle_ctag(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    args = message.text.split()
    
    if len(args) > 1:
        tag_text = ' '.join(args[1:])
        
        if not database.validate_tag_text(tag_text):
            await message.answer("Тэг содержит запрещенные символы или пустой! Разрешенные символы: кириллица, латиница, цифры, пробелы и некоторые спецсимволы.", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
        
        if tag_text.upper() in ['SYSTEM', 'DELETED', 'REPLY', 'MENTION']:
            await message.answer("Ставить тэг в виде системных сообщений - мошенничество!", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
        database.update_user(user_id, {'custom_tag': tag_text, 'custom_tag_enabled': 1})
        await message.answer(f"{tag_text}, рад знакомству!", reply_markup=keyboards.create_system_keyboard())
    else:
        database.update_user(user_id, {'custom_tag_enabled': 0})
        await message.answer("Дополнительный тэг удален", reply_markup=keyboards.create_system_keyboard())

async def show_info(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    total_users = database.get_total_users()
    today_messages = database.get_daily_stats()
    user_today_messages = database.get_user_daily_stats(user_id)
    
    bot_start_time = database.get_bot_start_time()
    uptime = datetime.now() - bot_start_time
    
    weeks = uptime.days // 7
    days = uptime.days % 7
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    uptime_parts = []
    if weeks > 0:
        uptime_parts.append(f"{weeks} недель")
    if days > 0:
        uptime_parts.append(f"{days} дней")
    if hours > 0:
        uptime_parts.append(f"{hours} часов")
    if minutes > 0:
        uptime_parts.append(f"{minutes} минут")
    
    uptime_text = ", ".join(uptime_parts) if uptime_parts else "менее минуты"
    
    info_text = f"Статистика бота:\n\n" \
                f"Пользователей: {total_users}\n" \
                f"Сообщений сегодня: {today_messages}\n" \
                f"Ваших сообщений сегодня: {user_today_messages}\n" \
                f"Бот работает уже {uptime_text}"
    
    await message.answer(info_text, reply_markup=keyboards.create_system_keyboard())

async def show_top(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    top_users = database.get_top_users(5)
    
    if not top_users:
        await message.answer("Топ пользователей пуст.", reply_markup=keyboards.create_system_keyboard())
        return
    
    text = "🏆 Топ-5 пользователей по сообщениям:\n\n"
    
    for i, (user_id, msg_count, enc_name, enc_username, tag_enabled, tag_text, custom_tag, custom_tag_enabled) in enumerate(top_users, 1):
        if custom_tag_enabled and custom_tag:
            name = custom_tag
        elif tag_enabled:
            if tag_text:
                name = tag_text
            elif enc_name:
                try:
                    name = database.decrypt_text(enc_name)
                except:
                    name = "Аноним"
            else:
                name = "Аноним"
            
            if enc_username:
                try:
                    username = database.decrypt_text(enc_username)
                    if username:
                        name = f'<a href="tg://user?id={user_id}">{name}</a>'
                except:
                    pass
        else:
            name = "Аноним"
        
        text += f"{i}. {name} — {msg_count} сообщ.\n"
    
    photo_path = 'data/img/top.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await bot.send_photo(message.from_user.id, photo, caption=text, parse_mode=ParseMode.HTML, 
                            reply_markup=keyboards.create_system_keyboard())
    else:
        await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=keyboards.create_system_keyboard())

async def show_profile(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user:
        await send_captcha(message, bot)
        return
    
    if not user['captcha_passed']:
        await send_captcha(message, bot)
        return

    if user['is_creator']:
        role = "Создатель"
    elif user['is_coowner']:
        role = "Co-Owner"
    elif user['is_admin']:
        role = "Администратор"
    else:
        role = "Пользователь"
    
    profile_text = f"👤 Ваш профиль:\n\n" \
                   f"▫️ ID: {user['user_id']}\n" \
                   f"▫️ Роль: {role}\n" \
                   f"▫️ Тэг: {'✅' if user['tag_enabled'] else '❌'}\n" \
                   f"▫️ Доп. тег: {user['custom_tag'] if user['custom_tag_enabled'] else '❌'}\n" \
                   f"▫️ Защита контента: {'✅' if user['protect_content'] else '❌'}\n" \
                   f"▫️ Автоудаление: {user['autodel_time'] or 0} минут\n" \
                   f"▫️ Предупреждений: {user['warnings']}\n" \
                   f"▫️ Сообщений: {user['message_count']}\n"
    
    photo_path = 'data/img/profile.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await bot.send_photo(message.from_user.id, photo, caption=profile_text, 
                            reply_markup=keyboards.create_system_keyboard())
    else:
        await message.answer(profile_text, reply_markup=keyboards.create_system_keyboard())

async def handle_ignore(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Эта команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    
    result = database.get_original_message_info(replied_message_id, user_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    ignored_user_id = result[1]
    
    if user_id == ignored_user_id:
        await message.answer("Нельзя игнорировать самого себя!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    database.add_ignored_user(user_id, ignored_user_id)
    await message.answer("Пользователь добавлен в игнор-лист", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_unignore(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    args = message.text.split()
    
    if len(args) > 1 and args[1].lower() == "all":
        database.cursor.execute('DELETE FROM ignored_users WHERE user_id = ?', (user_id,))
        database.conn.commit()
        await message.answer("Вы перестали игнорировать всех пользователей", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    if not message.reply_to_message:
        await message.answer("Эта команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    
    result = database.get_original_message_info(replied_message_id, user_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    ignored_user_id = result[1]
    
    database.remove_ignored_user(user_id, ignored_user_id)
    await message.answer("Пользователь удален из игнор-листа", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_protect(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, message.bot)
        return
    
    new_status = 0 if user['protect_content'] else 1
    database.update_user(user_id, {'protect_content': new_status})
    
    status_text = "✅ Защита контента включена" if new_status else "❌ Защита контента выключена"
    await message.answer(status_text, reply_markup=keyboards.create_system_keyboard())

async def send_privacy(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    text = '''Условия использования бота Ferum Echo All:
    
1. Бот предназначен для анонимного общения
2. Запрещена отправка незаконного контента
3. Администрация вправе блокировать пользователей
4. Сообщения могут быть удалены при нарушении правил
    
Подробнее: @FerumSupport'''
    
    photo_path = 'data/img/use.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await bot.send_photo(message.from_user.id, photo, caption=text, 
                            reply_markup=keyboards.create_system_keyboard())
    else:
        await message.answer(text, reply_markup=keyboards.create_system_keyboard())

async def handle_leave(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Да, удалить", callback_data=f"leave_yes:{user_id}")
    builder.button(text="Отмена", callback_data="leave_no")
    builder.adjust(2)
    
    photo_path = 'data/img/sure.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        await bot.send_photo(
            message.from_user.id,
            photo,
            caption="Вы уверены что хотите удалить все свои данные?",
            reply_markup=builder.as_markup()
        )
    else:
        await message.answer("Вы уверены что хотите удалить все свои данные?", reply_markup=builder.as_markup())

async def handle_tag_callback(query: types.CallbackQuery):
    data = query.data.split(":")
    action = data[0]
    user_id = int(data[1])
    
    if query.from_user.id != user_id:
        await query.answer("Это не ваши настройки!")
        return
    
    user = database.get_user(user_id)
    if not user:
        await query.answer("Пользователь не найден")
        return
    
    if action == "togtag":
        new_status = 0 if user['tag_enabled'] else 1
        database.update_user(user_id, {'tag_enabled': new_status})
        user['tag_enabled'] = new_status
    elif action == "togadmintag":
        new_status = 0 if user['admin_tag_enabled'] else 1
        database.update_user(user_id, {'admin_tag_enabled': new_status})
        user['admin_tag_enabled'] = new_status
    elif action == "togcreatortag":
        new_status = 0 if user['creator_tag_enabled'] else 1
        database.update_user(user_id, {'creator_tag_enabled': new_status})
        user['creator_tag_enabled'] = new_status
    
    builder = InlineKeyboardBuilder()
    
    tag_status = "✅" if user['tag_enabled'] else "❌"
    admin_tag_status = "✅" if user['admin_tag_enabled'] else "❌"
    creator_tag_status = "✅" if user['creator_tag_enabled'] else "❌"
    
    builder.button(text=f"{tag_status} Подпись", callback_data=f"togtag:{user_id}")
    
    if user['is_admin'] or user['is_coowner']:
        builder.button(text=f"{admin_tag_status} Метка Админ", callback_data=f"togadmintag:{user_id}")
    
    if user['is_creator']:
        builder.button(text=f"{creator_tag_status} Метка Создатель", callback_data=f"togcreatortag:{user_id}")
    
    builder.adjust(1)
    
    try:
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    except:
        pass
    
    await query.answer("Настройки обновлены")

async def handle_autodel_callback(query: types.CallbackQuery):
    minutes = int(query.data.split("_")[1])
    user_id = query.from_user.id
    
    database.update_user(user_id, {'autodel_time': minutes})
    
    if minutes == 0:
        await query.message.edit_text("Автоудаление выключено")
    else:
        await query.message.edit_text(f"Автоудаление установлено на {minutes} минут")
    
    await query.answer()

async def handle_delete_my_callback(query: types.CallbackQuery, bot: Bot):
    data = query.data.split("_")
    sender_id = int(data[1])
    original_message_id = int(data[2])
    
    if query.from_user.id != sender_id:
        await query.answer("Это не ваше сообщение!")
        return
    
    messages = database.get_messages_by_original(original_message_id)
    
    deleted_count = 0
    for target_user_id, message_id, msg_type, content in messages:
        try:
            await bot.delete_message(target_user_id, message_id)
            deleted_count += 1
        except:
            pass
    
    builder = InlineKeyboardBuilder()
    builder.button(text="SYSTEM", url="https://t.me/FerumEAterms/4")
    builder.button(text="DELETED", callback_data="delthis")
    builder.adjust(1, 1)
    
    try:
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    except:
        pass
    
    database.delete_messages_by_original(original_message_id, sender_id)
    
    await query.answer(f"Сообщение удалено у {deleted_count} пользователей")

async def handle_delthis_callback(query: types.CallbackQuery):
    try:
        await query.message.delete()
    except:
        pass
    await query.answer()

async def handle_leave_yes(query: types.CallbackQuery):
    user_id = int(query.data.split(":")[1])
    
    if query.from_user.id != user_id:
        await query.answer("Это не ваши данные!")
        return
    
    database.delete_user_data(user_id)
    
    await query.message.edit_text("Ваши данные успешно удалены. Бот больше не будет вас беспокоить\n\nЕсли захотите вернуться, просто запустите бота командой /start")
    await query.answer()

async def handle_leave_no(query: types.CallbackQuery):
    await query.message.edit_text("Удаление отменено. Спасибо, что вы с нами")
    await query.answer()

def check_media_type_enabled(media_type: str) -> bool:
    value = database.get_bot_setting(f'media_{media_type}_enabled', '1')
    return value != '0'

def check_spam_similarity(user_id, new_message_text):
    user = database.get_user(user_id)
    if not user or not user['last_message_text']:
        return False
    
    last_message = user['last_message_text']
    if not last_message or not new_message_text:
        return False
    
    similarity = SequenceMatcher(None, last_message, new_message_text).ratio()
    return similarity > 0.8

async def send_access_denied(chat_id: int, bot: Bot):
    try:
        if os.path.exists('data/img/access_denied.png'):
            photo = FSInputFile('data/img/access_denied.png')
            await bot.send_photo(chat_id, photo)
        else:
            await bot.send_message(chat_id, "❌ Доступ запрещен!", reply_markup=keyboards.create_system_keyboard())
    except Exception as e:
        await bot.send_message(chat_id, "❌ Доступ запрещен!", reply_markup=keyboards.create_system_keyboard())

async def distribute_message(message: types.Message, sender_user: dict, bot: Bot, rate_limiter: RateLimiter):
    user_id = message.from_user.id
    original_message_id = message.message_id
    
    if sender_user['banned']:
        return
    
    if sender_user['muted_until']:
        muted_until = sender_user['muted_until']
        if datetime.now() < muted_until:
            remaining = muted_until - datetime.now()
            minutes = int(remaining.total_seconds() // 60)
            await message.answer(f"Вы замьючены. Осталось: {minutes} минут", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
    
    if not rate_limiter.can_send(user_id):
        await message.answer("Подождите 1 секунду перед отправкой следующего сообщения", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    message_text = message.text or message.caption or ""
    if message_text and check_spam_similarity(user_id, message_text):
        await message.answer("Придумай что-нибудь новое", reply_markup=keyboards.create_system_keyboard())
        return
    
    message_type = message.content_type
    if not check_media_type_enabled(message_type):
        await message.answer("Данный тип сообщений недоступен", reply_markup=keyboards.create_system_keyboard())
        return
    
    if message_text:
        database.update_user(user_id, {'last_message_text': message_text, 'last_message_time': datetime.now()})
    
    database.update_stats(user_id)
    
    if (not sender_user['encrypted_name'] or not sender_user['encrypted_username']) and message.from_user:
        updates = {}
        if message.from_user.first_name:
            updates['encrypted_name'] = database.encrypt_text(message.from_user.first_name)
        
        if message.from_user.username:
            updates['encrypted_username'] = database.encrypt_text(message.from_user.username)
        
        if updates:
            database.update_user(user_id, updates)
            sender_user = database.get_user(user_id)
    
    is_paid_media = False
    paid_stars = 0
    paid_description = ""
    
    if message.photo and message.caption and message.caption.startswith('`'):
        match = re.match(r'`(\d+)\s+(.+)$', message.caption)
        if match:
            is_paid_media = True
            paid_stars = int(match.group(1))
            paid_description = match.group(2)
    
    all_users = database.get_active_users()
    
    replied_original_id = None
    replied_sender_id = None
    
    if message.reply_to_message:
        replied_message_id = message.reply_to_message.message_id
        
        result = database.get_original_message_info(replied_message_id, user_id)
        
        if result:
            replied_original_id, replied_sender_id = result
    
    tasks = []
    for target_user_id in all_users:
        if target_user_id == user_id:
            continue
        
        if database.is_ignored(target_user_id, user_id):
            continue
        
        task = send_to_user(target_user_id, message, sender_user, original_message_id, is_paid_media, paid_stars, paid_description, False, replied_original_id, replied_sender_id, bot)
        tasks.append(task)
    
    sender_task = send_to_user(user_id, message, sender_user, original_message_id, is_paid_media, paid_stars, paid_description, True, replied_original_id, replied_sender_id, bot)
    tasks.append(sender_task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            pass
    
    if message.poll:
        await handle_poll(message, original_message_id, bot)

async def send_to_user(target_user_id: int, message: types.Message, sender_user: dict, original_message_id: int, is_paid_media: bool, paid_stars: int, paid_description: str, is_sender: bool, replied_original_id: Optional[int] = None, replied_sender_id: Optional[int] = None, bot: Bot = None):
    try:
        keyboard = keyboards.create_message_keyboard(sender_user, target_user_id, is_sender, is_paid_media, original_message_id)
        
        target_reply_to = None
        
        if replied_original_id:
            target_reply_to = database.get_message_map(replied_original_id, target_user_id)
        
        need_reply_tag = False
        if replied_original_id and target_user_id == replied_sender_id and target_user_id != sender_user['user_id']:
            need_reply_tag = True
        
        if is_paid_media and message.photo:
            sent_message = await bot.send_paid_media(
                chat_id=target_user_id,
                star_count=paid_stars,
                media=[InputPaidMediaPhoto(media=message.photo[-1].file_id)],
                caption=paid_description,
                payload=f"{sender_user['user_id']}_{original_message_id}"
            )
            
            if keyboard:
                try:
                    await sent_message.edit_reply_markup(reply_markup=keyboard.as_markup())
                except:
                    pass
        else:
            sent_message = await send_message_copy(target_user_id, message, sender_user, target_reply_to, keyboard, need_reply_tag, bot)
        
        if sent_message:
            message_data = {
                'message_id': sent_message.message_id,
                'user_id': target_user_id,
                'original_message_id': original_message_id,
                'original_sender_id': sender_user['user_id'],
                'message_type': message.content_type,
                'content': message.text or message.caption or '',
                'tag_enabled': 1 if sender_user['tag_enabled'] else 0,
                'tag_text': sender_user['tag_text'],
                'custom_tag': sender_user['custom_tag'],
                'custom_tag_enabled': 1 if sender_user['custom_tag_enabled'] else 0,
                'admin_tag': 1 if sender_user['admin_tag_enabled'] else 0,
                'creator_tag': 1 if sender_user['creator_tag_enabled'] else 0,
                'coowner_tag': 1 if sender_user['is_coowner'] else 0,
                'protect_content': 1 if sender_user['protect_content'] else 0,
                'paid_media': 1 if is_paid_media else 0,
                'paid_stars': paid_stars if is_paid_media else 0,
                'is_reply': 1 if target_reply_to else 0,
                'reply_to_message_id': target_reply_to,
                'is_edited': 0,
                'edited_at': None
            }
            
            database.save_message(message_data)
            
            database.save_message_map(original_message_id, target_user_id, sent_message.message_id)
            
    except Exception as e:
        pass

async def send_message_copy(target_user_id: int, message: types.Message, sender_user: dict, reply_to: Optional[int], keyboard, need_reply_tag: bool = False, bot: Bot = None):
    protect_content = sender_user['protect_content']
    
    try:
        if need_reply_tag:
            caption_prefix = "#REPLY\n"
        else:
            caption_prefix = ""
        
        if message.text:
            text = f"{caption_prefix}{message.text}"
            return await bot.send_message(
                target_user_id,
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.photo:
            caption = f"{caption_prefix}{message.caption or ''}"
            return await bot.send_photo(
                target_user_id,
                message.photo[-1].file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.video:
            caption = f"{caption_prefix}{message.caption or ''}"
            return await bot.send_video(
                target_user_id,
                message.video.file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.sticker:
            return await bot.send_sticker(
                target_user_id,
                message.sticker.file_id,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.animation:
            caption = f"{caption_prefix}{message.caption or ''}"
            return await bot.send_animation(
                target_user_id,
                message.animation.file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.document:
            caption = f"{caption_prefix}{message.caption or ''}"
            return await bot.send_document(
                target_user_id,
                message.document.file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.voice:
            caption = f"{caption_prefix}{message.caption or ''}"
            return await bot.send_voice(
                target_user_id,
                message.voice.file_id,
                caption=caption,
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.poll:
            return await bot.send_poll(
                target_user_id,
                question=message.poll.question,
                options=[option.text for option in message.poll.options],
                is_anonymous=message.poll.is_anonymous,
                allows_multiple_answers=message.poll.allows_multiple_answers,
                explanation=message.poll.explanation,
                open_period=message.poll.open_period,
                close_date=message.poll.close_date,
                reply_to_message_id=reply_to,
                protect_content=protect_content
            )
        elif message.contact:
            return await bot.send_contact(
                target_user_id,
                phone_number=message.contact.phone_number,
                first_name=message.contact.first_name,
                last_name=message.contact.last_name,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.location:
            return await bot.send_location(
                target_user_id,
                latitude=message.location.latitude,
                longitude=message.location.longitude,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
        elif message.venue:
            return await bot.send_venue(
                target_user_id,
                latitude=message.venue.location.latitude,
                longitude=message.venue.location.longitude,
                title=message.venue.title,
                address=message.venue.address,
                reply_to_message_id=reply_to,
                reply_markup=keyboard.as_markup() if keyboard else None,
                protect_content=protect_content
            )
    except Exception as e:
        return None

async def handle_poll(message: types.Message, original_message_id: int, bot: Bot):
    try:
        POLL_CHANNEL_ID = int(os.getenv('POLL_CHANNEL_ID', '-1003584966418'))
        sent_poll = await bot.send_poll(
            chat_id=POLL_CHANNEL_ID,
            question=message.poll.question,
            options=[option.text for option in message.poll.options],
            is_anonymous=message.poll.is_anonymous,
            allows_multiple_answers=message.poll.allows_multiple_answers,
            explanation=message.poll.explanation,
            open_period=message.poll.open_period,
            close_date=message.poll.close_date,
        )
        
        all_users = database.get_active_users()
        
        for user_id in all_users:
            try:
                forwarded = await bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=POLL_CHANNEL_ID,
                    message_id=sent_poll.message_id
                )
                
                database.save_message_map(original_message_id, user_id, forwarded.message_id)
            except:
                pass
        
    except Exception as e:
        pass

async def handle_message(message: types.Message, bot: Bot, rate_limiter: RateLimiter):
    if message.text and message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user:
        await send_captcha(message, bot)
        return
    
    if not user['captcha_passed']:
        await send_captcha(message, bot)
        return
    
    bot_enabled = database.get_bot_setting('bot_enabled', '1')
    if bot_enabled == '0' and not is_admin(user_id):
        await message.answer("Бот временно отключен", reply_markup=keyboards.create_system_keyboard())
        return
    
    if user['banned']:
        await message.answer("Вы не можете отправлять сообщения, так как ваш аккаунт заблокирован в боте\n\nПравила: /rules", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    if user['muted_until']:
        muted_until = user['muted_until']
        if datetime.now() < muted_until:
            remaining = muted_until - datetime.now()
            minutes = int(remaining.total_seconds() // 60)
            await message.answer(f"Вы находитесь в муте. До окончания: {minutes} минут", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
    
    message_type = message.content_type
    if not check_media_type_enabled(message_type):
        await message.answer("Данный тип сообщения отключен", reply_markup=keyboards.create_system_keyboard())
        return
    
    await distribute_message(message, user, bot, rate_limiter)

async def handle_message_edit(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    
    result = database.get_original_message_info(message.message_id, user_id)
    
    if not result:
        return
    
    original_message_id, original_sender_id = result
    
    messages = database.get_messages_by_original(original_message_id)
    
    new_content = message.text or message.caption or ''
    if not new_content:
        return
    
    edited_mark = "\n\n✏️ (edited message)"
    full_content = new_content + edited_mark
    
    database.update_message_content(original_message_id, full_content, is_edited=True)
    
    edited_count = 0
    for target_user_id, msg_id, msg_type, old_content in messages:
        try:
            if message.text and msg_type == 'text':
                await bot.edit_message_text(
                    chat_id=target_user_id,
                    message_id=msg_id,
                    text=full_content,
                    parse_mode=ParseMode.MARKDOWN
                )
                edited_count += 1
            elif message.caption and msg_type in ['photo', 'video', 'document', 'animation', 'voice']:
                await bot.edit_message_caption(
                    chat_id=target_user_id,
                    message_id=msg_id,
                    caption=full_content,
                    parse_mode=ParseMode.MARKDOWN
                )
                edited_count += 1
        except Exception as e:
            continue
    
    return edited_count

async def handle_message_reaction(reaction: types.MessageReactionUpdated, bot: Bot):
    user_id = reaction.user.id
    message_id = reaction.message_id
    
    result = database.get_original_message_info(message_id, user_id)
    
    if not result:
        return
    
    original_message_id, original_sender_id = result
    
    messages = database.get_messages_by_original(original_message_id)
    
    for target_user_id, target_message_id, _, _ in messages:
        try:
            await bot.set_message_reaction(
                chat_id=target_user_id,
                message_id=target_message_id,
                reaction=reaction.new_reaction
            )
        except Exception as e:
            pass

async def handle_paid_media_purchase(message: types.Message, bot: Bot):
    try:
        if not hasattr(message, 'paid_media_purchased') or not message.paid_media_purchased:
            return
            
        payload = message.paid_media_purchased.payload
        if not payload:
            return
            
        parts = payload.split('_')
        if len(parts) != 2:
            return
        
        media_owner_id = int(parts[0])
        original_message_id = int(parts[1])
        
        database.save_paid_media_sale(media_owner_id, message.from_user.id, message.paid_media_purchased.star_count, payload)
        
        notification_text = f"✅ Ваше платное медиа было куплено!\n\n⭐ Звезд получено: {message.paid_media_purchased.star_count}\n\nДля получения выплаты обратитесь в поддержку - @FerumSupport"
        
        try:
            await bot.send_message(
                media_owner_id,
                notification_text,
                reply_markup=keyboards.create_system_keyboard()
            )
        except Exception as e:
            pass
            
    except Exception as e:
        pass