# Proteção do FiscWise contra cópia e engenharia reversa

Atualizado em 2026-11-12.

## Resumo honesto

O FiscWise é um app web instalável (PWA). "Instalar" não copia o sistema para o
computador do cliente: instala só a **tela** (HTML, CSS e JavaScript minificados)
e um cache para funcionar sem internet. O **cérebro** fica no servidor (Cloud
Run): cálculos fiscais, regras de plano, IA, emissão, integrações, banco de dados
e todas as chaves secretas.

Qualquer coisa que roda no navegador pode ser lida por quem souber abrir o
"Inspecionar elemento". Isso vale para todo site do mundo, inclusive Google e
bancos. Ninguém consegue esconder 100% a tela. O que dá para garantir é que a
tela sozinha **não serve para nada**: sem a nossa API, com login e plano ativo,
ela não calcula nem guarda nada.

## O que um cliente instalado consegue ver

| Parte | Fica onde | Dá para copiar? |
| --- | --- | --- |
| Visual das telas (layout, textos, cores) | Navegador | Sim, como qualquer site. Proteção aqui é jurídica (Termos + Lei do Software). |
| JavaScript do app | Navegador, minificado, sem source map | Só embaralhado: nomes curtos, sem comentários, sem o código original. Dá muito trabalho e não traz a lógica do servidor. |
| Cálculos fiscais, simulações, IA, regras do plano | Servidor | Não. A tela só manda os números e recebe o resultado. |
| Chaves (Stripe, Resend, Supabase service, JWT) | Servidor (Cloud Run / Secret Manager) | Não. O build é bloqueado se alguma aparecer no JavaScript. |
| Dados do escritório guardados para uso offline | IndexedDB do próprio usuário | Só os dados do próprio usuário; apagados no logout. |
| Lista de rotas da API (/docs, /openapi.json) | Desligada em produção | Não fica publicada. |

## O que já está aplicado

1. **Build sem código-fonte**: `sourcemap: false` e minificação; `debugger` removido
   (`frontend/vite.config.ts`).
2. **Trava no deploy**: o plugin `guardaBuild` em `frontend/vite.config.ts` derruba
   o build (e o deploy no Cloudflare Pages) se sair arquivo `.map`, referência a
   source map, ou algo que parece chave secreta (Stripe, Resend, chave privada,
   service_role do Supabase, segredo do JWT).
3. **Assinatura de autoria**: cada arquivo JS do app leva o aviso
   `FiscWise (c) VStack Solutions ... Lei 9.609/1998`. Se o código aparecer num
   concorrente, isso ajuda a provar a origem.
4. **Tudo que vale dinheiro é conferido no servidor**: login por JWT com
   validade, isolamento por escritório (tenant), plano verificado em cada rota
   (`backend/app/core/plan_access.py`), usuário do portal só acessa o portal.
   Mudar o JavaScript para "liberar" um recurso não adianta: a API recusa.
5. **Documentação da API escondida em produção** (`backend/app/main.py`).
6. **Termos de Uso v1.1** (`/termos`): licença de uso limitada e revogável;
   proíbe copiar, descompilar, engenharia reversa (inclusive do app instalado),
   scraping, criar produto concorrente e revender acesso; cita as leis
   9.609/1998, 9.610/1998 e 9.279/1996 e prevê suspensão e indenização. Novos
   cadastros gravam `terms_version = v1.1`.
7. **Arquivo `LICENSE` proprietário** na raiz do repositório.

## O que depende do dono (Vinicius)

1. **Tornar o repositório do GitHub privado — o mais importante.** Hoje
   `Vvs2705/FiscWise` está **público**: o código inteiro (frontend e backend) pode
   ser baixado por qualquer pessoa sem engenharia reversa nenhuma. Não há forks
   nem estrelas até agora. Caminho: GitHub → repositório → Settings → General →
   Danger Zone → Change visibility → Private.
   - Cloudflare Pages e o deploy do Cloud Run continuam funcionando com
     repositório privado.
   - GitHub Actions em repositório privado tem 2.000 minutos grátis por mês na
     conta pessoal; o CI atual cabe nisso no volume de hoje.
2. **Registrar o software no INPI** (opcional, barato): o registro de programa
   de computador dá prova de data e autoria. A taxa é baixa (tem desconto
   para empresário individual, MEI e EPP; conferir a tabela atual no site do
   INPI) e o pedido é todo online.
3. **Registrar a marca "FiscWise" no INPI**: impede que outro use o nome.

## Próximos passos possíveis (não feitos ainda)

- Limite de requisições por usuário em toda a API (hoje só `/api/v1/admin/*`
  tem limite), para dificultar robôs que tentem extrair dados em massa.
- Ofuscação pesada do JavaScript (ex.: javascript-obfuscator). Não recomendo
  agora: deixa o app mais lento e maior, e só atrasa quem quer copiar a tela,
  que já tem pouco valor sem o servidor.
