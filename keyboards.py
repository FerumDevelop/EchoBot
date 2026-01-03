# keyboards.py
from aiogram import types
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
import os
import database

def create_system_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="SYSTEM MESSAGE", url="https://t.me/FerumEAterms/4")
    return builder.as_markup()

async def show_help_command(message: types.Message, bot):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        return
    
    builder = InlineKeyboardBuilder()
    
    user_commands = [
        ("/start", "help_start"),
        ("/tag", "help_tag"),
        ("/ctag", "help_ctag"),
        ("/info", "help_info"),
        ("/report", "help_report"),
        ("/ignore", "help_ignore"),
        ("/unignore", "help_unignore"),
        ("/profile", "help_profile"),
        ("/protect", "help_protect"),
        ("/autodel", "help_autodel"),
        ("/privacy", "help_privacy"),
        ("/rules", "help_rules"),
        ("/leave", "help_leave"),
        ("/top", "help_top"),
    ]
    
    for cmd, callback in user_commands:
        builder.button(text=cmd, callback_data=callback)
    
    builder.adjust(4, 4, 4, 2)
    
    if user and (user['is_admin'] or user['is_creator'] or user['is_coowner']):
        builder.button(text="➖➖➖➖➖➖➖", callback_data="help_none")
        builder.adjust(1)
        
        admin_commands = [
            ("/ban", "help_ban"),
            ("/unban", "help_unban"),
            ("/mute", "help_mute"),
            ("/unmute", "help_unmute"),
            ("/warn", "help_warn"),
            ("/unwarn", "help_unwarn"),
            ("/del", "help_del"),
            ("/mediaoff", "help_mediaoff"),
            ("/mediaon", "help_mediaon"),
            ("/status", "help_status"),
            ("/calldown", "help_calldown"),
        ]
        
        if user['is_creator']:
            admin_commands.append(("/bc", "help_bc"))
        
        for cmd, callback in admin_commands:
            builder.button(text=cmd, callback_data=callback)
        builder.adjust(4, 4, 4)
    
    if user and user['is_creator']:
        builder.button(text="➖➖➖➖➖➖➖", callback_data="help_none")
        builder.adjust(1)
        
        creator_commands = [
            ("/botoff", "help_botoff"),
            ("/boton", "help_boton"),
            ("/newadmin", "help_newadmin"),
            ("/banadmin", "help_banadmin"),
            ("/cleanup", "help_cleanup"),
            ("/restart", "help_restart"),
        ]
        
        for cmd, callback in creator_commands:
            builder.button(text=cmd, callback_data=callback)
        builder.adjust(4, 2)
    
    photo_path = 'data/img/help.png'
    if os.path.exists(photo_path):
        photo = FSInputFile(photo_path)
        message_obj = await bot.send_photo(
            message.from_user.id,
            photo,
            caption="<b>Навигация по командам эхо-бота</b>\n\nНажми на кнопку, чтобы узнать информацию о команде",
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )
        return message_obj.message_id
    else:
        message_obj = await message.answer(
            "<b>Навигация по командам эхо-бота</b>\n\nНажми на кнопку, чтобы узнать информацию о команде",
            parse_mode=ParseMode.HTML,
            reply_markup=builder.as_markup()
        )
        return message_obj.message_id

