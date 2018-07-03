import discord
from asyncio import Queue
from asyncio import QueueEmpty
import youtube_dl


class SongQueue:
    def __init__(self):
        self.playlist = Queue()
        self.playing = False
        self.player = None
        self.current_song = {}

    def when_finished(self):
        self.playing = False
        next_song = self.pop()
        if next_song is not None:
            self.enqueue(next_song['url'], next_song['voice'])

    def enqueue(self, url: str, voice: discord.VoiceClient):
        song_info = self.get_dl(url)
        full_song = {"url": url, "voice": voice, "title": song_info['title'], "duration": song_info.get('duration')}
        if self.playing:
            print('Song is currently playing. Adding to queue...')
            self.playlist.put_nowait(full_song)
        else:
            print('Queue is empty. Starting song...')
            self.current_song = full_song
            self.player = voice.create_ffmpeg_player(song_info['url'], after=self.when_finished)
            self.playing = True
            self.player.start()

        return full_song

    def pop(self):
        try:
            next_song = self.playlist.get_nowait()
        except QueueEmpty:
            return None
        return next_song

    def get_queue(self):
        full_queue = []
        while not self.playlist.empty():
            full_queue.append(self.playlist.get_nowait())
        for i in full_queue:
            self.playlist.put_nowait(i)
        return full_queue

    def length(self):
        if self.playing:
            return self.playlist.qsize() + 1
        else:
            return self.playlist.qsize()

    def skip(self):
        print('Skipping...')
        self.player.stop()

    def clear(self):
        print('Stopping...')
        for x in range(0, self.length()):
            self.pop()
        self.player.stop()

    def get_dl(self, url: str):
        opts = {
            'format': 'webm[abr>0]/bestaudio/best',
        }
        ydl = youtube_dl.YoutubeDL(opts)
        info = ydl.extract_info(url, download=False)
        return info

    def calc_duration(self, sec: str):
        total_sec = int(sec)
        minutes = total_sec // 60
        seconds = total_sec % 60
        duration = {"minutes": str(minutes), "seconds": str(seconds).zfill(2)}
        return duration