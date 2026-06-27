<!-- PROJECT LOGO -->
<br />
<p align="center">
  <a href="https://github.com/villheik/Rankaisijabot">
    <img src="images/rankaisija.jpg" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Rankaisijabot</h3>

  <p align="center">
    Really good bot
    <br />
    <a href="https://github.com/villheik/Rankaisijabot/issues">Report Bug</a>
    ·
    <a href="https://github.com/villheik/Rankaisijabot/issues">Request Feature</a>
  </p>
</p>


## AI Development Guidelines

AI assistants should read [`.ai/GUIDELINES.md`](.ai/GUIDELINES.md) for project conventions before generating code or tests. This covers Python version requirements, cog structure, testing patterns, and code conventions.


## About The Project

Rankaisijabot is a Discord bot built for a private server. Commands use the `!` prefix.

### Built With

* Python 3.12+
* discord.py 2.x


## Getting Started

### Prerequisites

* Python 3.12+
* pip

### Installation (Local Development)

1. Clone the repo
   ```sh
   git clone https://github.com/villheik/Rankaisijabot.git
   ```
2. Install pip packages
   ```sh
   pip install -r requirements.txt
   ```
3. Set your bot token as an environment variable
   ```sh
   # Linux / macOS
   export BOT_TOKEN=your_token_here

   # Windows PowerShell
   $env:BOT_TOKEN = "your_token_here"
   ```
4. Run the bot
   ```sh
   python -m bot
   ```

### Docker Deployment (Raspberry Pi)

The bot is designed to run in Docker on a Raspberry Pi (arm64). Images are automatically built and pushed to GitHub Container Registry via GitHub Actions.

**CI/CD**
- Push to `dev` branch → runs tests → builds `ghcr.io/villheik/rankaisijabot:dev`
- Publish a GitHub Release → builds `ghcr.io/villheik/rankaisijabot:latest`

The `!releasechannel` command configures which channel receives release announcements. The bot posts the GitHub release notes automatically on startup when a new release is detected. Only publishing a GitHub Release triggers an announcement — dev deployments do not.

**Configuration**

Bot settings are in `config.yml`:
```yaml
bot:
    prefix: "!"
    token: !ENV "BOT_TOKEN"   # read from BOT_TOKEN environment variable

markov:
    rebuild_hour: 0           # UTC hour for nightly model rebuild (0 = 3am Finland time)
```

**First-time setup**

1. Install Docker
   ```sh
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker $USER
   ```
   Log out and back in for the group change to take effect.

2. Authenticate with GitHub Container Registry
   ```sh
   echo "YOUR_GITHUB_PAT" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
   ```
   The PAT needs `read:packages` scope.

3. Create persistent data directories for the Markov database
   ```sh
   mkdir -p /home/$USER/rankaisijabot-data
   mkdir -p /home/$USER/rankaisijabot-data-prod
   ```

4. Start the prod container
   ```sh
   docker run -d \
     --name rankaisija-prod \
     --restart unless-stopped \
     -e BOT_TOKEN=YOUR_PROD_TOKEN \
     -v /home/$USER/rankaisijabot-data-prod:/data \
     -v /etc/localtime:/etc/localtime:ro \
     ghcr.io/villheik/rankaisijabot:latest
   ```

5. (Optional) Start the dev container
   ```sh
   docker run -d \
     --name rankaisija-dev \
     --restart unless-stopped \
     -e BOT_TOKEN=YOUR_DEV_TOKEN \
     -v /home/$USER/rankaisijabot-data:/data \
     -v /etc/localtime:/etc/localtime:ro \
     ghcr.io/villheik/rankaisijabot:dev
   ```

6. Start Watchtower to automatically update containers when new images are pushed
   ```sh
   docker run -d \
     --name watchtower \
     --restart unless-stopped \
     -e DOCKER_API_VERSION=1.41 \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v /home/$USER/.docker/config.json:/config.json \
     containrrr/watchtower \
     --interval 300 \
     rankaisija-prod rankaisija-dev
   ```

**Useful commands**
```sh
# View bot logs
docker logs rankaisija-prod -f

# Check when Watchtower last updated containers
docker logs watchtower 2>&1 | grep -i "updated\|found new\|creating"
```

### Testing

```sh
pip install pytest
pytest tests/ -v
```


## Usage

Default chat command prefix is `!`

**Markov**

| Command | Description |
|---------|-------------|
| `!train` | Fetch full channel message history and rebuild Markov models (server owner only) |
| `!mimic <user>` | Generate a sentence in a user's writing style |
| `!mimiclong <user>` | Generate a longer sentence (minimum 6 words) |
| `!nickname <username> <nickname>` | Alias multiple usernames under one nickname |

**Random**

| Command | Description |
|---------|-------------|
| `!random` | Return a random message from the channel |
| `!random <term>` | Return a random message containing the search term (supports `*` wildcard) |
| `!random @user` | Return a random message where the user was mentioned (no ping sent) |

**Stock & Crypto**

| Command | Description |
|---------|-------------|
| `!btc [EUR\|USD]` | Bitcoin price (default: USD) |
| `!eth [EUR\|USD]` | Ethereum price (default: USD) |
| `!price <ticker or name>` | Stock price |

**Utility**

| Command | Description |
|---------|-------------|
| `!roll <NdN[+N]>` | Roll dice, e.g. `!roll 2d6+3` |
| `!coinflip` | Flip a coin |
| `!number [max]` | Random number between 1 and max (default: 100) |
| `!info` | Bot info |


## Contributing

New features are added as cogs in the `bot/cogs/` folder. See [`.ai/GUIDELINES.md`](.ai/GUIDELINES.md) for conventions.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Add tests in `tests/`
4. Commit your changes
5. Open a Pull Request


## License

Distributed under the MIT License. See `LICENSE` for more information.


## Acknowledgements

* [Rankaisijat](https://www.youtube.com/watch?v=Ix4GAHcOUwI)
