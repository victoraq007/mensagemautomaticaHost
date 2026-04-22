# dashboard/app.py
from flask import Flask, jsonify, request, render_template, abort, redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from config import (
    DASHBOARD_COOKIE_SECURE,
    DASHBOARD_PASSWORD,
    DASHBOARD_PASSWORD_HASH,
    DASHBOARD_SECRET_KEY,
    DASHBOARD_SESSION_LIFETIME,
    DASHBOARD_SESSION_PERMANENT,
    DASHBOARD_USERNAME,
)
from database import get_session
from models import TaskConfig, MessageGroup, Message, Settings, TaskExecutionLog
import json, datetime, functools, os

MAX_MSG_LEN = 1900  # Discord limita 2000, deixamos margem para o prefixo [TESTE]

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB limit
    app.secret_key = DASHBOARD_SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SECURE"] = DASHBOARD_COOKIE_SECURE
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = datetime.timedelta(minutes=DASHBOARD_SESSION_LIFETIME)
    app.config["SESSION_PERMANENT"] = DASHBOARD_SESSION_PERMANENT

    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200/hour"],
        storage_uri="memory://",
    )

    # ── Auth helpers ──────────────────────────────────────────────────────────
    def login_required(f):
        @functools.wraps(f)
        def decorated(*args, **kwargs):
            if not session.get("logged_in"):
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Não autorizado"}), 401
                return redirect(url_for("login_page"))
            return f(*args, **kwargs)
        return decorated

    @app.route("/login", methods=["GET"])
    def login_page():
        if session.get("logged_in"):
            return redirect("/")
        return render_template("login.html")

    @app.route("/login", methods=["POST"])
    @limiter.limit("10/minute")
    def do_login():
        data = request.get_json(force=True) if request.is_json else request.form
        user = (data.get("username") or "").strip()
        pw   = (data.get("password") or "").strip()
        ok = __import__("hmac").compare_digest(user, DASHBOARD_USERNAME) and _check_password(pw)
        if ok:
            session["logged_in"] = True
            session.permanent = DASHBOARD_SESSION_PERMANENT
            if request.is_json:
                return jsonify({"ok": True})
            return redirect("/")
        if request.is_json:
            return jsonify({"error": "Usuário ou senha incorretos"}), 401
        return render_template("login.html", error="Usuário ou senha incorretos")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect("/login")

    # ── Upload ───────────────────────────────────────────────────────────────
    UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads")
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @app.route("/api/upload", methods=["POST"])
    @login_required
    @limiter.limit("20/minute")
    def upload_file():
        if 'file' not in request.files:
            return jsonify({"error": "Nenhum arquivo enviado"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Nome de arquivo vazio"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Evitar sobreposição com timestamp
            base, ext = os.path.splitext(filename)
            filename = f"{base}_{int(datetime.datetime.now().timestamp())}{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))
            return jsonify({"ok": True, "url": f"/static/uploads/{filename}"})
        return jsonify({"error": "Extensão não permitida"}), 400


    # ── Página principal ──────────────────────────────────────────────────────
    @app.route("/")
    @login_required
    def index():
        return render_template("index.html")

    # ── Canais ────────────────────────────────────────────────────────────────
    @app.route("/api/channels")
    @login_required
    def list_channels():
        try:
            from cogs.tasks_cog import get_bot_channels
            return jsonify(get_bot_channels())
        except Exception:
            return jsonify([])

    @app.route("/api/roles")
    @login_required
    def list_roles():
        try:
            from cogs.tasks_cog import _bot_ref
            if not _bot_ref:
                return []
            
            roles_set = {}
            for guild in _bot_ref.guilds:
                for r in guild.roles:
                    if r.name != "@everyone" and not r.managed:
                        roles_set[str(r.id)] = {
                            "id": str(r.id),
                            "name": r.name,
                            "color": str(r.color)
                        }
            # ordenar por nome
            res = list(roles_set.values())
            res.sort(key=lambda x: x["name"].lower())
            return jsonify(res)
        except Exception:
            return jsonify([])

    @app.route("/api/users")
    @login_required
    def list_users():
        try:
            from cogs.tasks_cog import _bot_ref
            if not _bot_ref: return jsonify([])
            users_set = {}
            for guild in _bot_ref.guilds:
                for member in guild.members:
                    if not member.bot:
                        users_set[str(member.id)] = {"id": str(member.id), "name": member.name, "display_name": member.display_name}
            res = list(users_set.values())
            res.sort(key=lambda x: x["display_name"].lower())
            return jsonify(res)
        except Exception:
            return jsonify([])

    # ── API — Logs ────────────────────────────────────────────────────────────
    @app.route("/api/logs")
    @login_required
    def get_logs():
        lines = int(request.args.get("lines", 100))
        lines = min(lines, 500)
        log_path = os.path.join("logs", "tasks.log")
        if not os.path.exists(log_path):
            return jsonify({"lines": [], "exists": False})
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        return jsonify({"lines": [l.rstrip() for l in all_lines[-lines:]], "exists": True, "total": len(all_lines)})

    @app.route("/api/upcoming")
    @login_required
    def upcoming_tasks():
        """Retorna previsão das próximas execuções de cada task ativa."""
        import pytz
        from config import TIMEZONE
        now = datetime.datetime.now(TIMEZONE)
        result = []
        with get_session() as s:
            tasks = s.query(TaskConfig).filter_by(active=True).all()
            for t in tasks:
                cfg = json.loads(t.schedule_config or "{}")
                desc = _next_run_desc(t.type, t.test_mode, cfg, now)
                result.append({
                    "id": t.id,
                    "name": t.name,
                    "type": t.type,
                    "test_mode": bool(t.test_mode),
                    "next_run": desc,
                })
        return jsonify(result)

    @app.route("/api/sent_history")
    @login_required
    def sent_history():
        """Últimas N chaves de envio registradas no banco (Settings)."""
        limit = min(int(request.args.get("limit", 50)), 200)
        with get_session() as s:
            rows = s.query(Settings)\
                    .filter(Settings.key.like("task_%_sent_%"))\
                    .order_by(Settings.id.desc())\
                    .limit(limit).all()
            return jsonify([{"key": r.key, "value": r.value} for r in rows])

    @app.route("/api/logs_db")
    @login_required
    def get_logs_db():
        """Retorna os logs registrados em TaskExecutionLog."""
        limit = min(int(request.args.get("limit", 100)), 500)
        try:
            with get_session() as s:
                rows = s.query(TaskExecutionLog).order_by(TaskExecutionLog.id.desc()).limit(limit).all()
                return jsonify([{
                    "id": r.id,
                    "task_name": r.task_name,
                    "channel_id": r.channel_id,
                    "status": r.status,
                    "error_msg": r.error_msg,
                    "created_at": r.created_at.isoformat() if r.created_at else None
                } for r in rows])
        except Exception:
            return jsonify([])

    @app.route("/api/read_logs")
    @login_required
    def get_read_logs():
        """Retorna os recibos de leitura das DMs."""
        from models import MessageReadLog
        limit = min(int(request.args.get("limit", 100)), 500)
        try:
            with get_session() as s:
                rows = s.query(MessageReadLog).order_by(MessageReadLog.id.desc()).limit(limit).all()
                result = []
                for r in rows:
                    task = s.query(TaskConfig).filter_by(id=r.task_id).first()
                    result.append({
                        "task_name": task.name if task else f"({r.task_id})",
                        "user_name": r.user_name,
                        "read_at": r.read_at.isoformat() if r.read_at else None
                    })
                return jsonify(result)
        except Exception:
            return jsonify([])

    @app.route("/api/stats")
    @login_required
    def get_stats():
        """Retorna indicadores-chave do painel."""
        try:
            with get_session() as s:
                tasks_ativas = s.query(TaskConfig).filter_by(active=True).count()
                grupos = s.query(MessageGroup).count()
                envios_ok = s.query(TaskExecutionLog).filter_by(status="SUCCESS").count()
                envios_err = s.query(TaskExecutionLog).filter_by(status="ERROR").count()
                
                return jsonify({
                    "active_tasks": tasks_ativas,
                    "total_groups": grupos,
                    "sent_success": envios_ok,
                    "sent_errors": envios_err
                })
        except Exception:
            return jsonify({
                "active_tasks": 0, "total_groups": 0,
                "sent_success": 0, "sent_errors": 0
            })

    # ── API — Grupos ──────────────────────────────────────────────────────────
    @app.route("/api/groups", methods=["GET"])
    @login_required
    def list_groups():
        with get_session() as s:
            gs = s.query(MessageGroup).order_by(MessageGroup.id).all()
            return jsonify([_sg(g) for g in gs])

    @app.route("/api/groups", methods=["POST"])
    @login_required
    @limiter.limit("30/minute")
    def create_group():
        d = request.get_json(force=True)
        if not (d.get("name") or "").strip():
            abort(400, "name obrigatório")
        with get_session() as s:
            g = MessageGroup(name=d["name"].strip()[:200], description=d.get("description","")[:500])
            s.add(g); s.flush()
            return jsonify(_sg(g)), 201

    @app.route("/api/groups/<int:gid>", methods=["GET"])
    @login_required
    def get_group(gid):
        with get_session() as s:
            g = s.query(MessageGroup).filter_by(id=gid).first()
            if not g: abort(404)
            return jsonify(_sg(g, True))

    @app.route("/api/groups/<int:gid>", methods=["PUT"])
    @login_required
    @limiter.limit("30/minute")
    def update_group(gid):
        d = request.get_json(force=True)
        with get_session() as s:
            g = s.query(MessageGroup).filter_by(id=gid).first()
            if not g: abort(404)
            if d.get("name","").strip(): g.name = d["name"].strip()[:200]
            if "description" in d: g.description = d["description"][:500]
            return jsonify(_sg(g))

    @app.route("/api/groups/<int:gid>", methods=["DELETE"])
    @login_required
    @limiter.limit("20/minute")
    def delete_group(gid):
        with get_session() as s:
            g = s.query(MessageGroup).filter_by(id=gid).first()
            if not g: abort(404)
            s.delete(g)
        return jsonify({"ok": True})

    @app.route("/api/groups/<int:gid>/messages", methods=["POST"])
    @login_required
    @limiter.limit("60/minute")
    def add_message(gid):
        d = request.get_json(force=True)
        content = (d.get("content") or "").strip()
        if not content:
            abort(400, "content obrigatório")
        if len(content) > MAX_MSG_LEN:
            abort(400, f"Mensagem muito longa ({len(content)} chars). Máximo: {MAX_MSG_LEN}")
        with get_session() as s:
            if not s.query(MessageGroup).filter_by(id=gid).first(): abort(404)
            m = Message(
                group_id=gid, 
                content=content, 
                is_embed=bool(d.get("is_embed", False)),
                embed_color=str(d.get("embed_color", ""))[:50],
                media_url=str(d.get("media_url", ""))[:500],
                active=True
            )
            s.add(m); s.flush()
            return jsonify(_sm(m)), 201

    @app.route("/api/messages/<int:mid>", methods=["PUT"])
    @login_required
    @limiter.limit("60/minute")
    def update_message(mid):
        d = request.get_json(force=True)
        with get_session() as s:
            m = s.query(Message).filter_by(id=mid).first()
            if not m: abort(404)
            if "content" in d:
                content = d["content"].strip()
                if len(content) > MAX_MSG_LEN:
                    abort(400, f"Mensagem muito longa ({len(content)} chars). Máximo: {MAX_MSG_LEN}")
                m.content = content
            if "is_embed" in d: m.is_embed = bool(d["is_embed"])
            if "embed_color" in d: m.embed_color = str(d["embed_color"])[:50]
            if "media_url" in d: m.media_url = str(d["media_url"])[:500]
            if "active" in d: m.active = bool(d["active"])
            return jsonify(_sm(m))

    @app.route("/api/messages/<int:mid>", methods=["DELETE"])
    @login_required
    @limiter.limit("30/minute")
    def delete_message(mid):
        with get_session() as s:
            m = s.query(Message).filter_by(id=mid).first()
            if not m: abort(404)
            s.delete(m)
        return jsonify({"ok": True})

    @app.route("/api/groups/<int:gid>/messages/order", methods=["PUT"])
    @login_required
    @limiter.limit("60/minute")
    def update_messages_order(gid):
        d = request.get_json(force=True)
        order_list = d.get("order", [])
        if not isinstance(order_list, list):
            abort(400, "order deve ser uma lista de IDs")
        with get_session() as s:
            for idx, msg_id in enumerate(order_list):
                m = s.query(Message).filter_by(id=msg_id, group_id=gid).first()
                if m:
                    m.msg_order = idx
            return jsonify({"ok": True})

    @app.route("/api/export", methods=["GET"])
    @login_required
    def export_all():
        with get_session() as s:
            tasks = s.query(TaskConfig).all()
            groups = s.query(MessageGroup).all()
            
            export_data = {
                "tasks": [_st(t) for t in tasks],
                "groups": [_sg(g, msgs=True) for g in groups]
            }
            return jsonify(export_data)

    # ── API — Tasks ───────────────────────────────────────────────────────────
    @app.route("/api/tasks", methods=["GET"])
    @login_required
    def list_tasks():
        with get_session() as s:
            ts = s.query(TaskConfig).order_by(TaskConfig.id).all()
            return jsonify([_st(t) for t in ts])

    @app.route("/api/tasks", methods=["POST"])
    @login_required
    @limiter.limit("30/minute")
    def create_task():
        d = request.get_json(force=True)
        errs = _validate_task(d)
        if errs: abort(400, "; ".join(errs))
        with get_session() as s:
            t = TaskConfig(
                name=d["name"].strip()[:200],
                description=d.get("description","")[:500],
                type=d["type"],
                channel_ids=_normalize_channels(d.get("channel_ids", "")),
                roles_to_mention=_normalize_channels(d.get("roles_to_mention", "")),
                send_dm=bool(d.get("send_dm", False)),
                target_users=_normalize_channels(d.get("target_users", "")),
                message_group_id=d.get("message_group_id") or None,
                schedule_config=json.dumps(d.get("schedule_config", {})),
                active=d.get("active", True),
                test_mode=d.get("test_mode", False),
            )
            s.add(t); s.flush()
            return jsonify(_st(t)), 201

    @app.route("/api/tasks/<int:tid>", methods=["GET"])
    @login_required
    def get_task(tid):
        with get_session() as s:
            t = s.query(TaskConfig).filter_by(id=tid).first()
            if not t: abort(404)
            return jsonify(_st(t))

    @app.route("/api/tasks/<int:tid>", methods=["PUT"])
    @login_required
    @limiter.limit("30/minute")
    def update_task(tid):
        d = request.get_json(force=True)
        if d.get("type") and d.get("type") not in VALID_TYPES:
            abort(400, "type inválido")
        if "schedule_config" in d and not _valid_schedule_config(d.get("type") or "", d.get("schedule_config")):
            abort(400, "schedule_config inválido ou mal formado")
        with get_session() as s:
            t = s.query(TaskConfig).filter_by(id=tid).first()
            if not t: abort(404)
            if d.get("name","").strip(): t.name = d["name"].strip()[:200]
            if "description"      in d: t.description    = d["description"][:500]
            if "type"             in d: t.type            = d["type"]
            if "channel_ids"      in d: t.channel_ids     = _normalize_channels(d["channel_ids"])
            if "roles_to_mention" in d: t.roles_to_mention = _normalize_channels(d["roles_to_mention"])
            if "send_dm"          in d: t.send_dm          = bool(d["send_dm"])
            if "target_users"     in d: t.target_users     = _normalize_channels(d["target_users"])
            if "message_group_id" in d: t.message_group_id= d["message_group_id"] or None
            if "schedule_config"  in d: t.schedule_config = json.dumps(d["schedule_config"])
            if "active"           in d: t.active          = bool(d["active"])
            if "test_mode"        in d: t.test_mode       = bool(d["test_mode"])
            t.updated_at = datetime.datetime.utcnow()
            return jsonify(_st(t))

    # ── FIX BUG-3.6: Excluir task agora remove Settings órfãos ──────────────
    @app.route("/api/tasks/<int:tid>", methods=["DELETE"])
    @login_required
    @limiter.limit("20/minute")
    def delete_task(tid):
        with get_session() as s:
            t = s.query(TaskConfig).filter_by(id=tid).first()
            if not t: abort(404)
            # FIX BUG-3.6: Limpar todas as chaves Settings associadas à task
            s.query(Settings).filter(Settings.key.like(f"task_{tid}_%")).delete(synchronize_session=False)
            s.delete(t)
        return jsonify({"ok": True})

    @app.route("/api/tasks/<int:tid>/toggle", methods=["POST"])
    @login_required
    def toggle_task(tid):
        with get_session() as s:
            t = s.query(TaskConfig).filter_by(id=tid).first()
            if not t: abort(404)
            t.active = not t.active
            t.updated_at = datetime.datetime.utcnow()
            return jsonify({"id": t.id, "active": t.active})

    @app.route("/api/tasks/<int:tid>/toggle_test", methods=["POST"])
    @login_required
    def toggle_test(tid):
        with get_session() as s:
            t = s.query(TaskConfig).filter_by(id=tid).first()
            if not t: abort(404)
            t.test_mode = not t.test_mode
            t.updated_at = datetime.datetime.utcnow()
            return jsonify({"id": t.id, "test_mode": t.test_mode})

    # ── Erros JSON ────────────────────────────────────────────────────────────
    @app.errorhandler(400)
    @app.errorhandler(401)
    @app.errorhandler(404)
    @app.errorhandler(413)
    @app.errorhandler(429)
    @app.errorhandler(500)
    def handle_error(e):
        code = getattr(e, "code", 500)
        if request.path.startswith("/api/"):
            return jsonify({"error": str(e)}), code
        return str(e), code

    @app.after_request
    def set_security_headers(response):
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
        response.headers["Permissions-Policy"] = "interest-cohort=()"
        if app.config["SESSION_COOKIE_SECURE"]:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    _register_pwa(app)
    return app


# ── PWA ───────────────────────────────────────────────────────────────────────
import os as _os
from flask import send_from_directory as _sfd

def _register_pwa(app):
    static_dir = _os.path.join(_os.path.dirname(__file__), 'static')

    @app.route('/manifest.json')
    def manifest():
        return _sfd(static_dir, 'manifest.json', mimetype='application/manifest+json')

    @app.route('/sw.js')
    def service_worker():
        r = _sfd(static_dir, 'sw.js', mimetype='application/javascript')
        r.headers['Service-Worker-Allowed'] = '/'
        r.headers['Cache-Control'] = 'no-cache'
        return r

    @app.route('/icon-192.png')
    def icon192():
        return _sfd(static_dir, 'icon-192.png', mimetype='image/png')

    @app.route('/icon-512.png')
    def icon512():
        return _sfd(static_dir, 'icon-512.png', mimetype='image/png')


# ── Serializers ───────────────────────────────────────────────────────────────
def _sm(m):
    return {"id":m.id,"group_id":m.group_id,"content":m.content,"active":m.active,
            "is_embed":getattr(m, "is_embed", False),
            "embed_color":getattr(m, "embed_color", ""),
            "media_url":getattr(m, "media_url", ""),
            "msg_order":getattr(m, "msg_order", 0) or 0,
            "created_at":m.created_at.isoformat() if m.created_at else None,
            "length": len(m.content)}

def _sg(g, msgs=True):
    d = {"id":g.id,"name":g.name,"description":g.description,
         "message_count":len(g.messages),
         "created_at":g.created_at.isoformat() if g.created_at else None}
    if msgs:
        sorted_msgs = sorted(g.messages, key=lambda x: (getattr(x, "msg_order", 0) or 0, x.id))
        d["messages"] = [_sm(m) for m in sorted_msgs]
    return d

def _st(t):
    return {"id":t.id,"name":t.name,"description":t.description,"type":t.type,
            "channel_ids":t.channel_ids,"message_group_id":t.message_group_id,
            "roles_to_mention":getattr(t, "roles_to_mention", ""),
            "send_dm":getattr(t, "send_dm", False),
            "target_users":getattr(t, "target_users", ""),
            "schedule_config":json.loads(t.schedule_config or "{}"),
            "active":t.active,"test_mode":bool(t.test_mode),
            "created_at":t.created_at.isoformat() if t.created_at else None,
            "updated_at":t.updated_at.isoformat() if t.updated_at else None}

VALID_TYPES = {"fixed_times","interval_days","weekly","monthly","test"}

def _normalize_channels(raw):
    if isinstance(raw, list):
        normalized = [str(x).strip() for x in raw if str(x).strip()]
    else:
        normalized = [x.strip() for x in str(raw).split(",") if x.strip()]
    return ",".join(normalized)


def _check_password(password: str) -> bool:
    if DASHBOARD_PASSWORD_HASH:
        return check_password_hash(DASHBOARD_PASSWORD_HASH, password)
    return __import__("hmac").compare_digest(password, DASHBOARD_PASSWORD)


def _valid_schedule_config(task_type, cfg):
    if not isinstance(cfg, dict):
        return False
    if task_type == "fixed_times":
        return isinstance(cfg.get("times", []), list)
    if task_type == "interval_days":
        return isinstance(cfg.get("every_days", 0), int)
    if task_type in {"weekly", "monthly"}:
        return isinstance(cfg.get("hour_start", 0), int)
    if task_type == "test":
        return isinstance(cfg.get("every_minutes", 0), int)
    return False


def _validate_task(d):
    e = []
    if not (d.get("name") or "").strip():
        e.append("name obrigatório")
    if d.get("type") not in VALID_TYPES:
        e.append("type inválido")
    if d.get("send_dm"):
        if not d.get("target_users"):
            e.append("Nenhum usuário foi selecionado para a Mensagem Direta")
    else:
        if not d.get("channel_ids"):
            e.append("Nenhum canal foi selecionado para disparo")
    if "schedule_config" in d:
        cfg = d.get("schedule_config")
        if not _valid_schedule_config(d.get("type"), cfg):
            e.append("schedule_config inválido ou mal formado")
    return e


def _norm(raw):
    return _normalize_channels(raw)


def _next_run_desc(task_type, test_mode, cfg, now):
    if test_mode:
        every = cfg.get("every_minutes", 2)
        return f"Próxima em até {every} min (modo teste)"
    if task_type == "weekly":
        days = ["Seg","Ter","Qua","Qui","Sex","Sáb","Dom"]
        dow  = cfg.get("days_of_week", [0,1,2,3,4])
        return f"Semanal — {', '.join(days[d] for d in dow)} {cfg.get('hour_start',9)}h–{cfg.get('hour_end',18)}h"
    if task_type == "monthly":
        months = cfg.get("months",[])
        mstr = "todo mês" if not months else f"meses {months}"
        return f"Mensal — {mstr} {cfg.get('hour_start',9)}h–{cfg.get('hour_end',18)}h"
    if task_type == "fixed_times":
        times = cfg.get("times",[])
        return f"Horários fixos: {', '.join(times)}"
    if task_type == "interval_days":
        every = cfg.get("every_days", 10)
        start = cfg.get("start_from", "hoje")
        return f"A cada {every} dias (ref: {start})"
    return "—"
