#!/usr/bin/env python3
"""
patch_index_html.py — Aplica correções BUG-8.3, 8.5, 8.6, 8.7 no index.html
Uso: python3 patch_index_html.py [caminho_para_index.html]
Default: dashboard/templates/index.html
"""
import sys, os, re, shutil

path = sys.argv[1] if len(sys.argv) > 1 else "dashboard/templates/index.html"
if not os.path.exists(path):
    print(f"[ERRO] Arquivo não encontrado: {path}")
    sys.exit(1)

# Backup
backup = path + ".bak"
shutil.copy2(path, backup)
print(f"[OK] Backup criado: {backup}")

with open(path, "r", encoding="utf-8") as f:
    html = f.read()

changes = 0

# ── FIX BUG-8.6: Adicionar apple-touch-icon 180x180 ──────────────────────
if 'sizes="180x180"' not in html:
    html = html.replace(
        '<link rel="apple-touch-icon" href="/icon-192.png">',
        '<link rel="apple-touch-icon" href="/icon-192.png">\n<link rel="apple-touch-icon" sizes="180x180" href="/icon-192.png">'
    )
    changes += 1
    print("[OK] BUG-8.6: apple-touch-icon 180x180 adicionado")
else:
    print("[SKIP] BUG-8.6: já tem apple-touch-icon 180x180")

# ── FIX BUG-8.3: PWA dismiss com TTL de 7 dias ──────────────────────────
old_dismiss = "function dismissPWA(){\n  localStorage.setItem('pwa-dismissed','1');\n  hidePWABanner();\n}"
new_dismiss = """function dismissPWA(){
  localStorage.setItem('pwa-dismissed', Date.now().toString());
  hidePWABanner();
}"""

if old_dismiss in html:
    html = html.replace(old_dismiss, new_dismiss)
    changes += 1
    print("[OK] BUG-8.3: dismissPWA() agora salva timestamp")
else:
    # Tentar variação com espaços
    old_v2 = "function dismissPWA(){"
    if old_v2 in html and "Date.now()" not in html:
        # Substituição por regex mais flexível
        html = re.sub(
            r"function dismissPWA\(\)\s*\{[^}]*localStorage\.setItem\('pwa-dismissed'[^}]*\}",
            new_dismiss,
            html
        )
        changes += 1
        print("[OK] BUG-8.3: dismissPWA() corrigido (variação)")
    else:
        print("[SKIP] BUG-8.3: já corrigido ou não encontrado")

# FIX BUG-8.3 parte 2: Verificar TTL no initPWA
old_check = "const dismissed=localStorage.getItem('pwa-dismissed');"
new_check = """const dismissed=localStorage.getItem('pwa-dismissed');
    const dismissedExpired=dismissed&&!isNaN(dismissed)&&(Date.now()-parseInt(dismissed))>7*24*60*60*1000;
    if(dismissedExpired) localStorage.removeItem('pwa-dismissed');"""

if old_check in html and "dismissedExpired" not in html:
    html = html.replace(old_check, new_check)
    # Atualizar a condição de exibição do banner
    html = html.replace(
        "if(!dismissed&&!installed) showPWABanner();",
        "if((!dismissed||dismissedExpired)&&!installed) showPWABanner();"
    )
    changes += 1
    print("[OK] BUG-8.3: TTL de 7 dias no initPWA()")
else:
    print("[SKIP] BUG-8.3 TTL: já corrigido ou não encontrado")

# ── FIX BUG-8.5: Remover HTML órfão após fechamento do v-help ────────────
# O HTML órfão é uma <ul> e <div> que ficaram fora do panel v-help
# Identificar pelo padrão: aparece depois de </div> do v-help e contém
# "Vá em <strong>Tasks -> Novo</strong>"
orphan_pattern = re.compile(
    r'(</div>\s*<!-- HELP / COMO USAR -->\s*</div>\s*</div>|'
    r'</div>\s*</div>\s*)\s*'  # fechamento do v-help
    r'(<ul\s+style="margin-left:\s*20px[^>]*>.*?</ul>\s*'  # ul órfã
    r'<div\s+style="background:\s*var\(--bg3\)[^>]*>.*?</div>\s*'  # div órfã
    r'</div>\s*</div>)',  # fechamentos extras
    re.DOTALL
)

