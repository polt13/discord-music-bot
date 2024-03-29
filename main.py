import asyncio

import os

import keep_alive

from discord import FFmpegOpusAudio

import validators

from config import ydl_options, ffmpeg_options, embeds, prefix

from discord.ext import commands

from yt_dlp import YoutubeDL

import discord

ytdl = YoutubeDL(ydl_options)

queues = {}

currentlyPlaying = {}

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix=prefix,
                      help_command=None,
                      intents=intents)


async def __disp_curr_song(fn, title , thumbnail):
  emb = discord.Embed(title="🎶 Now Playing",
                      description=title,
                      type="rich",
                      color=discord.Color.red())
  emb.set_image(url=thumbnail)
  await fn(embed=emb)

@client.tree.command(name="now", description="What's currently playing")
async def __now(interaction: discord.Interaction):
  if interaction.guild_id in currentlyPlaying:
    await __disp_curr_song(interaction.response.send_message,
                           *currentlyPlaying[interaction.guild_id])

@client.tree.command(name="play", description="Stream audio track")
async def __play_track(interaction: discord.Interaction, song: str):

  entry = song

  await interaction.response.defer()

  server = interaction.guild_id

  if interaction.guild.voice_client is None:
    if interaction.user.voice is not None:
      vc = interaction.user.voice.channel
      await vc.connect()
      await interaction.guild.change_voice_state(channel=vc,
                                                 self_mute=False,
                                                 self_deaf=True)
    else:
      await interaction.followup.send(embed=embeds["not_connected"])
      return

  if interaction.user.voice.channel != interaction.guild.voice_client.channel:
    await interaction.followup.send(embed=embeds["connected_already"])
    return

  voice = interaction.guild.voice_client

  _songs = get_song_list(entry)

  if server in queues:
    queues[server] += [extract_metadata(s) for s in _songs]
  else:
    queues[server] = [ extract_metadata(s) for s in _songs]

  voice = interaction.guild.voice_client

  channel  = interaction.channel
  
  if not voice.is_playing(
  ) and not voice.is_paused():
    _vid = queues[server].pop(0)  # (entry,title)
    surl, title, thumbnail = _vid
    src = FFmpegOpusAudio(surl, **ffmpeg_options)
    currentlyPlaying[server] = (title, thumbnail)
    await __disp_curr_song(interaction.followup.send, title, thumbnail)
    voice.play(src, after = lambda s: client.loop.create_task(__next_song(server,channel)))
  else:
    emb = discord.Embed(
      title="🔗 Queued",
      description=queues[server][-1][1],
      type="rich",
      color=discord.Color.blurple(),
    )
    emb.set_image(url=queues[server][-1][2])
    await interaction.followup.send(embed=emb)




@client.tree.command(name="skip", description="Skip currently playing track")
async def __skip(interaction: discord.Interaction):
  if interaction.guild.voice_client is not None:
    interaction.guild.voice_client.stop()
    await interaction.response.send_message("Skipping..")


@client.event
async def on_ready():
  await client.tree.sync()
  await client.change_presence(activity=discord.Activity(
    name="/play", type=discord.ActivityType.listening))


async def __next_song(server,channel):
  
  guild = client.get_guild(server)
  voice = guild.voice_client
  if queues[server] == []:
    await asyncio.sleep(30)
    if voice is not None and not voice.is_playing(
    ):
      await voice.disconnect()
      return
  await __disp_curr_song(channel.send, queues[server][0][1], queues[server][0][2])
  _vid = queues[server].pop(0)
  surl, title, thumbnail = _vid
  src = FFmpegOpusAudio(surl, **ffmpeg_options)
  currentlyPlaying[server] = (title,thumbnail)
  voice.play(src, after = lambda s: client.loop.create_task(__next_song(server,channel)))
  
  

@client.tree.command(name="stop", description="Stop streaming")
async def __stop_track(interaction: discord.Interaction):
  voice = interaction.guild.voice_client
  if voice is not None and voice.is_playing(
  ):
    interaction.guild.voice_client.stop()
    queues[interaction.guild_id].clear()
    await interaction.response.send_message(embed=embeds["stop"])
  else:
    await interaction.response.send_message(embed=embeds["no_audio"])


@client.tree.command(name="resume", description="Resume playback")
async def __res_track(interaction: discord.Interaction):
  voice = interaction.guild.voice_client
  if voice is not None and voice.is_paused(
  ):
    interaction.guild.voice_client.resume()
    await interaction.response.send_message(embed=embeds["resume"])
  else:
    await interaction.response.send_message(embed=embeds["no_audio"])


@client.tree.command(name="pause", description="Pause audio stream")
async def __pause_track(interaction: discord.Interaction):
  voice = interaction.guild.voice_client
  if voice is not None and voice.is_playing(
  ):
    voice.pause()
    await interaction.response.send_message(embed=embeds["pause"])
  else:
    await interaction.response.send_message(embed=embeds["no_audio"])


@client.tree.command(name="tracklist", description="Display queue")
async def __display_track_queue(interaction: discord.Interaction):

  await interaction.response.defer()

  if interaction.guild_id not in queues:
    return
  if queues[interaction.guild_id] == []:
    await interaction.followup.send(embed=embeds["empty_queue"])
    return
  msg = "\n".join(f"{index + 1}. {s[1]}" for index,s in enumerate(queues[interaction.guild_id]))
  await interaction.followup.send(embed=discord.Embed(
    title="Queue",
    description="```\n" + msg + "```",
    color=discord.Color.blue(),
  ))


@client.tree.command(name="help", description="Display help menu")
async def __help(interaction: discord.Interaction):
  await interaction.response.send_message(embed=embeds["help_slash"])


@client.tree.command(name="rm", description="Remove track from queue")
async def __remove_track(interaction: discord.Interaction, index: int):
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


def extract_metadata(entry):
  video = ytdl.extract_info(entry, download=False)
  if "entries" in video:
    url =  video["entries"][0]["url"]
    title = video["entries"][0]["title"]
    thumbnail = video['entries'][0]['thumbnail']
  else:
    url = video["url"]
    title = video["title"]
    thumbnail = video['thumbnail']
    
  return url, title,thumbnail
  
def get_song_list(entry):
  if (
    "/playlist?list=" in entry or
  ("/watch" in entry and "list=" in entry)) and validators.url(entry):  # only for playlists from url
    output = ytdl.extract_info(entry, download=False)
    return ["youtube.com/watch?v=" + e["id"] for e in output["entries"]]
  return [entry]


@client.event
async def on_voice_state_update(member, before, after):
  if member.guild.voice_client is None:
    return
  channel = member.guild.voice_client.channel
  if len(channel.voice_states) == 1:
    await asyncio.sleep(10)
    if len(channel.voice_states) == 1:
      await member.guild.voice_client.disconnect()


try:
  keep_alive.keep_alive()
  client.run(os.getenv('BOT'))
except discord.errors.HTTPException:
  os.system("kill 1")
