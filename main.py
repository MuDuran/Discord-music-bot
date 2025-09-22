import os
import discord
import spotipy
import yt_dlp
import asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# Declarção de variáveis globais
song_queue = []
disconnect_timer = None
currently_playing_file = None

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Configura a autenticação com o Spotify
spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_ID,
                                                                 client_secret=SPOTIFY_SECRET))

# Configurações do yt-dlp
# Cria uma pasta chamada 'downloads' no seu projeto para organizar os arquivos
if not os.path.exists('downloads'):
    os.makedirs('downloads')

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'cookiefile': 'youtube-cookies.txt',
    'outtmpl': 'downloads/%(id)s.%(ext)s', # Salva o arquivo com um nome único na pasta downloads
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
    # Converte o áudio para o formato opus para melhor performance com discord.py
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'opus',
    }],
}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

# Define as intents (permissões) que o bot precisa
intents = discord.Intents.default()
intents.message_content = True # Permite que o bot leia o conteúdo das mensagens

# Cria a instância do bot, definindo o prefixo dos comandos
bot = commands.Bot(command_prefix='!', intents=intents)

# Evento que é disparado quando o bot está pronto e conectado
@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    print('QUAAAAAACK! É HORA DO SHOW!')
    print('------')
    buffer_manager.start()

@bot.command(name='join')
async def join(ctx):
    # Verifica se o autor do comando está em um canal de voz
    if not ctx.author.voice:
        await ctx.send(f'{ctx.author.mention}, você não está conectado a um canal de voz!')
        return
    else:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Conectado ao canal: {channel.name}')

@bot.command(name='leave')
async def leave(ctx):
    global disconnect_timer # <-- Declarar a variável global

    # Cancela qualquer cronômetro pendente antes de desconectar
    if disconnect_timer:
        disconnect_timer.cancel()
        disconnect_timer = None

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Desconectado do canal de voz.')
    else:
        await ctx.send('Eu não estou em nenhum canal de voz.')

def download_song(search_query):
    """
    Função síncrona que lida com Spotify, baixa a música e retorna o info do yt-dlp.
    """
    search_term = search_query
    if "open.spotify.com" in search_term:
        try:
            track = spotify.track(search_term)
            search_term = f"{track['name']} {track['artists'][0]['name']}"
        except Exception as e:
            print(f"Erro ao processar Spotify: {e}")
            return None

    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search_term}", download=True)['entries'][0]
            return info
        except Exception as e:
            print(f"Erro no download/busca: {e}")
            return None

@tasks.loop(seconds=5.0)
async def buffer_manager():
    """Verifica a fila e pré-carrega a próxima música."""
    if not song_queue or len(song_queue) == 0:
        return
        
    next_song = song_queue[0]
    
    if next_song.get('filepath'):
        return

    print(f"Buffer Manager: Pré-carregando '{next_song['title']}'...")
    info = await bot.loop.run_in_executor(None, download_song, next_song['query'])
    
    if info:
        filepath = info.get('requested_downloads')[0].get('filepath')
        song_queue[0].update({
            'title': info.get('title', 'Título desconhecido'),
            'filepath': filepath
        })
        print(f"Buffer Manager: '{info.get('title')}' pré-carregado com sucesso.")
    else:
        print(f"Buffer Manager: Falha ao pré-carregar '{next_song['title']}'. Removendo da fila.")
        song_queue.pop(0)

@bot.command(name='play', help='Toca uma música ou a adiciona na fila com buffer.')
async def play(ctx, *, search: str):
    global disconnect_timer
    if disconnect_timer:
        disconnect_timer.cancel()
        disconnect_timer = None

    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
        return
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    # Adiciona a 'tarefa' à fila. O buffer_manager vai cuidar do resto.
    song_task = {'query': search, 'title': search, 'filepath': None}
    song_queue.append(song_task)
    await ctx.send(f"**Adicionado à fila:** `{search}`")

    # Se NADA estiver tocando, inicia a primeira música para ser rápido
    if not ctx.voice_client.is_playing():
        play_next(ctx)

async def delayed_cleanup(path):
    """Espera um pouco e depois apaga um arquivo para evitar condições de corrida."""
    await asyncio.sleep(10)  # Espera 3 segundos
    try:
        if path and os.path.exists(path):
            os.remove(path)
            print(f"Limpeza atrasada: Arquivo removido: {path}")
    except OSError as e:
        print(f"Limpeza atrasada: Erro ao remover o arquivo {path}: {e}")

