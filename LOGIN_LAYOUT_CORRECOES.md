# Correções Técnicas — Layout da Área de Login FiscWise

## 1. Contexto

A tela de login atual apresenta problemas de distribuição espacial entre a área informativa lateral e a área branca do formulário de autenticação.

O principal problema identificado é que o radar/gráfico da área lateral está sendo cortado ou ficando parcialmente oculto. Além disso, a faixa branca onde fica o login parece ocupar largura excessiva, comprimindo o conteúdo lateral e forçando scroll vertical em resoluções comuns de desktop/notebook.

---

## 2. Problemas Identificados

### 2.1 Radar cortado

O radar/gráfico localizado na área inferior/lateral da tela está sendo renderizado parcialmente cortado.

Possíveis causas técnicas:

- Container pai com altura insuficiente.
- Uso de `overflow: hidden` em algum wrapper ancestral.
- Altura fixa mal dimensionada.
- Área lateral comprimida pela largura excessiva da coluna branca.
- Ausência de `min-height`, `aspect-ratio` ou regras responsivas adequadas para o gráfico.
- Distribuição vertical com `gap`, `padding` ou cards consumindo mais espaço que a viewport permite.

---

### 2.2 Área branca do login larga demais

A coluna branca do formulário ocupa espaço horizontal excessivo, reduzindo a área disponível para os dados laterais.

Consequências:

- Conteúdo lateral fica comprimido.
- Radar perde área útil.
- Layout exige scroll vertical.
- Tela parece desequilibrada visualmente.
- A experiência em notebooks fica prejudicada.

---

### 2.3 Scroll vertical desnecessário em desktop

A tela de login deveria caber em uma viewport comum de desktop/notebook, especialmente em resoluções como:

- `1366x768`
- `1440x900`
- `1536x864`
- `1920x1080`

Atualmente, o conteúdo aparenta ultrapassar a altura disponível, causando scroll e corte visual.

---

## 3. Objetivo da Correção

Reorganizar o layout da tela de login para que:

- O radar fique 100% visível.
- A tela caiba sem scroll vertical em desktops comuns.
- A área branca do login seja reduzida moderadamente.
- O formulário continue confortável, legível e premium.
- A área lateral tenha mais espaço para dados, cards e gráfico.
- O layout não fique achatado, espremido ou visualmente pobre.

---

## 4. Direção Técnica Recomendada

### 4.1 Usar layout em grid no desktop

A tela principal deve ser estruturada como um grid de duas colunas:

- Coluna esquerda: área institucional, dados, indicadores e radar.
- Coluna direita: área branca com o formulário de login.

Recomendação:

```css
.login-page {
  min-height: 100dvh;
  display: grid;
  grid-template-columns: minmax(620px, 1fr) minmax(420px, 520px);
  overflow: hidden;
}
```

### Explicação

* A coluna esquerda recebe a maior parte do espaço disponível.
* A coluna direita fica limitada entre `420px` e `520px`.
* Isso evita que a área branca ocupe largura exagerada.
* O uso de `100dvh` melhora o comportamento em navegadores modernos.

---

## 5. Ajuste da Área Branca do Login

### 5.1 Reduzir largura máxima

Evitar valores excessivos como `600px`, `640px`, `45vw` or `50vw` para a área branca.

Recomendação:

```css
.login-panel {
  width: 100%;
  max-width: 520px;
  min-width: 420px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(32px, 4vw, 56px);
}
```

### 5.2 Formulário interno

O formulário pode manter boa leitura sem ocupar toda a largura da coluna branca.

```css
.login-card {
  width: 100%;
  max-width: 400px;
}
```

### Resultado esperado

A área branca ficará mais compacta, mas o formulário continuará confortável.

---

## 6. Ajuste da Área Lateral

A área lateral deve ganhar mais espaço horizontal e melhor controle vertical.

```css
.login-hero {
  min-width: 0;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: clamp(32px, 4vw, 64px);
  overflow: hidden;
}
```

### Observações

* `min-width: 0` evita que filhos estourem o grid.
* `justify-content: space-between` ajuda a distribuir topo, meio e rodapé.
* `overflow: hidden` só deve ser usado se os filhos internos estiverem dimensionados corretamente.
* Não aplicar `overflow: hidden` diretamente no container do radar se isso estiver causando corte.

---

## 7. Correção do Radar/Gráfico

O radar precisa de um container próprio com altura controlada e proporção preservada.

```css
.radar-section {
  width: 100%;
  min-height: 240px;
  max-height: 340px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: visible;
}

.radar-chart {
  width: min(100%, 420px);
  aspect-ratio: 1 / 1;
  max-height: 320px;
}
```

Caso o radar seja renderizado via `canvas`, `svg`, `recharts`, `apexcharts`, `chart.js` ou similar, garantir que o componente respeite o tamanho do container.

Exemplo:

```tsx
<div className="radar-section">
  <div className="radar-chart">
    <ResponsiveContainer width="100%" height="100%">
      {/* RadarChart aqui */}
    </ResponsiveContainer>
  </div>
</div>
```

---

## 8. Evitar Corte por `overflow`

Verificar todos os ancestrais do radar.

Procurar por regras como:

```css
overflow: hidden;
height: 100%;
max-height: ...
position: absolute;
```

Caso o radar esteja sendo cortado, revisar especialmente:

```css
.hero-content
.hero-bottom
.metrics-wrapper
.radar-wrapper
.chart-container
```

O container direto do radar deve preferencialmente usar:

```css
overflow: visible;
```

ou ter altura suficiente para o gráfico completo.

---

## 9. Ajuste Para Viewports Baixas

