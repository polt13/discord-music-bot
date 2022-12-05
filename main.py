import asyncio
import itertools
import math
import random
import os
import keep_alive
from discord import FFmpegOpusAudio
from os import system

from config import ydl_options, ffmpeg_options, embeds, YoutubeDL, prefix
import discord
from async_timeout import timeout
from discord import app_commands
from discord.ext import commands

ytdl = YoutubeDL(ydl_options)

queues = {}

currentlyPlaying = {}

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=prefix, help_command=None,intents = intents)


#slash commands

async def __disp_curr_song(fn, title):
    emb = discord.Embed(title="🎶 Now Playing",
                        description=title,
                        type="rich",
                        color=discord.Color.red())
    await fn(embed=emb)

@client.tree.command(name="now",description = "What's currently playing")
async def __now(interaction):
    if interaction.guild_id in currentlyPlaying:
        await __disp_curr_song(interaction.response.send_message, currentlyPlaying[interaction.guild_id])

@client.tree.command(name = "play", description = "Stream audio track")
async def __play_track(interaction,song:str):
    
    entry = song

    await interaction.response.defer()

    server = interaction.guild_id
        
    if interaction.guild.voice_client is None:
        if interaction.user.voice is not None:
            vc = interaction.user.voice.channel
            await vc.connect()
            await interaction.guild.change_voice_state(channel=vc, self_mute=False, self_deaf=True)
        else:
            await interaction.followup.send(embed=embeds["not_connected"])
            return

    if interaction.user.voice.channel != interaction.guild.voice_client.channel:
        await interaction.followup.send(embed=embeds["connected_already"])
        return

    voice = interaction.guild.voice_client
    

    try:
        ytdl.cache.remove()
    except:
        print("clearing cache failed\n")

    _songs = await isPlaylist(entry)

    if not _songs:
        _songs = [entry]

    if server in queues:
        queues[server] += [(s, title_extract(s)) for s in _songs]
    else:
        queues[server] = [(s, title_extract(s)) for s in _songs]
        

    if not interaction.guild.voice_client.is_playing() and not interaction.guild.voice_client.is_paused():
        _vid = queues[server].pop(0)  # (entry,title)
        surl, title = surl_extract(_vid[0]), _vid[1]
        src = FFmpegOpusAudio(surl, **ffmpeg_options)
        player = voice.play(
            src,
            after=lambda x: next_up2(interaction, server),
        )
        currentlyPlaying[server] = title
        await __disp_curr_song(interaction.followup.send,title)
     
    else:
        emb = discord.Embed(
            title="🔗 Queued",
            description=queues[server][-1][1],
            type="rich",
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=emb)
   

@client.tree.command(name ="skip", description="Skip currently playing track")
async def __skip(interaction):
    if interaction.guild.voice_client is not None:
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("Skipping..")


@client.event
async def on_ready():
    print("[[Dandelion Online]]")
    await client.tree.sync()
    await client.change_presence(activity=discord.Activity(
        name="$play", type=discord.ActivityType.listening))

def next_up2(interaction,server):
    client.loop.create_task(_next_2(interaction,server))

async def _next_2(interaction,server):
    if queues[server] != []:
        await __disp_curr_song(interaction.followup.send,queues[server][-1][1])
        _vid = queues[server].pop(0)  # (entry,title)
        surl, title = surl_extract(_vid[0]), _vid[1]
        src = FFmpegOpusAudio(surl, **ffmpeg_options)
        voice = interaction.guild.voice_client
        currentlyPlaying[server] = title
        player = voice.play(src, after=lambda x: next_up2(interaction, server))

@client.tree.command(name = "stop", description = "Stop streaming")
async def __stop_track(interaction):
    if interaction.guild.voice_client is not None and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.stop()
        queues[interaction.guild_id].clear()
        await interaction.response.send_message(embed=embeds["stop"])
    else:
        await interaction.response.send_message(embed=embeds["no_audio"])


@client.tree.command(name = "resume", description="Resume playback")
async def __res_track(interaction):
    if interaction.guild.voice_client is not None and interaction.guild.voice_client.is_paused():
        interaction.guild.voice_client.resume()
        await interaction.response.send_message(embed=embeds["resume"])
    else:
        await interaction.response.send_message(embed=embeds["no_audio"])

