import random
from discord import Game
from discord.ext.commands import Bot
from discord.utils import get
import discord
import requests
import music_queue

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


BOT_PREFIX = "!"
TOKEN = "BOT TOKEN HERE"

YOUTUBE_DEV_KEY = 'API KEY HERE'
YOUTUBE_API_SVC_NAME = 'youtube'
YOUTUBE_API_VER = 'v3'

client = Bot(command_prefix=BOT_PREFIX)
playlists = {}
sound_playing = False

client.remove_command('help')


@client.command(name='face', aliases=['faces'])
async def face():
    possible_faces = [
        ':eye: :lips: :eye:',
        ':joy: :ok_hand: ',
        ':eye: :tongue: :eye:',
        ':eye: :nose: :eye:',
    ]
    await client.say(random.choice(possible_faces))


@client.event
async def on_ready():
    await client.change_presence(game=Game(name="with humans | Use !help for list of commands"))


@client.command(pass_context=True)
async def nick(ctx, *,  name: str):
    await client.change_nickname(ctx.message.author, name)


@client.command(pass_context=True)
async def echo(ctx, *, message: str):
    await client.send_message(ctx.message.channel, message)


@client.group(pass_context=True, aliases=['calculator'])
async def calc(ctx):
    if ctx.invoked_subcommand is None:
        await client.say('Invalid calculator command!')


@calc.command(aliases=['sum'])
async def add(num1: float, num2: float):
    summ = num1 + num2
    await client.say(str(summ))


@calc.command(aliases=['subtract'])
async def sub(num1: float, num2: float):
    diff = num1 - num2
    await client.say(str(diff))


@calc.command(aliases=['mult', 'product', 'prod'])
async def multiply(num1: float, num2: float):
    prod = num1 * num2
    await client.say(str(prod))


@calc.command(aliases=['div'])
async def divide(num1: float, num2: float):
    quot = num1 / num2
    await client.say(str(quot))


@calc.command(aliases=['sq', 'squared'])
async def square(num: float):
    squared = num * num
    await client.say(str(squared))


@client.command(pass_context=True)
async def color(ctx, col: str):
    user = ctx.message.author
    role = discord.utils.get(user.server.roles, name = col)
    if role is None:
        await client.say("Sorry, that color is not currently supported. :(")
    await client.replace_roles(user, role)
    await client.say(user.mention + ", your color has been changed to " + col + ".")


@client.event
async def on_message(message):
    user = message.author
    if client.user in message.mentions:
        possible_responses = [
            ' Yes',
            ' No'
        ]
        await client.send_message(message.channel, user.mention + random.choice(possible_responses))

    await client.process_commands(message)


@client.command()
async def qotd():
    url = "https://quotes.rest/qod"
    r = requests.get(url=url)
    data = r.json()
    quote = data['contents']['quotes'][0]['quote']
    author = data['contents']['quotes'][0]['author']
    await client.say('"' + quote + '"' + " - " + author)


@client.command(pass_context=True)
async def join(ctx):
    channel = ctx.message.author.voice.voice_channel

    if channel is None:
        await client.say('You are not currently in a voice channel. Please join a voice channel before inviting me in.')
        return

    await client.join_voice_channel(channel)


@client.command(pass_context=True)
async def leave(ctx):
    await (client.voice_client_in(ctx.message.server)).disconnect()


def youtube_query(query: str):
    youtube = build(YOUTUBE_API_SVC_NAME, YOUTUBE_API_VER, developerKey=YOUTUBE_DEV_KEY)

    response = youtube.search().list(q=query, part='id, snippet', maxResults=10).execute()

    videos = []

    for result in response.get('items', []):
        if result['id']['kind'] == 'youtube#video':
            current_vid = {"title": result['snippet']['title'],
                           "url": "https://www.youtube.com/watch?v=" + result['id']['videoId']}
            videos.append(current_vid)
            if len(videos) == 5:
                break
    return videos


