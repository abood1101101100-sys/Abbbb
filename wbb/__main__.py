"""
MIT License

Copyright (c) 2024 TheHamkerCat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import asyncio
import importlib
import re
from contextlib import suppress

from pyrogram import filters, idle
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


import wbb
from wbb import app, log
from wbb.server import start_server
from wbb.core.keyboard import ikb
from wbb.modules import ALL_MODULES
from wbb.modules.sudoers import bot_sys_stats
from wbb.utils import paginate_modules
from wbb.utils.constants import MARKDOWN
from wbb.utils.dbfunctions import clean_restart_stage, get_rules
from wbb.utils.functions import extract_text_and_keyb

HELPABLE = {}


async def start_bot():
    global HELPABLE

    # تشغيل الـ server أولاً حتى يكتشف Render الـ port
    await start_server()
    # تهيئة البوت
    await wbb.initialize()

    # الآن يمكن استخدام المتغيرات بعد initialize()
    BOT_NAME = wbb.BOT_NAME
    BOT_USERNAME = wbb.BOT_USERNAME
    LOG_GROUP_ID = wbb.LOG_GROUP_ID
    USERBOT_NAME = wbb.USERBOT_NAME
    aiohttpsession = wbb.aiohttpsession

    for module in ALL_MODULES:
        imported_module = importlib.import_module("wbb.modules." + module)
        if (
            hasattr(imported_module, "__MODULE__")
            and imported_module.__MODULE__
        ):
            imported_module.__MODULE__ = imported_module.__MODULE__
            if (
                hasattr(imported_module, "__HELP__")
                and imported_module.__HELP__
            ):
                HELPABLE[
                    imported_module.__MODULE__.replace(" ", "_").lower()
                ] = imported_module

    bot_modules = ""
    j = 1
    for i in ALL_MODULES:
        if j == 4:
            bot_modules += "|{:<15}|\n".format(i)
            j = 0
        else:
            bot_modules += "|{:<15}".format(i)
        j += 1

    print("+===============================================================+")
    print("|                              WBB                              |")
    print("+===============+===============+===============+===============+")
    print(bot_modules)
    print("+===============+===============+===============+===============+")
    log.info(f"BOT STARTED AS {BOT_NAME}!")
    log.info(f"USERBOT STARTED AS {USERBOT_NAME}!")

    restart_data = await clean_restart_stage()

    try:
        log.info("Sending online status")
        if restart_data:
            await app.edit_message_text(
                restart_data["chat_id"],
                restart_data["message_id"],
                "**Restarted Successfully**",
            )
        else:
            await app.send_message(LOG_GROUP_ID, "✅ البوت يعمل الآن!")
    except Exception:
        pass

    await idle()

    await aiohttpsession.close()
    log.info("Stopping clients")
    await app.stop()
    log.info("Cancelling asyncio tasks")
    for task in asyncio.all_tasks():
        task.cancel()
    log.info("Dead!")


@app.on_message(filters.command("start", prefixes="/!"))
async def start(_, message):
    BOT_NAME = wbb.BOT_NAME
    BOT_USERNAME = wbb.BOT_USERNAME

    home_keyboard_pm = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="الأوامر ❓", callback_data="bot_commands"
                ),
                InlineKeyboardButton(
                    text="المستودع 🛠",
                    url="https://github.com/thehamkercat/WilliamButcherBot",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="إحصائيات النظام 🖥",
                    callback_data="stats_callback",
                ),
                InlineKeyboardButton(
                    text="الدعم 👨", url="http://t.me/WBBSupport"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="أضفني لمجموعتك 🎉",
                    url=f"http://t.me/{BOT_USERNAME}?startgroup=new",
                )
            ],
        ]
    )

    home_text_pm = (
        f"مرحباً! أنا {BOT_NAME}. يمكنني إدارة مجموعتك "
        + "بالكثير من الميزات المفيدة. "
        + "أضفني إلى مجموعتك الآن!"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="المساعدة ❓",
                    url=f"t.me/{BOT_USERNAME}?start=help",
                ),
                InlineKeyboardButton(
                    text="المستودع 🛠",
                    url="https://github.com/thehamkercat/WilliamButcherBot",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="إحصائيات النظام 💻",
                    callback_data="stats_callback",
                ),
                InlineKeyboardButton(text="الدعم 👨", url="t.me/WBBSupport"),
            ],
        ]
    )

    FED_MARKUP = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "أوامر مالك الفيدرالية", callback_data="fed_owner"
                ),
                InlineKeyboardButton(
                    "أوامر مشرف الفيدرالية", callback_data="fed_admin"
                ),
            ],
            [
                InlineKeyboardButton("أوامر المستخدم", callback_data="fed_user"),
            ],
            [
                InlineKeyboardButton("رجوع", callback_data="help_back"),
            ],
        ]
    )

    if message.chat.type != ChatType.PRIVATE:
        return await message.reply(
            "راسلني في الخاص لمزيد من التفاصيل.", reply_markup=keyboard
        )
    if len(message.text.split()) > 1:
        user = await app.get_users(message.from_user.id)
        name = (message.text.split(None, 1)[1]).lower()
        match = re.match(r"rules_(.*)", name)
        if match:
            chat_id = match.group(1)
            user_id = message.from_user.id
            chat = await app.get_chat(int(chat_id))
            text = f"**The rules for `{chat.title}` are:\n\n**"
            rules = await get_rules(int(chat_id))
            if rules:
                text = text + rules
                if "{chat}" in text:
                    text = text.replace("{chat}", chat.title)
                if "{name}" in text:
                    text = text.replace("{name}", user.mention)
                keyb = None
                if re.findall(r"\[.+\,.+\]", text):
                    text, keyb = extract_text_and_keyb(ikb, text)
                await app.send_message(user_id, text=text, reply_markup=keyb)
            else:
                return await app.send_message(
                    user_id,
                    "لم يقم مشرفو المجموعة بتعيين قواعد بعد.\nهذا لا يعني أنه لا توجد قوانين!",
                )
        if name == "mkdwn_help":
            await message.reply(
                MARKDOWN,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        elif "_" in name:
            module = name.split("_", 1)[1]
            text = (
                f"مساعدة قسم **{HELPABLE[module].__MODULE__}**:\n"
                + HELPABLE[module].__HELP__
            )
            if module == "federation":
                return await message.reply(
                    text=text,
                    reply_markup=FED_MARKUP,
                    disable_web_page_preview=True,
                )
            await message.reply(
                text,
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("رجوع", callback_data="help_back")]]
                ),
                disable_web_page_preview=True,
            )
        elif name == "help":
            text, keyb = await help_parser(message.from_user.first_name)
            await message.reply(text, reply_markup=keyb)
    else:
        await message.reply(home_text_pm, reply_markup=home_keyboard_pm)
    return


@app.on_message(filters.command("help", prefixes="/!"))
async def help_command(_, message):
    BOT_USERNAME = wbb.BOT_USERNAME

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="المساعدة ❓",
                    url=f"t.me/{BOT_USERNAME}?start=help",
                ),
                InlineKeyboardButton(
                    text="المستودع 🛠",
                    url="https://github.com/thehamkercat/WilliamButcherBot",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="إحصائيات النظام 💻",
                    callback_data="stats_callback",
                ),
                InlineKeyboardButton(text="الدعم 👨", url="t.me/WBBSupport"),
            ],
        ]
    )

    if message.chat.type != ChatType.PRIVATE:
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                key = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text="اضغط هنا",
                                url=f"t.me/{BOT_USERNAME}?start=help_{name}",
                            )
                        ],
                    ]
                )
                await message.reply(
                    f"اضغط على الزر أدناه للحصول على مساعدة حول {name}",
                    reply_markup=key,
                )
            else:
                await message.reply(
                    "راسلني في الخاص لمزيد من التفاصيل.", reply_markup=keyboard
                )
        else:
            await message.reply(
                "راسلني في الخاص لمزيد من التفاصيل.", reply_markup=keyboard
            )
    else:
        if len(message.command) >= 2:
            name = (message.text.split(None, 1)[1]).replace(" ", "_").lower()
            if str(name) in HELPABLE:
                text = (
                    f"مساعدة قسم **{HELPABLE[name].__MODULE__}**:\n"
                    + HELPABLE[name].__HELP__
                )
                await message.reply(text, disable_web_page_preview=True)
            else:
                text, help_keyboard = await help_parser(
                    message.from_user.first_name
                )
                await message.reply(
                    text,
                    reply_markup=help_keyboard,
                    disable_web_page_preview=True,
                )
        else:
            text, help_keyboard = await help_parser(
                message.from_user.first_name
            )
            await message.reply(
                text, reply_markup=help_keyboard, disable_web_page_preview=True
            )
    return


async def help_parser(name, keyboard=None):
    BOT_NAME = wbb.BOT_NAME
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE, "help"))
    return (
        """مرحباً {first_name}! أنا {bot_name}.
