import json
import os
from os import path
from typing import Callable

import aiofiles
import aiohttp
import ffmpeg
import requests
import wget
from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import Voice
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from Python_ARQ import ARQ
from youtube_search import YoutubeSearch
from MusicKen.modules.play import generate_cover
from MusicKen.modules.play import arq
from MusicKen.modules.play import cb_admin_check
from MusicKen.modules.play import transcode
from MusicKen.modules.play import convert_seconds
from MusicKen.modules.play import time_to_seconds
from MusicKen.modules.play import changeImageSize
from MusicKen.config import BOT_NAME as bn
from MusicKen.config import DURATION_LIMIT, ASSISTANT_NAME
from MusicKen.config import SUPPORT_GROUP as groupsupport
from MusicKen.config import UPDATES_CHANNEL as updateschannel
from MusicKen.config import que
from MusicKen.function.admins import admins as a
from MusicKen.helpers.errors import DurationLimitError
from MusicKen.helpers.decorators import errors
from MusicKen.helpers.admins import get_administrators
from MusicKen.helpers.channelmusic import get_chat_id
from MusicKen.helpers.decorators import authorized_users_only
from MusicKen.helpers.filters import command, other_filters
from MusicKen.helpers.gets import get_file_name
from MusicKen.services.callsmusic import callsmusic, queues
from MusicKen.services.callsmusic.callsmusic import client as USER
from MusicKen.services.converter.converter import convert
from MusicKen.services.downloaders import youtube

chat_id = None



@Client.on_message(filters.command(["channelplaylist","cplaylist"]) & filters.group & ~filters.edited)
async def playlist(client, message):
    try:
      lel = await client.get_chat(message.chat.id)
      lol = lel.linked_chat.id
    except:
      message.reply("Apakah channel ini terhubung?")
      return
    global que
    queue = que.get(lol)
    if not queue:
        await message.reply_text("Assistant telah siap")
    temp = list(queue)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "**Now Playing** in {}".format(lel.linked_chat.title)
    msg += "\n- " + now_playing
    msg += "\n- Req by " + by
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Queue**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n- {name}"
            msg += f"\n- Req by {usr}\n"
    await message.reply_text(msg)


# ============================= Settings =========================================


def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.pytgcalls.active_calls:
        # if chat.id in active_chats:
        stats = "Settings of **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "Volume : {}%\n".format(vol)
            stats += "Songs in queue : `{}`\n".format(len(que))
            stats += "Now Playing : **{}**\n".format(queue[0][0])
            stats += "Requested by : {}".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "cleave"),
                InlineKeyboardButton("⏸", "cpuse"),
                InlineKeyboardButton("▶️", "cresume"),
                InlineKeyboardButton("⏭", "cskip"),
            ],
            [
                InlineKeyboardButton("Playlist 📖", "cplaylist"),
            ],
            [InlineKeyboardButton("❌ Close", "ccls")],
        ]
    )


@Client.on_message(filters.command(["channelcurrent","ccurrent"]) & filters.group & ~filters.edited)
async def ee(client, message):
    try:
      lel = await client.get_chat(message.chat.id)
      lol = lel.linked_chat.id
      conv = lel.linked_chat
    except:
      await message.reply("Apakah obrolan ini terhubung")
      return
    queue = que.get(lol)
    stats = updated_stats(conv, queue)
    if stats:
        await message.reply(stats)
    else:
        await message.reply("Tidak ada instance VCG yang berjalan dalam obrolan ini")

