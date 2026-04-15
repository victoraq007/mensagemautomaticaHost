# mensagemautomaticaHost

## Configuração do dashboard

O dashboard requer autenticação. Você pode usar uma senha em texto simples ou um hash seguro.

Exemplo de `.env`:

```env
DISCORD_TOKEN=seu_token_aqui
DASHBOARD_SECRET_KEY=uma_chave_secreta_forte
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD=senha_simples_ou_vazia
# ou use um hash seguro em vez de senha em texto plano
DASHBOARD_PASSWORD_HASH=pbkdf2:sha256:260000$...hash...
DASHBOARD_COOKIE_SECURE=true
DASHBOARD_SESSION_LIFETIME_MINUTES=60
```

### Quando usar `DASHBOARD_PASSWORD_HASH`

- `DASHBOARD_PASSWORD_HASH` deve conter um hash gerado com `werkzeug.security.generate_password_hash`.
- O valor deve ser um hash completo, não a senha em texto plano.
- O app compara a senha enviada pelo formulário com o hash para validar o login.

### Como gerar o hash

Execute no terminal do Python:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('sua-senha-segura'))"
```

Depois copie o valor gerado para o `.env`:

```env
DASHBOARD_PASSWORD_HASH=pbkdf2:sha256:260000$...valor...
```

### Uso alternativo

Se você não quiser usar hash, basta definir `DASHBOARD_PASSWORD`:

```env
DASHBOARD_PASSWORD=senha_simples
```

> Em produção, é mais seguro usar `DASHBOARD_PASSWORD_HASH` e `DASHBOARD_SECRET_KEY`.

