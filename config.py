# config.py
import os
import secrets
import pytz
from dotenv import load_dotenv

load_dotenv()

DEBUG    = os.getenv("DEBUG", "false").lower() == "true"
TIMEZONE = pytz.timezone("America/Sao_Paulo")

# ── Discord token ────────────────────────────────────────────────────────────
TOKEN = os.getenv("DISCORD_TOKEN", "").strip()

def _validate_token(token: str) -> str:
    """
    Valida o token do Discord antes de tentar conectar.
    Tokens do Discord têm formato: XXXXXXXX.XXXXXX.XXXXXXXXXXXXXXXXXXXXXXXXXXX
    (3 partes separadas por ponto, Base64)
    """
    if not token:
        raise ValueError(
            "\n[ERRO] DISCORD_TOKEN não definido no arquivo .env\n"
            "  1. Copie .env.example para .env\n"
            "  2. Preencha DISCORD_TOKEN com o token do seu bot\n"
            "  3. O token está em: discord.com/developers/applications → Bot → Token\n"
        )
    token = token.strip()
    # tokens do Discord têm 3 partes separadas por ponto
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError(
            f"\n[ERRO] DISCORD_TOKEN parece inválido (formato incorreto)\n"
            f"  Token recebido tem {len(parts)} parte(s), deveria ter 3\n"
            f"  Verifique se não há espaços ou quebras de linha no .env\n"
            f"  Token (primeiros 8 chars): {token[:8]}...\n"
        )
    if len(token) < 50:
        raise ValueError(
            f"\n[ERRO] DISCORD_TOKEN muito curto ({len(token)} chars, mínimo ~70)\n"
            f"  Verifique se o token está completo no .env\n"
        )
    return token

TOKEN = _validate_token(TOKEN)

# ── Dashboard ─────────────────────────────────────────────────────────────────
DASHBOARD_SECRET_KEY        = os.getenv("DASHBOARD_SECRET_KEY", "").strip()
DASHBOARD_PORT              = int(os.getenv("DASHBOARD_PORT", 5000))
DASHBOARD_HOST              = os.getenv("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_USERNAME          = os.getenv("DASHBOARD_USERNAME", "admin").strip()
DASHBOARD_PASSWORD          = os.getenv("DASHBOARD_PASSWORD", "").strip()
# Use um hash seguro em vez de senha em texto puro.
# Gere com: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha'))"
DASHBOARD_PASSWORD_HASH     = os.getenv("DASHBOARD_PASSWORD_HASH", "").strip()
DASHBOARD_COOKIE_SECURE     = os.getenv("DASHBOARD_COOKIE_SECURE", "").lower() == "true" if not DEBUG else False
DASHBOARD_SESSION_PERMANENT = os.getenv("DASHBOARD_SESSION_PERMANENT", "true").lower() == "true"
DASHBOARD_SESSION_LIFETIME  = int(os.getenv("DASHBOARD_SESSION_LIFETIME_MINUTES", 60))

if not DASHBOARD_SECRET_KEY:
    if DEBUG:
        DASHBOARD_SECRET_KEY = secrets.token_urlsafe(32)
        print("\n[AVISO] DASHBOARD_SECRET_KEY não definido; usando valor temporário em DEBUG.\n")
    else:
        raise ValueError(
            "DASHBOARD_SECRET_KEY obrigatório em produção. "
            "Defina no .env para proteger sessões do dashboard."
        )

if not (DASHBOARD_PASSWORD or DASHBOARD_PASSWORD_HASH):
    if DEBUG:
        DASHBOARD_PASSWORD = secrets.token_urlsafe(12)
        print(f"\n[AVISO] DASHBOARD_PASSWORD não definido no .env")
        print(f"  Usando senha temporária para esta sessão: {DASHBOARD_PASSWORD}")
        print("  Adicione ao .env: DASHBOARD_PASSWORD=<senha> ou DASHBOARD_PASSWORD_HASH=<hash>\n")
    else:
        raise ValueError(
            "DASHBOARD_PASSWORD ou DASHBOARD_PASSWORD_HASH obrigatório em produção. "
            "Defina no .env e use um hash seguro quando possível."
        )

# ── Google Sheets (opcional) ──────────────────────────────────────────────────
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "credentials/credentials.json")
GOOGLE_SHEETS_SPREADSHEET = os.getenv("GOOGLE_SHEETS_SPREADSHEET", "")
GOOGLE_SHEETS_WORKSHEET   = os.getenv("GOOGLE_SHEETS_WORKSHEET", "")