@Client.on_message(filters.command(["channelplayer","cplayer"]) & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    try:
      lel = await client.get_chat(message.chat.id)
      lol = lel.linked_chat.id
      conv = lel.linked_chat
    except:
      await message.reply("Apakah obrolan ini terhubung")
      return
    queue = que.get(lol)
    stats = updated_stats(conv, queue)
    if stats:
        playing = None
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause"))

        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply("Tidak ada instance VCG yang berjalan dalam obrolan ini")


@Client.on_callback_query(filters.regex(pattern=r"^(cplaylist)$"))
async def p_cb(b, cb):
    global que
    try:
      lel = await client.get_chat(cb.message.chat.id)
      lol = lel.linked_chat.id
      conv = lel.linked_chat
    except:
      return
    que.get(lol)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(lol)
        if not queue:
            await cb.message.edit("Assistant sudah siap")
        temp = list(queue)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Now Playing** in {}".format(conv.title)
        msg += "\n- " + now_playing
        msg += "\n- Req by " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Queue**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- Req by {usr}\n"
        await cb.message.edit(msg)


@Client.on_callback_query(
    filters.regex(pattern=r"^(cplay|cpause|cskip|cleave|cpuse|cresume|cmenu|ccls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que
    if (
        cb.message.chat.title.startswith("Channel Music: ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
      try:
        lel = await b.get_chat(cb.message.chat.id)
        lol = lel.linked_chat.id
        conv = lel.linked_chat
        chet_id = lol
      except:
        return
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat


    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "cpause":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer("Obrolan tidak terhubung!", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Music Paused!")
            await cb.message.edit(
                updated_stats(conv, qeue), reply_markup=r_ply("play")
            )

    elif type_ == "cplay":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer("Obrolan tidak terhubung!", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Music Resumed!")
            await cb.message.edit(
                updated_stats(conv, qeue), reply_markup=r_ply("pause")
            )

    elif type_ == "cplaylist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("Player is idle")
        temp = list(queue)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Now Playing** in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += "\n- Req by " + by
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Queue**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- Req by {usr}\n"
        await cb.message.edit(msg)

    elif type_ == "cresume":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "playing"
        ):
            await cb.answer("Obrolan tidak tersambung atau sudah diputar", show_alert=True)
        else:
            callsmusic.pytgcalls.resume_stream(chet_id)
            await cb.answer("Music Resumed!")
    elif type_ == "cpuse":
        if (chet_id not in callsmusic.pytgcalls.active_calls) or (
            callsmusic.pytgcalls.active_calls[chet_id] == "paused"
        ):
            await cb.answer("Obrolan tidak tersambung atau sudah dijeda", show_alert=True)
        else:
            callsmusic.pytgcalls.pause_stream(chet_id)

            await cb.answer("Music Paused!")
    elif type_ == "ccls":
        await cb.answer("Closed menu")
        await cb.message.delete()

    elif type_ == "cmenu":
        stats = updated_stats(conv, qeue)
        await cb.answer("Menu opened")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "cleave"),
                    InlineKeyboardButton("⏸", "cpuse"),
                    InlineKeyboardButton("▶️", "cresume"),
                    InlineKeyboardButton("⏭", "cskip"),
                ],
                [
                    InlineKeyboardButton("Playlist 📖", "cplaylist"),
                ],
                [InlineKeyboardButton("❌ Close", "ccls")],
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)
    elif type_ == "cskip":
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.pytgcalls.active_calls:
            await cb.answer("Obrolan tidak terhubung", show_alert=True)
        else:
            callsmusic.queues.task_done(chet_id)

            if callsmusic.queues.is_empty(chet_id):
                callsmusic.pytgcalls.leave_group_call(chet_id)

                await cb.message.edit("Tidak Ada Lagi Daftar Putar..\n- Meninggalkan VCG!")
            else:
                callsmusic.pytgcalls.change_stream(
                    chet_id, callsmusic.queues.get(chet_id)["file"]
                )
                await cb.answer("Skipped")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"- Skipped track\n- Now Playing **{qeue[0][0]}**"
                )

    elif chet_id in callsmusic.pytgcalls.active_calls:
        try:
            callsmusic.queues.clear(chet_id)
        except QueueEmpty:
            pass

        callsmusic.pytgcalls.leave_group_call(chet_id)
        await cb.message.edit("Berhasil Meninggalkan Obrolan!")
    else:
        await cb.answer("Obrolan tidak terhubung!", show_alert=True)


@Client.on_message(filters.command(["channelplay","cplay"])  & filters.group & ~filters.edited)
@authorized_users_only
async def play(_, message: Message):
    global que
    lel = await message.reply("🔄 **Processing**")

    try:
      conchat = await _.get_chat(message.chat.id)
      conv = conchat.linked_chat
      conid = conchat.linked_chat.id
      chid = conid
    except:
      await message.reply("Apakah obrolan ini terhubung")
      return
    try:
      administrators = await get_administrators(conv)
    except:
      await message.reply("Apakah saya admin di channel")
    try:
        user = await USER.get_me()
    except:
        user.first_name = "helper"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        f"<b>Ingatlah untuk menambahkan @{ASSISTANT_NAME} di channel anda!</b>",
                    )
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Jadikan saya admin di channel anda!</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await lel.edit(
                        "<b>Assistant sudah bergabung di channel anda</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood Wait Error 🔴 \nPengguna {user.first_name} tidak dapat bergabung dengan Channel Anda karena banyaknya permintaan untuk userbot! Pastikan pengguna tidak diblokir dalam channel."
                        "\n\nAtau tambahkan asisten ke Channel Anda secara manual dan coba lagi</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name} Userbot tidak ada dalam obrolan ini, Minta admin Channel untuk mengirim perintah /play untuk pertama kalinya atau menambahkan {user.first_name} secara manual</i>"
        )
        return
    message.from_user.id
    text_links = None
    message.from_user.first_name
    await lel.edit("🔎 **Finding**")
    message.from_user.id
    user_id = message.from_user.id
    message.from_user.first_name
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    if message.reply_to_message:
        entities = []
        toxt = message.reply_to_message.text or message.reply_to_message.caption
        if (
            message.reply_to_message.entities
            or message.reply_to_message.caption_entities
        ):
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls=None
    if text_links:
        urls = True
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            raise DurationLimitError(f"❌ Video yang berdurasi lebih dari {DURATION_LIMIT} menit tidak boleh diputar!")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📖 Playlist", callback_data="cplaylist"),
                    InlineKeyboardButton("Menu ⏯ ", callback_data="cmenu"),
                ],
                [InlineKeyboardButton(text="❌ Close", callback_data="ccls")],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/c9c7e24b03919fa5f8022.jpg"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locally added"
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("🎵 **Processing**")
        ydl_opts = {"format": "141/bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:40]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]

        except Exception as e:
            await lel.edit(
                "**Lagu tidak ditemukan.** Coba cari dengan judul lagu yang lebih jelas, Ketik `/help` bila butuh bantuan"
            )
            print(str(e))
            return
        dlurl = url
        dlurl=dlurl.replace("youtube","youtubepp")
        keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("📖 ᴘʟᴀʏʟɪꜱᴛ", callback_data="playlist"),
                                InlineKeyboardButton("💬 ɢʀᴏᴜᴘ", url=f"https://t.me/{groupsupport}"),
                            ],   
                            [InlineKeyboardButton("💌 ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{updateschannel}")],
                            [InlineKeyboardButton(text="🗑 ᴛᴜᴛᴜᴘ", callback_data="cls")],
                        ]
                    )
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(youtube.download(url))
    else:
        query = "".join(" " + str(i) for i in message.command[1:])
        print(query)
        await lel.edit("🎵 **Processing**")
        ydl_opts = {"format": "141/bestaudio[ext=m4a]"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:40]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]

        except Exception as e:
            await lel.edit(
                "Lagu tidak ditemukan. Coba lagu lain atau mungkin anda salah mengejanya."
            )
            print(str(e))
            return

        dlurl = url
        dlurl=dlurl.replace("youtube","youtubepp")
        keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("📖 ᴘʟᴀʏʟɪꜱᴛ", callback_data="playlist"),
                                InlineKeyboardButton("💬 ɢʀᴏᴜᴘ", url=f"https://t.me/{groupsupport}"),
                            ],   
                            [InlineKeyboardButton("💌 ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{updateschannel}")],
                            [InlineKeyboardButton(text="🗑 ᴛᴜᴛᴜᴘ", callback_data="cls")],
                        ]
                    )
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(youtube.download(url))
    chat_id = chid
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption = f"🏷 **Judul:** [{title[:60]}]({url})\n⏱ **Durasi:** {duration}\n💡 **Status:** Antrian Ke `{position}`\n" \
                    + f"🎼 **Request Dari:** {message.from_user.mention}",
                   reply_markup=keyboard)
    else:
        chat_id = chid
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption=f"🏷 **Judul:** [{title[:60]}]({url})\n**⏱ Durasi:** {duration}\n" \
                + f"💡 **Status:** Playing\n🎧 **Permintaan:** {requested_by}".format(
        message.from_user.mention()
        ),
    )

    os.remove("final.png")
    return await lel.delete()