@client.command(pass_context=True)
async def play(ctx, *, term: str):
    server = ctx.message.server
    voice = client.voice_client_in(server)

    global sound_playing

    if sound_playing:
        await client.say("Wait for the current sound to finish playing, then try again.")
        return

    if server.id not in playlists:
        playlists[server.id] = music_queue.SongQueue()

    playlist = playlists[server.id]

    channel = ctx.message.author.voice.voice_channel
    if channel is None:
        await client.say('You are not currently in a voice channel. Please join a voice channel before asking '
                         'me to play audio!')
        return

    if term.startswith("https://www.youtube.com"):
        if "&list=" in term:
            await client.say("I'm currently not able to play playlists :( . Please provide a link to a video!")
            return
        url = term
    else:
        try:
            results = youtube_query(term)
        except HttpError:
            print('An HTTP error occurred.\n')

        result_string = '**Select a choice by typing 1-5.**\n'
        for pos, song in enumerate(results, start=1):
            result_string += "**" + str(pos) + ".** " + song['title'] + "\n"

        await client.say(result_string, delete_after=30)

        def check(msg):
            return (msg.content == "1" or msg.content == "2" or msg.content == "3" or msg.content == "4"
                    or msg.content == "5")

        choice = await client.wait_for_message(timeout=30, author=ctx.message.author, check=check)
        if choice is None:
            return
        choice_num = int(choice.content) - 1
        url = results[choice_num]['url']

    if voice is None:
        await client.join_voice_channel(channel)
        voice = client.voice_client_in(server)

    song = playlist.enqueue(url, voice)
    duration = playlist.calc_duration(song['duration'])
    await client.say("**" + song['title'] + "** (" + duration['minutes'] + ":" + duration['seconds']
                     + ") was added to the queue.")


@client.command(pass_context=True)
async def skip(ctx):
    server = ctx.message.server
    playlist = playlists[server.id]
    if playlist.length() > 0:
        print('skip: playlist not empty')
        duration = playlist.calc_duration(playlist.current_song['duration'])
        await client.say("Skipping audio: **" + playlist.current_song['title'] + "** (" + duration['minutes'] + ":"
                         + duration['seconds'] + ")")
        playlist.skip()
    else:
        print('skip: playlist empty')
        await client.say("There is currently no audio to skip!")


@client.command(pass_context=True)
async def clear(ctx):
    server = ctx.message.server
    playlist = playlists[server.id]
    if playlist.length() > 0:
        await client.say("Clearing all audio from the queue.")
        playlist.clear()
    else:
        await client.say("There is no audio in the queue to clear!")


@client.command(pass_context=True)
async def queue(ctx):
    server = ctx.message.server
    playlist = playlists[server.id]
    if playlist.length() > 0:
        queue_list = playlist.get_queue()
        queue_string = ""
        curr_duration = playlist.calc_duration(playlist.current_song['duration'])
        queue_string += "**Now Playing:** " + playlist.current_song['title'] + " (" + curr_duration['minutes'] + ":" \
                        + curr_duration['seconds'] + ")\n"
        for pos, song in enumerate(queue_list, start=1):
            duration = playlist.calc_duration(song['duration'])
            queue_string += "**" + str(pos) + ".** " + song['title'] + " (" + duration['minutes'] + ":" + duration['seconds'] \
                            + ")\n"

        await client.say(queue_string)
    else:
        await client.say("The queue is currently empty.")


def image_search(term: str):
    service = build("customsearch", "v1", developerKey='API KEY HERE')

    response = service.cse().list(q=term, num=1, start=1, imgSize="medium", searchType="image",
                                  cx='SEARCH ENGINE KEY HERE').execute()

    result = response.get('items', [])
    img_url = result[0]['link']
    return img_url


@client.command(aliases=['img'])
async def image(*, term):
    link = image_search(term)
    await client.say(link)


def change_playing():
    global sound_playing
    sound_playing = False