بوت لإدارة المجموعات بميزات مفيدة.
اختر قسماً من الأقسام أدناه.
يمكنك أيضاً طرح أي سؤال في مجموعة الدعم.
""".format(
            first_name=name,
            bot_name=BOT_NAME,
        ),
        keyboard,
    )


@app.on_callback_query(filters.regex("bot_commands"))
async def commands_callbacc(_, CallbackQuery):
    text, keyboard = await help_parser(CallbackQuery.from_user.mention)
    await app.send_message(
        CallbackQuery.message.chat.id,
        text=text,
        reply_markup=keyboard,
    )
    await CallbackQuery.message.delete()


@app.on_callback_query(filters.regex("stats_callback"))
async def stats_callbacc(_, CallbackQuery):
    text = await bot_sys_stats()
    await app.answer_callback_query(CallbackQuery.id, text, show_alert=True)


@app.on_callback_query(filters.regex(r"help_(.*?)"))
async def help_button(client, query):
    BOT_NAME = wbb.BOT_NAME

    home_match = re.match(r"help_home\((.+?)\)", query.data)
    mod_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_match = re.match(r"help_next\((.+?)\)", query.data)
    back_match = re.match(r"help_back", query.data)
    create_match = re.match(r"help_create", query.data)

    top_text = f"""
