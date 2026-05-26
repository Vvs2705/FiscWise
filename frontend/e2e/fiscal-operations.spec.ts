import { test, expect } from '@playwright/test';

test.describe('Foco de Hoje', () => {
  test.beforeEach(async ({ page }) => {
    // Simula sessão logada via localStorage
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('fiscwise_session', JSON.stringify({ user: { id: 'mock', email: 'test@fiscwise.com' } }));
    });
  });

  test('deve exibir items críticos', async ({ page }) => {
    await page.goto('/foco');
    await expect(page.getByText('Foco de Hoje')).toBeVisible();
    await expect(page.getByText('Crítico')).toBeVisible();
  });

  test('deve filtrar por grupo', async ({ page }) => {
    await page.goto('/foco');
    await page.getByRole('button', { name: /Hoje/ }).click();
    await expect(page.getByText('Vencem hoje')).toBeVisible();
  });

  test('deve pesquisar por cliente', async ({ page }) => {
    await page.goto('/foco');
    await page.getByPlaceholder(/Buscar/).fill('Tech Solutions');
    await expect(page.getByText('Tech Solutions Ltda')).toBeVisible();
  });
});

test.describe('Caixa Postal Fiscal', () => {
  test('deve exibir mensagens', async ({ page }) => {
    await page.goto('/caixa-postal-fiscal');
    await expect(page.getByText('Caixa Postal Fiscal')).toBeVisible();
    await expect(page.getByText('Intimação')).toBeVisible();
  });

  test('deve filtrar por risco', async ({ page }) => {
    await page.goto('/caixa-postal-fiscal');
    await page.selectOption('select', 'critical');
    // Deve mostrar apenas críticos
    await expect(page.getByText('Crítico')).toBeVisible();
  });

  test('deve abrir detalhe ao clicar na linha', async ({ page }) => {
    await page.goto('/caixa-postal-fiscal');
    await page.locator('tr').nth(1).click();
    await expect(page.getByText('MENSAGEM')).toBeVisible();
  });
});

test.describe('Fechamento Mensal', () => {
  test('deve listar fechamentos', async ({ page }) => {
    await page.goto('/fechamento');
    await expect(page.getByText('Fechamento Mensal')).toBeVisible();
    await expect(page.getByText('Tech Solutions')).toBeVisible();
  });

  test('deve navegar para detalhe', async ({ page }) => {
    await page.goto('/fechamento');
    await page.getByRole('link', { name: /Abrir/ }).first().click();
    await expect(page.getByText('Checklist')).toBeVisible();
  });

  test('deve marcar item do checklist como feito', async ({ page }) => {
    await page.goto('/fechamento/clos-001');
    const btn = page.getByRole('button', { name: /Marcar como feito/ }).first();
    await btn.click();
    await expect(page.getByText('Checklist atualizado')).toBeVisible();
  });
});

test.describe('Procurações', () => {
  test('deve listar procurações com alertas', async ({ page }) => {
    await page.goto('/procuracoes');
    await expect(page.getByText('Procurações')).toBeVisible();
    await expect(page.getByText('procuração')).toBeVisible();
  });

  test('deve filtrar por status', async ({ page }) => {
    await page.goto('/procuracoes');
    await page.selectOption('select', 'expired');
    await expect(page.getByText('Vencida')).toBeVisible();
  });
});

test.describe('Relatórios', () => {
  test('deve exibir relatórios operacionais', async ({ page }) => {
    await page.goto('/relatorios');
    await expect(page.getByText('Relatórios')).toBeVisible();
    await expect(page.getByText('Clientes por risco fiscal')).toBeVisible();
  });
});

test.describe('Portal do Cliente', () => {
  test('deve exibir preview do portal', async ({ page }) => {
    await page.goto('/portal');
    await expect(page.getByText('Portal do Cliente')).toBeVisible();
    await expect(page.getByText('Modo preview')).toBeVisible();
  });

  test('deve mostrar documentos pendentes', async ({ page }) => {
    await page.goto('/portal');
    await page.getByRole('button', { name: /Documentos/ }).click();
    await expect(page.getByText('Extrato bancário')).toBeVisible();
  });
});