@client.command(pass_context=True)
async def mundo(ctx, num):
    server = ctx.message.server

    if server.id not in playlists:
        playlists[server.id] = music_queue.SongQueue()

    playlist = playlists[server.id]
    if playlist.length() > 0:
        await client.say("There is something currently playing or queued to play. Try again when the queue is empty.")
        return
    else:
        channel = ctx.message.author.voice.voice_channel
        if channel is None:
            await client.say('You are not currently in a voice channel. Please join a voice channel before asking '
                             'me to play audio!')
            return

        voice = client.voice_client_in(server)

        global sound_playing

        if sound_playing:
            await client.say("Wait for the current sound to finish playing, then try again.")
            return

        if voice is None:
            await client.join_voice_channel(channel)
            voice = client.voice_client_in(server)

        if num == "1":
            player = voice.create_ffmpeg_player('audio_files\Mundo1.mp3', after=change_playing)
        elif num == "2":
            player = voice.create_ffmpeg_player('audio_files\Mundo2.mp3', after=change_playing)
        elif num == "3":
            player = voice.create_ffmpeg_player('audio_files\Mundo3.mp3', after=change_playing)
        elif num == "4":
            player = voice.create_ffmpeg_player('audio_files\Mundo4.mp3', after=change_playing)
        elif num == "5":
            player = voice.create_ffmpeg_player('audio_files\Mundo5.mp3', after=change_playing)
        elif num == "6":
            player = voice.create_ffmpeg_player('audio_files\Mundo6.mp3', after=change_playing)
        elif num == "7":
            player = voice.create_ffmpeg_player('audio_files\Mundo8.mp3', after=change_playing)
        elif num == "8":
            player = voice.create_ffmpeg_player('audio_files\Mundo9.mp3', after=change_playing)
        else:
            await client.say("Mundo too strong for you! Please choose 1-8 for Mundo, he doesn't feel "
                             "like saying much else!")
            return

        sound_playing = True

        player.start()


@client.command(pass_context=True)
async def help(ctx):
    embed = discord.Embed(color=0x008000)
    embed.set_author(name="GrouchBot", icon_url=client.user.avatar_url)
    embed.set_thumbnail(url=client.user.avatar_url)
    embed.add_field(name="!help", value="Shows this message.", inline=False)
    embed.add_field(name="!face", value="Posts a random face out of a small selection into chat.", inline=False)
    embed.add_field(name="!nick [nickname]", value="Changes your nickname in this server to the provided name.",
                    inline=False)
    embed.add_field(name="!echo [message]", value="Echoes the message in chat.", inline=False)
    embed.add_field(name="!calc add [n1] [n2]", value="Posts the sum of n1 and n2 in chat.", inline=False)
    embed.add_field(name="!calc sub [n1] [n2]", value="Subtracts n2 from n1 and posts the difference in chat.",
                    inline=False)
    embed.add_field(name="!calc multiply [n1] [n2]", value="Posts the product of n1 and n2 in chat.", inline=False)
    embed.add_field(name="!calc divide [n1] [n2]", value="Divides n1 by n2 and posts the result in chat.", inline=False)
    embed.add_field(name="!calc square [num]", value="Squares num and posts the result in chat.", inline=False)
    embed.add_field(name="!color [color]", value="Changes your name color in the server to the provided color. \n"
                                                 "Color Options: aqua, green, blue, purple, magenta, orange, red, "
                                                 "yellow, white", inline=False)
    embed.add_field(name="!qotd", value="Gets the quote of the day from the They Said So Quotes API.", inline=False)
    embed.add_field(name="!image [term]", value="Returns the first image found after a Google search using the "
                                                "search term", inline=False)
    embed.add_field(name="!join", value="Invites the bot into the voice channel the user is currently in.",
                    inline=False)
    embed.add_field(name="!leave", value="Tells the bot to leave your voice channel.", inline=False)
    embed.add_field(name="!play [url/term]", value="If a YouTube url is provided, the bot "
                                                   "will join your voice channel and begin playing the audio. "
                                                   "If a search term is provided, the bot will search YouTube with the "
                                                   "term and provide the top 5 results. The user can then choose an "
                                                   "option to play in the voice channel. An option is chosen by "
                                                   "typing 1-5.", inline=False)
    embed.add_field(name="!skip", value="Skips the audio currently being played by the bot.", inline=False)
    embed.add_field(name="!clear", value="Clears the audio queue and stops the currently playing audio.", inline=False)
    embed.add_field(name="!queue", value="Displays the audio queue with song names and durations.", inline=False)
    embed.add_field(name="!mundo [1-8]", value="Mundo goes where he pleases.", inline=False)
    await client.send_message(destination=ctx.message.author, content="**Here is a list of my commands!**")
    await client.send_message(destination=ctx.message.author, embed=embed)

#pip install: requests, discord.py, youtube_dl
client.run(TOKEN)