@client.tree.command(name= "pause", description="Pause audio stream")
async def __pause_track(interaction):
    if interaction.guild.voice_client is not None and interaction.guild.voice_client.is_playing():
        interaction.guild.voice_client.pause()
        await interaction.response.send_message(embed=embeds["pause"])
    else:
        await interaction.response.send_message(embed=embeds["no_audio"])

@client.tree.command(name="tracklist", description= "Display queue")
async def __display_track_queue(interaction):

    await interaction.response.defer()

    if interaction.guild_id not in queues:
        return
    if queues[interaction.guild_id] == []:
        await interaction.followup.send(embed=embeds["empty_queue"])
        return
    counter = 1
    msg = "\n"
    for s in queues[interaction.guild_id]:
        msg += str(counter) + ". " + s[1] + "\n"
        counter += 1
    await interaction.followup.send(embed=discord.Embed(
        title="🐱‍👤 Queue: ",
        description="```" + msg + "```",
        color=discord.Color.blue(),
    ))

@client.tree.command(name="help", description = "Display help menu")
async def __help(interaction):
    await interaction.response.send_message(embed=embeds["help"])

@client.tree.command(name="rm", description= "Remove track from queue")
async def __remove_track(interaction, index:int):
    try:
        index = int(index)
    except ValueError:
        await interaction.response.send_message("Bad input")
        return

    if 1 <= index <= len(queues[interaction.guild_id]):
        t = queues[interaction.guild_id].pop(index - 1)[1]
        await interaction.response.send_message(embed=discord.Embed(
            title=f"Removed track {index} from queue",
            description=t,
            type="rich",
            color=discord.Color.dark_green(),
        ))
    else:
        await interaction.response.send_message(embed=discord.Embed(
            title="Bad index", type="rich", color=discord.Color.dark_red()))


#old ctx
def next_up(ctx, server):
    client.loop.create_task(_next_(
        ctx, server))  # add playing task to the event loop


async def _next_(ctx, server):
    if queues[server] != []:
        _vid = queues[server].pop(0)  # (entry,title)
        surl, title = surl_extract(_vid[0]), _vid[1]
        src = FFmpegOpusAudio(surl, **ffmpeg_options)
        voice = ctx.voice_client
        currentlyPlaying[server] = title
        await disp_curr_song(ctx, title)
        player = voice.play(src, after=lambda x: next_up(ctx, server))


async def disp_curr_song(ctx, title):
    emb = discord.Embed(title="🎶 Now Playing",
                        description=title,
                        type="rich",
                        color=discord.Color.red())
    await ctx.send(embed=emb)


@client.command(aliases=["now"])
async def _now(ctx):
    if ctx.message.guild.id in currentlyPlaying:
        await disp_curr_song(ctx, currentlyPlaying[ctx.message.guild.id])



def title_extract(entry):

    video = ytdl.extract_info(entry, download=False)  # entry = title/url
    if "entries" in video:
        title = video["entries"][0]["title"]  # title
    else:
        title = video["title"]
    return title


def surl_extract(entry):

    video = ytdl.extract_info(entry, download=False)
    if "entries" in video:
        return video["entries"][0]["url"]
    else:
        return video["url"]


@client.command(aliases=["skip", "next"])
async def _skip(ctx):
    if ctx.voice_client is not None:
        ctx.voice_client.stop()


@client.command(aliases=["rq", "remove"])
async def _rq(ctx, index):
    try:
        index = int(index)
    except ValueError:
        await ctx.send("Bad input")
        return

    if 1 <= index <= len(queues[ctx.message.guild.id]):
        t = queues[ctx.message.guild.id].pop(index - 1)[1]
        await ctx.send(embed=discord.Embed(
            title="Removed from queue",
            description=t,
            type="rich",
            color=discord.Color.dark_green(),
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="Bad index", type="rich", color=discord.Color.dark_red()))


@client.command(aliases=["swap"])
async def _swap(ctx, index1, index2):

    if ctx.message.guild.id not in queues:
        return

    try:
        index1 = int(index1)
        index2 = int(index2)
    except ValueError:
        await ctx.send("Bad input\n")
        return

    if (1 <= index1 <= len(queues[ctx.message.guild.id])) and (
            1 <= index2 <= len(queues[ctx.message.guild.id])):
        _t = queues[ctx.message.guild.id][index1 - 1]
        queues[ctx.message.guild.id][index1 -
                                     1] = queues[ctx.message.guild.id][index2 -
                                                                       1]
        queues[ctx.message.guild.id][index2 - 1] = _t
        await ctx.send(embed=discord.Embed(
            title="Swapped tracks",
            description=queues[ctx.message.guild.id][index2 - 1][1] + ", " +
            queues[ctx.message.guild.id][index1 - 1][1],
            type="rich",
            color=discord.Color.gold(),
        ))
    else:
        await ctx.send(embed=discord.Embed(
            title="Bad index", type="rich", color=discord.Color.dark_red()))


