import asyncio
import os
import sys
from dotenv import load_dotenv
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode, ChatMemberStatus
import admin
import user
import keyboards
import database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
load_dotenv()

token = os.getenv('token')
if not token:
    logger.error("Token not found in environment variables")
    sys.exit(1)

bot = Bot(token=token)
dp = Dispatcher()

rate_limiter = user.RateLimiter()

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await user.handle_start(message, bot)

@dp.callback_query(F.data.startswith("captcha_"))
async def captcha_callback(query: types.CallbackQuery):
    await user.handle_captcha_callback(query, bot)

@dp.message(Command("help"))
async def help_cmd(message: types.Message):
    await keyboards.show_help_command(message, bot)

@dp.message(Command("rules"))
async def rules_cmd(message: types.Message):
    await user.send_rules(message, bot)

@dp.message(Command("tag"))
async def tag_cmd(message: types.Message):
    await user.handle_tag(message)

@dp.message(Command("ctag"))
async def ctag_cmd(message: types.Message):
    await user.handle_ctag(message)

@dp.message(Command("info"))
async def info_cmd(message: types.Message):
    await user.show_info(message)

@dp.message(Command("top"))
async def top_cmd(message: types.Message):
    await user.show_top(message, bot)

@dp.message(Command("profile"))
async def profile_cmd(message: types.Message):
    await user.show_profile(message, bot)

@dp.message(Command("report"))
async def report_cmd(message: types.Message):
    await admin.handle_report(message, bot)

@dp.message(Command("ignore"))
async def ignore_cmd(message: types.Message):
    await user.handle_ignore(message)

@dp.message(Command("unignore"))
async def unignore_cmd(message: types.Message):
    await user.handle_unignore(message)

@dp.message(Command("protect"))
async def protect_cmd(message: types.Message):
    await user.handle_protect(message)

@dp.message(Command("autodel"))
async def autodel_cmd(message: types.Message):
    await keyboards.show_autodel_options(message)

@dp.message(Command("privacy"))
async def privacy_cmd(message: types.Message):
    await user.send_privacy(message, bot)

@dp.message(Command("ban"))
async def ban_cmd(message: types.Message):
    await admin.handle_ban(message, bot)

@dp.message(Command("unban"))
async def unban_cmd(message: types.Message):
    await admin.handle_unban(message, bot)

@dp.message(Command("mute"))
async def mute_cmd(message: types.Message):
    await admin.handle_mute(message, bot)

@dp.message(Command("unmute"))
async def unmute_cmd(message: types.Message):
    await admin.handle_unmute(message, bot)

@dp.message(Command("del"))
async def delete_cmd(message: types.Message):
    await admin.handle_delete(message, bot)

@dp.message(Command("warn"))
async def warn_cmd(message: types.Message):
    await admin.handle_warn(message, bot)

@dp.message(Command("unwarn"))
async def unwarn_cmd(message: types.Message):
    await admin.handle_unwarn(message, bot)

@dp.message(Command("newadmin"))
async def newadmin_cmd(message: types.Message, state: FSMContext):
    await admin.handle_newadmin(message, state, bot)

@dp.message(Command("banadmin"))
async def banadmin_cmd(message: types.Message):
    await admin.handle_banadmin(message, bot)

@dp.message(Command("bc"))
async def broadcast_cmd(message: types.Message, state: FSMContext):
    await admin.handle_broadcast(message, state, bot)

@dp.message(Command("botoff"))
async def botoff_cmd(message: types.Message):
    await admin.handle_botoff(message, bot)

@dp.message(Command("boton"))
async def boton_cmd(message: types.Message):
    await admin.handle_boton(message, bot)

@dp.message(Command("mediaoff"))
async def mediaoff_cmd(message: types.Message):
    await admin.handle_mediaoff(message, bot)

@dp.message(Command("mediaon"))
async def mediaon_cmd(message: types.Message):
    await admin.handle_mediaon(message, bot)

