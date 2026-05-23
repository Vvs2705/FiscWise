# 📋 Modelo de Submissão — Secrets do Cliente

**Versão:** 1.0  
**Formato Aceitos:** Excel (.xlsx), PDF preenchido, Google Forms, Email estruturado  
**Confidencialidade:** 🔐 Criptografado e-to-e, acesso restrito  

---

## 📌 Instruções Gerais

Este modelo organiza todos os dados sensíveis/secrets que o seu contador precisa ter acesso para gerenciar sua documentação, pagamentos e certificações digitais.

**Importante:**
- ✅ Preencha APENAS os campos que você deseja registrar
- ✅ Dados sensíveis (senhas) são criptografados no servidor
- ✅ Apenas seu contador tem acesso
- ✅ Você pode atualizar informações a qualquer momento
- ✅ Pode ser preenchido de forma parcial e incrementado depois

---

## 📄 Seção 1: Dados Pessoais Básicos

| Campo | Valor | Notas |
|-------|-------|-------|
| **Nome Completo** | | Como consta em documentos |
| **CPF** | ___.___.___-__ | Apenas números ou formato completo |
| **Data de Nascimento** | __/__/____ | DD/MM/YYYY |
| **Sexo** | ☐ Masculino ☐ Feminino ☐ Outro | |
| **Nacionalidade** | | Brasileira/Estrangeira |
| **Estado Civil** | ☐ Solteiro ☐ Casado ☐ Divorciado ☐ Viúvo | |
| **Email Pessoal** | | |
| **Email Profissional** | | |
| **Telefone Celular** | (_) _____ - ____ | |

---

## 📊 Seção 2: Dados da Empresa / PJ

| Campo | Valor | Notas |
|-------|-------|-------|
| **Razão Social** | | Nome oficial da empresa |
| **Nome Fantasia** | | Como é conhecido |
| **CNPJ** | __.__.__/____ - __ | Números ou formato completo |
| **Regime Tributário** | ☐ Simples ☐ Lucro Presumido ☐ Lucro Real ☐ MEI | |
| **Data de Constituição** | __/__/____ | DD/MM/YYYY |
| **Endereço** | | Rua, nº, complemento |
| **Cidade** | | |
| **Estado** | | |
| **CEP** | _____-___ | |
| **Telefone Comercial** | (_) _____ - ____ | |

---

## 🏦 Seção 3: Dados Bancários

**Para cada conta bancária que o contador precisa acessar:**

### Conta #1

| Campo | Valor | Notas |
|-------|-------|-------|
| **Banco** | | Ex: Banco do Brasil, Caixa, Bradesco, Itaú |
| **Tipo de Conta** | ☐ Corrente ☐ Poupança ☐ Investimento | |
| **Agência** | | Sem dígito |
| **Número da Conta** | | Com dígito |
| **IBAN (se internacional)** | | |
| **Email da Conta** | | CPF/CNPJ vinculado |
| **Telefone de Recuperação** | | Número registrado no banco |
| **Senha do App** | 🔐 _______ | Será armazenada criptografada |
| **Token/Código de Segurança** | 🔐 _______ | Se requerido pelo banco |
| **Open Finance Ativado?** | ☐ Sim ☐ Não | Autorização para API |

### Conta #2 (se houver)
*Repetir seção acima para cada conta adicional*

---

## 🔐 Seção 4: Certificado Digital

**Necessário para assinatura digital de documentos contábeis/fiscais:**

| Campo | Valor | Notas |
|-------|-------|-------|
| **Tipo de Certificado** | ☐ e-CPF ☐ e-CNPJ ☐ A1 ☐ A3 | |
| **Órgão Emissor** | | Ex: ICP-Brasil, Certisign, etc |
| **Nome do Titular** | | Deve corresponder ao documento |
| **Data de Validade** | __/__/____ | Quando expira |
| **Arquivo do Certificado** | *Upload via portal* | .pfx ou .p12 |
| **Senha do Certificado** | 🔐 _______ | Será criptografada |
| **Local de Armazenamento** | ☐ PC ☐ Token ☐ Smart Card | Onde está guardado |

**⚠️ Importante:**
- Se em token/smart card: disponibilizar para seu contador
- Certifique-se de que o certificado está válido
- Renovar 30 dias antes de expirar

---

## 👤 Seção 5: Sócios / Administradores (Para Empresas)

**Preencher para cada sócio/administrador que tenha acesso a contas ou certificados:**

### Sócio/Admin #1

| Campo | Valor | Notas |
|-------|-------|-------|
| **Nome Completo** | | |
| **CPF** | ___.___.___-__ | |
| **Data de Nascimento** | __/__/____ | |
| **Cargo/Função** | | Ex: Sócio-gerente, Diretor, Administrador |
| **Email** | | |
| **Telefone** | (_) _____ - ____ | |
| **Tem Acesso a Contas Bancárias?** | ☐ Sim ☐ Não | |
| **Tem Certificado Digital?** | ☐ Sim ☐ Não | Se sim, preencher Seção 4 adicional |
| **Percentual de Participação** | __% | Se aplicável |

