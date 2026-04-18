# cogs/tasks_cog.py
import json, random, datetime, asyncio
from discord.ext import tasks, commands
from config import TIMEZONE
from database import get_session
from models import Settings, TaskConfig, MessageGroup, TaskExecutionLog
from logger_setup import make_logger, purge_old_logs

_bot_ref = None
_channels_cache: list[dict] = []
ALERT_CHANNEL_ID = None  # definido via .env opcionalmente


def get_bot_channels() -> list[dict]:
    return _channels_cache


def _refresh_channels(bot):
    global _channels_cache
    result = []
    for guild in bot.guilds:
        for ch in guild.channels:
            if hasattr(ch, 'send'):
                result.append({
                    "id": str(ch.id),
                    "name": ch.name,
                    "guild": guild.name,
                    "type": str(ch.type).replace("ChannelType.", ""),
                })
    result.sort(key=lambda x: (x["guild"], x["name"]))
    _channels_cache = result


def now_tz() -> datetime.datetime:
    """Sempre retorna datetime com fuso de São Paulo."""
    return datetime.datetime.now(TIMEZONE)


def now_utc() -> datetime.datetime:
    """UTC para gravação no banco."""
    return datetime.datetime.now(datetime.timezone.utc)


def _get(key, default=None):
    with get_session() as s:
        r = s.query(Settings).filter_by(key=key).first()
        return r.value if r else default


def _set(key, value):
    with get_session() as s:
        r = s.query(Settings).filter_by(key=key).first()
        if r:
            r.value = str(value)
        else:
            s.add(Settings(key=key, value=str(value)))


