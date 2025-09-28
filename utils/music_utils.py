# utils/music_utils.py
import os
import yt_dlp
import asyncio
import discord
import traceback
from . import search_resolver

# --- CONSTANTES E CONFIGURAÇÕES GLOBAIS ---
MAX_SONG_DURATION = 900
if not os.path.exists('downloads'): os.makedirs('downloads')

YDL_OPTIONS = {
    'format': 'bestaudio/best', 'outtmpl': 'downloads/%(id)s', 'restrictfilenames': True, 'noplaylist': True,
    'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True,
    'default_search': 'auto', 'source_address': '0.0.0.0',
    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'opus'}],
    'cookiefile': 'youtube-cookies.txt' if os.path.exists('youtube-cookies.txt') else None
}

# --- A CORREÇÃO PRINCIPAL ESTÁ AQUI ---
# Removemos as opções de 'before_options' que eram para streaming.
# '-vn' significa "no video", o que é correto para áudio.
# '-loglevel error' fará o FFmpeg reportar erros no console se algo ainda der errado.
FFMPEG_OPTIONS = {'options': '-vn -loglevel error'}


class MusicManager:
    def __init__(self, bot, spotify_client):
        self.bot = bot
        self.spotify = spotify_client
        self.song_queue = []
        self.disconnect_timer = None
        self.currently_playing_file = None
        self.is_playing = False
        self.download_lock = asyncio.Lock()

    async def download_song_with_lock(self, url: str):
        print(f"--- [LOCK] Aguardando para adquirir o lock de download para: {url} ---")
        async with self.download_lock:
            print(f"--- [LOCK] Lock adquirido! Iniciando download para: {url} ---")
            try:
                return await self.bot.loop.run_in_executor(
                    None, self._download_song_sync, url
                )
            finally:
                print(f"--- [LOCK] Lock liberado para: {url} ---")

    def _download_song_sync(self, url: str):
        try:
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(url, download=False)
                video_id = info.get('id')
                filepath = f"downloads/{video_id}.opus"
                if not os.path.exists(filepath):
                    ydl.download([url])
                print(f"DEBUG: Download síncrono concluído. Arquivo: {filepath}")
                return 'SUCCESS', info, filepath
        except Exception as e:
            print(f"Erro crítico no download síncrono com yt-dlp: {e}")
            return 'NOT_FOUND', None, None

    async def delayed_cleanup(self, path):
        await asyncio.sleep(2)
        try:
            if path and os.path.exists(path):
                os.remove(path)
                print(f"[CLEANUP]: Arquivo removido: {path}")
        except OSError as e:
            print(f"[CLEANUP]: Erro ao remover o arquivo {path}: {e}")

    def play_after_cleanup(self, error, ctx, song_path):
        print("\n--- [CALLBACK AFTER]: Função play_after_cleanup ATIVADA ---")
        if error:
            print(f"--- [CALLBACK AFTER]: Um ERRO foi recebido pelo player! ---")
            traceback.print_exception(type(error), error, error.__traceback__)
        else:
            print("--- [CALLBACK AFTER]: Música finalizada normalmente (sem erros reportados pelo player). ---")
        
        self.is_playing = False
        self.bot.loop.create_task(self.delayed_cleanup(song_path))
        self.currently_playing_file = None
        self.play_next(ctx)
        print("--- [CALLBACK AFTER]: Próxima música agendada. ---\n")

    def play_next(self, ctx):
        self.bot.loop.create_task(self._play_next_async(ctx))

    async def _play_next_async(self, ctx):
        print("\n--- [PLAY_NEXT] CHECKPOINT A: Iniciando _play_next_async ---")
        if self.is_playing or not self.song_queue:
            print(f"--- [PLAY_NEXT] CHECKPOINT B: Saindo. Causa: is_playing={self.is_playing}, Fila vazia={not self.song_queue} ---")
            if not self.song_queue and not self.is_playing:
                self.disconnect_timer = self.bot.loop.create_task(self.disconnect_after_inactivity(ctx))
            return

        self.is_playing = True
        song_to_play = self.song_queue.pop(0)
        filepath = song_to_play.get('filepath')
        print(f"--- [PLAY_NEXT] CHECKPOINT C: Processando '{song_to_play['title']}'. Filepath no dict: {filepath} ---")

        if not filepath:
            print("--- [PLAY_NEXT] CHECKPOINT D: Filepath não encontrado. Chamando download_song_with_lock. ---")
            status, data, filepath = await self.download_song_with_lock(song_to_play['query'])
            if status != 'SUCCESS':
                await ctx.send(f"❌ Falha ao baixar '{song_to_play['title']}'. Pulando.")
                self.is_playing = False
                return self.play_next(ctx)
        
        print(f"--- [PLAY_NEXT] CHECKPOINT E: Caminho do arquivo a ser tocado: '{filepath}' ---")
        
        if not os.path.exists(filepath):
            print(f"--- [PLAY_NEXT] CHECKPOINT F: ERRO CRÍTICO! Arquivo '{filepath}' não existe no disco. ---")
            await ctx.send(f"❌ Erro: Arquivo para '{song_to_play['title']}' não encontrado. Pulando.")
            self.is_playing = False
            return self.play_next(ctx)
            
        print("--- [PLAY_NEXT] CHECKPOINT G: Arquivo confirmado no disco. Criando FFmpegPCMAudio. ---")
        self.currently_playing_file = filepath
        source = discord.FFmpegPCMAudio(filepath, **FFMPEG_OPTIONS)
        
        print("--- [PLAY_NEXT] CHECKPOINT H: Chamando ctx.voice_client.play() AGORA. ---")
        ctx.voice_client.play(source, after=lambda e: self.play_after_cleanup(e, ctx, filepath))
        
        await ctx.send(f'**Tocando agora:** {song_to_play["title"]}')
        print("--- [PLAY_NEXT] CHECKPOINT I: Música enviada para o Discord. ---")

    async def buffer_manager_loop(self):
        if not self.song_queue: return
        next_song = self.song_queue[0]
        if next_song.get('filepath'): return

        status, data, filepath = await self.download_song_with_lock(next_song['query'])
        
        if self.song_queue and self.song_queue[0]['query'] == next_song['query']:
            if status == 'SUCCESS':
                self.song_queue[0].update({'title': data.get('title', 'Título desconhecido'), 'filepath': filepath})
                print(f"Buffer: '{data.get('title')}' pré-carregado.")
            else:
                self.song_queue.pop(0)
    
    # ... (o resto das funções, como play, stop, skip, etc., não precisam de mudanças) ...
    async def disconnect_after_inactivity(self, ctx):
        await asyncio.sleep(60)
        if not self.is_playing and not self.song_queue:
            await ctx.send("Fiquei um tempo ocioso. Quack!")
            await ctx.voice_client.disconnect()
            
    async def play(self, ctx, search):
        if self.disconnect_timer: self.disconnect_timer.cancel()
        if not ctx.author.voice:
            return await ctx.send("Você precisa estar em um canal de voz para tocar música!")
        voice_client = ctx.voice_client
        if not voice_client:
            try:
                voice_client = await ctx.author.voice.channel.connect()
            except Exception as e:
                await ctx.send(f"Não consegui me conectar ao canal de voz: {e}")
                return
        queue_was_empty = not self.song_queue and not self.is_playing
        await ctx.send(f"🔎 Processando sua busca: `{search}`...")
        songs, message = await self.bot.loop.run_in_executor(None, search_resolver.resolve_query, search, self.spotify)
        if songs:
            self.song_queue.extend(songs)
            await ctx.send(message)
        else:
            await ctx.send(message)
        if queue_was_empty and self.song_queue:
            self.play_next(ctx)

    async def stop(self, ctx):
        if ctx.voice_client:
            self.song_queue.clear()
            self.is_playing = False
            if self.currently_playing_file:
                self.bot.loop.create_task(self.delayed_cleanup(self.currently_playing_file))
            if ctx.voice_client.is_playing():
                ctx.voice_client.stop()
            await ctx.send("Música parada e fila limpa.")
            if self.disconnect_timer: self.disconnect_timer.cancel()
            self.disconnect_timer = self.bot.loop.create_task(self.disconnect_after_inactivity(ctx))

    async def skip(self, ctx):
        if ctx.voice_client and self.is_playing:
            await ctx.send("Pulando...")
            ctx.voice_client.stop()
        else:
            await ctx.send("Não há música tocando para pular.")