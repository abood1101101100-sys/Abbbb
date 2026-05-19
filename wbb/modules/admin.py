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
import re
from contextlib import suppress
from time import time

from pyrogram import filters
from pyrogram.enums import ChatMembersFilter, ChatMemberStatus, ChatType
from pyrogram.errors import FloodWait
from pyrogram.types import (
    CallbackQuery,
    ChatMemberUpdated,
    ChatPermissions,
    ChatPrivileges,
    Message,
)

from wbb import BOT_ID, SUDOERS, app, log
from wbb.core.decorators.errors import capture_err
from wbb.core.keyboard import ikb
from wbb.utils.dbfunctions import (
    add_warn,
    get_warn,
    int_to_alpha,
    remove_warns,
    save_filter,
)
from wbb.utils.functions import (
    extract_user,
    extract_user_and_reason,
    time_converter,
)

__MODULE__ = "الإدارة"
__HELP__ = """/ban - حظر مستخدم
/dban - حذف الرسالة وحظر مرسلها
/tban - حظر مؤقت لمستخدم
/unban - رفع الحظر عن مستخدم
/warn - تحذير مستخدم
/dwarn - حذف الرسالة وتحذير مرسلها
/rmwarns - إزالة جميع تحذيرات مستخدم
/warns - عرض تحذيرات مستخدم
/kick - طرد مستخدم
/dkick - حذف الرسالة وطرد مرسلها
/purge - تنظيف الرسائل
/del - حذف رسالة محددة
/promote - ترقية عضو
/fullpromote - ترقية عضو بكامل الصلاحيات
/demote - تخفيض رتبة عضو
/pin - تثبيت رسالة
/mute - كتم مستخدم
/tmute - كتم مؤقت لمستخدم
/unmute - رفع الكتم عن مستخدم
/ban_ghosts - حظر الحسابات المحذوفة
/report | @admins | @admin - الإبلاغ عن رسالة للمشرفين
/invite - إرسال رابط دعوة المجموعة"""


async def member_permissions(chat_id: int, user_id: int):
    perms = []
    member = (await app.get_chat_member(chat_id, user_id)).privileges
    if not member:
        return []
    if member.can_post_messages:
        perms.append("can_post_messages")
    if member.can_edit_messages:
        perms.append("can_edit_messages")
    if member.can_delete_messages:
        perms.append("can_delete_messages")
    if member.can_restrict_members:
        perms.append("can_restrict_members")
    if member.can_promote_members:
        perms.append("can_promote_members")
    if member.can_change_info:
        perms.append("can_change_info")
    if member.can_invite_users:
        perms.append("can_invite_users")
    if member.can_pin_messages:
        perms.append("can_pin_messages")
    if member.can_manage_video_chats:
        perms.append("can_manage_video_chats")
    return perms


from wbb.core.decorators.permissions import adminsOnly

admins_in_chat = {}


async def list_admins(chat_id: int):
    global admins_in_chat
    if chat_id in admins_in_chat:
        interval = time() - admins_in_chat[chat_id]["last_updated_at"]
        if interval < 3600:
            return admins_in_chat[chat_id]["data"]

    admins_in_chat[chat_id] = {
        "last_updated_at": time(),
        "data": [
            member.user.id
            async for member in app.get_chat_members(
                chat_id, filter=ChatMembersFilter.ADMINISTRATORS
            )
        ],
    }
    return admins_in_chat[chat_id]["data"]


# Admin cache reload


@app.on_chat_member_updated()
async def admin_cache_func(_, cmu: ChatMemberUpdated):
    if cmu.old_chat_member and cmu.old_chat_member.promoted_by:
        admins_in_chat[cmu.chat.id] = {
            "last_updated_at": time(),
            "data": [
                member.user.id
                async for member in app.get_chat_members(
                    cmu.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
                )
            ],
        }
        log.info(f"Updated admin cache for {cmu.chat.id} [{cmu.chat.title}]")


# Purge Messages


