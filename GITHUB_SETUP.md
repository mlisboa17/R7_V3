# 📦 Setup GitHub para R7 Sniper V3

## Passo 1: Criar Repositório no GitHub

1. Acesse https://github.com/new
2. Nome do repositório: `R7_Sniper_V3` (ou outro nome)
3. **Privado** ✅ (recomendado por segurança)
4. NÃO inicialize com README, .gitignore ou licença
5. Clique em **"Create repository"**

## Passo 2: Configurar Git Local

Execute os comandos abaixo no PowerShell:

```powershell
# Navegar até o diretório do projeto
cd C:\Users\mlisb\PROJETOS_Local\R7_V3

# Configurar nome e email (se ainda não configurou)
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# Verificar status
git status
```

## Passo 3: Primeiro Commit

```powershell
# Adicionar todos os arquivos (exceto os que estão no .gitignore)
git add .

# Fazer o primeiro commit
git commit -m "🚀 Initial commit: R7 Sniper V3 Trading System"
```

## Passo 4: Conectar ao GitHub

**IMPORTANTE:** Substitua `SEU_USUARIO` pelo seu nome de usuário do GitHub:

```powershell
# Adicionar origem remota
git remote add origin https://github.com/SEU_USUARIO/R7_Sniper_V3.git

# Verificar remote
git remote -v

# Renomear branch para main (se necessário)
git branch -M main

# Fazer push inicial
git push -u origin main
```

## Passo 5: Autenticação GitHub

Se pedir senha, use um **Personal Access Token** (não use sua senha):

1. Vá em: https://github.com/settings/tokens
2. Clique em **"Generate new token"** → **"Classic"**
3. Marque os scopes: `repo`, `workflow`
4. Copie o token (guarde em local seguro!)
5. Use o token como senha no comando `git push`

### Alternativa: Git Credential Manager

```powershell
# Instalar (se não tiver)
winget install Microsoft.GitCredentialManager

# Configurar
git config --global credential.helper manager
```

## 🔒 Segurança - Arquivos NUNCA commitados

O `.gitignore` já protege:
- ✅ `.env` (credenciais API)
- ✅ `*.db` (bancos de dados)
- ✅ `*.pkl`, `*.joblib` (modelos treinados)
- ✅ `data/` (histórico de trades)
- ✅ `*.log` (logs)

**VERIFIQUE antes do push:**
```powershell
# Ver arquivos que SERÃO commitados
git status

# Ver diferenças
git diff --cached
```

## 📊 Comandos Úteis

### Atualizar repositório
```powershell
# Adicionar mudanças
git add .

# Commit com mensagem
git commit -m "feat: adiciona nova funcionalidade X"

# Push para GitHub
git push
```

### Ver histórico
```powershell
git log --oneline --graph --all
```

### Criar branch para testes
```powershell
# Criar e mudar para branch
git checkout -b feature/nova-funcionalidade

# Fazer commit na branch
git add .
git commit -m "test: experimenta nova estratégia"

# Push da branch
git push -u origin feature/nova-funcionalidade
```

### Voltar para main
```powershell
git checkout main
```

## 🚨 ATENÇÃO

**NUNCA faça commit de:**
- ❌ Chaves de API
- ❌ Senhas
- ❌ Arquivos .env
- ❌ Bancos de dados com trades reais
- ❌ Logs com informações sensíveis

**Se você acidentalmente commitou algo sensível:**
```powershell
# Remover arquivo do histórico
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force push (CUIDADO!)
git push origin --force --all
```

## 📝 Padrões de Commit

Use commits descritivos:
- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `refactor:` refatoração de código
- `test:` adição de testes
- `chore:` manutenção

Exemplos:
```
feat: adiciona Cerebro Stop Loss IA
fix: corrige cálculo de Order Book
docs: atualiza README com novas features
refactor: otimiza verificação de saldo
test: adiciona testes para candlestick patterns
```

## 🎯 Pronto!

Seu código agora está no GitHub de forma segura! 🎉

Para ver: https://github.com/SEU_USUARIO/R7_Sniper_V3