@Client.on_message(filters.command(["channeldplay","cdplay"]) & filters.group & ~filters.edited)
@authorized_users_only
async def deezer(client: Client, message_: Message):
    global que
    lel = await message_.reply("🔄 **Processing**")

    try:
      conchat = await client.get_chat(message_.chat.id)
      conid = conchat.linked_chat.id
      conv = conchat.linked_chat
      chid = conid
    except:
      await message_.reply("Apakah obrolan ini terhubung")
      return
    try:
      administrators = await get_administrators(conv)
    except:
      await message.reply("Jadikan saya admin di Channel")
    try:
        user = await USER.get_me()
    except:
        user.first_name = "MusicKen"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await client.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message_.from_user.id:
                if message_.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        "<b>Ingatlah untuk menambahkan Assistant di Channel Anda</b>",
                    )
                try:
                    invitelink = await client.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Jadikan saya Admin di Channel Anda</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await lel.edit(
                        "<b>Assistant berhasil bergabung di channel Anda</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood Wait Error 🔴 \nPengguna {user.first_name} tidak dapat bergabung dengan Channel Anda karena banyaknya permintaan untuk userbot! Pastikan pengguna tidak diblokir dalam Channel."
                        "\n\nAtau tambahkan asisten ke Channel Anda secara manual dan coba lagi</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i>{user.first_name} Userbot tidak ada dalam obrolan ini, Minta admin saluran untuk mengirim perintah /play untuk pertama kalinya atau menambahkan {user.first_name} secara manual</i>"
        )
        return
    requested_by = message_.from_user.first_name

    text = message_.text.split(" ", 1)
    queryy = text[1]
    query=queryy
    res = lel
    await res.edit(f'Mencari 👀👀👀 lagu `{query}` dari deezer')
    try:
        songs = await arq.deezer(query,1)
        if not songs.ok:
            await message_.reply_text(songs.result)
            return
        title = songs.result[0].title
        url = songs.result[0].url
        artist = songs.result[0].artist
        duration = songs.result[0].duration
        thumbnail = songs.result[0].thumbnail
    except:
        await res.edit("**Lagu tidak ditemukan.** Coba cari dengan judul lagu yang lebih jelas, Ketik `/help` bila butuh bantuan"
            )    
    return