async def isPlaylist(entry):
    import validators

    if validators.url(entry) and ("/playlist?list=" in entry or
                                  ("/watch" in entry and "list="
                                   in entry)):  # only for playlists from url
        output = ytdl.extract_info(entry, download=False)
        url_list = []
        for e in output["entries"]:
            url_list.append("youtube.com/watch?v=" + e["id"])
        return url_list


@client.command(aliases=["p", "play"])
async def _play(ctx, *, entry):  
    server = ctx.message.guild.id

    if ctx.voice_client is None:
        if ctx.message.author.voice is not None:
            vc = ctx.message.author.voice.channel
            await vc.connect()
            await ctx.guild.change_voice_state(channel=vc, self_mute=False, self_deaf=True)
        else:
            await ctx.send(embed=embeds["not_connected"])
            return

    if ctx.message.author.voice.channel != ctx.voice_client.channel:
        await ctx.send(embed=embeds["connected_already"])
        return

    voice = ctx.voice_client
    

    try:
        ytdl.cache.remove()
    except:
        print("clearing cache failed\n")

    _songs = await isPlaylist(entry)

    if not _songs:
        _songs = [entry]

    if server in queues:
        queues[server] += [(s, title_extract(s)) for s in _songs]
    else:
        queues[server] = [(s, title_extract(s)) for s in _songs]
        

    if not ctx.voice_client.is_playing() and not ctx.voice_client.is_paused():
        _vid = queues[server].pop(0)  # (entry,title)
        surl, title = surl_extract(_vid[0]), _vid[1]
        print(surl)
        src = FFmpegOpusAudio(surl, **ffmpeg_options)
        player = voice.play(
            src,
            after=lambda x: next_up(ctx, server),
        )
        currentlyPlaying[server] = title
        await disp_curr_song(ctx, title)
    else:
        emb = discord.Embed(
            title="🔗 Queued",
            description=queues[server][-1][1],
            type="rich",
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=emb)


@client.command(aliases=["stop"])
async def _stop(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        queues[ctx.message.guild.id].clear()
        await ctx.send(embed=embeds["stop"])
    else:
        await ctx.send(embed=embeds["no_audio"])


@client.command(aliases=["res"])
async def _res(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send(embed=embeds["resume"])
    else:
        await ctx.send(embed=embeds["no_audio"])


@client.command(aliases=["pau"])
async def _pause(ctx):
    if ctx.voice_client is not None and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send(embed=embeds["pause"])
    else:
        await ctx.send(embed=embeds["no_audio"])


@client.command(aliases=["dc", "disconnect"])
async def _dc(ctx):
    if (ctx.voice_client is not None and ctx.message.author.voice is not None
            and ctx.message.author.voice.channel == ctx.voice_client.channel):
        await _clear(ctx)
        await ctx.voice_client.disconnect()


@client.command(aliases=["dq", "list"])
async def _dq(ctx):
    if ctx.message.guild.id not in queues:
        return
    if queues[ctx.message.guild.id] == []:
        await ctx.send(embed=embeds["empty_queue"])
        return
    counter = 1
    msg = "\n"
    for s in queues[ctx.message.guild.id]:
        msg += str(counter) + ". " + s[1] + "\n"
        counter += 1
    await ctx.send(embed=discord.Embed(
        title="🌛 Queue: ",
        description="```" + msg + "```",
        color=discord.Color.blue(),
    ))


@client.command(aliases=["clear"])
async def _clear(ctx):
    if ctx.message.guild.id in queues:
        queues[ctx.message.guild.id].clear()


@client.command(aliases=["help"])
async def _help(ctx):
    await ctx.send(embed=embeds["help"])


@client.event
async def on_voice_state_update(member, before, after):
    if member.guild.voice_client is None:
        return
    channel = member.guild.voice_client.channel
    if len(channel.voice_states) == 1:
        await asyncio.sleep(60)
        if len(channel.voice_states) == 1:
            await member.guild.voice_client.disconnect()


try:
    keep_alive.keep_alive()
    client.run('PLACEHOLDER')
except discord.errors.HTTPException:
    os.system("kill 1")
