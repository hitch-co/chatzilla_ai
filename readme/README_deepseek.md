# DeepSeek Local Setup Notes (Updated)

This document consolidates everything we’ve done to self-host DeepSeek using Ollama and a Docker-based Open WebUI setup on Windows 11 (with WSL). By following these steps, you’ll be able to:

1. Run the **Ollama** service with DeepSeek models in WSL.  
2. Host a **Docker container** for Open WebUI (with host networking).  
3. Access your local model from another machine on the same LAN.

---

## Table of Contents
1. [WSL & Ollama Setup](#1-wsl--ollama-setup)  
2. [Enabling Automatic Startup (Optional)](#2-enabling-automatic-startup-optional)  
3. [Running Docker-Based Open WebUI](#3-running-docker-based-open-webui)  
4. [Manually Controlling Open WebUI](#4-manually-controlling-open-webui)  
5. [Firewall Management](#5-firewall-management)  
6. [Port Forwarding (Obsolete with Docker Host Networking)](#6-port-forwarding-obsolete-with-docker-host-networking)  
7. [DeepSeek API (Optional)](#7-deepseek-api-optional)  
8. [References](#8-references)

----------

## 1. WSL & Ollama Setup

# 1. **Launch your WSL Ubuntu distribution** (Ubuntu 22.04 or similar).

# 2. **Install Ollama** (if not already):
   `curl -fsSL https://ollama.com/install.sh | sh`

## Enabling Automatic Startup (Optional)
If you want Ollama to run automatically at WSL startup:

`sudo systemctl enable ollama.service`
`sudo systemctl start ollama.service`

Note: This requires systemd to be enabled in WSL. Otherwise, you can just start Ollama manually when needed.

## Running Docker-Based Open WebUI
We use a Docker container (with host networking) so that Open WebUI can talk directly to Ollama.

# 3.1 Install & Start Docker in WSL

`sudo apt update`
`sudo apt install docker.io -y`
`sudo systemctl enable docker`
`sudo systemctl start docker`

(If systemd isn’t enabled, you might need to start dockerd manually.)

# #3.2 Pull & Run Open WebUI

`docker run -d --name open-webui --network host -e OLLAMA_API_BASE_URL=http://localhost:11434 ghcr.io/open-webui/open-webui:latest`

--network host shares WSL’s network namespace directly, so Open WebUI can reach Ollama on localhost:11434.
OLLAMA_API_BASE_URL is set to http://localhost:11434 to point to Ollama’s API port.

## 3.3 Verifying Access

Local Access (same PC)

`curl http://localhost:8080`

or open your browser to http://localhost:8080.

LAN Access (another device)

http://<YOUR-WINDOWS-LAN-IP>:8080

e.g., http://10.0.0.14:8080

## Manually Controlling Open WebUI
Start: `docker start open-webui`

Stop: `docker stop open-webui`

Remove (to clean up entirely): `docker rm open-webui`

If you want it always running, enable Docker container auto-restart: `docker update --restart=always open-webui`

## Firewall Management
# 5.1 Windows Firewall

To allow inbound connections on your chosen port (e.g., 8080):

Open Windows Defender Firewall with Advanced Security.
Inbound Rules → New Rule:
Type: Port
TCP → 8080
Allow
Profile: Private
Name: “Open WebUI 8080”

Finish and verify inbound traffic is allowed.

# 5.2 Quick On/Off from PowerShell

`netsh advfirewall set allprofiles state off`
`netsh advfirewall set allprofiles state on`

Use with caution—disabling all firewall profiles is only recommended for quick troubleshooting.

Port Forwarding (Obsolete with Docker Host Networking)
We previously used a manual portproxy approach in WSL:

`netsh interface portproxy add v4tov4 listenaddress=10.0.0.14 listenport=8080 connectaddress=172.17.x.x connectport=8080`

Now that we run Open WebUI with --network host, this is no longer needed. Docker + host networking bypasses the NAT issue by sharing the WSL namespace directly.

If you still have old rules, remove them:

`netsh interface portproxy delete v4tov4 listenaddress=10.0.0.14 listenport=8080`

DeepSeek API (Optional)
DeepSeek sometimes references a deepseek --api command. However, with Ollama-based models, you typically just run:

ollama serve for a built-in HTTP endpoint
Open WebUI for a front-end + limited API

If you want an official separate “DeepSeek API,” you’d follow a different Docker approach. But for most local usage, Ollama + Open WebUI is enough.

References
Ollama Docs for local model usage
Open WebUI GitHub for Docker instructions
Windows Firewall Docs for custom inbound rules

Conclusion

WSL runs Ollama to provide the DeepSeek models.
Docker with --network host runs Open WebUI, letting it talk directly to Ollama on localhost:11434.
No more manual port-forwarding or netsh trickery is needed.
Firewall rules just need to allow inbound traffic on port 8080 for LAN access.

With this setup, you can easily chat or integrate DeepSeek from any device on your LAN.