@dp.message(Command("calldown"))
async def calldown_cmd(message: types.Message):
    await admin.handle_calldown(message, rate_limiter, bot)

@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    await admin.show_status(message, rate_limiter, bot)

@dp.message(Command("cleanup"))
async def cleanup_cmd(message: types.Message):
    await admin.handle_cleanup(message, bot)

@dp.message(Command("leave"))
async def leave_cmd(message: types.Message):
    await user.handle_leave(message, bot)

@dp.message(Command("restart"))
async def restart_cmd(message: types.Message):
    await admin.handle_restart(message, bot)

@dp.callback_query(F.data.startswith("help_"))
async def help_callback(query: types.CallbackQuery):
    await keyboards.show_help_detail(query, bot)

@dp.callback_query(F.data.startswith("tog"))
async def tag_callback(query: types.CallbackQuery):
    await user.handle_tag_callback(query)

@dp.callback_query(F.data.startswith("autodel_"))
async def autodel_callback(query: types.CallbackQuery):
    await user.handle_autodel_callback(query)

@dp.callback_query(F.data.startswith("delmy_"))
async def delete_my_callback(query: types.CallbackQuery):
    await user.handle_delete_my_callback(query, bot)

@dp.callback_query(F.data == "delthis")
async def delthis_callback(query: types.CallbackQuery):
    await user.handle_delthis_callback(query)

@dp.callback_query(F.data == "none")
async def none_callback(query: types.CallbackQuery):
    await query.answer()

@dp.callback_query(F.data.startswith("perm_"), admin.AdminPermState.waiting_perm)
async def admin_perm_callback(query: types.CallbackQuery, state: FSMContext):
    await admin.handle_admin_perm_callback(query, state, bot)

@dp.callback_query(F.data == "confirm_bc", admin.BroadcastState.waiting_confirm)
async def confirm_bc_callback(query: types.CallbackQuery, state: FSMContext):
    await admin.confirm_broadcast_callback(query, state, bot)

@dp.callback_query(F.data == "cancel_bc", admin.BroadcastState.waiting_confirm)
async def cancel_bc_callback(query: types.CallbackQuery, state: FSMContext):
    await admin.cancel_broadcast_callback(query, state)

@dp.callback_query(F.data.startswith("leave_yes:"))
async def leave_yes_callback(query: types.CallbackQuery):
    await user.handle_leave_yes(query)

@dp.callback_query(F.data == "leave_no")
async def leave_no_callback(query: types.CallbackQuery):
    await user.handle_leave_no(query)

@dp.message(F.content_type.in_(['text', 'photo', 'video', 'sticker', 'animation', 'document', 'voice', 'poll', 'contact', 'location', 'venue']))
async def handle_msg(message: types.Message):
    await user.handle_message(message, bot, rate_limiter)

@dp.edited_message(F.content_type.in_(['text', 'photo', 'video', 'document', 'animation', 'voice']))
async def handle_edit(message: types.Message):
    await user.handle_message_edit(message, bot)

@dp.message_reaction()
async def handle_reaction(reaction: types.MessageReactionUpdated):
    await user.handle_message_reaction(reaction, bot)

@dp.message(F.paid_media_purchased)
async def handle_paid_purchase(message: types.Message):
    await user.handle_paid_media_purchase(message, bot)

@dp.my_chat_member()
async def handle_chat_member(update: types.ChatMemberUpdated):
    if update.new_chat_member.status == ChatMemberStatus.KICKED:
        database.delete_user_data(update.from_user.id)

async def autodel_task():
    while True:
        await asyncio.sleep(60)
        database.cleanup_old_messages()

async def setup_webhook():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")

async def main():
    logger.info("Starting bot...")
    await setup_webhook()
    database.initialize_database()
    autodel_task_obj = asyncio.create_task(autodel_task())
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(e)
    finally:
        autodel_task_obj.cancel()
        try:
            await autodel_task_obj
        except asyncio.CancelledError:
            pass
        await bot.session.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        sys.exit(1)