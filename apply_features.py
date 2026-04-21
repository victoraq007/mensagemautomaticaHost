import sys

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    html = f.read()

print(f"Arquivo lido: {len(html)} chars", file=sys.stderr)

# ── 1. CSS ───────────────────────────────────────────────────────────────────
NEW_CSS = """
/* ── Preview Discord ── */
.discord-preview{background:#313338;border-radius:8px;padding:16px 18px;font-family:'gg sans','Noto Sans',sans-serif;margin-top:10px}
.discord-avatar{width:40px;height:40px;border-radius:50%;background:#5865f2;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0}
.discord-msg-wrap{display:flex;gap:12px;align-items:flex-start}
.discord-bot-name{font-size:14px;font-weight:600;color:#fff;margin-bottom:2px}
.discord-bot-tag{font-size:10px;background:#5865f2;color:#fff;padding:1px 5px;border-radius:3px;margin-left:4px;font-weight:600;vertical-align:middle}
.discord-body{font-size:14px;color:#dbdee1;line-height:1.5;white-space:pre-wrap;word-break:break-word}
.discord-embed{border-left:4px solid #5865f2;background:#2b2d31;border-radius:0 4px 4px 0;padding:12px 14px;margin-top:8px;max-width:520px}
.discord-embed-desc{font-size:14px;color:#dbdee1;line-height:1.5;white-space:pre-wrap}
.discord-embed-img{width:100%;border-radius:4px;margin-top:10px;max-height:200px;object-fit:cover}
.discord-role-mention{background:rgba(88,101,242,.3);color:#c9cdfb;border-radius:3px;padding:0 2px;font-weight:500}
.discord-timestamp{font-size:11px;color:#87898c;margin-left:6px}
/* ── Bulk import ── */
.import-drop{border:2px dashed var(--b2);border-radius:var(--r2);padding:20px;text-align:center;color:var(--t3);font-size:12px;transition:.2s;cursor:pointer;background:var(--bg3)}
.import-drop:hover,.import-drop.drag{border-color:var(--ac);color:var(--t2);background:rgba(88,101,242,.05)}
.import-table{width:100%;border-collapse:collapse;font-size:12px;margin-top:10px}
.import-table th{background:var(--bg3);color:var(--t2);padding:7px 10px;text-align:left;font-weight:500;border-bottom:1px solid var(--b)}
.import-table td{padding:7px 10px;border-bottom:1px solid var(--b);color:var(--t);vertical-align:top}
.import-table tr:last-child td{border-bottom:none}
.import-table tr.ok td{background:rgba(22,163,74,.05)}
.import-table tr.err td{background:rgba(220,38,38,.05)}
.import-count{font-size:11px;color:var(--t3);font-family:var(--mono);margin-top:6px}
/* ── Template cards ── */
.tpl-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:12px}
.tpl-card{background:var(--bg3);border:1px solid var(--b);border-radius:var(--r2);padding:14px 16px;position:relative}
.tpl-card-title{font-size:13px;font-weight:600;color:var(--t);margin-bottom:4px;display:flex;align-items:center;gap:6px}
.tpl-card-desc{font-size:11px;color:var(--t3);margin-bottom:10px;line-height:1.5}
.tpl-card-meta{font-size:10px;color:var(--t3);font-family:var(--mono)}
.tpl-copy-btn{position:absolute;top:10px;right:10px}
.prompt-box{background:var(--bg);border:1px solid var(--b);border-radius:var(--r);padding:14px;font-size:11px;font-family:var(--mono);color:var(--t2);line-height:1.6;white-space:pre-wrap;max-height:200px;overflow-y:auto;margin-top:8px}
"""
html = html.replace('</style>', NEW_CSS + '\n</style>', 1)
print("CSS OK", file=sys.stderr)

# ── 2. Botão preview nas msgs salvas ─────────────────────────────────────────
OLD_EDIT = '`<button class="btn bd sm" onclick="editMsg(${i})" title="Editar">\u270e</button>`'
NEW_EDIT = '`<button class="btn bg-b sm" onclick="previewMsg(${i})" title="Preview Discord">\U0001f441</button><button class="btn bd sm" onclick="editMsg(${i})" title="Editar">\u270e</button>`'
if OLD_EDIT in html:
    html = html.replace(OLD_EDIT, NEW_EDIT)
    print("Botao preview OK", file=sys.stderr)
else:
    print("WARN: botao preview nao encontrado", file=sys.stderr)

