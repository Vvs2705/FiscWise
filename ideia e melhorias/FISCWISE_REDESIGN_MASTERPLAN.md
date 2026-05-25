Analisei novamente o repositório e preparei um **arquivo Markdown completo** para você salvar como:

```txt
docs/FISCWISE_REDESIGN_MASTERPLAN.md
```

Usei como base o estado atual do projeto: o README ainda posiciona o FiscWise como SaaS para “escritórios de contabilidade” e multi-tenant, enquanto o produto agora deve mirar **contadores autônomos**. O frontend já usa React, TypeScript, Vite, Tailwind, TanStack Query, Zustand, Recharts, Framer Motion e Lucide; o login e dashboard também ainda carregam linguagem/fluxos mais voltados para operação de escritório/equipe. ([GitHub][1])

Também pesquisei bibliotecas atuais para elevar UI/UX: `shadcn/ui`, `Motion`, `TanStack Table`, `cmdk`, `Sonner`, `Vaul`, `Driver.js`, `React Joyride`, `Embla Carousel`, `Lottie` e `React Three Fiber`, priorizando opções úteis para um SaaS visualmente premium e interativo. ([Shadcn UI][2])

Abaixo está o conteúdo do arquivo:

````md
# FiscWise — Masterplan de Redesign, Produto, UX, UI e Evolução Técnica

## Objetivo deste documento

Este documento define uma direção completa para transformar o **FiscWise** em um sistema premium, moderno, confiável e desejável para **contadores autônomos**.

O objetivo não é apenas “deixar bonito”.

O objetivo é fazer o usuário olhar para o produto e pensar:

> “Esse sistema parece profissional.  
> Esse sistema entende minha rotina.  
> Esse sistema vai me ajudar a parecer mais organizado para meus clientes.  
> Esse sistema eu teria vontade de usar todos os dias.”

---

# 1. Diagnóstico estratégico atual

## 1.1 Problema central

O FiscWise tem uma base técnica promissora, mas ainda sofre de um problema de posicionamento e percepção.

Hoje o produto parece comunicar:

> Plataforma SaaS para escritórios de contabilidade, equipes, multiusuários e operação interna.

Mas a direção correta é:

> Sistema de gestão fiscal e operacional para contadores autônomos que precisam organizar clientes, documentos, prazos, obrigações, certificados, guias e rotina mensal em um único lugar.

Essa diferença muda tudo:

- Linguagem
- Telas
- Menus
- Dashboard
- Login
- Jornada de cadastro
- Funcionalidades
- Métricas
- Prioridades
- Animações
- Onboarding
- Design visual
- Argumentos de venda

---

## 1.2 O que precisa sair do centro do produto

Evitar dar protagonismo a termos como:

- Escritório contábil
- Equipe
- Admin
- Colaborador
- Departamento
- Multiusuário
- Permissões complexas
- Produtividade por colaborador
- Gestão de times
- Operação empresarial pesada

Esses recursos podem existir no futuro, mas não devem ser a narrativa inicial.

---

## 1.3 O que deve entrar no centro do produto

O FiscWise deve girar em torno da vida real do contador autônomo:

- Minha carteira de clientes
- Meus prazos
- Meus documentos pendentes
- Minhas obrigações fiscais
- Meus certificados digitais
- Minhas guias
- Meus recebíveis
- Minha agenda
- Minha rotina de fechamento
- Meus clientes que precisam de atenção hoje
- Meu nível de organização mensal

A pergunta principal do sistema deve ser:

> “O que eu preciso resolver hoje para manter meus clientes em dia?”

---

# 2. Novo posicionamento do produto

## 2.1 Frase principal

> FiscWise é a central de controle para contadores autônomos gerenciarem clientes, obrigações, documentos, prazos e rotina fiscal com mais organização e profissionalismo.

---

## 2.2 Promessa de valor

> Organize sua carteira de clientes, acompanhe prazos fiscais e entregue uma experiência mais profissional sem depender de planilhas espalhadas.

---

## 2.3 Subpromessas

- Controle tudo em um só lugar
- Nunca mais perca um prazo importante
- Saiba quais clientes precisam da sua atenção
- Receba, acompanhe e organize documentos
- Tenha uma rotina fiscal mais previsível
- Passe mais profissionalismo para seus clientes
- Reduza retrabalho no fechamento mensal

---

## 2.4 Público-alvo

### Público principal

- Contadores autônomos
- Consultores contábeis independentes
- Profissionais que atendem MEIs, microempresas e pequenas empresas
- Contadores em início de carreira com carteira própria
- Profissionais que ainda usam Excel, WhatsApp, Drive e lembretes manuais

### Público secundário futuro

- Pequenos escritórios de 2 a 5 pessoas
- Escritórios familiares
- Consultorias contábeis enxutas

---

# 3. Nova personalidade da marca

## 3.1 Como o FiscWise deve parecer

O FiscWise deve parecer:

- Profissional
- Premium
- Inteligente
- Seguro
- Fiscal
- Moderno
- Claro
- Organizado
- Confiável
- Agradável de usar

---

## 3.2 Como o FiscWise não deve parecer

O FiscWise não deve parecer:

- Template genérico
- Dashboard comum de startup
- Sistema escolar
- Planilha colorida
- ERP antigo
- Sistema pesado de governo
- Landing page exagerada
- SaaS azul genérico sem personalidade

---

## 3.3 Tom de voz

Usar linguagem direta e útil.

### Evitar