@Client.on_message(filters.command(["channelsplay","csplay"]) & filters.group & ~filters.edited)
@authorized_users_only
async def jiosaavn(client: Client, message_: Message):
    global que
    lel = await message_.reply("🔄 **Processing**")
    try:
      conchat = await client.get_chat(message_.chat.id)
      conid = conchat.linked_chat.id
      conv = conchat.linked_chat
      chid = conid
    except:
      await message_.reply("Apakah obrolan ini terhubung")
      return
    try:
      administrators = await get_administrators(conv)
    except:
      await message.reply("Apakah saya admin di channel")
    try:
        user = await USER.get_me()
    except:
        user.first_name = "MusicKen"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await client.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message_.from_user.id:
                if message_.chat.title.startswith("Channel Music: "):
                    await lel.edit(
                        "<b>Ingatlah untuk menambahkan Assistant di Channel Anda</b>",
                    )
                try:
                    invitelink = await client.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Jadikan saya Admin di Channel Anda</b>",
                    )                    
                    return

                try:
                    await USER.join_chat(invitelink)
                    await lel.edit(
                        "<b>Assistant berhasil bergabung di channel Anda</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood Wait Error 🔴 \nPengguna {user.first_name} tidak dapat bergabung dengan Channel Anda karena banyaknya permintaan untuk userbot! Pastikan pengguna tidak diblokir dalam Channel."
                        "\n\nAtau tambahkan asisten ke Channel Anda secara manual dan coba lagi</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i>{user.first_name} Userbot tidak ada dalam obrolan ini, Minta admin saluran untuk mengirim perintah /play untuk pertama kalinya atau menambahkan {user.first_name} secara manual</i>"
       )
        return
    requested_by = message_.from_user.first_name
    chat_id = message_.chat.id
    text = message_.text.split(" ", 1)
    query = text[1]
    res = lel
    await res.edit(f"Mencari 👀👀👀 lagu `{query}` dari jio saavn")
    try:
        songs = await arq.saavn(query)
        if not songs.ok:
            await message_.reply_text(songs.result)
            return
        sname = songs.result[0].song
        slink = songs.result[0].media_url
        ssingers = songs.result[0].singers
        sthumb = "https://telegra.ph/file/c9c7e24b03919fa5f8022.jpg"
        sduration = int(songs.result[0].duration)
    except Exception as e:
        await res.edit("**Lagu tidak ditemukan.** Coba cari dengan judul lagu yang lebih jelas.")
        print(str(e))
        return
    keyboard = InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton("📖 ᴘʟᴀʏʟɪꜱᴛ", callback_data="playlist"),
                                InlineKeyboardButton("💬 ɢʀᴏᴜᴘ", url=f"https://t.me/{groupsupport}"),
                            ],   
                            [InlineKeyboardButton("💌 ᴄʜᴀɴɴᴇʟ", url=f"https://t.me/{updateschannel}")],
                            [InlineKeyboardButton(text="🗑 ᴛᴜᴛᴜᴘ", callback_data="cls")],
                        ]
                    )
    file_path = await convert(wget.download(slink))
    chat_id = chid
    if chat_id in callsmusic.pytgcalls.active_calls:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await res.delete()
        m = await client.send_photo(
            chat_id=message_.chat.id,
            reply_markup=keyboard,
            photo="final.png",
            caption=f"✯{bn}✯=#️⃣ Antri di posisi {position}",
        )

    else:
        await res.edit_text(f"{bn}=▶️ Playing.....")
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        callsmusic.pytgcalls.join_group_call(chat_id, file_path)
    await res.edit("Generating Thumbnail.")
    await generate_cover(requested_by, sname, ssingers, sduration, sthumb)
    await res.delete()
    m = await client.send_photo(
        chat_id=message_.chat.id,
        reply_markup=keyboard,
        photo="final.png",
        caption=f"Memutar {sname} Via Jiosaavn di channel",
    )
    os.remove("final.png")


# Have u read all. If read RESPECT :-)
# Translate asal-asalan ke indonesia by @kenkanasw
