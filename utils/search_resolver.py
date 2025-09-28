# utils/search_resolver.py
import re
import spotipy
import traceback
from youtubesearchpython import VideosSearch

# MUDANÇA AQUI: Regex atualizada para lidar com códigos de idioma (ex: /intl-pt/)
SPOTIFY_URL_REGEX = re.compile(
    r'https?:\/\/open\.spotify\.com\/(?:[a-z\-]+\/)?(?P<type>track|playlist|album)\/(?P<id>[a-zA-Z0-9]+)'
)


def _find_youtube_video(search_term: str):
    """
    Função auxiliar que busca um termo no YouTube e retorna a URL e o Título.
    """
    try:
        search = VideosSearch(search_term, limit=1)
        search_result = search.result()
        results_list = search_result.get('result')

        if not results_list:
            return None, None

        video_info = results_list[0]
        return video_info['link'], video_info['title']
    except Exception as e:
        # --- MUDANÇA AQUI ---
        # Este bloco agora irá imprimir o relatório completo do erro.
        print(f"\n--- TRACEBACK DETALHADO DO ERRO ---")
        print(f"O erro ocorreu ao buscar pelo termo: '{search_term}'")
        traceback.print_exc()
        print("------------------------------------\n")
        return None, None


def _parse_spotify_track(spotify_client: spotipy.Spotify, track_id: str):
    """
    Busca os dados de uma música do Spotify, prioriza o ISRC para a busca no YouTube e retorna a URL direta.
    """
    try:
        track = spotify_client.track(track_id)
        
        isrc = track.get('external_ids', {}).get('isrc')
        if isrc:
            search_term = isrc
        else:
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            search_term = f"{track_name} {artist_name}"

        video_url, video_title = _find_youtube_video(search_term)
        
        if not video_url:
            return None, f"❌ Não encontrei '{track['name']}' no YouTube."

        song_info = {'query': video_url, 'title': video_title, 'filepath': None}
        message = f"**Adicionado da Spotify:** `{video_title}`"
        return [song_info], message

    except Exception as e:
        print(f"Erro ao processar música do Spotify: {e}")
        return None, "❌ Não consegui encontrar essa música no Spotify."


def _parse_spotify_collection(spotify_client: spotipy.Spotify, collection_id: str, collection_type: str):
    """
    Busca os dados de uma playlist/álbum, priorizando o ISRC para cada música na busca do YouTube.
    """
    songs_to_add = []
    try:
        if collection_type == 'playlist':
            results = spotify_client.playlist(collection_id)
        else:  # album
            results = spotify_client.album(collection_id)
        
        collection_name = results['name']
        tracks = results['tracks']['items']

        for item in tracks:
            track = item if collection_type == 'album' else item.get('track')
            if track:
                isrc = track.get('external_ids', {}).get('isrc')
                if isrc:
                    search_term = isrc
                else:
                    track_name = track['name']
                    artist_name = track['artists'][0]['name']
                    search_term = f"{track_name} {artist_name}"

                video_url, video_title = _find_youtube_video(search_term)

                if video_url:
                    songs_to_add.append({'query': video_url, 'title': video_title, 'filepath': None})

        if not songs_to_add:
            return None, f"❌ Não encontrei resultados no YouTube para as músicas da {collection_type} '{collection_name}'."

        message = f"✅ Adicionado **{len(songs_to_add)}** músicas da {collection_type} **'{collection_name}'** à fila!"
        return songs_to_add, message

    except Exception as e:
        print(f"Erro ao processar {collection_type} do Spotify: {e}")
        return None, f"❌ Não consegui processar essa {collection_type} do Spotify."


def resolve_query(query: str, spotify_client: spotipy.Spotify):
    """
    Função principal que delega a busca para as funções corretas.
    """
    match = SPOTIFY_URL_REGEX.match(query)

    if spotify_client and match:
        url_type = match.group('type')
        url_id = match.group('id')
        if url_type == 'track':
            return _parse_spotify_track(spotify_client, url_id)
        elif url_type in ['playlist', 'album']:
            return _parse_spotify_collection(spotify_client, url_id, url_type)

    video_url, video_title = _find_youtube_video(query)
    
    if not video_url:
        return None, f"❌ Não encontrei nenhum resultado no YouTube para: `{query}`"
    
    song_info = {'query': video_url, 'title': video_title, 'filepath': None}
    message = f"**Adicionado à fila:** `{video_title}`"
    return [song_info], message