# CHANGELOG — QA Session Fixes (2026-04-20)

## Correções Aplicadas

### CRÍTICO
- **BUG-8.1** — `manifest.json` com `"purpose": "any maskable"` inválido separado em ícones distintos (`"any"` e `"maskable"`) para compatibilidade com Chrome 107+

### ALTO
- **BUG-4.2** — Task `weekly` agora salva chave com ano ISO (`2026-W16` em vez de `16`) para evitar colisão na virada de ano
- **BUG-4.4** — Task `fixed_times` agora itera `reversed(sorted(times))` — envia apenas o horário mais recente atrasado em vez de gotejar 1 por tick
- **BUG-3.6** — `DELETE /api/tasks/:id` agora remove todas as chaves `Settings` com prefixo `task_{id}_*` (evita poluição do banco)
- **BUG-5.5** — Mensagens DM agora são truncadas para 1997+`"..."` se ultrapassarem 2000 chars (igual ao fluxo de canais)
- **BUG-8.5** — HTML órfão (bloco `<ul>` + `<div>` duplicado) removido de fora do panel `#v-help`
- **BUG-8.2** — Service Worker agora cacheia rotas locais (`/`, `/login`, `/manifest.json`, ícones) e incrementou versão do cache para `bot-avisos-v2`
- **BUG-8.3** — Banner PWA "Agora não" agora salva timestamp e reaparece após 7 dias

### MÉDIO
- **BUG-4.3** — Task `monthly` agora usa zero-padding no mês (`2026-01` em vez de `2026-1`)
- **BUG-5.9** — Guard de truncamento adicionado ao `roles_prefix` no path de embed
- **BUG-7.2** — `auto_migrate()` agora cobre colunas `send_dm` e `target_users` em `task_configs`
- **BUG-8.6** — `manifest.json` agora inclui `id`, `scope`, `display_override`, `categories`; `index.html` recebe `apple-touch-icon` 180x180
- **BUG-8.7** — Modal agora ajusta `maxHeight` via `visualViewport` API quando teclado virtual abre no Android

## Arquivos Modificados
| Arquivo | Bugs Corrigidos |
|---|---|
| `cogs/tasks_cog.py` | BUG-4.2, 4.3, 4.4, 5.5, 5.9 |
| `dashboard/app.py` | BUG-3.6 |
| `database.py` | BUG-7.2 |
| `dashboard/static/manifest.json` | BUG-8.1, 8.6 |
| `dashboard/static/sw.js` | BUG-8.2 |
| `dashboard/templates/index.html` | BUG-8.3, 8.5, 8.6, 8.7 |