def play_after_cleanup(ctx, song_path):
    """
    Inicia a tarefa de limpeza atrasada para o arquivo antigo e 
    chama a próxima música imediatamente.
    """
    global currently_playing_file
    
    # Inicia a limpeza em segundo plano, sem esperar
    bot.loop.create_task(delayed_cleanup(song_path))
    
    currently_playing_file = None
    play_next(ctx)

def play_next(ctx):
    """Verifica a fila e toca a próxima música, seja do buffer ou baixando na hora."""
    global disconnect_timer
    global currently_playing_file

    if disconnect_timer:
        disconnect_timer.cancel()
        disconnect_timer = None
        
    if len(song_queue) > 0 and ctx.voice_client and ctx.voice_client.is_connected():
        voice_client = ctx.voice_client
        song_info = song_queue.pop(0)
        
        filepath = song_info.get('filepath')
        # Se a música já foi baixada pelo buffer, toca direto
        if filepath and os.path.exists(filepath):
            currently_playing_file = filepath
            callback = lambda e: play_after_cleanup(ctx, filepath)
            source = discord.FFmpegPCMAudio(filepath)
            voice_client.play(source, after=callback)
            bot.loop.create_task(ctx.send(f'**Tocando (do buffer):** {song_info["title"]}'))
        # Se não foi baixada (ex: primeira música, ou skip muito rápido)
        else:
            bot.loop.create_task(ctx.send(f"🔎 O buffer está alcançando... Baixando `{song_info['title']}` agora."))
            bot.loop.create_task(play_now(ctx, song_info['query']))
    else:
        disconnect_timer = bot.loop.create_task(disconnect_after_inactivity(ctx))

async def play_now(ctx, query):
    """Função async para baixar e tocar uma música imediatamente (fallback)."""
    global currently_playing_file
    info = await bot.loop.run_in_executor(None, download_song, query)
    if info:
        filepath = info['requested_downloads'][0]['filepath']
        currently_playing_file = filepath
        callback = lambda e: play_after_cleanup(ctx, filepath)
        source = discord.FFmpegPCMAudio(filepath)
        ctx.voice_client.play(source, after=callback)
        await ctx.send(f'**Tocando agora:** {info["title"]}')
    else:
        await ctx.send(f"Não consegui tocar `{query}`.")
        play_next(ctx)

@bot.command(name='stop')
async def stop(ctx):
    global song_queue
    global disconnect_timer

    if ctx.voice_client:
        # Limpa os arquivos da FILA (buffer), mas NÃO o que está tocando
        for song in song_queue:
            filepath = song.get('filepath')
            if filepath and os.path.exists(filepath):
                # Usamos a limpeza atrasada aqui também para segurança
                bot.loop.create_task(delayed_cleanup(filepath))
        
        song_queue = []
        
        # Para o player, o que vai acionar o 'after' para limpar o arquivo atual
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        
        await ctx.send("Música parada e fila de downloads limpa.")
        
        if disconnect_timer:
            disconnect_timer.cancel()
        disconnect_timer = bot.loop.create_task(disconnect_after_inactivity(ctx))

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send("Pulando para a próxima música...")
        # Apenas paramos o player. O 'after' callback fará o resto.
        ctx.voice_client.stop()
    else:
        await ctx.send("Não há música tocando para pular.")

@bot.command(name='queue', help='Mostra as músicas na fila')
async def queue(ctx):
    if len(song_queue) == 0:
        await ctx.send("A fila de músicas está vazia!")
        return

    # Cria uma mensagem formatada
    embed = discord.Embed(title="Fila de Músicas", color=discord.Color.blue())
    
    # Adiciona as músicas na mensagem
    # O enumerate começa do 1 para uma lista mais amigável
    description = ""
    for i, song in enumerate(song_queue, 1):
        description += f"**{i}.** {song['title']}\n"
    
    embed.description = description
    await ctx.send(embed=embed)

async def disconnect_after_inactivity(ctx):
    """Espera 5 minutos e desconecta se o bot estiver inativo."""
    print("Iniciando cronômetro de inatividade...")
    await asyncio.sleep(60) # Var em Segundos -> 60 = 1 minuto

    voice_client = ctx.voice_client
    if voice_client and not voice_client.is_playing() and len(song_queue) == 0:
        await ctx.send("Fiquei um tempo ocioso e a fila está vazia. Estou me desconectando. Quack!")
        await voice_client.disconnect()
        print("Desconectado por inatividade.")

# Inicialização do QuackMusic
bot.run(TOKEN)