# ── 3. Botão importar no footer modal-group ───────────────────────────────────
OLD_SAVE = '    <button class="btn bp" onclick="saveGroup()">Salvar</button>\n  </div>\n</div>\n</div>\n\n<!-- \u2500\u2500 Banner PWA'
NEW_SAVE = '    <button class="btn bg-b" onclick="openImport()" style="margin-right:4px">\U0001f4e5 Importar Lote</button>\n    <button class="btn bp" onclick="saveGroup()">Salvar</button>\n  </div>\n</div>\n</div>\n\n<!-- \u2500\u2500 Banner PWA'
if OLD_SAVE in html:
    html = html.replace(OLD_SAVE, NEW_SAVE)
    print("Botao importar OK", file=sys.stderr)
else:
    print("WARN: botao importar nao encontrado, tentando alternativa", file=sys.stderr)
    html = html.replace(
        '<button class="btn bp" onclick="saveGroup()">Salvar</button>\n  </div>\n</div>\n</div>',
        '<button class="btn bg-b" onclick="openImport()" style="margin-right:4px">\U0001f4e5 Importar Lote</button>\n    <button class="btn bp" onclick="saveGroup()">Salvar</button>\n  </div>\n</div>\n</div>'
    )

# ── 4. Modais (antes do banner PWA) ──────────────────────────────────────────
MODAIS = '''<!-- Modal Importacao em Lote -->
<div class="ov" id="modal-import" onclick="closeBg(event,'modal-import')">
<div class="modal" role="dialog" aria-modal="true" style="max-width:720px">
  <div class="mh"><span class="mt">&#128229; Importar Mensagens em Lote</span><button class="btn bg-b sm" onclick="closeModal('modal-import')">&#10005;</button></div>
  <div class="mb">
    <input type="hidden" id="import-gid">
    <div id="import-step1">
      <div style="background:rgba(88,101,242,.08);border:1px solid rgba(88,101,242,.2);border-radius:var(--r);padding:12px 14px;margin-bottom:14px">
        <div style="font-size:12px;font-weight:600;color:#818cf8;margin-bottom:4px">&#128203; Como usar</div>
        <div style="font-size:11px;color:var(--t2);line-height:1.6">1. Va em <b>Como Usar &#8594; Prompts para IA</b> e copie o prompt desejado<br>2. Cole no ChatGPT ou Claude e descreva o assunto<br>3. Cole o JSON gerado abaixo</div>
      </div>
      <label class="fl">Cole o JSON gerado pela IA</label>
      <div class="import-drop" id="import-drop" onclick="document.getElementById('import-json').focus()">
        <div style="font-size:24px;margin-bottom:6px">&#128203;</div>
        <div>Clique aqui e cole o JSON (Ctrl+V) ou arraste um arquivo .json</div>
      </div>
      <textarea id="import-json" class="fta" style="min-height:120px;margin-top:8px;font-family:var(--mono);font-size:11px" placeholder="Cole aqui o JSON gerado pela IA" oninput="parseImportJSON()"></textarea>
      <div class="import-count" id="import-count"></div>
    </div>
    <div id="import-step2" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <span style="font-size:13px;font-weight:600;color:var(--t)" id="import-preview-title"></span>
        <button class="btn bg-b sm" onclick="showImportStep1()">&#8592; Voltar</button>
      </div>
      <div style="max-height:340px;overflow-y:auto;border:1px solid var(--b);border-radius:var(--r)">
        <table class="import-table"><thead><tr><th style="width:32px">#</th><th>Mensagem</th><th style="width:60px">Tipo</th><th style="width:70px">Status</th></tr></thead><tbody id="import-tbody"></tbody></table>
      </div>
      <div class="import-count" id="import-summary"></div>
    </div>
  </div>
  <div class="mf">
    <button class="btn bg-b" onclick="closeModal('modal-import')">Cancelar</button>
    <button class="btn bp" id="btn-import-confirm" onclick="confirmImport()" style="display:none">&#10003; Importar todas</button>
  </div>
</div>
</div>

<!-- Modal Preview Discord -->
<div class="ov" id="modal-preview" onclick="closeBg(event,'modal-preview')">
<div class="modal" role="dialog" aria-modal="true" style="max-width:560px">
  <div class="mh"><span class="mt">&#128065; Preview no Discord</span><button class="btn bg-b sm" onclick="closeModal('modal-preview')">&#10005;</button></div>
  <div class="mb">
    <div style="font-size:11px;color:var(--t3);margin-bottom:10px">Simulacao visual de como a mensagem aparecera no Discord</div>
    <div class="discord-preview">
      <div class="discord-msg-wrap">
        <div class="discord-avatar">&#129302;</div>
        <div style="flex:1;min-width:0">
          <div><span class="discord-bot-name">Bot Avisos</span><span class="discord-bot-tag">BOT</span><span class="discord-timestamp" id="preview-ts"></span></div>
          <div id="preview-roles" style="margin-bottom:4px;display:none"></div>
          <div id="preview-body-wrap"><div class="discord-body" id="preview-body"></div></div>
          <div id="preview-embed-wrap" style="display:none">
            <div class="discord-embed" id="preview-embed">
              <div class="discord-embed-desc" id="preview-embed-desc"></div>
              <img id="preview-embed-img" style="display:none" class="discord-embed-img">
            </div>
          </div>
        </div>
      </div>
    </div>
    <div style="margin-top:14px">
      <label class="fl">Simular mencao de cargo</label>
      <input class="fi" id="preview-role-input" placeholder="ex: @Suporte, @Analistas" oninput="updatePreview()">
      <label class="fl" style="margin-top:10px">Simular canal</label>
      <input class="fi" id="preview-channel-input" placeholder="ex: #avisos-gerais" value="#avisos-gerais" oninput="updatePreview()">
    </div>
  </div>
  <div class="mf"><button class="btn bg-b" onclick="closeModal('modal-preview')">Fechar</button></div>
</div>
</div>

'''
html = html.replace('<div id="pwa-banner"', MODAIS + '<div id="pwa-banner"')
print("Modais OK", file=sys.stderr)