@app.on_message(filters.command("purge", prefixes="/!") & ~filters.private)
@adminsOnly("can_delete_messages")
async def purgeFunc(_, message: Message):
    repliedmsg = message.reply_to_message
    await message.delete()

    if not repliedmsg:
        return await message.reply_text("ردّ على رسالة لتنظيف الرسائل من هناك.")

    cmd = message.command
    if len(cmd) > 1 and cmd[1].isdigit():
        purge_to = repliedmsg.id + int(cmd[1])
        if purge_to > message.id:
            purge_to = message.id
    else:
        purge_to = message.id

    chat_id = message.chat.id
    message_ids = []

    for message_id in range(
        repliedmsg.id,
        purge_to,
    ):
        message_ids.append(message_id)

        # Max message deletion limit is 100
        if len(message_ids) == 100:
            await app.delete_messages(
                chat_id=chat_id,
                message_ids=message_ids,
                revoke=True,  # For both sides
            )

            # To delete more than 100 messages, start again
            message_ids = []

    # Delete if any messages left
    if len(message_ids) > 0:
        await app.delete_messages(
            chat_id=chat_id,
            message_ids=message_ids,
            revoke=True,
        )


# Kick members


@app.on_message(filters.command(["kick", "dkick"], prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def kickFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "لا أستطيع طرد نفسي، يمكنني المغادرة إن أردت."
        )
    if user_id in SUDOERS:
        return await message.reply_text("تريد طرد شخص مميّز؟ لا يمكنني فعل ذلك.")
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "لا أستطيع طرد مشرف، أنت تعرف القواعد كما أعرفها."
        )
    mention = (await app.get_users(user_id)).mention
    msg = f"""
**Kicked User:** {mention}
**Kicked By:** {message.from_user.mention if message.from_user else 'Anon'}
**السبب:** {reason or 'لم يُذكر سبب.'}"""
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    await message.chat.ban_member(user_id)
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(msg)
    await asyncio.sleep(1)
    await message.chat.unban_member(user_id)


# Ban members