```txt
Gerencie sua operação empresarial com indicadores estratégicos.
````

### Preferir

```txt
Veja quais clientes precisam da sua atenção hoje.
```

### Evitar

```txt
Painel de produtividade por colaborador.
```

### Preferir

```txt
Sua rotina de hoje.
```

### Evitar

```txt
Controle de escritório.
```

### Preferir

```txt
Controle da sua carteira de clientes.
```

---

# 4. Direção visual premium

## 4.1 Conceito visual

Criar uma estética chamada:

> Fiscal Intelligence OS

A ideia é fazer o FiscWise parecer um “sistema operacional fiscal” para o contador autônomo.

Visualmente, isso deve unir:

* Fundo escuro sofisticado
* Superfícies translúcidas
* Verde fiscal / teal como cor de confiança
* Azul petróleo como base institucional
* Dourado discreto para valor financeiro
* Vermelho apenas para risco real
* Microanimações suaves
* Ícones finos e consistentes
* Cards com profundidade
* Tabelas limpas
* Estados vazios elegantes
* Experiência responsiva

---

## 4.2 Paleta recomendada

```css
:root {
  --fw-bg: #06111f;
  --fw-bg-soft: #091827;
  --fw-bg-elevated: #0d2136;

  --fw-surface: rgba(13, 33, 54, 0.78);
  --fw-surface-solid: #10263d;
  --fw-surface-hover: #16324f;

  --fw-primary: #2dd4bf;
  --fw-primary-strong: #14b8a6;
  --fw-primary-soft: rgba(45, 212, 191, 0.14);

  --fw-blue: #38bdf8;
  --fw-blue-soft: rgba(56, 189, 248, 0.14);

  --fw-gold: #f5c542;
  --fw-gold-soft: rgba(245, 197, 66, 0.14);

  --fw-success: #22c55e;
  --fw-success-soft: rgba(34, 197, 94, 0.14);

  --fw-warning: #f59e0b;
  --fw-warning-soft: rgba(245, 158, 11, 0.14);

  --fw-danger: #ef4444;
  --fw-danger-soft: rgba(239, 68, 68, 0.14);

  --fw-text: #edf6ff;
  --fw-text-muted: #91a8c3;
  --fw-text-soft: #6f86a3;

  --fw-border: rgba(148, 163, 184, 0.18);
  --fw-border-strong: rgba(45, 212, 191, 0.35);

  --fw-shadow-soft: 0 20px 60px rgba(0, 0, 0, 0.28);
  --fw-shadow-glow: 0 0 42px rgba(45, 212, 191, 0.16);
}
```

---

## 4.3 Gradientes principais

```css
--fw-gradient-primary: linear-gradient(135deg, #2dd4bf 0%, #38bdf8 100%);
--fw-gradient-gold: linear-gradient(135deg, #f5c542 0%, #f59e0b 100%);
--fw-gradient-danger: linear-gradient(135deg, #ef4444 0%, #fb7185 100%);
--fw-gradient-surface: linear-gradient(180deg, rgba(16, 38, 61, 0.92), rgba(8, 22, 38, 0.92));
--fw-gradient-login: radial-gradient(circle at 20% 20%, rgba(45, 212, 191, 0.22), transparent 28%),
                     radial-gradient(circle at 80% 30%, rgba(56, 189, 248, 0.18), transparent 30%),
                     linear-gradient(135deg, #06111f 0%, #0d2136 100%);
```

---

## 4.4 Tipografia

Recomendação:

* Fonte principal: Inter, Geist, Manrope ou Plus Jakarta Sans
* Peso base: 400
* Títulos: 700 ou 800
* Números de dashboard: 800
* Labels pequenos: 600
* Evitar fontes muito arredondadas ou infantis

Hierarquia:

```txt
H1: 36–48px, bold, letter-spacing negativo leve
H2: 26–32px, bold
H3: 20–24px, semibold
Card title: 14–15px, semibold
Card value: 28–40px, bold
Body: 14–16px
Label: 12–13px, medium
```

---

# 5. Redesign da logo

## 5.1 Problema comum a evitar

Não usar logo com:

* Gráfico genérico
* Moeda genérica
* Documento genérico
* Calculadora genérica
* Check aleatório
* Ícone de escudo comum
* Símbolo que pareça retirado de banco de ícones

---

## 5.2 Conceito recomendado

Criar um monograma:

> FW + sinal de validação fiscal

Ideia:

* A letra F formada por linhas/documentos
* A letra W sugerindo fluxo/organização
* Um check sutil em espaço negativo
* Bordas levemente arredondadas
* Visual de tecnologia fiscal

---

## 5.3 Aplicações da logo

Criar variações:

```txt
Logo completa horizontal
Logo compacta
Ícone isolado
Favicon
Splash/loading mark
Marca monocromática
Marca para fundo claro
Marca para fundo escuro
```

---

## 5.4 Animação da logo

Criar uma animação curta:

1. Linhas aparecem como se fossem documentos sendo organizados.
2. Monograma FW se forma.
3. Check aparece com leve brilho.
4. Texto FiscWise aparece com fade/slide.

Duração ideal:

```txt
700ms a 1100ms
```

Não passar disso para não cansar.

---

# 6. Login premium

## 6.1 Objetivo da tela de login

O login deve vender o produto antes mesmo do usuário entrar.

Ele deve comunicar:

* Segurança
* Organização
* Controle
* Modernidade
* Valor para contador autônomo

---

## 6.2 Problemas atuais a corrigir

Substituir textos voltados a “escritório” por textos voltados ao contador individual.

### Trocar

```txt
Dados criptografados e isolados por escritório.
```

### Por

```txt
Seus clientes e documentos protegidos em um ambiente exclusivo.
```

### Trocar

```txt
Controle total da sua operação contábil.
```

### Por

```txt
Controle sua carteira contábil com precisão.
```

### Trocar

```txt
Dashboard com KPIs financeiros e de compliance.
```

### Por

```txt
Veja prazos, documentos e clientes que precisam da sua atenção.
```

---

## 6.3 Layout recomendado

Tela dividida:

```txt
Esquerda: narrativa visual premium
Direita: formulário limpo, rápido e seguro
```

### Painel esquerdo

Elementos:

* Logo animada
* Headline forte
* Cards flutuantes
* Radar fiscal animado
* Mini timeline de obrigações
* Chips de status
* Fundo com aurora sutil
* Ilustração abstrata de documentos virando checklists

### Painel direito

Elementos:

* Card de login com glassmorphism discreto
* Login Google
* E-mail/senha
* Mostrar/ocultar senha com animação leve
* 2FA com OTP bonito
* Mensagem de segurança
* Link para cadastro grátis
* Rodapé limpo

---

## 6.4 Headline recomendada

```txt
Controle sua carteira contábil com precisão.
```

Subheadline:

```txt
Clientes, documentos, prazos, certificados e obrigações fiscais em uma central feita para contadores autônomos.
```

---

## 6.5 Cards animados no login

Criar cards flutuantes no painel esquerdo:

```txt
Hoje
7 obrigações vencendo

Documentos
12 aguardando clientes

Certificados
2 vencem este mês

Fechamentos
81% concluídos
```

Esses cards devem subir/descer levemente com animação suave.

---

## 6.6 Animação “Radar Fiscal”

Criar um componente visual chamado:

```txt
FiscalRadar
```

Ele deve exibir:

* Círculos concêntricos
* Linha de varredura suave
* Pontos representando clientes
* Cores por status:

  * Verde: regular
  * Amarelo: atenção
  * Vermelho: pendência crítica
* Ao passar o mouse, mostrar tooltip:

  * “Cliente com DAS pendente”
  * “Documento aguardando envio”
  * “Certificado vence em 12 dias”

Esse recurso pode ser apenas decorativo no login e funcional no dashboard futuramente.

---

## 6.7 Animações do login

Usar:

* Fade in no painel
* Slide up no formulário
* Stagger nos cards
* Aurora background animada
* Botão com brilho sutil no hover
* Inputs com borda teal no foco
* OTP com microinteração por dígito
* Mensagem de erro com shake curto
* Loading do botão com spinner elegante

Evitar:

* Neon excessivo
* Muitas partículas
* 3D pesado obrigatório
* Vídeo de fundo
* Animações longas

---

# 7. Dashboard: transformar em cockpit diário

## 7.1 Problema atual

O dashboard atual mistura métricas financeiras, prazos, gráficos e produtividade com cara de painel genérico.

Para contador autônomo, o dashboard precisa responder:

> O que preciso fazer hoje?

---

## 7.2 Novo nome

Trocar:

```txt
Dashboard
```

Por:

```txt
Painel
```

Ou:

```txt
Minha Rotina
```

Recomendação final:

```txt
Painel
```

Mas o título interno pode ser:

```txt
Sua rotina de hoje
```

---

## 7.3 Estrutura ideal do dashboard

```txt
1. Hero de boas-vindas
2. Bloco “Foco de hoje”
3. Métricas essenciais
4. Clientes que precisam de atenção
5. Agenda fiscal da semana
6. Documentos pendentes
7. Fechamentos mensais
8. Risco da carteira
9. Ações rápidas
10. Aprendizado/contexto
```

---

## 7.4 Métricas principais

Substituir métricas genéricas por métricas acionáveis:

```txt
Obrigações vencendo hoje
Obrigações atrasadas
Clientes com pendências
Documentos aguardando envio
Certificados vencendo
Fechamentos em aberto
Guias pendentes
Recebíveis em atraso
```

---

## 7.5 Componente “Foco de Hoje”

Criar o principal card da tela:

```txt
Foco de hoje

Você tem 6 itens importantes:
- 2 obrigações vencem hoje
- 3 clientes ainda não enviaram documentos
- 1 certificado vence em 8 dias
```

Com CTA:

```txt
Resolver agora
```

Esse card deve ser visualmente mais forte que os outros.

---

## 7.6 Componente “Clientes que precisam de atenção”

Lista com score:

```txt
Cliente                    Motivo                  Risco
Padaria São Jorge           DAS pendente            Alto
Clínica Vida Plena          Documentos ausentes     Médio
TechNova Serviços           Certificado vencendo    Médio
```

Criar badge:

```txt
Alto
Médio
Baixo
Regular
```

---

## 7.7 Componente “Agenda Fiscal da Semana”

Formato timeline:

```txt
Hoje
- DAS Simples Nacional
- Enviar guia para cliente
- Conferir documentos pendentes

Amanhã
- Fechamento da competência
- Revisar notas fiscais

Sexta
- Certificado de cliente vence
```

---

## 7.8 Componente “Fechamentos Mensais”

Exibir por competência:

```txt
Maio/2026

Concluídos: 18
Em andamento: 7
Bloqueados por cliente: 4
Atrasados: 2
```

Com barra de progresso.

---

## 7.9 Componente “Risco da Carteira”

Criar score visual:

```txt
Saúde da carteira: 82/100
```

Fatores:

* Prazos em atraso
* Documentos ausentes
* Certificados vencendo
* Guias não pagas
* Clientes sem movimentação

Classificação:

```txt
90–100 Excelente
75–89 Boa
55–74 Atenção
0–54 Crítica
```

---

# 8. Menu lateral redesenhado

## 8.1 Menu recomendado

```txt
Painel
Clientes
Agenda Fiscal
Obrigações
Documentos
Guias e DAS
Certificados
Financeiro
Calculadora
Aprender
Configurações
```

---

## 8.2 Ajustes de nomenclatura

Trocar:

```txt
Agenda / Prazos
```

Por:

```txt
Agenda Fiscal
```

Trocar:

```txt
DAS Mensal
```

Por:

```txt
Guias e DAS
```

Adicionar:

```txt
Aprender
```

---

## 8.3 Sidebar premium

A sidebar deve ter:

* Logo compacta
* Estado ativo com barra lateral teal
* Ícones consistentes
* Tooltip em modo recolhido
* Mini indicador de pendências
* Botão de ação rápida
* Rodapé com plano atual
* Atalho para suporte/aprendizado

Exemplo:

```txt
[FW] FiscWise

Painel
Clientes
Agenda Fiscal        3
Obrigações           8
Documentos           12
Guias e DAS
Certificados         2
Financeiro
Calculadora
Aprender
Configurações

+ Novo cliente
Plano Starter
```

---

# 9. Páginas principais: melhorias detalhadas

## 9.1 Clientes

A página de clientes deve ser a “carteira” do contador.

### Melhorias

* Tabela premium com filtros avançados
* Score de risco por cliente
* Status mensal
* Última interação
* Documentos pendentes
* Obrigações abertas
* Certificado associado
* Tags personalizadas
* Busca rápida
* Visualização em lista e cards
* Drawer lateral com detalhes do cliente

### Campos recomendados

```txt
Nome/Razão social
CPF/CNPJ
Regime tributário
Tipo de cliente
Telefone
E-mail
WhatsApp
Status
Responsável fiscal externo, se houver
Observações
Tags
```

### Estados

```txt
Regular
Atenção
Pendente
Crítico
Inativo
```

---

## 9.2 Detalhe do cliente

Criar uma página ou drawer:

```txt
/clientes/:id
```

Seções:

```txt
Resumo
Documentos
Obrigações
Guias
Certificados
Financeiro
Histórico
Notas internas
```

Essa tela é essencial para dar profundidade ao produto.

---

## 9.3 Agenda Fiscal

Esta deve ser uma das telas mais importantes.

### Visualizações

```txt
Calendário
Lista
Semana
Competência
Cliente
Tipo de obrigação
```

### Recursos

* Obrigações recorrentes
* Filtros por cliente
* Alertas
* Status
* Priorização
* Datas críticas
* Ações rápidas
* Transformar prazo em tarefa
* Marcar como concluído
* Anexar guia/documento

````

---

## 9.4 Obrigações

Separar obrigação de tarefa comum.

### Obrigação

Algo fiscal/contábil que precisa ser cumprido.

Exemplos:

```txt
DAS
DEFIS
DCTFWeb
EFD-Reinf
EFD-Contribuições
ECD
ECF
eSocial
Emissão de guia
Conferência de notas
Fechamento mensal
````

### Campos

```txt
Título
Cliente
Competência
Tipo
Data de vencimento
Status
Prioridade
Recorrência
Documentos vinculados
Observações
```

### Status

```txt
Pendente
Em andamento
Aguardando cliente
Concluída
Atrasada
Cancelada
```

---

## 9.5 Documentos

A página de documentos deve parecer mais confiável.

### Melhorias

* Área drag and drop premium
* Preview
* Status de conferência
* Documento vinculado ao cliente
* Documento vinculado à competência
* Documento vinculado à obrigação
* Versões
* Filtros por tipo
* Histórico de envio
* Origem:

  * Enviado pelo contador
  * Enviado pelo cliente
  * Importado
  * Gerado pelo sistema

### Estados

```txt
Recebido
Aguardando conferência
Aprovado
Rejeitado
Pendente do cliente
```

---

## 9.6 Guias e DAS

Criar tela específica para guias.

### Recursos

* Guias geradas
* Guias enviadas ao cliente
* Guias pagas
* Guias vencidas
* Valor
* Vencimento
* Cliente
* Competência
* Anexo PDF
* Comprovante de pagamento
* Lembrete automático

### Status

```txt
A gerar
Gerada
Enviada
Paga
Vencida
Cancelada
```

---

## 9.7 Certificados

A página de certificados deve ser visualmente forte porque passa segurança.

### Melhorias

* Timeline de vencimento
* Alertas 30/15/7 dias
* Tipo A1/A3
* Titular
* CPF/CNPJ
* Cliente vinculado
* Status
* Botão “avisar cliente”
* Histórico de renovação

### Visual

Usar cards com:

* Ícone de escudo
* Data de validade grande
* Badge de risco
* Barra de proximidade do vencimento

---

## 9.8 Financeiro

Para contador autônomo, financeiro não deve virar ERP completo no início.

Foco:

* Recebíveis
* Pagamentos dos clientes
* Receita mensal
* Inadimplência
* Histórico por cliente
* Honorários mensais

### Métricas

```txt
Recebido no mês
A receber
Em atraso
Clientes inadimplentes
Ticket médio
Receita recorrente estimada
```

---

## 9.9 Calculadora Fiscal

Transformar calculadora em recurso de valor percebido.

### Melhorias

* Layout mais didático
* Explicação do cálculo
* Histórico de simulações
* Exportar simulação em PDF
* Salvar simulação no cliente
* Comparar cenários
* Tooltips explicativos

---

# 10. Nova aba “Aprender”

## 10.1 Objetivo

Criar uma central de aprendizado dentro do FiscWise para reduzir dúvidas, aumentar percepção de valor e melhorar ativação.

Nome sugerido:

```txt
Aprender
```

Alternativas:

```txt
Guia FiscWise
Central de Ajuda
Academia FiscWise
Primeiros Passos
```

Recomendação:

```txt
Aprender
```

É simples, humano e direto.

---

## 10.2 Estrutura da aba Aprender

```txt
Aprender
├── Primeiros passos
├── Como cadastrar clientes
├── Como usar a Agenda Fiscal
├── Como controlar documentos
├── Como acompanhar guias e DAS
├── Como controlar certificados
├── Como usar o financeiro
├── Como interpretar o painel
├── Boas práticas para contador autônomo
└── Novidades do sistema
```

---

## 10.3 Tipos de conteúdo

* Cards de tutorial
* Vídeos curtos
* Passo a passo interativo
* Checklists
* Guias rápidos
* Artigos
* Perguntas frequentes
* Tours guiados
* Dicas contextuais

---

## 10.4 Onboarding inicial

Ao primeiro acesso, mostrar:

```txt
Bem-vindo ao FiscWise

Vamos organizar sua rotina em 3 passos:

1. Cadastre seu primeiro cliente
2. Crie uma obrigação fiscal
3. Envie ou solicite um documento
```

Com botão:

```txt
Começar tour
```

---

## 10.5 Tours guiados

Criar tours para:

```txt
Painel
Clientes
Agenda Fiscal
Documentos
Guias e DAS
Certificados
Financeiro
```

Exemplo:

```txt
Tour do Painel
1. Este é o Foco de Hoje
2. Aqui ficam seus clientes com maior risco
3. Aqui está sua agenda fiscal da semana
4. Use estas ações rápidas para cadastrar clientes e obrigações
```

---

## 10.6 Checklist de ativação

Criar um componente fixo no dashboard até o usuário completar:

```txt
Configure seu FiscWise

[ ] Complete seu perfil
[ ] Cadastre seu primeiro cliente
[ ] Adicione uma obrigação
[ ] Envie um documento
[ ] Configure um certificado
```

Quando completar:

```txt
Seu ambiente está pronto.
```

---

# 11. Bibliotecas recomendadas

## 11.1 Bibliotecas que o projeto já tem e devem continuar

Manter:

```txt
React
TypeScript
Vite
Tailwind
TanStack Query
Zustand
React Hook Form
Zod
Recharts
Framer Motion / Motion
Lucide React
```

---

## 11.2 Bibliotecas recomendadas para adicionar

### 1. shadcn/ui

Uso:

* Base para design system
* Componentes acessíveis
* Código copiável e customizável
* Integração natural com Tailwind

Adicionar componentes:

```txt
button
card
badge
input
select
dialog
sheet
dropdown-menu
command
popover
tabs
tooltip
table
calendar
separator
skeleton
alert
avatar
progress
accordion
```

Importante:

> Não usar shadcn/ui como visual genérico.
> Usar como base e personalizar totalmente para a identidade FiscWise.

---

### 2. Radix UI

Uso:

* Primitivos acessíveis
* Dialogs
* Dropdowns
* Tooltips
* Popovers
* Tabs
* Menus

Recomendação:

* Usar via shadcn/ui quando possível.
* Usar Radix diretamente apenas quando for necessário controle avançado.

---

### 3. TanStack Table

Uso:

* Tabelas profissionais
* Ordenação
* Filtros
* Paginação
* Seleção de linhas
* Colunas customizadas
* Controle total de markup

Aplicar em:

```txt
Clientes
Documentos
Obrigações
Guias
Certificados
Financeiro
```

---

### 4. Motion

O projeto já usa Framer Motion. Evoluir para uso mais organizado.

Criar:

```txt
src/lib/motion.ts
```

Com padrões reutilizáveis:

```txt
fadeIn
slideUp
staggerContainer
scaleIn
pageTransition
cardHover
modalMotion
```

Evitar animações duplicadas em cada arquivo.

---

### 5. cmdk

Uso:

* Command palette
* Busca global
* Ações rápidas

Atalho:

```txt
Ctrl + K
```

Comandos:

```txt
Buscar cliente
Criar obrigação
Enviar documento
Cadastrar certificado
Abrir Agenda Fiscal
Abrir Guias e DAS
Ir para Aprender
```

Isso dá sensação de produto avançado.

---

### 6. Sonner

Substituir ou evoluir o sistema de toast atual.

Uso:

* Feedback bonito
* Toasts com promessa
* Estados de carregamento
* Confirmações

Exemplos:

```txt
Cliente cadastrado com sucesso
Documento enviado para conferência
Obrigação marcada como concluída
Guia registrada como paga
```

---

### 7. Vaul

Uso:

* Drawers elegantes
* Detalhes de cliente
* Preview de documentos
* Criação rápida de obrigação
* Filtros avançados em mobile

Aplicar em:

```txt
ClientDetailsDrawer
CreateObligationDrawer
DocumentPreviewDrawer
AdvancedFiltersDrawer
```

---

### 8. Driver.js ou React Joyride

Recomendação principal:

```txt
Driver.js
```

Motivo:

* Ótimo para destacar áreas específicas
* Bom para tours contextuais
* Leve
* Pode funcionar em várias telas

Uso:

```txt
Tour do dashboard
Tour de clientes
Tour da agenda fiscal
Tour de documentos
```

Alternativa:

```txt
React Joyride
```

Usar se quiser controle mais React-first e fluxo totalmente controlado por estado.

---

### 9. Embla Carousel

Uso:

* Carrossel de tutoriais na aba Aprender
* Cards de novidades
* Dicas rápidas
* Onboarding inicial

---

### 10. Lottie React

Uso opcional:

* Empty states premium
* Login
* Sucesso de cadastro
* Upload concluído
* Onboarding

Cuidado:

* Não usar Lottie demais.
* Não usar animações infantis.
* Manter estilo institucional.

---

### 11. React Three Fiber

Uso opcional e experimental.

Aplicar apenas se houver maturidade técnica para manter performance.

Ideias:

* Radar fiscal no login
* Mapa visual abstrato de clientes
* Animação 3D sutil da marca

Recomendação:

> Não usar React Three Fiber no core do produto inicialmente.
> Começar com CSS + Motion.
> Só usar 3D se agregar valor visual sem pesar o carregamento.

---

## 11.3 Instalação sugerida

```bash
npm install @tanstack/react-table cmdk sonner vaul driver.js embla-carousel-react lottie-react
```

Se optar por React Joyride:

```bash
npm install react-joyride
```

Se optar por React Three Fiber futuramente:

```bash
npm install three @react-three/fiber @react-three/drei
```

---

# 12. Design system obrigatório

## 12.1 Criar estrutura

```txt
src/
  components/
    ui/
      button.tsx
      card.tsx
      badge.tsx
      input.tsx
      select.tsx
      dialog.tsx
      drawer.tsx
      table.tsx
      tooltip.tsx
      tabs.tsx
      command-menu.tsx
      empty-state.tsx
      loading-skeleton.tsx
      status-pill.tsx
      metric-card.tsx
      page-header.tsx
      section-card.tsx
      progress-ring.tsx
      fiscal-radar.tsx
```

---

## 12.2 Componentes específicos FiscWise

```txt
ClientRiskBadge
ObligationStatusPill
FiscalTimeline
DailyFocusCard
ClientAttentionList
DocumentDropzone
CertificateExpiryCard
GuideStatusCard
MonthlyClosingProgress
LearningCard
OnboardingChecklist
CommandCenter
```

---

## 12.3 Variantes de botão

```txt
primary
secondary
ghost
danger
warning
success
premium
outline
link
```

### Botão premium

Deve ter:

* Gradiente teal/blue
* Sombra suave
* Hover com elevação
* Active com leve compressão
* Loading integrado
* Ícone opcional

---

## 12.4 Badges

Variantes:

```txt
regular
attention
critical
pending
completed
overdue
paid
unpaid
expiring
```

---

## 12.5 Cards

Criar tipos:

```txt
MetricCard
ActionCard
RiskCard
LearningCard
DocumentCard
CertificateCard
ClientCard
```

---

# 13. Microinterações

## 13.1 Botões

Comportamento:

```txt
hover: translateY(-1px)
active: scale(0.98)
focus: ring teal
loading: spinner + texto
success: check curto
```

---

## 13.2 Cards

Comportamento:

```txt
hover: borda teal suave
hover: sombra premium
hover: ícone se move 2px
hover: botão contextual aparece
```

---

## 13.3 Tabelas

Comportamento:

```txt
hover row
selected row
ações aparecem no hover
status com cor clara
linhas compactas e legíveis
```

---

## 13.4 Inputs

Comportamento:

```txt
focus com borda primary
label claro
erro com mensagem humana
ícone contextual
validação sem agressividade
```

---

## 13.5 Modais e drawers

Comportamento:

```txt
backdrop blur
entrada com slide/scale
fechamento rápido
foco acessível
```

---

## 13.6 Empty states

Todo empty state deve vender ação.

### Ruim

```txt
Nenhum item encontrado.
```

### Bom

```txt
Você ainda não cadastrou clientes.
Cadastre seu primeiro cliente para começar a organizar sua rotina fiscal.
[Cadastrar cliente]
```

---

# 14. Arquitetura frontend recomendada

## 14.1 Problema a evitar

Páginas muito grandes com lógica, layout, dados, animação e renderização no mesmo arquivo.

---

## 14.2 Estrutura recomendada

```txt
src/
  app/
    routes.tsx
    providers.tsx

  components/
    ui/
    layout/
    shared/

  features/
    dashboard/
      components/
      hooks/
      types.ts
      utils.ts

    clients/
      components/
      hooks/
      schemas.ts
      types.ts
      utils.ts

    obligations/
    documents/
    certificates/
    guides/
    finance/
    learning/
    onboarding/

  lib/
    api/
    motion.ts
    routes.ts
    formatters.ts
    constants.ts
    queryKeys.ts

  styles/
    tokens.css
    animations.css
```

---

## 14.3 Refatorar DashboardPage

Quebrar em:

```txt
features/dashboard/
  DashboardPage.tsx
  components/
    DashboardHero.tsx
    DailyFocusCard.tsx
    MetricsGrid.tsx
    ClientAttentionList.tsx
    FiscalWeekTimeline.tsx
    PendingDocumentsCard.tsx
    MonthlyClosingCard.tsx
    PortfolioRiskCard.tsx
    QuickActions.tsx
```

---

## 14.4 Refatorar LoginPage

Quebrar em:

```txt
features/auth/
  LoginPage.tsx
  components/
    AuthLayout.tsx
    LoginForm.tsx
    LoginBrandPanel.tsx
    FiscalRadarAnimation.tsx
    FloatingMetricCards.tsx
    TwoFactorPanel.tsx
    OtpInput.tsx
```

---

## 14.5 Criar query keys centralizadas

```ts
export const queryKeys = {
  dashboard: ['dashboard'] as const,
  clients: {
    all: ['clients'] as const,
    detail: (id: string) => ['clients', id] as const,
  },
  obligations: {
    all: ['obligations'] as const,
    byClient: (clientId: string) => ['obligations', 'client', clientId] as const,
  },
};
```

---

# 15. Ajustes técnicos prioritários

## 15.1 Produto

* Remover linguagem de escritório do README, login e configurações.
* Renomear “Escritório” para “Minha conta” ou “Meu ambiente”.
* Remover protagonismo de admin/colaborador.
* Reposicionar `tenant` como ambiente isolado do contador.
* Manter arquitetura isolada, mas simplificar UX.

---

## 15.2 Frontend

* Padronizar componentes UI.
* Criar design tokens.
* Reduzir inline styles.
* Centralizar animações.
* Implementar command palette.
* Melhorar tabelas.
* Criar drawers.
* Criar empty states.
* Adicionar tours.
* Criar aba Aprender.
* Criar skeletons consistentes.
* Criar responsividade real mobile/tablet.

---

## 15.3 Backend

* Revisar nomenclatura de `Tenant` no produto.
* Manter tecnicamente se for útil, mas exibir como “ambiente”.
* Criar endpoints para onboarding.
* Criar endpoint para checklist inicial.
* Criar entidade de conteúdo de aprendizado futuramente.
* Criar status de tours concluídos.
* Criar preferências do usuário.
* Criar histórico de ações relevantes.

---

## 15.4 Segurança

* Garantir isolamento de dados.
* Garantir upload seguro.
* Validar tipo e tamanho de arquivo.
* Não expor documentos sem autorização.
* Logs de acesso a documentos.
* Proteção contra XSS.
* Sanitização de campos textuais.
* Rotas protegidas corretamente.
* Tokens seguros.
* CORS restrito em produção.

---

## 15.5 Performance

* Lazy loading de páginas.
* Dividir bundle.
* Evitar carregar animações pesadas no primeiro paint.
* Evitar Recharts em telas que não usam gráfico.
* Carregar Lottie sob demanda.
* Usar skeletons.
* Paginar tabelas.
* Usar debounce na busca.
* Virtualizar listas grandes futuramente.

---

# 16. Nova experiência de onboarding

## 16.1 Primeiro login

Fluxo:

```txt
1. Bem-vindo
2. Escolha seu perfil de atuação
3. Cadastre primeiro cliente
4. Escolha obrigações comuns
5. Configure lembretes
6. Abrir painel com tour
```

---

## 16.2 Perfil de atuação

Perguntar:

```txt
Que tipo de clientes você atende mais?

[ ] MEI
[ ] Simples Nacional
[ ] Lucro Presumido
[ ] Prestadores de serviço
[ ] Comércio
[ ] Clínicas
[ ] Autônomos
```

Isso ajuda o sistema a parecer inteligente.

---

## 16.3 Sugestões automáticas

Depois da escolha:

```txt
Para clientes do Simples Nacional, você pode acompanhar DAS, documentos mensais e fechamento da competência.
```

Sempre deixar claro que é sugestão, não regra fiscal definitiva.

---

# 17. Página Aprender: especificação

## 17.1 Rota

```txt
/aprender
```

---

## 17.2 Componentes

```txt
LearningPage
LearningHero
GettingStartedChecklist
LearningPathCard
TutorialCard
FeatureGuideCard
ReleaseNotesCard
HelpSearch
```

---

## 17.3 Conteúdos iniciais

```txt
Primeiros passos no FiscWise
Como cadastrar seu primeiro cliente
Como criar uma obrigação fiscal
Como organizar documentos por cliente
Como controlar certificados digitais
Como registrar guias e DAS
Como acompanhar seu financeiro
Como usar a calculadora fiscal
Como interpretar o Painel
```

---

## 17.4 Aprendizado contextual

Em cada página, adicionar botão:

```txt
Aprender sobre esta tela
```

Exemplo na Agenda Fiscal:

```txt
Entenda como usar a Agenda Fiscal para acompanhar prazos e obrigações dos seus clientes.
```

---

# 18. Funcionalidade única: Modo Foco

## 18.1 Conceito

Criar um recurso chamado:

```txt
Modo Foco
```

Objetivo:

Ajudar o contador a resolver pendências sem se perder no sistema.

---

## 18.2 Como funciona

O usuário clica:

```txt
Iniciar Modo Foco
```

O sistema mostra uma tarefa por vez:

```txt
1 de 6
Cliente: Padaria São Jorge
Pendência: DAS vence hoje
Ação sugerida: gerar guia ou marcar como concluída
```

Botões:

```txt
Resolver
Adiar
Marcar como aguardando cliente
Pular
```

---

## 18.3 Valor percebido

Isso diferencia o FiscWise de um CRUD comum.

O produto deixa de ser apenas cadastro e vira assistente de rotina.

---

# 19. Funcionalidade única: Score da Carteira

## 19.1 Conceito

Criar um indicador:

```txt
Saúde da Carteira
```

Pontuação de 0 a 100 baseada em:

* Obrigações atrasadas
* Clientes com documentos pendentes
* Certificados próximos do vencimento
* Guias vencidas
* Fechamentos em aberto
* Recebíveis atrasados

---

## 19.2 Visual

Card grande no dashboard:

```txt
Saúde da Carteira
82/100
Boa

3 pontos de atenção:
- 2 documentos pendentes
- 1 certificado vencendo
- 1 guia em aberto
```

---

# 20. Funcionalidade única: Linha do Tempo do Cliente

## 20.1 Conceito

Cada cliente deve ter uma timeline:

```txt
Hoje
Documento recebido

Ontem
Obrigação DAS concluída

12/05
Guia enviada ao cliente

10/05
Certificado cadastrado
```

---

## 20.2 Valor

Isso passa profissionalismo e reduz perda de informação.

---

# 21. Textos e copywriting

## 21.1 Dashboard

### Antes

```txt
Suas operações financeiras em tempo real, com total clareza e controle.
```

### Depois

```txt
Veja o que precisa da sua atenção hoje e mantenha seus clientes em dia.
```

---

## 21.2 Login

### Antes

```txt
Controle total da sua operação contábil.
```

### Depois

```txt
Controle sua carteira contábil com precisão.
```

---

## 21.3 Clientes

```txt
Organize sua carteira de clientes, acompanhe pendências e mantenha cada fechamento sob controle.
```

---

## 21.4 Agenda Fiscal

```txt
Acompanhe vencimentos, obrigações e tarefas fiscais por cliente e competência.
```

---

## 21.5 Documentos

```txt
Receba, organize e acompanhe documentos sem depender de conversas perdidas no WhatsApp.
```

---

## 21.6 Aprender

```txt
Aprenda a usar o FiscWise e organize sua rotina contábil passo a passo.
```

---

# 22. Roadmap de execução

## Fase 1 — Reposicionamento e visual

Prioridade máxima.

```txt
1. Atualizar README
2. Atualizar textos do login
3. Atualizar textos do dashboard
4. Renomear menus
5. Criar tokens visuais
6. Padronizar botões/cards/badges
7. Remover linguagem de escritório
8. Criar nova direção de marca
```

---

## Fase 2 — Login premium

```txt
1. Quebrar LoginPage em componentes
2. Criar LoginBrandPanel
3. Criar FloatingMetricCards
4. Criar FiscalRadarAnimation
5. Melhorar OTP
6. Criar microinterações
7. Melhorar copy
8. Melhorar responsividade
```

---

## Fase 3 — Dashboard cockpit

```txt
1. Quebrar DashboardPage em componentes
2. Criar DailyFocusCard
3. Criar ClientAttentionList
4. Criar FiscalWeekTimeline
5. Criar PortfolioRiskCard
6. Criar MonthlyClosingCard
7. Ajustar métricas
8. Remover painel por colaborador do MVP
```

---

## Fase 4 — Design system

```txt
1. Implantar shadcn/ui customizado
2. Criar Button com variantes
3. Criar Card premium
4. Criar Badge/StatusPill
5. Criar Drawer
6. Criar Table
7. Criar EmptyState
8. Criar Skeleton
9. Criar CommandMenu
```

---

## Fase 5 — Tabelas e drawers

```txt
1. Adicionar TanStack Table
2. Refatorar Clientes
3. Refatorar Documentos
4. Refatorar Obrigações
5. Criar ClientDetailsDrawer
6. Criar DocumentPreviewDrawer
7. Criar filtros avançados
```

---

## Fase 6 — Aprender e onboarding

```txt
1. Criar rota /aprender
2. Criar cards de tutorial
3. Criar checklist de primeiros passos
4. Adicionar Driver.js
5. Criar tours por página
6. Criar botões “Aprender sobre esta tela”
7. Criar central de ajuda contextual
```

---

## Fase 7 — Diferenciais

```txt
1. Criar Modo Foco
2. Criar Score da Carteira
3. Criar Timeline do Cliente
4. Criar templates de mensagem
5. Criar lembretes inteligentes
6. Criar relatórios simples por cliente
```

---

# 23. Arquivos que provavelmente precisam ser alterados

## Frontend

```txt
frontend/src/pages/LoginPage.tsx
frontend/src/pages/DashboardPage.tsx
frontend/src/components/Sidebar.tsx
frontend/src/components/Logo.tsx
frontend/src/index.css
frontend/src/App.tsx
frontend/src/lib/routes.ts, se existir
frontend/src/lib/hooks/useOperations.ts
frontend/src/components/ui/*
```

## Novos arquivos

```txt
frontend/src/features/auth/components/LoginBrandPanel.tsx
frontend/src/features/auth/components/FiscalRadarAnimation.tsx
frontend/src/features/auth/components/FloatingMetricCards.tsx
frontend/src/features/dashboard/components/DailyFocusCard.tsx
frontend/src/features/dashboard/components/ClientAttentionList.tsx
frontend/src/features/dashboard/components/FiscalWeekTimeline.tsx
frontend/src/features/dashboard/components/PortfolioRiskCard.tsx
frontend/src/features/learning/LearningPage.tsx
frontend/src/features/learning/components/LearningCard.tsx
frontend/src/features/onboarding/GuidedTourProvider.tsx
frontend/src/components/ui/command-menu.tsx
frontend/src/components/ui/drawer.tsx
frontend/src/components/ui/status-pill.tsx
frontend/src/lib/motion.ts
frontend/src/lib/queryKeys.ts
```

---

# 24. Padrões de qualidade exigidos

## 24.1 Visual

Nenhuma tela deve parecer inacabada.

Toda tela precisa ter:

* Título claro
* Subtítulo útil
* Ação principal
* Estado vazio
* Estado de loading
* Estado de erro
* Responsividade
* Animação sutil
* Ícones consistentes
* Espaçamento adequado

---

## 24.2 Código

Todo código novo deve:

* Ser tipado
* Ser componentizado
* Evitar duplicação
* Evitar inline style desnecessário
* Usar tokens visuais
* Usar componentes reutilizáveis
* Ter nomes claros
* Ser fácil de mover/refatorar

---

## 24.3 UX

Toda tela deve responder:

```txt
Onde estou?
O que posso fazer aqui?
O que exige minha atenção?
Qual é a próxima ação recomendada?
```

---

# 25. Critérios de sucesso

O redesign será considerado bem-sucedido quando:

```txt
[ ] O login causar boa primeira impressão
[ ] O dashboard mostrar prioridades reais
[ ] O produto falar com contador autônomo
[ ] O menu estiver claro
[ ] As telas tiverem unidade visual
[ ] Os botões e cards tiverem microinterações
[ ] O sistema tiver onboarding
[ ] A aba Aprender existir
[ ] O usuário souber o que fazer ao entrar
[ ] O FiscWise deixar de parecer genérico
[ ] O produto parecer vendável visualmente
```

---

# 26. Ordem exata recomendada para começar

Começar nesta ordem:

```txt
1. Corrigir posicionamento textual
2. Refatorar Sidebar
3. Criar tokens visuais
4. Criar Button/Card/Badge premium
5. Redesenhar Login
6. Redesenhar Dashboard
7. Criar aba Aprender
8. Adicionar tours guiados
9. Melhorar Clientes
10. Melhorar Agenda Fiscal
```

Não começar por integrações complexas.

O produto precisa primeiro parecer valioso, claro e profissional.

---

# 27. Princípio final

Toda decisão deve seguir esta frase:

> O FiscWise deve fazer um contador autônomo parecer mais organizado, mais profissional e mais confiante diante dos próprios clientes.

Se uma funcionalidade não ajuda nisso, ela não é prioridade agora.