# Abordagem mais direta: encontrar o bloco que começa com a <ul> contendo "Tasks -> Novo"
# e termina com o </div></div> extra
orphan_marker = 'Vá em <strong>Tasks -&gt; Novo</strong>'
if orphan_marker not in html:
    orphan_marker = 'Vá em <strong>Tasks -> Novo</strong>'

# Localizar a segunda ocorrência do texto "Como funciona o rodízio" que é a cópia órfã
rodizio_count = html.count('Como funciona o rodízio do bot?')
if rodizio_count >= 2:
    # Encontrar o bloco órfão: tudo entre o fechamento de v-help e o fechamento de .content
    # O bloco órfão está entre </div> (fecha v-help) e </div> (fecha content)
    # Vamos encontrar a posição da segunda <ul> com "Tasks -> Novo"
    
    # Encontrar o final do panel v-help
    v_help_end = html.find('</div>\n      </div>\n\n    </div>\n  </div>\n</div>')
    
    # Abordagem mais segura: procurar o bloco que contém a duplicata
    # entre o final de v-help e o início de </div></div> (shell)
    
    # Procurar pelo padrão exato do HTML órfão
    orphan_start_markers = [
        '          <ul style="margin-left: 20px; list-style-type: disc;',
        '      <ul style="margin-left: 20px; list-style-type: disc;',
    ]
    
    for marker in orphan_start_markers:
        idx = html.find(marker)
        if idx > 0:
            # Verificar se está FORA de um .panel
            # Procurar o </div> do panel v-help antes deste ponto
            panel_end_before = html.rfind('</div>', 0, idx)
            # Verificar se o conteúdo antes é o fechamento do v-help
            context_before = html[max(0, idx-200):idx]
            if '</div>' in context_before and 'v-help' not in context_before:
                # Encontrar o final do bloco órfão (procurar pelos </div> de fechamento)
                # O bloco termina com </div>\n  </div> que fecha .content e .main
                end_search = html.find('</div>\n  </div>', idx)
                if end_search > 0:
                    # Não remover os </div> estruturais, só o conteúdo órfão
                    orphan_block = html[idx:end_search]
                    if 'Como funciona o rodízio' in orphan_block:
                        html = html[:idx] + html[end_search:]
                        changes += 1
                        print("[OK] BUG-8.5: HTML órfão removido")
                        break
    else:
        if rodizio_count >= 2:
            print("[WARN] BUG-8.5: Detectado HTML duplicado mas não consegui remover automaticamente.")
            print("       Remova manualmente o bloco <ul>...</ul><div>...</div> após o fechamento de #v-help")
else:
    print("[SKIP] BUG-8.5: sem HTML órfão detectado")

# ── FIX BUG-8.7: Modal com visualViewport para teclado virtual ───────────
viewport_fix = """
// FIX BUG-8.7: Ajuste de modal quando teclado virtual abre (Android)
if(window.visualViewport){
  window.visualViewport.addEventListener('resize',function(){
    var modals=document.querySelectorAll('.modal');
    var vh=window.visualViewport.height;
    modals.forEach(function(m){m.style.maxHeight=(vh-20)+'px';});
  });
}
"""

if "visualViewport" not in html:
    # Inserir antes do fechamento do último </script>
    last_script_close = html.rfind("</script>")
    if last_script_close > 0:
        html = html[:last_script_close] + viewport_fix + "\n" + html[last_script_close:]
        changes += 1
        print("[OK] BUG-8.7: visualViewport listener adicionado")
else:
    print("[SKIP] BUG-8.7: já tem visualViewport")

# ── Salvar ────────────────────────────────────────────────────────────────
with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"\n{'='*50}")
print(f"[RESULTADO] {changes} correção(ões) aplicada(s) em {path}")
print(f"[BACKUP] Arquivo original em {backup}")
print(f"{'='*50}")