Em notebooks com altura reduzida, como `1366x768`, aplicar modo compacto sem comprometer a leitura.

```css
@media (min-width: 1024px) and (max-height: 820px) {
  .login-hero {
    padding-block: 28px;
    gap: 20px;
  }

  .hero-title {
    font-size: clamp(32px, 3vw, 44px);
    line-height: 1.05;
  }

  .hero-description {
    font-size: 15px;
    line-height: 1.45;
    max-width: 640px;
  }

  .metrics-grid {
    gap: 12px;
  }

  .metric-card {
    padding: 14px 16px;
  }

  .radar-section {
    min-height: 220px;
    max-height: 280px;
  }

  .radar-chart {
    max-height: 260px;
  }

  .login-panel {
    padding-block: 32px;
  }
}
```

### Importante

Não resolver o problem usando apenas:

```css
transform: scale(0.8);
zoom: 0.8;
font-size muito pequeno;
```

Essas soluções prejudicam acessibilidade, legibilidade e qualidade visual.

---

## 10. Breakpoints Recomendados

### Desktop grande

```css
@media (min-width: 1600px) {
  .login-page {
    grid-template-columns: minmax(760px, 1fr) minmax(460px, 540px);
  }
}
```

### Desktop/notebook padrão

```css
@media (min-width: 1024px) and (max-width: 1599px) {
  .login-page {
    grid-template-columns: minmax(600px, 1fr) minmax(420px, 500px);
  }
}
```

### Tablet e mobile

Em telas menores, o layout deve virar uma coluna única.

```css
@media (max-width: 1023px) {
  .login-page {
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
    overflow: auto;
  }

  .login-hero {
    min-height: auto;
    padding: 32px 24px;
  }

  .login-panel {
    min-width: 0;
    max-width: none;
    width: 100%;
    padding: 32px 24px;
  }

  .login-card {
    max-width: 440px;
    margin: 0 auto;
  }

  .radar-section {
    min-height: 220px;
  }
}
```

---

## 11. Estrutura HTML/JSX Recomendada

```tsx
<main className="login-page">
  <section className="login-hero" aria-label="Resumo da plataforma FiscWise">
    <div className="hero-top">
      <Logo />
      <h1 className="hero-title">
        Gestão contábil inteligente em uma única plataforma
      </h1>
      <p className="hero-description">
        Controle clientes, documentos, certificados digitais, prazos fiscais e financeiro com mais clareza.
      </p>
    </div>

    <div className="metrics-grid">
      <MetricCard label="Clientes ativos" value="..." />
      <MetricCard label="Documentos processados" value="..." />
      <MetricCard label="Prazos monitorados" value="..." />
    </div>

    <div className="radar-section">
      <div className="radar-chart">
        <RadarComponent />
      </div>
    </div>
  </section>

  <aside className="login-panel" aria-label="Acesso à conta">
    <div className="login-card">
      <h2>Entrar na FiscWise</h2>

      <form>
        <label htmlFor="email">E-mail</label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="username"
          inputMode="email"
          required
        />

        <label htmlFor="password">Senha</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
        />

        <button type="submit">
          Entrar
        </button>
      </form>
    </div>
  </aside>
</main>
```

---

## 12. Checklist de Implementação

### Layout

* [ ] Reduzir largura máxima da área branca.
* [ ] Garantir `max-width` entre `500px` e `520px` para a coluna de login.
* [ ] Aumentar área útil da coluna esquerda.
* [ ] Usar `grid-template-columns` com proporção mais favorável à lateral.
* [ ] Evitar que a coluna branca ocupe metade da tela em desktop.

### Radar

* [ ] Garantir que o radar tenha container próprio.
* [ ] Definir `aspect-ratio: 1 / 1`.
* [ ] Remover ou ajustar `overflow: hidden` que esteja cortando o gráfico.
* [ ] Testar radar em `1366x768`.
* [ ] Testar radar em `1440x900`.
* [ ] Testar radar em `1536x864`.
* [ ] Testar radar em `1920x1080`.

### Responsividade

* [ ] Desktop sem scroll vertical.
* [ ] Notebook baixo com modo compacto.
* [ ] Tablet/mobile em coluna única.
* [ ] Formulário sem ficar estreito.
* [ ] Radar sem achatamento.

### UX

* [ ] Login visualmente confortável.
* [ ] Hierarquia clara entre título, descrição, métricas e radar.
* [ ] Não reduzir fontes abaixo de tamanho confortável.
* [ ] Não usar `zoom` ou `transform: scale()` como solução principal.
* [ ] Manter aparência premium.

---

## 13. Critérios de Aceite

A correção será considerada aprovada quando:

1. A tela de login abrir sem scroll vertical em desktop comum.
2. O radar estiver completamente visível.
3. A área branca do login estiver menor e melhor proporcionalmente.
4. O formulário continuar legível, confortável e centralizado.
5. Nenhum conteúdo lateral estiver cortado.
6. A tela funcionar bem em `1366x768`, `1440x900`, `1536x864` e `1920x1080`.
7. O layout mobile continuar funcional.
8. Não houver uso de soluções artificiais como `zoom`, `scale` global ou fontes excessivamente pequenas.

---

## 14. Resumo Técnico da Solução

A solução não deve simplesmente diminuir elementos aleatoriamente.

O adjustment correto é redistribuir o espaço da tela:

* Menos largura para a área branca.
* Mais área útil para a lateral informativa.
* Radar com container responsivo e proporção preservada.
* Layout controlado por grid.
* Ajustes específicos para telas com pouca altura.
* Sem cortes, sem scroll desnecessário e sem perda de legibilidade.