# ── 5. Secao de prompts no v-help ────────────────────────────────────────────
PROMPTS_SECTION = '''
          <h3 style="font-size:16px;margin-top:32px;margin-bottom:12px;font-weight:600;padding-bottom:4px;border-bottom:1px solid var(--b);">&#129302; Prompts Prontos para IA (Importacao em Lote)</h3>
          <p style="margin-bottom:12px;color:var(--t2);font-size:12px;">Copie um prompt, cole no ChatGPT ou Claude, descreva o assunto e importe o JSON gerado via <b>Grupos &#8594; Editar &#8594; Importar Lote</b>.</p>
          <div class="tpl-grid">
            <div class="tpl-card">
              <div class="tpl-card-title">&#128221; Texto Simples</div>
              <div class="tpl-card-desc">Mensagens de texto puro. Ideal para avisos rapidos e lembretes informais.</div>
              <div class="tpl-card-meta">50 mensagens sem embed</div>
              <button class="btn bg-b sm tpl-copy-btn" onclick="copyPrompt('simple')">&#128203; Copiar</button>
              <div class="prompt-box" id="prompt-simple">Gere exatamente 50 mensagens de aviso para equipe de suporte sobre o tema: [DESCREVA O TEMA AQUI].

Regras:
- Varie o tom: formal, informal, motivacional
- Use emojis com moderacao (maximo 2 por mensagem)
- Cada mensagem entre 20 e 150 caracteres
- Nenhuma mensagem pode ser igual ou parecida
- Voce pode usar: {hoje}, {hora}, {dia_semana}, {canal}

Responda APENAS com JSON valido, sem explicacoes, sem markdown:
[
  {"content": "texto 1", "is_embed": false},
  {"content": "texto 2", "is_embed": false}
]</div>
            </div>
            <div class="tpl-card">
              <div class="tpl-card-title">&#128142; Rich Embed</div>
              <div class="tpl-card-desc">Mensagens com card colorido no Discord. Visual profissional para comunicados importantes.</div>
              <div class="tpl-card-meta">50 mensagens com embed</div>
              <button class="btn bg-b sm tpl-copy-btn" onclick="copyPrompt('embed')">&#128203; Copiar</button>
              <div class="prompt-box" id="prompt-embed">Gere exatamente 50 mensagens Rich Embed do Discord sobre o tema: [DESCREVA O TEMA AQUI].

Regras:
- Varie o tom e estilo entre as mensagens
- Use emojis estrategicamente (maximo 2 por mensagem)
- Cada mensagem entre 30 e 200 caracteres
- Nenhuma mensagem pode ser igual ou parecida
- Voce pode usar: {hoje}, {hora}, {dia_semana}, {canal}
- Alterne as cores: #5865f2, #16a34a, #d97706, #dc2626, #7c3aed

Responda APENAS com JSON valido, sem explicacoes, sem markdown:
[
  {"content": "texto 1", "is_embed": true, "embed_color": "#5865f2"},
  {"content": "texto 2", "is_embed": true, "embed_color": "#16a34a"}
]</div>
            </div>
            <div class="tpl-card">
              <div class="tpl-card-title">&#127919; Misto Inteligente</div>
              <div class="tpl-card-desc">Combina textos simples e embeds intercalados. Variedade natural no feed.</div>
              <div class="tpl-card-meta">50 mensagens misto</div>
              <button class="btn bg-b sm tpl-copy-btn" onclick="copyPrompt('mixed')">&#128203; Copiar</button>
              <div class="prompt-box" id="prompt-mixed">Gere exatamente 50 mensagens sobre o tema: [DESCREVA O TEMA AQUI].

Misture (intercalados, nao agrupados):
- 25 mensagens texto simples (is_embed: false)
- 25 mensagens Rich Embed (is_embed: true)

Regras:
- Varie muito o tom: formal, informal, motivacional, direto, descontraido
- Use emojis com moderacao (maximo 2 por mensagem)
- Cada mensagem entre 20 e 180 caracteres
- Nenhuma mensagem pode ser igual ou parecida
- Voce pode usar: {hoje}, {hora}, {dia_semana}, {canal}
- Para embeds, cores: #5865f2, #16a34a, #d97706, #7c3aed

Responda APENAS com JSON valido, sem explicacoes, sem markdown:
[
  {"content": "texto simples", "is_embed": false},
  {"content": "embed", "is_embed": true, "embed_color": "#5865f2"}
]</div>
            </div>
            <div class="tpl-card">
              <div class="tpl-card-title">&#128197; Com Variaveis Dinamicas</div>
              <div class="tpl-card-desc">Mensagens com {hoje}, {hora} e {dia_semana} para parecerem enviadas em tempo real.</div>
              <div class="tpl-card-meta">50 mensagens dinamicas</div>
              <button class="btn bg-b sm tpl-copy-btn" onclick="copyPrompt('dynamic')">&#128203; Copiar</button>
              <div class="prompt-box" id="prompt-dynamic">Gere exatamente 50 mensagens usando variaveis dinamicas sobre o tema: [DESCREVA O TEMA AQUI].

Variaveis (use ao menos uma por mensagem):
- {hoje} - data atual (ex: 21/04/2026)
- {hora} - horario atual (ex: 09:30)
- {dia_semana} - dia da semana (ex: Segunda-feira)
- {canal} - mention do canal (#avisos)

Regras:
- Cada mensagem DEVE usar pelo menos uma variavel
- Varie quais variaveis aparecem em cada mensagem
- Varie muito o tom entre as mensagens
- Cada mensagem entre 30 e 180 caracteres
- Nenhuma mensagem pode ser igual ou parecida
- Misture is_embed true e false (metade de cada)

Responda APENAS com JSON valido, sem explicacoes, sem markdown:
[
  {"content": "Bom dia! Hoje e {dia_semana}, {hoje}.", "is_embed": false},
  {"content": "Ja sao {hora}!", "is_embed": true, "embed_color": "#5865f2"}
]</div>
            </div>
          </div>
'''

