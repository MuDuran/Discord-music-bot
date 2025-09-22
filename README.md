# 🦆 QuackMusic Bot

Um bot de música para Discord desenvolvido em Python que toca músicas do YouTube e do Spotify.

## ✨ Funcionalidades

- Toca músicas a partir de buscas por texto no YouTube.
- Toca músicas a partir de links do YouTube.
- Toca músicas a partir de links de faixas do Spotify.
- Sistema de fila de músicas.
- Comandos `play`, `skip`, `stop`, `queue` e `leave`.
- Desconexão automática após um período de inatividade.

## 🚀 Como Usar

1. Clone este repositório.
2. Crie um arquivo `.env` e adicione seus tokens:
   - `DISCORD_TOKEN=...`
   - `SPOTIFY_CLIENT_ID=...`
   - `SPOTIFY_CLIENT_SECRET=...`
3. Instale as dependências: `pip install -r requirements.txt` (teremos que criar este arquivo)
4. Rode o bot: `python main.py`

## ⚙️ Comandos

- `!play <nome da música ou link>`
- `!skip`
- `!stop`
- `!queue`
- `!leave`
