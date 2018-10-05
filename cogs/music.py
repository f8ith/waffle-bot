"""Music commands."""
import asyncio
import pathlib

import discord
from discord.ext import commands
import youtube_dl

class YoutubeSource:
    """Getting the source and info from youtube."""
    def __init__(self):
        self.opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
                }],
            'outtmpl': '%(id)s.%(ext)s',
            'quiet': True,
        }
        self.ytdl = youtube_dl.YoutubeDL(self.opts)

    def download(self, url):
        """Downloads youtube video and returns file name."""
        info = self.ytdl.extract_info(str(url), download=False)
        title = info.get('id', None) + ".mp3"
        if not pathlib.Path(title).exists():
            self.ytdl.download([url])
        return title

    def getinfo(self, url):
        """Returns video's info."""
        info = self.ytdl.extract_info(str(url), download=False)
        return info

class Music:
    """Main music cog"""

    def __init__(self, bot):
        self.bot = bot
        self.queue = asyncio.Queue(maxsize=50)
        self.youtube = YoutubeSource()
        self.voice_client = None
        self._volume = 0.5

    async def on_ready(self):
        """Prints a message when the cog is ready."""
        print('Music is ready!')

    def play_next_song(self):
        """Creates an event loop for _play_next_song."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._play_next_song())

    async def _play_next_song(self):
        """Plays next song."""
        if self.queue.empty():
            self.voice_client.stop()
            await self.voice_client.disconnect()
            self.voice_client = None
        else:
            source = self.queue.get_nowait()
            self.voice_client.play(discord.FFmpegPCMAudio(source),
                                   after=lambda e: self.play_next_song())
            self.voice_client.source = discord.PCMVolumeTransformer(self.voice_client.source)
            self.voice_client.volume = self._volume
        return

    @commands.command()
    @commands.guild_only()
    async def join(self, ctx):
        """Joins author's channel."""
        voice_state = ctx.author.voice
        self.voice_client = ctx.guild.voice_client
        if voice_state is None:
            await ctx.send("You aren't in a voice channel!")
        elif not self.voice_client:
            voice_channel = voice_state.channel
            self.voice_client = await voice_channel.connect()
        else:
            await ctx.send("I'm already in a voice channel!")

    @commands.command()
    @commands.guild_only()
    async def play(self, ctx, url):
        """Plays a song or adds a song to queue."""
        info = self.youtube.getinfo(url)
        voice_channel = ctx.author.voice.channel
        if self.voice_client is None or voice_channel != self.voice_client.channel:
            self.voice_client = await voice_channel.connect()
        if not self.voice_client.is_playing():
            source = self.youtube.download(url)
            self.voice_client.play(discord.FFmpegPCMAudio(source),
                                   after=lambda e: self.play_next_song())
            self.voice_client.source = discord.PCMVolumeTransformer(self.voice_client.source)
            self.voice_client.volume = self._volume
            await ctx.send("I'm playing %s!" % (info.get("title", None)))
        else:
            song = self.youtube.download(url)
            self.queue.put_nowait(song)
            await ctx.send("I queued up %s!" % (info.get("title", None)))

    @commands.command()
    async def stop(self, ctx):
        """Stops the voice client."""
        self.voice_client = ctx.guild.voice_client
        if not self.voice_client is None:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            await self.voice_client.disconnect()
            del self.queue
            self.queue = asyncio.Queue(maxsize=50)
        else:
            await ctx.send("I'm not connected to voice!")

    @commands.command()
    @commands.guild_only()
    async def pause(self, ctx):
        """Pauses the voice client."""
        self.voice_client = ctx.guild.voice_client
        if not self.voice_client is None:
            if self.voice_client.is_paused():
                await ctx.send("I'm already paused!")
            else:
                self.voice_client.pause()
        else:
            await ctx.send("I'm not connected to voice!")

    @commands.command()
    @commands.guild_only()
    async def resume(self, ctx):
        """Resumes the voice client."""
        self.voice_client = ctx.guild.voice_client
        if not self.voice_client is None:
            if not self.voice_client.is_paused():
                await ctx.send("I'm not paused!")
            else:
                self.voice_client.resume()
        else:
            await ctx.send("I'm not connected to voice!")

    @commands.command()
    @commands.guild_only()
    async def volume(self, ctx, volume):
        """Changes voice client volume."""
        self.voice_client = ctx.guild.voice_client
        self._volume = volume
        if self.voice_client:
            self.voice_client.source = discord.PCMVolumeTransformer(self.voice_client.source)
            self.voice_client.volume = self._volume
        else:
            await ctx.send("I'm not connected to voice!")

    @commands.command()
    @commands.guild_only()
    async def skip(self, ctx):
        """Skips next song."""
        self.voice_client = ctx.guild.voice_client
        if self.queue.empty():
            self.voice_client.stop()
            await self.voice_client.disconnect()
            self.voice_client = None
        else:
            source = self.queue.get_nowait()
            self.voice_client.source = discord.FFmpegPCMAudio(source)
            self.voice_client.source = discord.PCMVolumeTransformer(self.voice_client.source)
            self.voice_client.volume = self._volume


def setup(bot):
    """Sets up the cog."""
    bot.add_cog(Music(bot))
