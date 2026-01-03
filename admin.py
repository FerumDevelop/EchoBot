# admin.py
from aiogram import Bot, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database
import user
import keyboards
import asyncio
import subprocess
import os
import sys

class BroadcastState(StatesGroup):
    waiting_confirm = State()

class AdminPermState(StatesGroup):
    waiting_perm = State()

async def handle_report(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Эта команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    if not message.text or len(message.text.split()) < 2:
        await message.answer("Укажите причину: /report [причина]", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    reason = ' '.join(message.text.split()[1:])
    replied_message_id = message.reply_to_message.message_id
    reporter_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, reporter_id)
    
    if not result:
        await message.answer("Сообщение не найдено!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    original_message_id, original_sender_id = result
    
    admins = database.get_admin_users()
    
    sent_count = 0
    for admin_id in admins:
        if admin_id == reporter_id:
            continue
        
        admin_message = database.get_message_map(original_message_id, admin_id)
        
        if admin_message:
            try:
                await bot.send_message(
                    admin_id,
                    f"Жалоба на сообщение\n\nПричина: {reason}",
                    reply_to_message_id=admin_message,
                    reply_markup=keyboards.create_system_keyboard()
                )
                sent_count += 1
            except:
                pass
    
    if sent_count > 0:
        await message.answer(f"Жалоба отправлена администраторам\nСпасибо!", 
                             reply_markup=keyboards.create_system_keyboard())
    else:
        await message.answer("Не удалось отправить жалобу администраторам", 
                             reply_markup=keyboards.create_system_keyboard())

async def handle_ban(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Укажите причину: /ban [причина]", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    reason = ' '.join(args[1:])
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    if target_user_id == admin_id:
        await message.answer("Нельзя забанить самого себя!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    database.update_user(target_user_id, {'banned': 1})
    database.add_warning(target_user_id, admin_id, f"Бан: {reason}")
    
    await message.answer(f"Пользователь забанен. Причина: {reason}", 
                         reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, f"Вы были забанены администратором.\nПричина: {reason}", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_unban(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    database.update_user(target_user_id, {'banned': 0})
    
    await message.answer("Пользователь разбанен", 
                         reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, "Ваша блокировка снята администратором", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_mute(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Использование: /mute [время в мин] [причина]", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    try:
        mute_minutes = int(args[1])
        reason = ' '.join(args[2:])
    except:
        await message.answer("Неверный формат времени!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    if target_user_id == admin_id:
        await message.answer("Нельзя замутить самого себя!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    from datetime import datetime, timedelta
    muted_until = datetime.now() + timedelta(minutes=mute_minutes)
    
    database.update_user(target_user_id, {'muted_until': muted_until})
    database.add_warning(target_user_id, admin_id, f"Мут на {mute_minutes} мин: {reason}")
    
    await message.answer(f"Пользователь замучен на {mute_minutes} минут\nПричина: {reason}", 
                         reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, f"Вы были замучены на {mute_minutes} минут.\nПричина: {reason}", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_unmute(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    database.update_user(target_user_id, {'muted_until': None})
    
    await message.answer("Мут снят", reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, "Ваш мут снят администратором.", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_delete(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти сообщение в базе!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    original_message_id = result[0]
    
    messages = database.get_messages_by_original(original_message_id)
    
    deleted_count = 0
    for target_user_id, msg_id, msg_type, content in messages:
        try:
            await bot.delete_message(target_user_id, msg_id)
            deleted_count += 1
        except:
            pass
    
    database.delete_messages_by_original(original_message_id)
    
    await message.answer(f"Сообщение удалено у {deleted_count} пользователей", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_warn(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /warn [причина]", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    reason = ' '.join(args[1:])
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    database.add_warning(target_user_id, admin_id, reason)
    
    target_user = database.get_user(target_user_id)
    if target_user:
        new_warnings = target_user['warnings'] + 1
        database.update_user(target_user_id, {'warnings': new_warnings})
        
        if new_warnings >= 3:
            database.update_user(target_user_id, {'banned': 1})
    
    if target_user and target_user['warnings'] >= 3:
        try:
            await bot.send_message(target_user_id, "Вы получили 3ье предупреждение. Ваш аккаунт заблокирован по причине получения большого количества предупреждений", 
                                   reply_markup=keyboards.create_system_keyboard())
        except:
            pass
        await message.answer(f"Пользователь получил 3е предупреждение и был забанен\nПричина: {reason}", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    await message.answer(f"Пользователь получил предупреждение.\nПричина: {reason}", 
                         reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, f"Вы получили предупреждение от администратора\nПричина: {reason}\n\nИмейте ввиду - при полчении 3х предупреждений, ваш аккаунт будет заблокирован", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_unwarn(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    admin_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, admin_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    target_user_id = result[1]
    
    target_user = database.get_user(target_user_id)
    if target_user and target_user['warnings'] > 0:
        database.update_user(target_user_id, {'warnings': target_user['warnings'] - 1})
    
    database.cursor.execute('DELETE FROM warnings WHERE user_id = ? AND id = (SELECT MAX(id) FROM warnings WHERE user_id = ?)', (target_user_id, target_user_id))
    database.conn.commit()
    
    await message.answer("Предупреждение снято", reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(target_user_id, "С вас снято последнее предупреждение", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_newadmin(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    creator_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, creator_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    new_admin_id = result[1]
    
    await state.set_state(AdminPermState.waiting_perm)
    await state.update_data(new_admin_id=new_admin_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Бан", callback_data="perm_ban")
    builder.button(text="❌ Мут", callback_data="perm_mute")
    builder.button(text="❌ Варн", callback_data="perm_warn")
    builder.button(text="❌ Удаление сообщений", callback_data="perm_del")
    builder.button(text="❌ Управление медиа", callback_data="perm_media")
    builder.button(text="Назначить Co-Owner", callback_data="perm_coowner")
    builder.button(text="✅ Подтвердить", callback_data="perm_confirm")
    builder.button(text="❌ Отмена", callback_data="perm_cancel")
    builder.adjust(2, 2, 2, 1, 1)
    
    await message.answer(
        f"Настройка прав для нового администратора",
        reply_markup=builder.as_markup()
    )

async def handle_admin_perm_callback(query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    new_admin_id = data.get('new_admin_id')
    
    if query.data == "perm_confirm":
        await state.clear()
        
        if not database.get_user(new_admin_id):
            database.cursor.execute('INSERT INTO users (user_id, is_admin) VALUES (?, 1)', (new_admin_id,))
        else:
            database.update_user(new_admin_id, {'is_admin': 1})
        
        database.conn.commit()
        
        await query.message.edit_text(f"Пользователь назначен администратором!")
        
        try:
            await bot.send_message(new_admin_id, "Вы были назначены администратором. Подробнее - /help", 
                                   reply_markup=keyboards.create_system_keyboard())
        except:
            pass
        
        await query.answer()
        return
    
    if query.data == "perm_cancel":
        await state.clear()
        await query.message.edit_text("Отменено")
        await query.answer()
        return
    
    if query.data == "perm_coowner":
        await state.clear()
        
        if not database.get_user(new_admin_id):
            database.cursor.execute('INSERT INTO users (user_id, is_coowner) VALUES (?, 1)', (new_admin_id,))
        else:
            database.update_user(new_admin_id, {'is_coowner': 1})
        
        database.conn.commit()
        
        await query.message.edit_text(f"Пользователь {new_admin_id} назначен Co-Owner!")
        
        try:
            await bot.send_message(new_admin_id, "Вам были выданы права Co-Owner. Подробнее - /help", 
                                   reply_markup=keyboards.create_system_keyboard())
        except:
            pass
        
        await query.answer()
        return
    
    perm_map = {
        "perm_ban": ("❌ Бан", "✅ Бан"),
        "perm_mute": ("❌ Мут", "✅ Мут"),
        "perm_warn": ("❌ Варн", "✅ Варн"),
        "perm_del": ("❌ Удаление сообщений", "✅ Удаление сообщений"),
        "perm_media": ("❌ Управление медиа", "✅ Управление медиа")
    }
    
    current_text = None
    for btn in query.message.reply_markup.inline_keyboard:
        for button in btn:
            if button.callback_data == query.data:
                current_text = button.text
                break
    
    if current_text in perm_map.values():
        for perm, texts in perm_map.items():
            if current_text == texts[0] or current_text == texts[1]:
                new_text = texts[1] if current_text == texts[0] else texts[0]
                break
    else:
        new_text = perm_map[query.data][1]
    
    builder = InlineKeyboardBuilder()
    for btn in query.message.reply_markup.inline_keyboard:
        for button in btn:
            if button.callback_data == query.data:
                builder.button(text=new_text, callback_data=button.callback_data)
            else:
                builder.button(text=button.text, callback_data=button.callback_data)
    
    builder.adjust(2, 2, 2, 1, 1)
    
    try:
        await query.message.edit_reply_markup(reply_markup=builder.as_markup())
    except:
        pass
    
    await query.answer()

async def handle_banadmin(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    if not message.reply_to_message:
        await message.answer("Команда должна быть отправлена в ответ на сообщение!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    replied_message_id = message.reply_to_message.message_id
    creator_id = message.from_user.id
    
    result = database.get_original_message_info(replied_message_id, creator_id)
    
    if not result:
        await message.answer("Не удалось найти автора сообщения!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    admin_id = result[1]
    
    if admin_id == creator_id:
        await message.answer("Нельзя забанить самого себя!", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    database.update_user(admin_id, {'is_admin': 0, 'is_coowner': 0})
    
    await message.answer("Администратор удален", reply_markup=keyboards.create_system_keyboard())
    
    try:
        await bot.send_message(admin_id, "Вы были сняты с должности администратора", 
                               reply_markup=keyboards.create_system_keyboard())
    except:
        pass

async def handle_broadcast(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    await state.set_state(BroadcastState.waiting_confirm)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="Отправить всем", callback_data="confirm_bc")
    builder.button(text="Отмена", callback_data="cancel_bc")
    
    broadcast_text = ""
    if message.text:
        broadcast_text = message.text.replace("/bc", "", 1).strip()
    
    try:
        if message.photo:
            await bot.send_photo(
                message.from_user.id,
                message.photo[-1].file_id,
                caption=f"Подтвердите рассылку:\n\n{broadcast_text}" if broadcast_text else "Подтвердите рассылку:",
                reply_markup=builder.as_markup()
            )
        elif message.video:
            await bot.send_video(
                message.from_user.id,
                message.video.file_id,
                caption=f"Подтвердите рассылку:\n\n{broadcast_text}" if broadcast_text else "Подтвердите рассылку:",
                reply_markup=builder.as_markup()
            )
        elif message.document:
            await bot.send_document(
                message.from_user.id,
                message.document.file_id,
                caption=f"Подтвердите рассылку:\n\n{broadcast_text}" if broadcast_text else "Подтвердите рассылку:",
                reply_markup=builder.as_markup()
            )
        elif message.text:
            await bot.send_message(
                message.from_user.id,
                f"Подтвердите рассылку:\n\n{broadcast_text}",
                reply_markup=builder.as_markup()
            )
        else:
            await message.copy_to(message.from_user.id, caption="Подтвердите рассылку:", reply_markup=builder.as_markup())
    except Exception as e:
        await message.answer(f"Ошибка при создании предпросмотра: {e}", 
                             reply_markup=keyboards.create_system_keyboard())
        await state.clear()
        return
    
    await state.update_data(
        broadcast_message=message,
        broadcast_text=broadcast_text
    )
    
    await message.answer("Сообщение отправлено для подтверждения", 
                         reply_markup=keyboards.create_system_keyboard())

async def confirm_broadcast_callback(query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    
    broadcast_message = data.get('broadcast_message')
    broadcast_text = data.get('broadcast_text', '')
    
    if not broadcast_message:
        try:
            await query.message.edit_text("Ошибка: сообщение не найдено")
        except:
            pass
        return
    
    try:
        if query.message.photo:
            await query.message.edit_caption(caption="Начинаю рассылку...")
        else:
            await query.message.edit_text("Начинаю рассылку...")
    except:
        pass
    
    builder = InlineKeyboardBuilder()
    builder.button(text="SYSTEM MESSAGE", url="https://t.me/FerumEA_terms/4")
    
    users = database.get_active_users()
    
    success = 0
    failed = 0
    
    for user_id in users:
        try:
            if broadcast_message.photo:
                msg = await bot.send_photo(
                    user_id,
                    broadcast_message.photo[-1].file_id,
                    caption=broadcast_text,
                    reply_markup=builder.as_markup()
                )
            elif broadcast_message.video:
                msg = await bot.send_video(
                    user_id,
                    broadcast_message.video.file_id,
                    caption=broadcast_text,
                    reply_markup=builder.as_markup()
                )
            elif broadcast_message.document:
                msg = await bot.send_document(
                    user_id,
                    broadcast_message.document.file_id,
                    caption=broadcast_text,
                    reply_markup=builder.as_markup()
                )
            elif broadcast_text:
                msg = await bot.send_message(
                    user_id,
                    broadcast_text,
                    reply_markup=builder.as_markup()
                )
            else:
                msg = await broadcast_message.copy_to(user_id, reply_markup=builder.as_markup())
            
            await bot.pin_chat_message(user_id, msg.message_id, disable_notification=True)
            success += 1
        except Exception as e:
            failed += 1
        
        await asyncio.sleep(0.05)
    
    try:
        if query.message.photo:
            await query.message.edit_caption(
                caption=f"Рассылка завершена\nДоставлено: {success}\nНе доставлено: {failed}"
            )
        else:
            await query.message.edit_text(
                f"Рассылка завершена\nДоставлено: {success}\nНе доставлено: {failed}"
            )
    except:
        pass
    
    await query.answer()

async def cancel_broadcast_callback(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        if query.message.photo:
            await query.message.edit_caption(caption="Рассылка отменена")
        else:
            await query.message.edit_text("Рассылка отменена")
    except:
        pass
    await query.answer()

async def handle_botoff(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    database.set_bot_setting('bot_enabled', '0')
    
    await message.answer("Бот выключен", reply_markup=keyboards.create_system_keyboard())

async def handle_boton(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    database.set_bot_setting('bot_enabled', '1')
    
    await message.answer("Бот включен", reply_markup=keyboards.create_system_keyboard())

async def handle_mediaoff(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /mediaoff [тип]\nТипы: text, photo, video, sticker, gif, poll, file, contact, location, venue, voice, animation", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    media_type = args[1].lower()
    database.set_bot_setting(f'media_{media_type}_enabled', '0')
    
    await message.answer(f"Медиа-тип '{media_type}' отключен", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_mediaon(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /mediaon [тип]\nТипы: text, photo, video, sticker, gif, poll, file, contact, location, venue, voice, animation", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    media_type = args[1].lower()
    database.set_bot_setting(f'media_{media_type}_enabled', '1')
    
    await message.answer(f"Медиа-тип '{media_type}' включен", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_calldown(message: types.Message, rate_limiter, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /calldown [секунды]\nУстанавливает задержку между сообщениями.", 
                             reply_markup=keyboards.create_system_keyboard())
        return
    
    try:
        seconds = float(args[1])
        if seconds < 0.1 or seconds > 10:
            await message.answer("Задержка должна быть от 0.1 до 10 секунд.", 
                                 reply_markup=keyboards.create_system_keyboard())
            return
        
        rate_limiter.cooldown = seconds
        await message.answer(f"Задержка между сообщениями установлена: {seconds} сек.", 
                             reply_markup=keyboards.create_system_keyboard())
    except ValueError:
        await message.answer("Неверный формат числа.", reply_markup=keyboards.create_system_keyboard())

async def show_status(message: types.Message, rate_limiter, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_admin(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    active_users = database.get_total_users()
    total_messages = database.get_total_messages()
    today_messages = database.get_daily_stats()
    
    bot_enabled = database.get_bot_setting('bot_enabled', '1')
    bot_status = "Включен" if bot_enabled == '1' else "Выключен"
    
    status_text = f"📊 Статус бота:\n\n" \
                  f"Статус: {bot_status}\n" \
                  f"Активных пользователей: {active_users}\n" \
                  f"Всего сообщений отправлено: {total_messages}\n" \
                  f"Сообщений сегодня: {today_messages}\n" \
                  f"Задержка сообщений: {rate_limiter.cooldown} сек."
    
    await message.answer(status_text, reply_markup=keyboards.create_system_keyboard())

async def handle_cleanup(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    from datetime import datetime, timedelta
    cutoff_date = datetime.now() - timedelta(days=30)
    
    database.cursor.execute('DELETE FROM messages WHERE created_at < ?', (cutoff_date,))
    database.cursor.execute('DELETE FROM message_map WHERE created_at < ?', (cutoff_date,))
    database.cursor.execute('DELETE FROM stats WHERE date < ?', (cutoff_date.strftime('%Y-%m-%d'),))
    
    deleted_messages = database.cursor.rowcount
    database.conn.commit()
    
    await message.answer(f"Очищено {deleted_messages} старых сообщений", 
                         reply_markup=keyboards.create_system_keyboard())

async def handle_restart(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    user_data = database.get_user(user_id)
    
    if not user_data or not user_data['captcha_passed']:
        await user.send_captcha(message, bot)
        return
    
    if not user.is_creator(user_id):
        await user.send_access_denied(user_id, bot)
        return
    
    await message.answer("Перезапуск бота...", reply_markup=keyboards.create_system_keyboard())
    
    python = sys.executable
    os.execl(python, python, *sys.argv)