# Inserir antes do fechamento do card de ajuda
target = '          \n        </div>\n      </div>\n\n    </div>\n  </div>\n</div>'
if target in html:
    html = html.replace(target, PROMPTS_SECTION + '\n        </div>\n      </div>\n\n    </div>\n  </div>\n</div>')
    print("Prompts OK", file=sys.stderr)
else:
    # fallback: inserir antes do ul orfao
    html = html.replace(
        '          <ul style="margin-left: 20px; list-style-type: disc;',
        PROMPTS_SECTION + '          <ul style="margin-left: 20px; list-style-type: disc;'
    )
    print("Prompts OK (fallback)", file=sys.stderr)

# ── 6. JavaScript ─────────────────────────────────────────────────────────────
NEW_JS = '''
// ── Importacao em Lote ────────────────────────────────────────────────────
var _importRows = [];

function openImport() {
  var gid = document.getElementById('g-id').value;
  if (!gid) { toast('Salve o grupo primeiro antes de importar', false); return; }
  document.getElementById('import-gid').value = gid;
  document.getElementById('import-json').value = '';
  document.getElementById('import-count').textContent = '';
  document.getElementById('btn-import-confirm').style.display = 'none';
  showImportStep1();
  openModal('modal-import');
}

function showImportStep1() {
  document.getElementById('import-step1').style.display = 'block';
  document.getElementById('import-step2').style.display = 'none';
  document.getElementById('btn-import-confirm').style.display = 'none';
}

function parseImportJSON() {
  var raw = document.getElementById('import-json').value.trim();
  var countEl = document.getElementById('import-count');
  if (!raw) { countEl.textContent = ''; _importRows = []; return; }
  raw = raw.replace(/^```json?\\s*/i, '').replace(/\\s*```$/, '').trim();
  try {
    var parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) throw new Error('Esperado um array JSON');
    _importRows = parsed.map(function(item, i) {
      var content = (item.content || item.text || item.mensagem || item.message || '').trim();
      var ok = content.length > 0 && content.length <= 1900;
      return { content: content, is_embed: !!item.is_embed, embed_color: item.embed_color || '', media_url: item.media_url || '', ok: ok, idx: i + 1 };
    });
    var valid = _importRows.filter(function(r) { return r.ok; }).length;
    var invalid = _importRows.length - valid;
    countEl.textContent = _importRows.length + ' mensagens detectadas | ' + valid + ' validas' + (invalid ? ' | ' + invalid + ' com problema' : '');
    showImportPreviewTable();
  } catch(e) {
    countEl.textContent = 'JSON invalido: ' + e.message;
    _importRows = [];
    document.getElementById('btn-import-confirm').style.display = 'none';
  }
}

function showImportPreviewTable() {
  if (!_importRows.length) return;
  var valid = _importRows.filter(function(r) { return r.ok; });
  document.getElementById('import-preview-title').textContent = _importRows.length + ' mensagens | ' + valid.length + ' serao importadas';
  var tbody = document.getElementById('import-tbody');
  tbody.innerHTML = _importRows.map(function(r) {
    var sb = r.ok ? '<span class="badge bg-gr">OK</span>' : '<span class="badge bg-rd">Erro</span>';
    var tb = r.is_embed ? '<span class="badge bg-pu">Embed</span>' : '<span class="badge bg-gy">Texto</span>';
    var prev = esc(r.content).substring(0, 80) + (r.content.length > 80 ? '...' : '');
    return '<tr class="' + (r.ok ? 'ok' : 'err') + '"><td style="color:var(--t3)">' + r.idx + '</td><td>' + prev + '</td><td>' + tb + '</td><td>' + sb + '</td></tr>';
  }).join('');
  document.getElementById('import-summary').textContent = valid.length + ' de ' + _importRows.length + ' mensagens serao importadas.';
  document.getElementById('import-step1').style.display = 'none';
  document.getElementById('import-step2').style.display = 'block';
  document.getElementById('btn-import-confirm').style.display = valid.length ? 'inline-flex' : 'none';
}

async function confirmImport() {
  var gid = document.getElementById('import-gid').value;
  var valid = _importRows.filter(function(r) { return r.ok; });
  if (!valid.length) { toast('Nenhuma mensagem valida', false); return; }
  var btn = document.getElementById('btn-import-confirm');
  btn.textContent = 'Importando...'; btn.disabled = true;
  var ok = 0, err = 0;
  for (var i = 0; i < valid.length; i++) {
    var m = valid[i];
    try { await api('POST', '/groups/' + gid + '/messages', { content: m.content, is_embed: m.is_embed, embed_color: m.embed_color, media_url: m.media_url }); ok++; }
    catch(e) { err++; }
    btn.textContent = 'Importando ' + (ok + err) + '/' + valid.length + '...';
  }
  closeModal('modal-import');
  try { var g = await api('GET', '/groups/' + gid); editMsgs = g.messages || []; renderMsgs(); } catch(e) {}
  toast(ok + ' mensagens importadas!' + (err ? ' (' + err + ' erros)' : ''));
  btn.textContent = 'Importar todas'; btn.disabled = false;
}

document.addEventListener('DOMContentLoaded', function() {
  var drop = document.getElementById('import-drop');
  if (!drop) return;
  drop.addEventListener('dragover', function(e) { e.preventDefault(); drop.classList.add('drag'); });
  drop.addEventListener('dragleave', function() { drop.classList.remove('drag'); });
  drop.addEventListener('drop', function(e) {
    e.preventDefault(); drop.classList.remove('drag');
    var file = e.dataTransfer.files[0]; if (!file) return;
    var reader = new FileReader();
    reader.onload = function(ev) { document.getElementById('import-json').value = ev.target.result; parseImportJSON(); };
    reader.readAsText(file);
  });
});

// ── Preview Discord ───────────────────────────────────────────────────────
var _previewMsg = null;

function previewMsg(i) {
  var m = editMsgs[i]; if (!m) return;
  _previewMsg = m; updatePreview(); openModal('modal-preview');
}

function updatePreview() {
  if (!_previewMsg) return;
  var now = new Date();
  document.getElementById('preview-ts').textContent = 'Hoje as ' + now.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'});
  var dias = ['Domingo','Segunda-feira','Terca-feira','Quarta-feira','Quinta-feira','Sexta-feira','Sabado'];
  var canal = (document.getElementById('preview-channel-input') ? document.getElementById('preview-channel-input').value : '#avisos-gerais');
  var content = (_previewMsg.content || '')
    .replace(/\{hoje\}/g, now.toLocaleDateString('pt-BR'))
    .replace(/\{hora\}/g, now.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'}))
    .replace(/\{dia_semana\}/g, dias[now.getDay()])
    .replace(/\{canal\}/g, '<span class="discord-role-mention">' + esc(canal) + '</span>');
  var roleInput = document.getElementById('preview-role-input') ? document.getElementById('preview-role-input').value.trim() : '';
  var rolesEl = document.getElementById('preview-roles');
  if (roleInput) {
    rolesEl.innerHTML = roleInput.split(',').map(function(r) { return '<span class="discord-role-mention">' + esc(r.trim()) + '</span>'; }).join(' ');
    rolesEl.style.display = 'block';
  } else { rolesEl.style.display = 'none'; }
  if (_previewMsg.is_embed) {
    document.getElementById('preview-body-wrap').style.display = 'none';
    document.getElementById('preview-embed-wrap').style.display = 'block';
    document.getElementById('preview-embed').style.borderLeftColor = _previewMsg.embed_color || '#5865f2';
    document.getElementById('preview-embed-desc').innerHTML = content;
    var img = document.getElementById('preview-embed-img');
    if (_previewMsg.media_url) { img.src = _previewMsg.media_url; img.style.display = 'block'; } else { img.style.display = 'none'; }
  } else {
    document.getElementById('preview-body-wrap').style.display = 'block';
    document.getElementById('preview-embed-wrap').style.display = 'none';
    document.getElementById('preview-body').innerHTML = content;
  }
}

// ── Copiar prompts ────────────────────────────────────────────────────────
function copyPrompt(type) {
  var el = document.getElementById('prompt-' + type); if (!el) return;
  navigator.clipboard.writeText(el.textContent.trim()).then(function() { toast('Prompt copiado! Cole no ChatGPT ou Claude.'); });
}

// ── visualViewport fix (teclado virtual Android) ──────────────────────────
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', function() {
    var vh = window.visualViewport.height;
    document.querySelectorAll('.modal').forEach(function(m) { m.style.maxHeight = (vh - 20) + 'px'; });
  });
}
'''

