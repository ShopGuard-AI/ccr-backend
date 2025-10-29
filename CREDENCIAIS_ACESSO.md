# 🔐 Credenciais de Acesso - Sistema de Monitoramento CCR

## Login do Sistema

**URL de Acesso:** https://front-end-costa-silva-ccr-poc-tkkg.vercel.app

### Usuário Autorizado

```
Usuário: admin_ccr
Senha: admin_ccr
```

---

## ⚠️ Notas Importantes

- **Autenticação Hardcoded**: As credenciais estão definidas no código do frontend para esta POC
- **Único Usuário**: Apenas um usuário configurado no momento
- **Acesso Total**: Este usuário tem acesso a todas as câmeras e funcionalidades do sistema

---

## 📋 Funcionalidades Disponíveis

Após login, o usuário `admin_ccr` terá acesso a:

1. **Videowall** - Visualização de todas as câmeras em tempo real
2. **Dashboard** - Estatísticas e análises de ocupação
3. **Configuração de Câmeras** - Adicionar/remover câmeras
4. **Configuração de Áreas** - Definir vagas de estacionamento

---

## 🔒 Segurança

**Para Produção:**
- [ ] Migrar para autenticação com backend (JWT)
- [ ] Implementar controle de permissões por usuário
- [ ] Adicionar logs de acesso
- [ ] Implementar timeout de sessão
- [ ] Criptografar credenciais

---

**Última Atualização:** 2025-10-29
