

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
    <a href="https://github.com/villheik/Rankaisijabot"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/villheik/Rankaisijabot/issues">Report Bug</a>
    ·
    <a href="https://github.com/villheik/Rankaisijabot/issues">Request Feature</a>
  </p>
</p>



<!-- TABLE OF CONTENTS -->
<details open="open">
  <summary><h2 style="display: inline-block">Table of Contents</h2></summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgements">Acknowledgements</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

Rankaisijabot is a good bot


### Built With

* Python



<!-- GETTING STARTED -->
## Getting Started

To get a local copy up and running follow these simple steps.

### Prerequisites

This is an example of how to list things you need to use the software and how to install them.
* python 3
* pip

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/villheik/Rankaisijabot.git
   ```
2. Install pip packages
   ```sh
   pip install -r requirements.txt
   ```
3. Set your bot token to env variable BOT_TOKEN
    ```
      $env:BOT_TOKEN = ' bot token '
      or
      export BOT_TOKEN = bot_token
    ```
4. Run bot
    ```
    python -m bot
    ```

### Docker Deployment (Raspberry Pi)

The bot is designed to run in Docker on a Raspberry Pi (arm64). Images are automatically built and pushed to GitHub Container Registry via GitHub Actions.

**CI/CD**
- Push to `dev` branch → builds `ghcr.io/villheik/rankaisijabot:dev`
- Publish a GitHub Release → builds `ghcr.io/villheik/rankaisijabot:latest`

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
   These must be created manually. Without them the Markov cog will fail to start.

4. Start the prod container
   ```sh
   docker run -d \
     --name rankaisija-prod \
     --restart unless-stopped \
     -e BOT_TOKEN=YOUR_PROD_TOKEN \
     -v /home/$USER/rankaisijabot-data-prod:/data \
     ghcr.io/villheik/rankaisijabot:latest
   ```

5. (Optional) Start the dev container
   ```sh
   docker run -d \
     --name rankaisija-dev \
     --restart unless-stopped \
     -e BOT_TOKEN=YOUR_DEV_TOKEN \
     -v /home/$USER/rankaisijabot-data:/data \
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

# Force Watchtower to check for updates immediately
docker exec watchtower /watchtower --run-once
```

<!-- USAGE EXAMPLES -->
## Usage
Default chat command prefix is `!`

| Command | Description |
|---------|-------------|
| `!btc [EUR\|USD]` | Bitcoin price |
| `!eth [EUR\|USD]` | Ethereum price |
| `!price <ticker or name>` | Stock price |
| `!roll <NdN>` | Roll dice |
| `!train` | Collect channel message history for Markov (server owner only) |
| `!mimic <username or nickname>` | Generate text in a user's style |
| `!nickname <username> <nickname>` | Alias multiple usernames under one nickname (admin only) |


<!-- ROADMAP -->
## Roadmap

See the [open issues](https://github.com/villheik/Rankaisijabot/issues) for a list of proposed features (and known issues).



<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to be learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

New features are added in the `cogs` folder. The cogs that are loaded for the bot to use are configured in `config.yml`


<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE` for more information.



<!-- CONTACT -->
## Contact



Project Link: [https://github.com/villheik/Rankaisijabot](https://github.com/villheik/Rankaisijabot)



<!-- ACKNOWLEDGEMENTS -->
## Acknowledgements

* [Rankaisijat](https://www.youtube.com/watch?v=Ix4GAHcOUwI)
* []()
* []()





<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/villheik/repo.svg?style=for-the-badge
[contributors-url]: https://github.com/villheik/repo/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/villheik/repo.svg?style=for-the-badge
[forks-url]: https://github.com/villheik/repo/network/members
[stars-shield]: https://img.shields.io/github/stars/villheik/repo.svg?style=for-the-badge
[stars-url]: https://github.com/villheik/repo/stargazers
[issues-shield]: https://img.shields.io/github/issues/villheik/repo.svg?style=for-the-badge
[issues-url]: https://github.com/villheik/repo/issues
[license-shield]: https://img.shields.io/github/license/villheik/repo.svg?style=for-the-badge
[license-url]: https://github.com/villheik/repo/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/villheik
