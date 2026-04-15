import sys, os, asyncio, json
sys.path.insert(0, '.')
os.environ.setdefault('DISCORD_TOKEN', '')

from database import get_session
from models import TaskConfig, MessageGroup, Settings
import pytz, datetime, random

TIMEZONE = pytz.timezone('America/Sao_Paulo')

# ── 1. Verificar banco ────────────────────────────────────────────────────
print("=== 1. BANCO ===")
with get_session() as s:
    tasks = s.query(TaskConfig).filter_by(active=True).all()
    print(f"Tasks ativas: {len(tasks)}")
    for t in tasks:
        print(f"  id={t.id} nome={t.name} type={t.type} test_mode={t.test_mode}")
        print(f"  channel_ids={t.channel_ids}")
        cfg = json.loads(t.schedule_config or '{}')
        print(f"  schedule_config={cfg}")
        if t.message_group_id:
            g = s.query(MessageGroup).filter_by(id=t.message_group_id).first()
            msgs = [m.content for m in g.messages if m.active] if g else []
            print(f"  grupo={g.name if g else 'NAO ENCONTRADO'} msgs={msgs}")

# ── 2. Teste de conexão Discord ───────────────────────────────────────────
print()
print("=== 2. TESTE DISCORD ===")

from config import TOKEN
print(f"Token definido: {'SIM ('+TOKEN[:8]+'...)' if TOKEN and TOKEN != 'SEU_TOKEN_AQUI' else 'NAO OU INVALIDO'}")

import discord

async def test_send():
    intents = discord.Intents.default()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Bot conectado: {client.user}")
        print(f"Guilds: {[g.name for g in client.guilds]}")

        with get_session() as s:
            tasks = s.query(TaskConfig).filter_by(active=True).all()
            for t in tasks:
                ids = [int(x.strip()) for x in t.channel_ids.split(',') if x.strip()]
                for cid in ids:
                    ch = client.get_channel(cid)
                    print(f"Canal {cid}: {'ENCONTRADO — '+str(ch) if ch else 'NAO ENCONTRADO'}")
                    if ch:
                        try:
                            await ch.send("🧪 Mensagem de teste de diagnóstico — Bot Avisos")
                            print(f"  >> MENSAGEM ENVIADA COM SUCESSO para #{ch.name}")
                        except Exception as e:
                            print(f"  >> ERRO AO ENVIAR: {e}")
                    else:
                        print(f"  >> Bot nao tem acesso ao canal {cid}")
                        print(f"     Canais disponíveis:")
                        for guild in client.guilds:
                            for channel in guild.channels:
                                if hasattr(channel, 'send'):
                                    print(f"       #{channel.name} id={channel.id}")

        await client.close()

    try:
        await client.start(TOKEN)
    except discord.LoginFailure:
        print("ERRO: Token inválido!")
    except Exception as e:
        print(f"ERRO: {e}")

asyncio.run(test_send())