مرحباً {query.from_user.first_name}! أنا {BOT_NAME}.
بوت لإدارة المجموعات بميزات مفيدة.
اختر قسماً من الأقسام أدناه.

الأوامر الأساسية:
 - /start أو !start — تشغيل البوت
 - /help أو !help — عرض هذه الرسالة
 """

    FED_MARKUP = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "أوامر مالك الفيدرالية", callback_data="fed_owner"
                ),
                InlineKeyboardButton(
                    "أوامر مشرف الفيدرالية", callback_data="fed_admin"
                ),
            ],
            [
                InlineKeyboardButton("أوامر المستخدم", callback_data="fed_user"),
            ],
            [
                InlineKeyboardButton("رجوع", callback_data="help_back"),
            ],
        ]
    )

    if mod_match:
        module = (mod_match.group(1)).replace(" ", "_")
        text = (
            "{} **{}**:\n".format("مساعدة قسم", HELPABLE[module].__MODULE__)
            + HELPABLE[module].__HELP__
        )
        if module == "federation":
            return await query.message.edit(
                text=text,
                reply_markup=FED_MARKUP,
                disable_web_page_preview=True,
            )
        await query.message.edit(
            text=text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("رجوع", callback_data="help_back")]]
            ),
            disable_web_page_preview=True,
        )
    elif home_match:
        BOT_USERNAME = wbb.BOT_USERNAME
        home_keyboard_pm = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="الأوامر ❓", callback_data="bot_commands"
                    ),
                    InlineKeyboardButton(
                        text="المستودع 🛠",
                        url="https://github.com/thehamkercat/WilliamButcherBot",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="إحصائيات النظام 🖥",
                        callback_data="stats_callback",
                    ),
                    InlineKeyboardButton(
                        text="الدعم 👨", url="http://t.me/WBBSupport"
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="أضفني لمجموعتك 🎉",
                        url=f"http://t.me/{BOT_USERNAME}?startgroup=new",
                    )
                ],
            ]
        )
        home_text_pm = (
            f"مرحباً! أنا {BOT_NAME}. يمكنني إدارة مجموعتك "
            + "بالكثير من الميزات المفيدة. "
            + "أضفني إلى مجموعتك الآن!"
        )
        await app.send_message(
            query.from_user.id,
            text=home_text_pm,
            reply_markup=home_keyboard_pm,
        )
        await query.message.delete()
    elif prev_match:
        curr_page = int(prev_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(curr_page - 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )
    elif next_match:
        next_page = int(next_match.group(1))
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(next_page + 1, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )
    elif back_match:
        await query.message.edit(
            text=top_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(0, HELPABLE, "help")
            ),
            disable_web_page_preview=True,
        )
    elif create_match:
        text, keyboard = await help_parser(query)
        await query.message.edit(
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    return await client.answer_callback_query(query.id)


def handle_task_exception(loop, context):
    exc = context.get("exception")
    if isinstance(exc, ValueError) and "Peer id invalid" in str(exc):
        return  # تجاهل خطأ الـ peer غير المعروف بصمت
    loop.default_exception_handler(context)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(handle_task_exception)
    with suppress(asyncio.exceptions.CancelledError):
        loop.run_until_complete(start_bot())
