# Disk Monitor

Script em Python para monitoramento de espaço em disco com envio de alertas por e-mail.

## 📌 Funcionalidade
O `disk_monitor.py` verifica periodicamente o uso do disco de um ou mais diretórios e envia um e-mail de alerta quando o uso ultrapassa um limite configurado.

O objetivo é facilitar o acompanhamento de servidores ou máquinas locais, evitando indisponibilidade por falta de espaço.

---


## 📂 Estrutura de Arquivos

/opt/monitor/
├── disk_monitor.py # Script principal
├── config.json # Arquivo de configuração
├── logs/
│ └── disk_monitor.log # Registro de execuções
└── requirements.txt # Dependências do projeto


- **disk_monitor.py** — Contém toda a lógica de monitoramento e envio de e-mails.
- **config.json** — Configurações de limite de uso, caminhos monitorados e credenciais de e-mail.
- **logs/disk_monitor.log** — Histórico das execuções e alertas emitidos.
- **requirements.txt** — Lista de pacotes necessários para rodar o script.

---

## ⚙️ Exemplo de `config.json`
```json
{
    "paths": ["/", "/home"],
    "limit_percent": 80,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "email_sender": "alerta@seudominio.com",
    "email_password": "sua_senha",
    "email_recipients": ["admin@seudominio.com"]
}

EXECUÇÃO:
pip install -r requirements.txt
apt install python3-psutil
python3 disk_monitor.py --config config.json