def _purge_old_settings(days=90):
    """Remove chaves de controle de envio mais antigas que N dias."""
    cutoff = (now_tz() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    removed = 0
    with get_session() as s:
        rows = s.query(Settings).filter(Settings.key.like("task_%_sent_%")).all()
        for r in rows:
            # chave formato: task_1_sent_20240601_0900
            parts = r.key.split("_sent_")
            if len(parts) == 2:
                date_part = parts[1][:8]  # YYYYMMDD
                if date_part < cutoff:
                    s.delete(r)
                    removed += 1
    return removed


def _active_tasks_as_dicts():
    """Serializa tasks para dicts dentro da sessão — evita DetachedInstanceError."""
    with get_session() as s:
        rows = s.query(TaskConfig).filter_by(active=True).all()
        result = []
        for t in rows:
            msgs = []
            if t.message_group_id:
                g = s.query(MessageGroup).filter_by(id=t.message_group_id).first()
                if g:
                    msgs = [{
                        "content": m.content,
                        "is_embed": getattr(m, "is_embed", False),
                        "embed_color": getattr(m, "embed_color", ""),
                        "media_url": getattr(m, "media_url", "")
                    } for m in g.messages if m.active]
            try:
                schedule_config = json.loads(t.schedule_config or "{}")
            except (ValueError, TypeError):
                schedule_config = {}
            result.append({
                "id":              t.id,
                "name":            t.name,
                "type":            t.type,
                "test_mode":       bool(t.test_mode),
                "active":          bool(t.active),
                "channel_ids":     t.channel_ids or "",
                "roles_to_mention":getattr(t, "roles_to_mention", ""),
                "schedule_config": schedule_config,
                "messages":        msgs,
            })
        return result


def _get_channel_ids(task_dict):
    result = []
    for value in str(task_dict.get("channel_ids", "")).split(","):
        raw = value.strip()
        if not raw:
            continue
        try:
            result.append(int(raw))
        except ValueError:
            continue
    return result


class TasksCog(commands.Cog):
    def __init__(self, bot, geral_logger):
        global _bot_ref
        _bot_ref = bot
        self.bot = bot
        self.logger = geral_logger
        self.tlog = make_logger("discord_bot.tasks", "tasks.log")
        self._sched_times: dict[int, str] = {}
        self._test_last: dict[int, datetime.datetime] = {}
        self.dispatcher.start()
        self.daily_maintenance.start()

    def cog_unload(self):
        self.dispatcher.cancel()
        self.daily_maintenance.cancel()

    # ── Eventos ───────────────────────────────────────────────────────────────
    @commands.Cog.listener()
    async def on_ready(self):
        _refresh_channels(self.bot)
        self.logger.info(f"Bot online | {self.bot.user} | {len(self.bot.guilds)} servidor(es) | {len(_channels_cache)} canais")
        print(f"[BOT] {self.bot.user} online — {len(_channels_cache)} canais carregados")

    @commands.Cog.listener()
    async def on_disconnect(self):
        self.logger.warning("Bot desconectado do Discord.")
        print("[BOT] AVISO: desconectado do Discord — tentando reconectar...")

    @commands.Cog.listener()
    async def on_resumed(self):
        _refresh_channels(self.bot)
        self.logger.info("Bot reconectado e sessão retomada.")
        print("[BOT] Reconectado com sucesso.")
        # Tentar enviar alerta num canal de monitoramento se configurado
        await self._send_alert("⚠️ Bot reconectado ao Discord após desconexão.")

    # ── Dispatcher ────────────────────────────────────────────────────────────
    @tasks.loop(minutes=1)
    async def dispatcher(self):
        now = now_tz()
        try:
            tlist = _active_tasks_as_dicts()
        except Exception as e:
            self.tlog.exception(f"Erro ao carregar tasks: {e}")
            return

        for task in tlist:
            try:
                cfg = task["schedule_config"]
                if task["test_mode"]:
                    await self._handle_test(task, cfg, now)
                    continue
                handler = {
                    "fixed_times":   self._handle_fixed_times,
                    "interval_days": self._handle_interval_days,
                    "weekly":        self._handle_weekly,
                    "monthly":       self._handle_monthly,
                    "test":          self._handle_test,
                }.get(task["type"])
                if handler:
                    await handler(task, cfg, now)
            except Exception as e:
                self.tlog.exception(f"Erro dispatcher task_id={task.get('id')} nome={task.get('name')}: {e}")

    @dispatcher.before_loop
    async def before_dispatcher(self):
        await self.bot.wait_until_ready()
        _refresh_channels(self.bot)
        self.tlog.info("Dispatcher iniciado.")
        print("[BOT] Dispatcher iniciado.")

    @dispatcher.error
    async def dispatcher_error(self, exc):
        self.tlog.critical(f"DISPATCHER ENGINE MORTO / CONGELADO: {exc}")
        self.tlog.warning("Auto-Cura acionada. Reiniciando engine do Dispatcher em 15 segundos...")
        await asyncio.sleep(15)
        self.dispatcher.restart()

    # ── Manutenção diária ─────────────────────────────────────────────────────
    @tasks.loop(hours=24)
    async def daily_maintenance(self):
        logs_removed = purge_old_logs()
        settings_removed = _purge_old_settings(days=90)
        db_logs_removed = 0
        try:
            with get_session() as s:
                cutoff = now_utc() - datetime.timedelta(days=30)
                db_logs_removed = s.query(TaskExecutionLog).filter(TaskExecutionLog.created_at < cutoff).delete()
        except Exception as e:
            self.tlog.error(f"Erro ao limpar TaskExecutionLog: {e}")

        self._sched_times.clear()
        _refresh_channels(self.bot)
        self.tlog.info(
            f"Manutenção: {logs_removed} log(s) de arquivo removido(s), "
            f"{settings_removed} settings antigo(s), {db_logs_removed} db logs removidos, canais atualizados."
        )

    @daily_maintenance.before_loop
    async def before_daily_maintenance(self):
        await self.bot.wait_until_ready()

    # ── Handlers ─────────────────────────────────────────────────────────────
    async def _handle_test(self, task, cfg, now):
        every = int(cfg.get("every_minutes", 2))
        last  = self._test_last.get(task["id"])
        if last and (now - last).total_seconds() < every * 60:
            return
        msg = self._pick(task) or {"content": f"[TESTE] Task '{task['name']}' — {now.strftime('%H:%M:%S')}"}
        await self._send(task, msg, True)
        self._test_last[task["id"]] = now
        self.tlog.info(f"[TEST] task_id={task['id']} nome={task['name']} enviada.")

    async def _handle_fixed_times(self, task, cfg, now):
        times         = cfg.get("times", [])
        days_of_month = cfg.get("days_of_month", [])
        days_of_week  = cfg.get("days_of_week", [])
        months        = cfg.get("months", [])

        if months        and now.month    not in months:        return
        if days_of_month and now.day      not in days_of_month: return
        if days_of_week  and now.weekday() not in days_of_week: return

        cur = now.strftime("%H:%M")
        
        for target_time in times:
            if cur >= target_time:
                key = f"task_{task['id']}_sent_{now.strftime('%Y%m%d')}_{target_time.replace(':','')}"
                if not _get(key):
                    msg = self._pick(task)
                    if msg:
                        await self._send(task, msg)
                    _set(key, "1")
                    self.tlog.info(f"[fixed_times] task_id={task['id']} delay_safe=true target_time={target_time} disp_at={cur}")
                    break # Se tiver mais atrasados, manda no próximo tick para não floodar

    async def _handle_interval_days(self, task, cfg, now):
        every      = int(cfg.get("every_days", 10))
        start_from = cfg.get("start_from")
        hour_start = int(cfg.get("hour_start", 9))
        hour_end   = int(cfg.get("hour_end", 18))
        random_t   = cfg.get("random_time", True)
        today      = now.date()
        today_str  = today.strftime("%Y-%m-%d")

        if start_from:
            try:
                ref = datetime.datetime.strptime(start_from, "%Y-%m-%d").date()
            except ValueError:
                ref = today
        else:
            ref_str = _get(f"task_{task['id']}_interval_ref")
            ref     = datetime.datetime.strptime(ref_str, "%Y-%m-%d").date() if ref_str else today
            if not ref_str:
                _set(f"task_{task['id']}_interval_ref", today_str)

        days_since = (today - ref).days
        if days_since < 0 or days_since % every != 0: return

        sent_key = f"task_{task['id']}_sent_{today_str.replace('-','')}"
        if _get(sent_key): return

        sched_key = f"task_{task['id']}_sched_{today_str.replace('-','')}"
        sched     = self._sched_times.get(task["id"]) or _get(sched_key)
        if not sched:
            h     = random.randint(hour_start, max(hour_start, hour_end - 1)) if random_t else hour_start
            m     = random.randint(0, 59) if random_t else 0
            sched = f"{h:02d}:{m:02d}"
            self._sched_times[task["id"]] = sched
            _set(sched_key, sched)

        cur = now.strftime("%H:%M")
        if cur < sched: return

        msg = self._pick(task)
        if not msg: return
        await self._send(task, msg)
        _set(sent_key, "1")
        self._sched_times.pop(task["id"], None)
        self.tlog.info(f"[interval_days] task_id={task['id']} data={today_str} target_time={sched} disp_at={cur}")

    async def _handle_weekly(self, task, cfg, now):
        days_of_week = cfg.get("days_of_week", [0,1,2,3,4])
        hour_start   = int(cfg.get("hour_start", 9))
        hour_end     = int(cfg.get("hour_end", 18))

        if now.weekday() not in days_of_week:       return
        if not (hour_start <= now.hour < hour_end): return

        cur_week = str(now.isocalendar()[1])
        if _get(f"task_{task['id']}_last_week") == cur_week: return

        msg = self._pick(task)
        if not msg: return
        await self._send(task, msg)
        _set(f"task_{task['id']}_last_week", cur_week)
        self.tlog.info(f"[weekly] task_id={task['id']} semana={cur_week}")

    async def _handle_monthly(self, task, cfg, now):
        hour_start = int(cfg.get("hour_start", 9))
        hour_end   = int(cfg.get("hour_end", 18))
        months     = cfg.get("months", [])

        if months and now.month not in months:      return
        if not (hour_start <= now.hour < hour_end): return

        cur = f"{now.year}-{now.month}"
        if _get(f"task_{task['id']}_last_month") == cur: return

        msg = self._pick(task)
        if not msg: return
        await self._send(task, msg)
        _set(f"task_{task['id']}_last_month", cur)
        self.tlog.info(f"[monthly] task_id={task['id']} mês={cur}")

    # ── Envio ─────────────────────────────────────────────────────────────────
    def _format_message_text(self, text: str, now, ch) -> str:
        dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
        t = text
        t = t.replace("{hoje}", now.strftime('%d/%m/%Y'))
        t = t.replace("{hora}", now.strftime('%H:%M'))
        t = t.replace("{dia_semana}", dias_semana[now.weekday()])
        if ch:
            t = t.replace("{canal}", f"<#{ch.id}>")
        return t

    def _get_roles_prefix(self, task) -> str:
        roles_str = task.get("roles_to_mention", "")
        if not roles_str:
            return ""
        mentions = []
        for r in roles_str.split(","):
            r = r.strip()
            if r:
                mentions.append(f"<@&{r}>")
        return " ".join(mentions) + "\n" if mentions else ""

    async def _send(self, task, message_dict, is_test=False):
        import discord
        now = now_tz()
        roles_prefix = self._get_roles_prefix(task)

        for cid in _get_channel_ids(task):
            ch = self.bot.get_channel(cid)
            status = "ERROR"
            error_msg = ""
            if ch:
                try:
                    raw_content = message_dict.get("content", "")
                    content = self._format_message_text(raw_content, now, ch)
                    if is_test:
                        content = f"🧪 **[MODO TESTE]**\n{content}"

                    full_content = roles_prefix + content
                    if len(full_content) > 2000:
                        full_content = full_content[:1997] + "..."

                    kwargs = {"content": full_content}

                    if message_dict.get("is_embed"):
                        color_hex = message_dict.get("embed_color", "")
                        color_val = discord.Color.default()
                        if color_hex and color_hex.startswith("#"):
                            try:
                                color_val = discord.Color(int(color_hex[1:], 16))
                            except ValueError:
                                pass
                        
                        # Movemos o content principal para a description do Embed (opcional)
                        # ou mantemos o content normal e enviamos um Embed com a imagem.
                        emb = discord.Embed(description=content, color=color_val)
                        if is_test:
                            emb.title = "🧪 [MODO TESTE]"
                        
                        media_url = message_dict.get("media_url", "")
                        if media_url:
                            emb.set_image(url=media_url)
                        
                        # enviamos mentions + content vazio no message body se o texto estiver no embed
                        # ou mentions sozinhos, para pifar a notificacao
                        kwargs["content"] = roles_prefix
                        kwargs["embed"] = emb

                    await ch.send(**kwargs)
                    status = "SUCCESS"
                    self.tlog.info(f"task_id={task['id']} canal={cid} enviado OK")
                    print(f"[BOT] task={task['name']} → #{ch.name} → SUCCESS")
                except Exception as e:
                    status = "ERROR"
                    error_msg = str(e)
                    self.tlog.exception(f"task_id={task['id']} canal={cid} erro: {e}")
            else:
                status = "ERROR"
                error_msg = "Canal não encontrado"
                self.tlog.error(f"task_id={task['id']} canal={cid} não encontrado")

            # Salvar execution log (ignorar tests)
            if not is_test:
                try:
                    with get_session() as s:
                        log = TaskExecutionLog(
                            task_id=task["id"],
                            task_name=task["name"],
                            channel_id=str(cid),
                            status=status,
                            error_msg=error_msg,
                            created_at=now_utc()
                        )
                        s.add(log)
                except Exception as db_e:
                    self.tlog.error(f"Erro ao salvar TaskExecutionLog: {db_e}")

    async def _send_alert(self, message: str):
        """Envia alerta num canal de monitoramento se ALERT_CHANNEL_ID estiver definido."""
        import os
        cid_str = os.getenv("ALERT_CHANNEL_ID", "")
        if not cid_str: return
        try:
            cid = int(cid_str)
            ch  = self.bot.get_channel(cid)
            if ch:
                await ch.send(message)
        except Exception as e:
            self.tlog.warning(f"Não foi possível enviar alerta: {e}")

    def _pick(self, task):
        msgs = task.get("messages", [])
        if not msgs: return None
        
        cfg = task.get("schedule_config", {})
        pick_mode = cfg.get("pick_mode", "random")
        
        if pick_mode == "sequential":
            task_id = task.get("id")
            key = f"task_{task_id}_seq_idx"
            idx_str = _get(key, "0")
            try:
                idx = int(idx_str)
            except ValueError:
                idx = 0
            
            idx = idx % len(msgs)
            chosen = msgs[idx]
            _set(key, str(idx + 1))
            return chosen
            
        return random.choice(msgs)