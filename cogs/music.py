# cogs/music.py (Versão limpa)
import os
import discord
import spotipy
import traceback
from discord.ext import commands, tasks
from utils.music_utils import MusicManager
from spotipy.oauth2 import SpotifyClientCredentials

class MusicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.music_manager = None
        self.buffer_task = None

    def cog_unload(self):
        if self.buffer_task:
            self.buffer_task.cancel()

    def _initialize_spotify_sync(self):
        try:
            spotify_id = os.getenv('SPOTIFY_CLIENT_ID')
            spotify_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
            if not spotify_id or not spotify_secret:
                print("AVISO: Credenciais do Spotify não encontradas.")
                return None
            auth_manager = SpotifyClientCredentials(client_id=spotify_id, client_secret=spotify_secret)
            spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            print("Cliente do Spotify pronto.")
            return spotify_client
        except Exception as e:
            print(f"ERRO CRÍTICO ao inicializar Spotipy: {e}")
            return None

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Bot conectado como {self.bot.user}")
        print(f"Verificando Opus... Carregado: {discord.opus.is_loaded()}")
        print("Inicializando dependências de música de forma assíncrona...")
        spotify_client = await self.bot.loop.run_in_executor(None, self._initialize_spotify_sync)
        self.music_manager = MusicManager(self.bot, spotify_client)
        print('QUAAAAAACK! É HORA DO SHOW!')
        print('------')
        self.buffer_task = self.buffer_manager.start()

    @tasks.loop(seconds=5.0)
    async def buffer_manager(self):
        try:
            if self.music_manager:
                await self.music_manager.buffer_manager_loop()
        except Exception as e:
            print(f"!!! ERRO FATAL NO BUFFER MANAGER: {e} !!!")
            traceback.print_exc()
    
    # --- Comandos ---
    @commands.command(name='play')
    async def play(self, ctx, *, search: str):
        if not self.music_manager: return await ctx.send("O módulo de música ainda está inicializando.")
        await self.music_manager.play(ctx, search)

    @commands.command(name='skip')
    async def skip(self, ctx):
        if not self.music_manager: return await ctx.send("O módulo de música ainda está inicializando.")
        await self.music_manager.skip(ctx)

    @commands.command(name='stop')
    async def stop(self, ctx):
        if not self.music_manager: return await ctx.send("O módulo de música ainda está inicializando.")
        await self.music_manager.stop(ctx)

    @commands.command(name='queue')
    async def queue(self, ctx):
        if not self.music_manager or not self.music_manager.song_queue:
            return await ctx.send("A fila está vazia.")
        embed = discord.Embed(title="Fila de Músicas", color=discord.Color.blue())
        description = ""
        queue_copy = list(self.music_manager.song_queue)
        for i, song in enumerate(queue_copy, 1):
            status = "✅ (Pré-carregado)" if song.get('filepath') else "⏳ (Aguardando download)"
            description += f"**{i}.** {song['title']} {status}\n"
        embed.description = description if description else "A fila está vazia."
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MusicCog(bot))