@app.on_message(filters.command(["ban", "dban", "tban"], prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def banFunc(_, message: Message):
    user_id, reason = await extract_user_and_reason(message, sender_chat=True)

    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "لا أستطيع حظر نفسي، يمكنني المغادرة إن أردت."
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "تريد حظر شخص مميّز؟ أعد التفكير!"
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "لا أستطيع حظر مشرف، أنت تعرف القواعد كما أعرفها."
        )

    try:
        mention = (await app.get_users(user_id)).mention
    except IndexError:
        mention = (
            message.reply_to_message.sender_chat.title
            if message.reply_to_message
            else "Anon"
        )

    msg = (
        f"**Banned User:** {mention}\n"
        f"**Banned By:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if message.command[0] == "tban":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_ban = await time_converter(message, time_value)
        msg += f"**Banned For:** {time_value}\n"
        if temp_reason:
            msg += f"**السبب:** {temp_reason}"
        with suppress(AttributeError):
            if len(time_value[:-1]) < 3:
                await message.chat.ban_member(user_id, until_date=temp_ban)
                replied_message = message.reply_to_message
                if replied_message:
                    message = replied_message
                await message.reply_text(msg)
            else:
                await message.reply_text("لا يمكنك استخدام أكثر من 99.")
        return
    if reason:
        msg += f"**السبب:** {reason}"
    await message.chat.ban_member(user_id)
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(msg)


# Unban members


@app.on_message(filters.command("unban", prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def unban_func(_, message: Message):
    # we don't need reasons for unban, also, we
    # don't need to get "text_mention" entity, because
    # normal users won't get text_mention if the user
    # they want to unban is not in the group.
    reply = message.reply_to_message

    if reply and reply.sender_chat and reply.sender_chat != message.chat.id:
        return await message.reply_text("لا يمكنك إلغاء حظر قناة.")

    if len(message.command) == 2:
        user = message.text.split(None, 1)[1]
    elif len(message.command) == 1 and reply:
        user = message.reply_to_message.from_user.id
    else:
        return await message.reply_text(
            "أرسل معرّف المستخدم أو ردّ على رسالته لإلغاء الحظر."
        )
    await message.chat.unban_member(user)
    umention = (await app.get_users(user)).mention
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(f"✅ تم رفع الحظر عن {umention}")


# Ban users listed in a message


@app.on_message(SUDOERS & filters.command("listban", prefixes="/!") & ~filters.private)
async def list_ban_(c, message: Message):
    userid, msglink_reason = await extract_user_and_reason(message)
    if not userid or not msglink_reason:
        return await message.reply_text(
            "أرسل معرّف المستخدم مع رابط الرسالة والسبب لحظر جماعي."
        )
    if (
        len(msglink_reason.split(" ")) == 1
    ):  # message link included with the reason
        return await message.reply_text(
            "يجب تقديم سبب للحظر الجماعي."
        )
    # seperate messge link from reason
    lreason = msglink_reason.split()
    messagelink, reason = lreason[0], " ".join(lreason[1:])

    if not re.search(
        r"(https?://)?t(elegram)?\.me/\w+/\d+", messagelink
    ):  # validate link
        return await message.reply_text("رابط الرسالة غير صالح.")

    if userid == BOT_ID:
        return await message.reply_text("لا أستطيع حظر نفسي.")
    if userid in SUDOERS:
        return await message.reply_text(
            "تريد حظر شخص مميّز؟ أعد التفكير!"
        )
    splitted = messagelink.split("/")
    uname, mid = splitted[-2], int(splitted[-1])
    m = await message.reply_text(
        "`Banning User from multiple groups. \
         This may take some time`"
    )
    try:
        msgtext = (await app.get_messages(uname, mid)).text
        gusernames = re.findall(r"@\\w+", msgtext)
    except:
        return await m.edit_text("تعذّر الحصول على معرّفات المجموعات.")
    count = 0
    for username in gusernames:
        try:
            await app.ban_chat_member(username.strip("@"), userid)
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except:
            continue
        count += 1
    mention = (await app.get_users(userid)).mention

    msg = f"""
**List-Banned User:** {mention}
**Banned User ID:** `{userid}`
**Admin:** {message.from_user.mention}
**Affected chats:** `{count}`
**السبب:** {reason}
"""
    await m.edit_text(msg)


# Unban users listed in a message


@app.on_message(SUDOERS & filters.command("listunban", prefixes="/!") & ~filters.private)
async def list_unban_(c, message: Message):
    userid, msglink = await extract_user_and_reason(message)
    if not userid or not msglink:
        return await message.reply_text(
            "أرسل معرّف المستخدم مع رابط الرسالة لإلغاء الحظر الجماعي."
        )

    if not re.search(
        r"(https?://)?t(elegram)?\.me/\w+/\d+", msglink
    ):  # validate link
        return await message.reply_text("رابط الرسالة غير صالح.")

    splitted = msglink.split("/")
    uname, mid = splitted[-2], int(splitted[-1])
    m = await message.reply_text(
        "`Unbanning User from multiple groups. \
         This may take some time`"
    )
    try:
        msgtext = (await app.get_messages(uname, mid)).text
        gusernames = re.findall(r"@\\w+", msgtext)
    except:
        return await m.edit_text("تعذّر الحصول على معرّفات المجموعات.")
    count = 0
    for username in gusernames:
        try:
            await app.unban_chat_member(username.strip("@"), userid)
            await asyncio.sleep(1)
        except FloodWait as e:
            await asyncio.sleep(e.x)
        except:
            continue
        count += 1
    mention = (await app.get_users(userid)).mention
    msg = f"""
**List-Unbanned User:** {mention}
**Unbanned User ID:** `{userid}`
**Admin:** {message.from_user.mention}
**Affected chats:** `{count}`
"""
    await m.edit_text(msg)


# Delete messages


@app.on_message(filters.command("del", prefixes="/!") & ~filters.private)
@adminsOnly("can_delete_messages")
async def deleteFunc(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ردّ على رسالة لحذفها.")
    await message.reply_to_message.delete()
    await message.delete()


# Promote Members


@app.on_message(filters.command(["promote", "fullpromote"], prefixes="/!") & ~filters.private)
@adminsOnly("can_promote_members")
async def promoteFunc(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")

    bot = (await app.get_chat_member(message.chat.id, BOT_ID)).privileges
    if user_id == BOT_ID:
        return await message.reply_text("لا أستطيع ترقية نفسي.")
    if not bot:
        return await message.reply_text("لست مشرفًا في هذه المحادثة.")
    if not bot.can_promote_members:
        return await message.reply_text("ليس لديّ صلاحيات كافية.")

    umention = (await app.get_users(user_id)).mention

    if message.command[0][0] == "f":
        await message.chat.promote_member(
            user_id=user_id,
            privileges=ChatPrivileges(
                can_change_info=bot.can_change_info,
                can_invite_users=bot.can_invite_users,
                can_delete_messages=bot.can_delete_messages,
                can_restrict_members=bot.can_restrict_members,
                can_pin_messages=bot.can_pin_messages,
                can_promote_members=bot.can_promote_members,
                can_manage_chat=bot.can_manage_chat,
                can_manage_video_chats=bot.can_manage_video_chats,
            ),
        )
        return await message.reply_text(f"✅ تمت الترقية الكاملة! {umention}")

    await message.chat.promote_member(
        user_id=user_id,
        privileges=ChatPrivileges(
            can_change_info=False,
            can_invite_users=bot.can_invite_users,
            can_delete_messages=bot.can_delete_messages,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=bot.can_manage_chat,
            can_manage_video_chats=bot.can_manage_video_chats,
        ),
    )
    await message.reply_text(f"✅ تمت الترقية! {umention}")


# Demote Member


@app.on_message(filters.command("demote", prefixes="/!") & ~filters.private)
@adminsOnly("can_promote_members")
async def demote(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    if user_id == BOT_ID:
        return await message.reply_text("لا أستطيع تخفيض رتبة نفسي.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "تريد تخفيض رتبة شخص مميّز؟ أعد التفكير!"
        )
    try:
        member = await app.get_chat_member(message.chat.id, user_id)
        if member.status == ChatMemberStatus.ADMINISTRATOR:
            await message.chat.promote_member(
                user_id=user_id,
                privileges=ChatPrivileges(
                    can_change_info=False,
                    can_invite_users=False,
                    can_delete_messages=False,
                    can_restrict_members=False,
                    can_pin_messages=False,
                    can_promote_members=False,
                    can_manage_chat=False,
                    can_manage_video_chats=False,
                ),
            )
            umention = (await app.get_users(user_id)).mention
            await message.reply_text(f"✅ تم التخفيض! {umention}")
        else:
            await message.reply_text(
                "الشخص الذي ذكرته ليس مشرفًا."
            )
    except Exception as e:
        await message.reply_text(e)


# Pin Messages


@app.on_message(filters.command(["pin", "unpin"], prefixes="/!") & ~filters.private)
@adminsOnly("can_pin_messages")
async def pin(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("ردّ على رسالة لتثبيتها أو إلغاء تثبيتها.")
    r = message.reply_to_message
    if message.command[0][0] == "u":
        await r.unpin()
        return await message.reply_text(
            f"**Unpinned [this]({r.link}) message.**",
            disable_web_page_preview=True,
        )
    await r.pin(disable_notification=True)
    await message.reply(
        f"**Pinned [this]({r.link}) message.**",
        disable_web_page_preview=True,
    )
    msg = "Please check the pinned message: ~ " + f"[Check, {r.link}]"
    filter_ = dict(type="text", data=msg)
    await save_filter(message.chat.id, "~pinned", filter_)


# Mute members


@app.on_message(filters.command(["mute", "tmute"], prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def mute(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    if user_id == BOT_ID:
        return await message.reply_text("لا أستطيع كتم نفسي.")
    if user_id in SUDOERS:
        return await message.reply_text(
            "تريد كتم شخص مميّز؟ أعد التفكير!"
        )
    if user_id in (await list_admins(message.chat.id)):
        return await message.reply_text(
            "لا أستطيع كتم مشرف، أنت تعرف القواعد."
        )
    mention = (await app.get_users(user_id)).mention
    keyboard = ikb({"🚨  رفع الكتم  🚨": f"unmute_{user_id}"})
    msg = (
        f"**المستخدم المكتوم:** {mention}\n"
        f"**كُتم بواسطة:** {message.from_user.mention if message.from_user else 'Anon'}\n"
    )
    if message.command[0] == "tmute":
        split = reason.split(None, 1)
        time_value = split[0]
        temp_reason = split[1] if len(split) > 1 else ""
        temp_mute = await time_converter(message, time_value)
        msg += f"**مدة الكتم:** {time_value}\n"
        if temp_reason:
            msg += f"**السبب:** {temp_reason}"
        try:
            if len(time_value[:-1]) < 3:
                await message.chat.restrict_member(
                    user_id,
                    permissions=ChatPermissions(),
                    until_date=temp_mute,
                )
                replied_message = message.reply_to_message
                if replied_message:
                    message = replied_message
                await message.reply_text(msg, reply_markup=keyboard)
            else:
                await message.reply_text("لا يمكنك استخدام أكثر من 99.")
        except AttributeError:
            pass
        return
    if reason:
        msg += f"**السبب:** {reason}"
    await message.chat.restrict_member(user_id, permissions=ChatPermissions())
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(msg, reply_markup=keyboard)


# Unmute members


@app.on_message(filters.command("unmute", prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def unmute(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    await message.chat.unban_member(user_id)
    umention = (await app.get_users(user_id)).mention
    replied_message = message.reply_to_message
    if replied_message:
        message = replied_message
    await message.reply_text(f"✅ تم رفع الكتم! {umention}")


# Ban deleted accounts


@app.on_message(filters.command("ban_ghosts", prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def ban_deleted_accounts(_, message: Message):
    chat_id = message.chat.id
    deleted_users = []
    banned_users = 0
    m = await message.reply("جارٍ البحث عن الحسابات المحذوفة...")

    async for i in app.get_chat_members(chat_id):
        if i.user.is_deleted:
            deleted_users.append(i.user.id)
    if len(deleted_users) > 0:
        for deleted_user in deleted_users:
            try:
                await message.chat.ban_member(deleted_user)
            except Exception:
                pass
            banned_users += 1
        await m.edit(f"تم حظر {banned_users} حساب محذوف.")
    else:
        await m.edit("لا توجد حسابات محذوفة في هذه المحادثة.")


@app.on_message(filters.command(["warn", "dwarn"], prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def warn_user(_, message: Message):
    user_id, reason = await extract_user_and_reason(message)
    chat_id = message.chat.id
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    if user_id == BOT_ID:
        return await message.reply_text(
            "لا أستطيع تحذير نفسي."
        )
    if user_id in SUDOERS:
        return await message.reply_text(
            "تريد تحذير شخص مميّز؟ أعد التفكير!"
        )
    if user_id in (await list_admins(chat_id)):
        return await message.reply_text(
            "لا أستطيع تحذير مشرف."
        )
    user, warns = await asyncio.gather(
        app.get_users(user_id),
        get_warn(chat_id, await int_to_alpha(user_id)),
    )
    mention = user.mention
    keyboard = ikb({"🚨  إزالة التحذير  🚨": f"unwarn_{user_id}"})
    if warns:
        warns = warns["warns"]
    else:
        warns = 0
    if message.command[0][0] == "d":
        await message.reply_to_message.delete()
    if warns >= 2:
        await message.chat.ban_member(user_id)
        await message.reply_text(
            f"⛔ تجاوز {mention} الحد الأقصى للتحذيرات، تم الحظر!"
        )
        await remove_warns(chat_id, await int_to_alpha(user_id))
    else:
        warn = {"warns": warns + 1}
        msg = f"""
**المستخدم المحذَّر:** {mention}
**حذَّره:** {message.from_user.mention if message.from_user else 'Anon'}
**السبب:** {reason or 'لم يُذكر سبب.'}
**التحذيرات:** {warns + 1}/3"""
        replied_message = message.reply_to_message
        if replied_message:
            message = replied_message
        await message.reply_text(msg, reply_markup=keyboard)
        await add_warn(chat_id, await int_to_alpha(user_id), warn)


@app.on_callback_query(filters.regex("unwarn_"))
async def remove_warning(_, cq: CallbackQuery):
    from_user = cq.from_user
    chat_id = cq.message.chat.id
    permissions = await member_permissions(chat_id, from_user.id)
    permission = "can_restrict_members"
    if permission not in permissions:
        return await cq.answer(
            "You don't have enough permissions to perform this action.\n"
            + f"Permission needed: {permission}",
            show_alert=True,
        )
    user_id = cq.data.split("_")[1]
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if not warns or warns == 0:
        return await cq.answer("User لا توجد لديه تحذيرات.")
    warn = {"warns": warns - 1}
    await add_warn(chat_id, await int_to_alpha(user_id), warn)
    text = cq.message.text.markdown
    text = f"~~{text}~~\n\n"
    text += f"__Warn removed by {from_user.mention}__"
    await cq.message.edit(text)


# Rmwarns


@app.on_message(filters.command("rmwarns", prefixes="/!") & ~filters.private)
@adminsOnly("can_restrict_members")
async def remove_warnings(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text(
            "ردّ على رسالة لإزالة تحذيرات المستخدم."
        )
    user_id = message.reply_to_message.from_user.id
    mention = message.reply_to_message.from_user.mention
    chat_id = message.chat.id
    warns = await get_warn(chat_id, await int_to_alpha(user_id))
    if warns:
        warns = warns["warns"]
    if warns == 0 or not warns:
        await message.reply_text(f"{mention} لا توجد لديه تحذيرات.")
    else:
        await remove_warns(chat_id, await int_to_alpha(user_id))
        await message.reply_text(f"✅ تمت إزالة تحذيرات {mention}.")


# Warns


@app.on_message(filters.command("warns", prefixes="/!") & ~filters.private)
@capture_err
async def check_warns(_, message: Message):
    user_id = await extract_user(message)
    if not user_id:
        return await message.reply_text("لا أستطيع العثور على هذا المستخدم.")
    warns = await get_warn(message.chat.id, await int_to_alpha(user_id))
    mention = (await app.get_users(user_id)).mention
    if warns:
        warns = warns["warns"]
    else:
        return await message.reply_text(f"{mention} لا توجد لديه تحذيرات.")
    return await message.reply_text(f"{mention} has {warns}/3 warnings.")


# Report


@app.on_message(
    (
        filters.command("report", prefixes="/!")
        | filters.command(["admins", "admin"], prefixes="@")
    )
    & ~filters.private
)
@capture_err
async def report_user(_, message):
    if len(message.text.split()) <= 1 and not message.reply_to_message:
        return await message.reply_text(
            "ردّ على رسالة للإبلاغ عن هذا المستخدم."
        )

    reply = message.reply_to_message if message.reply_to_message else message
    reply_id = reply.from_user.id if reply.from_user else reply.sender_chat.id
    user_id = (
        message.from_user.id if message.from_user else message.sender_chat.id
    )

    list_of_admins = await list_admins(message.chat.id)
    linked_chat = (await app.get_chat(message.chat.id)).linked_chat
    if linked_chat is not None:
        if (
            reply_id in list_of_admins
            or reply_id == message.chat.id
            or reply_id == linked_chat.id
        ):
            return await message.reply_text(
                "هل تعلم أن الشخص الذي ردّيت عليه مشرف؟"
            )
    else:
        if reply_id in list_of_admins or reply_id == message.chat.id:
            return await message.reply_text(
                "هل تعلم أن الشخص الذي ردّيت عليه مشرف؟"
            )

    user_mention = (
        reply.from_user.mention if reply.from_user else reply.sender_chat.title
    )
    text = f"تم الإبلاغ عن {user_mention} للمشرفين!"
    admin_data = [
        i
        async for i in app.get_chat_members(
            chat_id=message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS
        )
    ]  # will it give floods ???
    for admin in admin_data:
        if admin.user.is_bot or admin.user.is_deleted:
            # return bots or deleted admins
            continue
        text += f"[\u2063](tg://user?id={admin.user.id})"

    await reply.reply_text(text)


@app.on_message(filters.command("invite", prefixes="/!"))
@adminsOnly("can_invite_users")
async def invite(_, message):
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        link = (await app.get_chat(message.chat.id)).invite_link
        if not link:
            link = await app.export_chat_invite_link(message.chat.id)
        text = f"Here's This Group's Invite Link.\n\n{link}"
        if message.reply_to_message:
            await message.reply_to_message.reply_text(
                text, disable_web_page_preview=True
            )
        else:
            await message.reply_text(text, disable_web_page_preview=True)
