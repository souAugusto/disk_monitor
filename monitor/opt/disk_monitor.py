"""
disk_monitor.py
Monitora uso de disco e envia alerta por e-mail quando o uso (%)
ultrapassa o limite configurado.

Requisitos: psutil
    pip install psutil

Uso:
    python3 disk_monitor.py --config config.json
"""

import argparse
import json
import shutil
import smtplib
import socket
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

try:
    import psutil
except Exception:
    psutil = None

DEFAULT_CONFIG = {
    "paths": ["/"],            # caminhos a checar (ex: "/", "/home", "C:\\")
    "threshold_percent": 85,   # disparar alerta quando uso >= (em porcentagem)
    "check_interval_minutes": 10,  # (opcional) se rodar em loop - não usado em cron mode
    "smtp": {
        "host": "smtp.example.com",
        "port": 587,
        "use_tls": True,
        "username": "monitor@example.com",
        "password": "SUA_SENHA_AQUI"
    },
    "mail": {
        "from": "monitor@example.com",
        "to": ["admin@example.com"],
        "subject_prefix": "[ALERTA DISCO]"
    },
    "hostname": None,  # opcional, para identificação do servidor; se None, usa socket.gethostname()
    "dry_run": False   # se True, não envia e-mail, apenas imprime
}


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config não encontrada: {path}")
    cfg = json.loads(path.read_text(encoding="utf-8"))
    # merge com DEFAULT_CONFIG simples (somente chaves de primeiro nível)
    final = DEFAULT_CONFIG.copy()
    final.update(cfg)
    # merge nested smtp/mail se existirem
    final["smtp"] = {**DEFAULT_CONFIG["smtp"], **cfg.get("smtp", {})}
    final["mail"] = {**DEFAULT_CONFIG["mail"], **cfg.get("mail", {})}
    return final


def get_disk_usage(path: str) -> dict:
    """
    Retorna dicionário: total, used, free (bytes) e percent (0-100)
    Usa psutil se disponível, senão shutil.disk_usage.
    """
    if psutil:
        try:
            du = psutil.disk_usage(path)
            return {"total": du.total, "used": du.used, "free": du.free, "percent": du.percent}
        except Exception:
            pass
    # fallback
    du = shutil.disk_usage(path)
    percent = (du.used / du.total) * 100 if du.total else 0
    return {"total": du.total, "used": du.used, "free": du.free, "percent": round(percent, 2)}


def bytes_to_human(n: int) -> str:
    # formata bytes para string legível
    for unit in ["B", "KB", "MB", "GB", "TB", "PB"]:
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


def compose_message(hostname: str, alerts: list, cfg: dict) -> EmailMessage:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"{cfg['mail']['subject_prefix']} {hostname} - {len(alerts)} alerta(s)"
    body_lines = [
        f"Relatório de uso de disco - {hostname}",
        f"Gerado em: {now}",
        "",
        "Partições com alerta (uso acima do limite):",
        ""
    ]
    for a in alerts:
        body_lines += [
            f"Caminho: {a['path']}",
            f"Uso: {a['percent']}%",
            f"Total: {bytes_to_human(a['total'])} | Usado: {bytes_to_human(a['used'])} | Livre: {bytes_to_human(a['free'])}",
            "-"*40
        ]
    body = "\n".join(body_lines)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["mail"]["from"]
    msg["To"] = ", ".join(cfg["mail"]["to"])
    msg.set_content(body)
    return msg


def send_email(msg: EmailMessage, smtp_cfg: dict):
    host = smtp_cfg["host"]
    port = int(smtp_cfg.get("port", 587))
    username = smtp_cfg.get("username")
    password = smtp_cfg.get("password")
    use_tls = smtp_cfg.get("use_tls", True)

    if use_tls:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if username:
                server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if username:
                server.login(username, password)
            server.send_message(msg)


def main():
    parser = argparse.ArgumentParser(description="Disk usage monitor with email alerts")
    parser.add_argument("--config", "-c", type=str, default="config.json", help="Caminho para config.json")
    parser.add_argument("--dry-run", action="store_true", help="Não envia e-mails, apenas mostra o que faria")
    args = parser.parse_args()

    cfg_path = Path(args.config)
    try:
        cfg = load_config(cfg_path)
    except Exception as e:
        print(f"Erro ao carregar config: {e}", file=sys.stderr)
        sys.exit(2)

    if args.dry_run:
        cfg["dry_run"] = True

    hostname = cfg.get("hostname") or socket.gethostname()
    threshold = float(cfg.get("threshold_percent", 85.0))
    paths = cfg.get("paths", ["/"])

    alerts = []
    for p in paths:
        try:
            du = get_disk_usage(p)
        except Exception as e:
            print(f"Erro ao checar {p}: {e}", file=sys.stderr)
            continue
        percent = float(du["percent"])
        if percent >= threshold:
            alerts.append({"path": p, **du})

    if not alerts:
        print(f"[{datetime.now().isoformat()}] Nenhum alerta. Uso dentro do limite ({threshold}%).")
        return 0

    msg = compose_message(hostname, alerts, cfg)
    print(f"[{datetime.now().isoformat()}] {len(alerts)} alerta(s) - preparando envio para: {cfg['mail']['to']}")

    if cfg.get("dry_run"):
        print("=== DRY RUN: conteúdo do e-mail ===")
        print(msg)
        return 0

    try:
        send_email(msg, cfg["smtp"])
        print("E-mail enviado com sucesso.")
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}", file=sys.stderr)
        return 3

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)