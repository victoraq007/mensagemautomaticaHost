#!/bin/bash
# ══════════════════════════════════════════════════════════════
# deploy_patches.sh — Aplica TODAS as correções do QA Session
# 
# Bugs corrigidos:
#   BUG-3.6  — Delete task remove Settings órfãos
#   BUG-4.2  — Weekly com ano na chave ISO
#   BUG-4.3  — Monthly com zero-padding
#   BUG-4.4  — Fixed_times reversed (apenas mais recente atrasado)
#   BUG-5.5  — DM truncamento 2000 chars
#   BUG-5.9  — roles_prefix guard no embed path
#   BUG-7.2  — auto_migrate cobre send_dm e target_users
#   BUG-8.1  — manifest.json purpose separado
#   BUG-8.2  — sw.js STATIC array utilizado + cache v2
#   BUG-8.3  — PWA dismiss com TTL 7 dias
#   BUG-8.5  — HTML órfão removido
#   BUG-8.6  — manifest campos recomendados + apple-touch-icon
#   BUG-8.7  — Modal keyboard fix (visualViewport)
#
# Uso:
#   cd /home/ubuntu/bot_discord   (ou o diretório do projeto)
#   bash deploy_patches.sh
# ══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo ""
echo "══════════════════════════════════════════════════"
echo "  Bot Avisos Discord — Deploy de Correções QA"
echo "══════════════════════════════════════════════════"
echo ""

# Verificar se estamos no diretório correto
if [ ! -f "main.py" ]; then
    echo "[ERRO] Execute este script na raiz do projeto (onde está main.py)"
    echo "  Exemplo: cd /home/ubuntu/bot_discord && bash $0"
    exit 1
fi

# Criar backups
echo "[1/6] Criando backups..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -f cogs/tasks_cog.py "$BACKUP_DIR/tasks_cog.py.bak" 2>/dev/null || true
cp -f dashboard/app.py "$BACKUP_DIR/app.py.bak" 2>/dev/null || true
cp -f database.py "$BACKUP_DIR/database.py.bak" 2>/dev/null || true
cp -f dashboard/static/manifest.json "$BACKUP_DIR/manifest.json.bak" 2>/dev/null || true
cp -f dashboard/static/sw.js "$BACKUP_DIR/sw.js.bak" 2>/dev/null || true
cp -f dashboard/templates/index.html "$BACKUP_DIR/index.html.bak" 2>/dev/null || true
echo "  Backups em: $BACKUP_DIR/"

# Aplicar patches dos arquivos Python
echo ""
echo "[2/6] Aplicando patch: cogs/tasks_cog.py (BUG-4.2, 4.3, 4.4, 5.5, 5.9)..."
cp -f "$SCRIPT_DIR/cogs/tasks_cog.py" cogs/tasks_cog.py
echo "  ✅ OK"

echo ""
echo "[3/6] Aplicando patch: dashboard/app.py (BUG-3.6)..."
cp -f "$SCRIPT_DIR/dashboard/app.py" dashboard/app.py
echo "  ✅ OK"

echo ""
echo "[4/6] Aplicando patch: database.py (BUG-7.2)..."
cp -f "$SCRIPT_DIR/database.py" database.py
echo "  ✅ OK"

# Aplicar patches dos arquivos estáticos
echo ""
echo "[5/6] Aplicando patches PWA (BUG-8.1, 8.2, 8.6)..."
cp -f "$SCRIPT_DIR/dashboard/static/manifest.json" dashboard/static/manifest.json
cp -f "$SCRIPT_DIR/dashboard/static/sw.js" dashboard/static/sw.js
echo "  ✅ manifest.json e sw.js atualizados"

# Patch do index.html (via script Python)
echo ""
echo "[6/6] Aplicando patch: index.html (BUG-8.3, 8.5, 8.6, 8.7)..."
python3 "$SCRIPT_DIR/patch_index_html.py" dashboard/templates/index.html
echo ""

# Resumo
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✅ TODAS AS CORREÇÕES APLICADAS COM SUCESSO"
echo "══════════════════════════════════════════════════"
echo ""
echo "  Arquivos modificados:"
echo "    • cogs/tasks_cog.py"
echo "    • dashboard/app.py"
echo "    • database.py"
echo "    • dashboard/static/manifest.json"
echo "    • dashboard/static/sw.js"
echo "    • dashboard/templates/index.html"
echo ""
echo "  Próximo passo: reiniciar o bot"
echo "    sudo systemctl restart bot_discord"
echo ""
echo "  Para reverter (caso algo dê errado):"
echo "    cp $BACKUP_DIR/*.bak . (restaurar manualmente)"
echo ""
echo "══════════════════════════════════════════════════"