html = html.replace('</script>\n</body>', NEW_JS + '\n</script>\n</body>')
print("JS OK", file=sys.stderr)

# ── 7. PWA dismiss TTL ────────────────────────────────────────────────────────
html = html.replace(
    "function dismissPWA(){\n  localStorage.setItem('pwa-dismissed','1');\n  hidePWABanner();\n}",
    "function dismissPWA(){\n  localStorage.setItem('pwa-dismissed', Date.now().toString());\n  hidePWABanner();\n}"
)
html = html.replace(
    "    const dismissed=localStorage.getItem('pwa-dismissed');\n    const installed=localStorage.getItem('pwa-installed');\n    if(!dismissed&&!installed) showPWABanner();",
    "    const dismissed=localStorage.getItem('pwa-dismissed');\n    const installed=localStorage.getItem('pwa-installed');\n    const dismissedExpired=dismissed&&!isNaN(dismissed)&&(Date.now()-parseInt(dismissed))>7*24*60*60*1000;\n    if(dismissedExpired) localStorage.removeItem('pwa-dismissed');\n    if((!dismissed||dismissedExpired)&&!installed) showPWABanner();"
)
print("PWA TTL OK", file=sys.stderr)

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Arquivo salvo: {len(html)} chars", file=sys.stderr)
print("DONE")