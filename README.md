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

### Execução Local
1. Clone este repositório.
2. Crie um arquivo `.env` e adicione seus tokens:
   - `DISCORD_TOKEN=...`
   - `SPOTIFY_CLIENT_ID=...`
   - `SPOTIFY_CLIENT_SECRET=...`
3. Instale as dependências: `pip install -r requirements.txt`
4. Rode o bot: `python main.py`

### Execução com Docker e Kubernetes

#### Pré-requisitos
- [Task](https://taskfile.dev/) instalado
- Docker instalado e configurado
- Kubectl configurado para seu cluster Kubernetes
- Helm instalado

#### Configuração
1. Copie o arquivo de exemplo de ambiente:
   ```bash
   cp .env.example .env
   ```

2. Edite o arquivo `.env` e preencha suas credenciais:
   ```bash
   DISCORD_TOKEN=your_discord_bot_token_here
   SPOTIFY_CLIENT_ID=your_spotify_client_id_here
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
   ```

#### Comandos Disponíveis

Verifique as variáveis de ambiente:
```bash
task check-env
```

Construir a imagem Docker:
```bash
task build
```

Publicar a imagem para docker.lunari.studio:
```bash
task push
```

Instalar o bot no Kubernetes:
```bash
task helm-install
```

Instalar com armazenamento persistente:
```bash
task helm-install-with-persistence
```

Deploy completo (build + push + install):
```bash
task deploy
```

Ver logs do bot:
```bash
task logs
```

Verificar status da instalação:
```bash
task helm-status
```

Desinstalar o bot:
```bash
task helm-uninstall
```

Ver todos os comandos disponíveis:
```bash
task help
```

## ⚙️ Comandos

- `!play <nome da música ou link>`
- `!skip`
- `!stop`
- `!queue`
- `!leave`