async def show_help_detail(query: types.CallbackQuery, bot):
    try:
        callback_data = query.data[5:]
        
        if callback_data == "none":
            await query.answer()
            return
        
        help_texts = {
            "start": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/start</code>\n<blockquote>Начало работы с ботом</blockquote>",
            "tag": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/tag</code>\n<blockquote>Настройка подписи к сообщениям\n\nИспользование:\n/tag [текст] - установить подпись\n/tag - переключить отображение подписи</blockquote>",
            "ctag": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/ctag</code>\n<blockquote>Добавление кастомного тэга\n\nИспользование:\n/ctag [текст] - установить кастомный тэг\n/ctag - удалить кастомный тэг</blockquote>",
            "info": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/info</code>\n<blockquote>Статистика бота и ваша активность</blockquote>",
            "report": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/report</code>\n<blockquote>Пожаловаться на сообщение\n\nИспользование:\nОтправьте команду в ответ на сообщение с причиной\n/report [причина]</blockquote>",
            "ignore": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/ignore</code>\n<blockquote>Игнорировать пользователя\n\nИспользование:\nОтправьте команду в ответ на сообщение пользователя</blockquote>",
            "unignore": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/unignore</code>\n<blockquote>Перестать игнорировать пользователя\n\nИспользование:\n/unignore all - перестать игнорировать всех\nОтправьте команду в ответ на сообщение пользователя</blockquote>",
            "profile": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/profile</code>\n<blockquote>Ваш профиль и статистика</blockquote>",
            "protect": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/protect</code>\n<blockquote>Включение/выключение защиты контента</blockquote>",
            "autodel": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/autodel</code>\n<blockquote>Настройка автоудаления сообщений</blockquote>",
            "privacy": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/privacy</code>\n<blockquote>Условия использования бота</blockquote>",
            "rules": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/rules</code>\n<blockquote>Правила бота</blockquote>",
            "leave": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/leave</code>\n<blockquote>Удаление всех ваших данных из бота</blockquote>",
            "top": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/top</code>\n<blockquote>Топ-5 пользователей по количеству сообщений</blockquote>",
            "ban": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/ban</code>\n<blockquote>Бан пользователя (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение с причиной\n/ban [причина]</blockquote>",
            "unban": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/unban</code>\n<blockquote>Разбан пользователя (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение</blockquote>",
            "mute": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/mute</code>\n<blockquote>Мут пользователя (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение\n/mute [время в минутах] [причина]</blockquote>",
            "unmute": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/unmute</code>\n<blockquote>Размут пользователя (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение</blockquote>",
            "warn": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/warn</code>\n<blockquote>Выдать предупреждение (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение с причиной\n/warn [причина]</blockquote>",
            "unwarn": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/unwarn</code>\n<blockquote>Снять последнее предупреждение (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение</blockquote>",
            "del": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/del</code>\n<blockquote>Удалить сообщение у всех пользователей (только для администраторов)\n\nИспользование:\nОтправьте команду в ответ на сообщение</blockquote>",
            "mediaoff": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/mediaoff</code>\n<blockquote>Отключить тип медиа (только для администраторов)\n\nИспользование:\n/mediaoff [тип]\nТипы: text, photo, video, sticker, animation, document, voice, poll, contact, location, venue</blockquote>",
            "mediaon": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/mediaon</code>\n<blockquote>Включить тип медиа (только для администраторов)\n\nИспользование:\n/mediaon [тип]</blockquote>",
            "status": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/status</code>\n<blockquote>Статус бота (только для администраторов)</blockquote>",
            "calldown": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/calldown</code>\n<blockquote>Установка задержки между сообщениями (только для администраторов)\n\nИспользование:\n/calldown [секунды]</blockquote>",
            "bc": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/bc</code>\n<blockquote>Рассылка сообщения всем пользователям (только для создателя)\n\nИспользование:\n/bc [текст] или отправьте медиа с подписью</blockquote>",
            "botoff": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/botoff</code>\n<blockquote>Выключение бота (только для создателя)</blockquote>",
            "boton": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/boton</code>\n<blockquote>Включение бота (только для создателя)</blockquote>",
            "newadmin": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/newadmin</code>\n<blockquote>Назначение нового администратора (только для создателя)\n\nИспользование:\nОтправьте команду в ответ на сообщение пользователя</blockquote>",
            "banadmin": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/banadmin</code>\n<blockquote>Снятие администратора (только для создателя)\n\nИспользование:\nОтправьте команду в ответ на сообщение администратора</blockquote>",
            "cleanup": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/cleanup</code>\n<blockquote>Очистка старых данных (только для создателя)</blockquote>",
            "restart": "<b>Навигация по командам эхо-бота</b>\n\nКоманда: <code>/restart</code>\n<blockquote>Перезапуск бота (только для создателя)</blockquote>",
        }
        
        text = help_texts.get(callback_data, "<b>Навигация по командам эхо-бота</b>\n\nИнформация о команде не найдена.")
        
        if query.message.photo:
            await query.message.edit_caption(
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=query.message.reply_markup
            )
        else:
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=query.message.reply_markup
            )
        await query.answer()
    except Exception as e:
        await query.answer("Ошибка при загрузке информации")

async def show_autodel_options(message: types.Message):
    user_id = message.from_user.id
    user = database.get_user(user_id)
    
    if not user or not user['captcha_passed']:
        return
    
    builder = InlineKeyboardBuilder()
    times = [("1 минута", 1), ("5 минут", 5), ("30 минут", 30), 
             ("1 час", 60), ("5 часов", 300), ("Выключить", 0)]
    
    for text, minutes in times:
        builder.button(text=text, callback_data=f"autodel_{minutes}")
    
    builder.adjust(2)
    await message.answer("Выберите время автоудаления:", reply_markup=builder.as_markup())

def create_message_keyboard(sender_user: dict, target_user_id: int, is_sender: bool, is_paid_media: bool = False, original_message_id: int = None):
    builder = InlineKeyboardBuilder()
    
    if sender_user['tag_enabled'] and not is_paid_media:
        if sender_user['tag_text']:
            tag_text = sender_user['tag_text']
        elif sender_user['encrypted_name']:
            try:
                tag_text = database.decrypt_text(sender_user['encrypted_name'])
            except:
                tag_text = "Пользователь"
        else:
            tag_text = "Пользователь"
        
        builder.button(text=tag_text, url=f"tg://user?id={sender_user['user_id']}")
    
    if sender_user['custom_tag_enabled'] and sender_user['custom_tag']:
        builder.button(text=sender_user['custom_tag'], callback_data="none")
    
    if sender_user['admin_tag_enabled'] and (sender_user['is_admin'] or sender_user['is_coowner']):
        builder.button(text="Администратор", url="https://t.me/FerumEAterms/3")
    
    if sender_user['creator_tag_enabled'] and sender_user['is_creator']:
        builder.button(text="Создатель", url="https://t.me/FerumEAterms/2")
    
    if sender_user['is_coowner']:
        builder.button(text="Co-Owner", url="https://t.me/FerumEAterms/5")
    
    if is_sender and not is_paid_media and original_message_id:
        builder.button(text="Удалить мое сообщение", callback_data=f"delmy_{sender_user['user_id']}_{original_message_id}")
    
    if builder.buttons:
        builder.adjust(1)
        return builder
    
    return None