### Sócio/Admin #2 (se houver)
*Repetir seção acima para cada sócio adicional*

---

## 📄 Seção 6: Senhas & Acessos (Geral)

**Para serviços/plataformas que o contador pode precisar acessar:**

| Plataforma | Login | Senha | 2FA/Segurança | Notas |
|-----------|-------|-------|---------------|-------|
| **Portal da Receita Federal** | CPF/CNPJ | 🔐 _______ | ☐ Ativado | e-CAC |
| **Portal do INSS** | CPF/CNPJ | 🔐 _______ | ☐ Ativado | Consultas |
| **SPED/Escrituração** | Email | 🔐 _______ | ☐ Ativado | Sistema contábil |
| **Ponto Eletrônico** | Email | 🔐 _______ | ☐ Ativado | Se aplicável |
| **Folha de Pagamento** | Email | 🔐 _______ | ☐ Ativado | Sistema RH |
| **Google Workspace** | Email | 🔐 _______ | ☐ Ativado | Email corporativo |
| **Microsoft 365** | Email | 🔐 _______ | ☐ Ativado | Se em uso |
| **Outros Serviços** | | | | Especificar |

---

## 💰 Seção 7: Informações Contábeis / Fiscais

| Campo | Valor | Notas |
|-------|-------|-------|
| **Contador Anterior** | | Se houver migração |
| **Última Declaração de IR** | Ano ______ | |
| **ECF (Escrituração Contábil Fiscal)** | ☐ Obrigado ☐ Dispensado | |
| **ECD (Escrituração Contábil Digital)** | ☐ Obrigado ☐ Dispensado | |
| **EFD-Contribuições** | ☐ Obrigado ☐ Dispensado | |
| **Sistema Contábil Atual** | | Ex: SAP, Oracle, Sistema caseiro, Omie |
| **Contato de Backup** | | Pessoa que pode acessar esses dados se precisar |

---

## 📞 Seção 8: Contatos de Emergência / Backup

| Campo | Valor | Notas |
|-------|-------|-------|
| **Contato 1 (Sócio/Cônjuge)** | | Nome e telefone |
| **Contato 2 (Parente)** | | Nome e telefone |
| **Email de Recuperação** | | Para 2FA/reset de senha |
| **Telefone de Backup** | | Outro celular/fixo |

---

## 📋 Seção 9: Autorizações & Consentimentos

Ao preencher este formulário, você autoriza:

- ☐ Seu contador acessar as informações acima para fins administrativos/contábeis
- ☐ Armazenamento seguro de dados sensíveis em servidor criptografado
- ☐ Compartilhamento de informações (não-sensíveis) com outros membros da sua equipe contábil se necessário
- ☐ Contato via email/telefone para confirmação de dados

**Data de Preenchimento:** ____/____/____  
**Assinatura (digital):** ______________________

---

## 🚀 Como Enviar Este Formulário

### **Opção 1: Excel/Google Sheets**
1. Baixar template em `fiscwise.com.br/templates/secrets.xlsx`
2. Preencher offline
3. Upload via portal FiscWise (botão "Enviar Secrets")

### **Opção 2: Google Forms**
1. Acessar link fornecido pelo contador
2. Preencher online
3. Respostas salvas automaticamente

### **Opção 3: Email**
1. Preencher este PDF ou Word
2. Enviar para: `secrets@fiscwise.com.br` (criptografado)
3. Confirmação dentro de 24h

### **Opção 4: Portal FiscWise**
1. Login em `fiscwise.com.br/portal`
2. Ir para "Meus Dados" → "Secrets"
3. Preencher campo por campo
4. Salvar rascunho ou enviar

---

## 🔒 Segurança & Privacidade

✅ **O que garantimos:**
- Criptografia end-to-end (AES-256)
- Backup automático seguro
- Acesso auditado (logs de quem viu o quê)
- Sem compartilhamento com terceiros
- Conformidade com LGPD/GDPR

❌ **Nunca envie por:**
- Email não criptografado
- WhatsApp / SMS
- Formulários públicos
- Documentos não protegidos

---

## ❓ Perguntas Frequentes

**P: Posso deixar alguns campos em branco?**  
R: Sim, preencha apenas o que você quer registrar. Pode atualizar depois.

**P: Minha senha é segura se eu enviar aqui?**  
R: Sim, usamos criptografia de nível bancário. Mas recomendamos trocar a senha depois.

**P: Meu contador pode acessar meu banco diretamente?**  
R: Só se você autorizar. Open Finance permite acesso read-only sem compartilhar senha.

**P: Preciso renovar essas informações?**  
R: Sim, anualmente ou quando houver mudanças (nova conta, certificado renovado, etc).

**P: E se eu esquecer minha senha?**  
R: Seu contador não tem acesso (está criptografada). Use "Esqueci Senha" no portal.

---

## 📞 Suporte

**Dúvidas sobre o formulário?**
- Email: support@fiscwise.com.br
- Chat: fiscwise.com.br/chat (horário comercial)
- WhatsApp: (11) 99999-9999

---

**Obrigado por fornecer essas informações!**  
Isso nos ajuda a oferecer o melhor serviço possível. 🎯
