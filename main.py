import os
import discord
import spotipy
import yt_dlp
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# Declarção de variáveis globais
song_queue = []
disconnect_timer = None

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
SPOTIFY_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Configura a autenticação com o Spotify
spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_ID,
                                                                 client_secret=SPOTIFY_SECRET))

# Configurações do yt-dlp
YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
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

def search_and_extract_info(search_term):
    """
    Função síncrona que executa o trabalho pesado do yt-dlp.
    Retorna o dicionário 'info' da primeira entrada encontrada.
    """
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            search_results = ydl.extract_info(f"ytsearch:{search_term}", download=False)
            if not search_results or not search_results.get('entries'):
                return None # Retorna None se nada for encontrado
            return search_results['entries'][0]
        except Exception as e:
            print(f"Erro no search_and_extract_info: {e}")
            return None

@bot.command(name='play', help='Toca uma música do YouTube ou Spotify')
async def play(ctx, *, search: str):
    global disconnect_timer
    if disconnect_timer:
        disconnect_timer.cancel()
        disconnect_timer = None

    # --- Bloco de conexão ao canal de voz (sem alterações) ---
    if not ctx.author.voice:
        await ctx.send("Você precisa estar em um canal de voz para usar este comando!")
        return
    if not ctx.voice_client:
        try:
            channel = ctx.author.voice.channel
            await channel.connect()
        except Exception as e:
            await ctx.send("Não consegui me conectar ao canal de voz.")
            print(f"Erro ao conectar no canal: {e}")
            return

    # --- LÓGICA DE BUSCA (com pequena alteração) ---
    search_term = search
    if "open.spotify.com" in search:
        try:
            await ctx.send("Processando link do Spotify...")
            track = spotify.track(search)
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            search_term = f"{track_name} {artist_name}"
            await ctx.send(f'Música encontrada: **{track_name}** por **{artist_name}**. Buscando no YouTube...')
        except Exception as e:
            await ctx.send("Ocorreu um erro ao processar o link do Spotify.")
            print(f"Erro na API do Spotify: {e}")
            return

    # --------------------------------------------------------------------------
    # MUDANÇA PRINCIPAL: EXECUTANDO A BUSCA EM SEGUNDO PLANO
    # --------------------------------------------------------------------------
    await ctx.send(f"🔎 Buscando por `{search_term}`...")
    
    # Delegamos a função bloqueante 'search_and_extract_info' para o executor do loop
    info = await bot.loop.run_in_executor(None, search_and_extract_info, search_term)

    if info is None:
        await ctx.send(f"Não encontrei nenhum resultado no YouTube para `{search_term}`.")
        return
    
    # --- O resto da lógica da fila e de tocar a música continua igual ---
    song = {'url': info['url'], 'title': info['title']}
    
    if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
        song_queue.append(song)
        await ctx.send(f"**Adicionado à fila:** {song['title']}")
    else:
        ctx.voice_client.play(discord.FFmpegPCMAudio(song['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        await ctx.send(f'**Tocando agora:** {song["title"]}')

# Função auxiliar para tocar a próxima da fila
def play_next(ctx):
    # Verifica se a fila não está vazia E se o bot ainda está conectado
    if len(song_queue) > 0 and ctx.voice_client and ctx.voice_client.is_connected():
        voice_client = ctx.voice_client
        
        # Pega a primeira música da fila
        next_song = song_queue.pop(0)
        
        # O argumento 'after' garante que esta função será chamada de novo, criando um loop
        voice_client.play(discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        
        # Envia a mensagem em uma corrotina para não bloquear o bot
        # Isso avisa no chat qual é a próxima música
        bot.loop.create_task(ctx.send(f'**Tocando agora:** {next_song["title"]}'))

@bot.command(name='stop')
async def stop(ctx):
    global song_queue
    global disconnect_timer

    if ctx.voice_client:
        ctx.voice_client.stop()
        song_queue = [] # Limpa a fila
        await ctx.send("Música parada e fila limpa.")
        
        # Como o bot agora está inativo, iniciamos o cronômetro
        if disconnect_timer:
            disconnect_timer.cancel() # Cancela qualquer timer antigo antes de criar um novo
        disconnect_timer = bot.loop.create_task(disconnect_after_inactivity(ctx))

@bot.command(name='skip')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop() # Isso vai acionar o 'after' da função play e tocar a próxima
        await ctx.send("Música pulada.")
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

def play_next(ctx):
    global disconnect_timer

    if len(song_queue) > 0 and ctx.voice_client and ctx.voice_client.is_connected():
        voice_client = ctx.voice_client
        next_song = song_queue.pop(0)
        voice_client.play(discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx))
        bot.loop.create_task(ctx.send(f'**Tocando agora:** {next_song["title"]}'))
    else:
        # A fila acabou, então iniciamos o cronômetro para desconectar
        disconnect_timer = bot.loop.create_task(disconnect_after_inactivity(ctx))

# Inicialização do QuackMusic
bot.run(TOKEN)