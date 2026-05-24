import { useState, useMemo, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Calculator,
  ChevronDown,
  TrendingDown,
  TrendingUp,
  AlertCircle,
  Save,
  RotateCcw,
  Copy,
  Upload,
} from 'lucide-react';
import readXlsxFile from 'read-excel-file';
import toast from 'react-hot-toast';
import { api } from '@/lib/api';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MONTH_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'] as const;

interface AnexoFaixa {
  limite: number;
  aliquota: number;
  deducao: number;
}

const ANEXO_III: AnexoFaixa[] = [
  { limite: 180_000, aliquota: 0.06, deducao: 0 },
  { limite: 360_000, aliquota: 0.112, deducao: 9_360 },
  { limite: 720_000, aliquota: 0.135, deducao: 17_640 },
  { limite: 1_800_000, aliquota: 0.16, deducao: 35_640 },
  { limite: 3_600_000, aliquota: 0.21, deducao: 125_640 },
  { limite: 4_800_000, aliquota: 0.33, deducao: 648_000 },
];

const ANEXO_V: AnexoFaixa[] = [
  { limite: 180_000, aliquota: 0.155, deducao: 0 },
  { limite: 360_000, aliquota: 0.18, deducao: 4_500 },
  { limite: 720_000, aliquota: 0.195, deducao: 9_900 },
  { limite: 1_800_000, aliquota: 0.205, deducao: 17_100 },
  { limite: 3_600_000, aliquota: 0.23, deducao: 62_100 },
  { limite: 4_800_000, aliquota: 0.305, deducao: 540_000 },
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface MonthRow {
  receita: number;
  proLabore: number;
  inssProLabore: number;
  irrfProLabore: number;
  salarioFuncionarios: number;
  inssFuncionarios: number;
  irrfFuncionarios: number;
  fgts: number;
  outros: number;
}


interface MonthDAS {
  mes: string;
  receita: number;
  aliquotaEfetiva: number;
  das: number;
}

interface CalcResult {
  rbt12: number;
  folha12m: number;
  fatorR: number;
  anexo: 'III' | 'V';
  aliquotaEfetiva: number;
  monthlyDAS: MonthDAS[];
  totalDAS: number;
  // comparison with the other annex
  otherAnexo: 'III' | 'V';
  otherAliquotaEfetiva: number;
  otherMonthlyDAS: MonthDAS[];
  otherTotalDAS: number;
  savings: number; // positive = current is cheaper, negative = would save switching
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function moneyBRL(value: number): string {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

function pctBR(value: number, decimals = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

const COL_HEADER_MAP: { [key in keyof MonthRow]: string[] } = {
  receita: ['receita', 'faturamento', 'receitas', 'revenue'],
  proLabore: ['pró-labore', 'pro-labore', 'pro_labore', 'pro labore', 'pró labore'],
  inssProLabore: ['inss pró-labore', 'inss pro-labore', 'inss pro_labore', 'inss pró labore', 'inss pro labore', 'inss p.l.', 'inss pl'],
  irrfProLabore: ['irrf pró-labore', 'irrf pro-labore', 'irrf pro_labore', 'irrf pró labore', 'irrf pro labore', 'irrf p.l.', 'irrf pl'],
  salarioFuncionarios: ['salário funcionários', 'salario funcionarios', 'salários', 'salarios', 'salário func.', 'salario func', 'folha salarios', 'employee salary'],
  inssFuncionarios: ['inss funcionários', 'inss funcionarios', 'inss func', 'inss empregados', 'inss employee'],
  irrfFuncionarios: ['irrf funcionários', 'irrf funcionarios', 'irrf func', 'irrf empregados', 'irrf employee'],
  fgts: ['fgts', 'fgts funcionários', 'fgts funcionarios', 'fgts func'],
  outros: ['outros', 'outras despesas', 'outros custos', 'other'],
};

function matchHeader(header: string, aliases: string[]): boolean {
  if (!header) return false;
  const normalized = header.toString().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
  return aliases.some(alias => {
    const normAlias = alias.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim();
    return normalized === normAlias || normalized.includes(normAlias);
  });
}

function parseMonthIndex(cell: unknown): number | null {
  if (!cell) return null;
  if (cell instanceof Date) {
    return cell.getMonth();
  }
  const str = String(cell).toLowerCase().trim();
  const monthAbbrs = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const monthFull = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
  
  const num = parseInt(str, 10);
  if (!isNaN(num) && num >= 1 && num <= 12) {
    return num - 1;
  }
  
  for (let i = 0; i < 12; i++) {
    if (str.startsWith(monthAbbrs[i]) || str.startsWith(monthFull[i])) {
      return i;
    }
  }
  return null;
}

function formatBRL(val: number): string {
  if (val === 0) return '';
  return val.toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function parseCurrencyString(str: string): number {
  const digits = str.replace(/\D/g, '');
  if (!digits) return 0;
  return parseFloat(digits) / 100;
}

function emptyRow(): MonthRow {
  return {
    receita: 0,
    proLabore: 0,
    inssProLabore: 0,
    irrfProLabore: 0,
    salarioFuncionarios: 0,
    inssFuncionarios: 0,
    irrfFuncionarios: 0,
    fgts: 0,
    outros: 0,
  };
}

function totalFolha(row: MonthRow): number {
  return (
    row.proLabore +
    row.inssProLabore +
    row.irrfProLabore +
    row.salarioFuncionarios +
    row.inssFuncionarios +
    row.irrfFuncionarios +
    row.fgts +
    row.outros
  );
}

function findFaixa(rbt12: number, tabela: AnexoFaixa[]): AnexoFaixa {
  for (const faixa of tabela) {
    if (rbt12 <= faixa.limite) return faixa;
  }
  return tabela[tabela.length - 1];
}

function calcAliquotaEfetiva(rbt12: number, tabela: AnexoFaixa[]): number {
  if (rbt12 <= 0) return 0;
  const faixa = findFaixa(rbt12, tabela);
  return (rbt12 * faixa.aliquota - faixa.deducao) / rbt12;
}

function calcMonthlyDAS(
  rows: MonthRow[],
  aliquotaEfetiva: number,
): MonthDAS[] {
  return rows.map((row, i) => ({
    mes: MONTH_LABELS[i],
    receita: row.receita,
    aliquotaEfetiva,
    das: row.receita * aliquotaEfetiva,
  }));
}

function computeResult(rows: MonthRow[]): CalcResult | null {
  const rbt12 = rows.reduce((sum, r) => sum + r.receita, 0);
  if (rbt12 <= 0) return null;

  const folha12m = rows.reduce((sum, r) => sum + totalFolha(r), 0);
  const fatorR = folha12m / rbt12;
  const anexo: 'III' | 'V' = fatorR >= 0.28 ? 'III' : 'V';
  const otherAnexo: 'III' | 'V' = anexo === 'III' ? 'V' : 'III';

  const tabela = anexo === 'III' ? ANEXO_III : ANEXO_V;
  const otherTabela = anexo === 'III' ? ANEXO_V : ANEXO_III;

  const aliquotaEfetiva = calcAliquotaEfetiva(rbt12, tabela);
  const otherAliquotaEfetiva = calcAliquotaEfetiva(rbt12, otherTabela);

  const monthlyDAS = calcMonthlyDAS(rows, aliquotaEfetiva);
  const otherMonthlyDAS = calcMonthlyDAS(rows, otherAliquotaEfetiva);

  const totalDAS = monthlyDAS.reduce((s, m) => s + m.das, 0);
  const otherTotalDAS = otherMonthlyDAS.reduce((s, m) => s + m.das, 0);

  return {
    rbt12,
    folha12m,
    fatorR,
    anexo,
    aliquotaEfetiva,
    monthlyDAS,
    totalDAS,
    otherAnexo,
    otherAliquotaEfetiva,
    otherMonthlyDAS,
    otherTotalDAS,
    savings: otherTotalDAS - totalDAS,
  };
}

// ---------------------------------------------------------------------------
// Column header config
// ---------------------------------------------------------------------------

const INPUT_COLUMNS: { key: keyof MonthRow; label: string }[] = [
  { key: 'receita', label: 'Receita (R$)' },
  { key: 'proLabore', label: 'Pró-labore (R$)' },
  { key: 'inssProLabore', label: 'INSS Pró-labore (R$)' },
  { key: 'irrfProLabore', label: 'IRRF Pró-labore (R$)' },
  { key: 'salarioFuncionarios', label: 'Salário Func. (R$)' },
  { key: 'inssFuncionarios', label: 'INSS Func. (R$)' },
  { key: 'irrfFuncionarios', label: 'IRRF Func. (R$)' },
  { key: 'fgts', label: 'FGTS (R$)' },
  { key: 'outros', label: 'Outros (R$)' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function FatorRCalculator() {
  const [rows, setRows] = useState<MonthRow[]>(() =>
    Array.from({ length: 12 }, () => emptyRow()),
  );

  const [templateRow, setTemplateRow] = useState<MonthRow>(emptyRow);
  const [showApplyAll, setShowApplyAll] = useState(false);
  const [calculated, setCalculated] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // ---- derived result (client-side, instant) ----
  const result = useMemo<CalcResult | null>(() => {
    if (!calculated) return null;
    return computeResult(rows);
  }, [rows, calculated]);

  // ---- handlers ----
  const updateCell = useCallback(
    (monthIdx: number, field: keyof MonthRow, raw: string) => {
      const value = parseCurrencyString(raw);
      setRows((prev) => {
        const next = [...prev];
        next[monthIdx] = { ...next[monthIdx], [field]: value };
        return next;
      });
      // live-update result if already calculated
      // (result recalculates via useMemo)
    },
    [],
  );

  const updateTemplateCell = useCallback(
    (field: keyof MonthRow, raw: string) => {
      const value = parseCurrencyString(raw);
      setTemplateRow((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const applyToAll = useCallback(() => {
    setRows(Array.from({ length: 12 }, () => ({ ...templateRow })));
  }, [templateRow]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleImportExcel = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reset value so selection of same file fires change event again
    e.target.value = '';

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'xlsx') {
      toast.error('Arquivo inválido. Por favor, selecione um arquivo .xlsx.');
      return;
    }

    const toastId = toast.loading('Lendo planilha...');

    try {
      let excelRows;
      try {
        excelRows = await readXlsxFile(file, { sheet: 'Lancamentos' });
      } catch {
        excelRows = await readXlsxFile(file);
      }

      if (!excelRows || excelRows.length < 2) {
        toast.error('Nenhum dado encontrado na planilha.', { id: toastId });
        return;
      }

      const headers = excelRows[0].map(h => String(h || '').trim());
      const headerIndexes: { [key in keyof MonthRow]?: number } = {};
      let monthColIdx = 0;

      headers.forEach((header, idx) => {
        const headerNorm = header.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        if (headerNorm === 'mes' || headerNorm === 'ms' || headerNorm === 'month') {
          monthColIdx = idx;
          return;
        }

        for (const [field, aliases] of Object.entries(COL_HEADER_MAP)) {
          if (matchHeader(header, aliases)) {
            headerIndexes[field as keyof MonthRow] = idx;
          }
        }
      });

      const newRows: MonthRow[] = Array.from({ length: 12 }, () => emptyRow());
      let parsedCount = 0;

      for (let i = 1; i < excelRows.length; i++) {
        const rowData = excelRows[i];
        if (!rowData || rowData.length === 0) continue;

        const firstColVal = String(rowData[monthColIdx] || '').trim();
        const firstColNorm = firstColVal.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '');
        if (
          !firstColVal ||
          firstColNorm.includes('rbt12') ||
          firstColNorm.includes('folha') ||
          firstColNorm.includes('total') ||
          firstColNorm.includes('fator r') ||
          firstColNorm.includes('anexo')
        ) {
          continue;
        }

        const monthIdx = parseMonthIndex(rowData[monthColIdx]);
        if (monthIdx === null || monthIdx < 0 || monthIdx > 11) {
          continue;
        }

        const newRow: MonthRow = emptyRow();
        let hasValues = false;

        for (const [field, colIdx] of Object.entries(headerIndexes)) {
          if (colIdx !== undefined && colIdx < rowData.length) {
            const rawVal = rowData[colIdx];
            const parsedVal = typeof rawVal === 'number' ? rawVal : parseFloat(String(rawVal || '')) || 0;
            newRow[field as keyof MonthRow] = Math.max(0, parsedVal);
            if (parsedVal > 0) hasValues = true;
          }
        }

        if (hasValues) {
          newRows[monthIdx] = newRow;
          parsedCount++;
        }
      }

      if (parsedCount === 0) {
        toast.error('Nenhum dado mensal de faturamento ou folha pôde ser extraído.', { id: toastId });
        return;
      }

      setRows(newRows);
      setCalculated(true);
      toast.success(`Planilha importada com sucesso! (${parsedCount} meses preenchidos)`, { id: toastId });
    } catch (err) {
      console.error(err);
      toast.error('Erro ao ler planilha. Verifique se o formato está correto.', { id: toastId });
    }
  };

  const handleCalculate = () => {
    setCalculated(true);
  };

  const handleReset = () => {
    setRows(Array.from({ length: 12 }, () => emptyRow()));
    setTemplateRow(emptyRow());
    setCalculated(false);
    setSaveSuccess(false);
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!result) return;
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      await api.post('/api/v1/calculator/simulate-fator-r', {
        months: rows.map((r, i) => ({
          month: MONTH_LABELS[i],
          revenue: r.receita,
          pro_labore: r.proLabore,
          inss_pro_labore: r.inssProLabore,
          irrf_pro_labore: r.irrfProLabore,
          employee_salary: r.salarioFuncionarios,
          inss_employees: r.inssFuncionarios,
          irrf_employees: r.irrfFuncionarios,
          fgts: r.fgts,
          other: r.outros,
        })),
        title: `Fator R — ${pctBR(result.fatorR)} (Anexo ${result.anexo})`,
      });
      setSaveSuccess(true);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: unknown } } };
      const msg =
        error?.response?.data?.detail ||
        'Erro ao salvar simulação. Tente novamente.';
      setSaveError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSaving(false);
    }
  };

  const handleCopy = () => {
    if (!result) return;
    const lines = [
      `Fator R: ${pctBR(result.fatorR)}`,
      `Anexo: ${result.anexo}`,
      `RBT12: ${moneyBRL(result.rbt12)}`,
      `Folha 12M: ${moneyBRL(result.folha12m)}`,
      `Alíquota Efetiva: ${pctBR(result.aliquotaEfetiva)}`,
      `DAS Anual: ${moneyBRL(result.totalDAS)}`,
      '',
      'Mês | Receita | Alíq. Efetiva | DAS',
      ...result.monthlyDAS.map(
        (m) =>
          `${m.mes} | ${moneyBRL(m.receita)} | ${pctBR(m.aliquotaEfetiva)} | ${moneyBRL(m.das)}`,
      ),
    ];
    navigator.clipboard.writeText(lines.join('\n'));
  };

  // ---- optimisation tip ----
  const showOptTip =
    result && result.fatorR >= 0.2 && result.fatorR <= 0.35;

  // ---- render ----
  return (
    <div className="space-y-6">
      {/* ---------- Apply-all toggle ---------- */}
      <div className="rounded-xl border border-border bg-card p-4">
        <button
          type="button"
          onClick={() => setShowApplyAll((v) => !v)}
          className="flex w-full items-center justify-between text-sm font-semibold text-foreground"
        >
          <span className="flex items-center gap-2">
            <Copy className="h-4 w-4 text-muted-foreground" />
            Aplicar a todos os meses
          </span>
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform ${
              showApplyAll ? 'rotate-180' : ''
            }`}
          />
        </button>

        <AnimatePresence>
          {showApplyAll && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
                {INPUT_COLUMNS.map((col) => (
                  <div key={col.key}>
                    <label className="mb-1 block text-xs text-muted-foreground">
                      {col.label}
                    </label>
                    <div className="relative">
                      <span className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground">
                        R$
                      </span>
                      <input
                        type="text"
                        placeholder="0,00"
                        value={templateRow[col.key] ? formatBRL(templateRow[col.key]) : ''}
                        onChange={(e) =>
                          updateTemplateCell(col.key, e.target.value)
                        }
                        className="w-full rounded border border-input bg-background pl-7 pr-2 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40"
                      />
                    </div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                onClick={applyToAll}
                className="mt-3 rounded-lg bg-primary/10 px-4 py-1.5 text-xs font-semibold text-primary hover:bg-primary/20 transition"
              >
                Aplicar valores a todos os 12 meses
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* ---------- Spreadsheet table ---------- */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] text-xs">
            <thead>
              <tr className="bg-muted/50 text-muted-foreground">
                <th className="sticky left-0 z-10 bg-muted/50 px-2 py-2 text-left font-semibold whitespace-nowrap">
                  Mês
                </th>
                {INPUT_COLUMNS.map((col) => (
                  <th
                    key={col.key}
                    className="px-2 py-2 text-right font-semibold whitespace-nowrap"
                  >
                    {col.label}
                  </th>
                ))}
                <th className="px-2 py-2 text-right font-semibold whitespace-nowrap">
                  Total Folha (R$)
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr
                  key={idx}
                  className="border-t border-border/50 hover:bg-muted/20 transition-colors"
                >
                  <td className="sticky left-0 z-10 bg-card px-2 py-1.5 font-medium text-foreground whitespace-nowrap">
                    {MONTH_LABELS[idx]}
                  </td>
                  {INPUT_COLUMNS.map((col) => (
                    <td key={col.key} className="px-1 py-1">
                      <div className="relative">
                        <span className="pointer-events-none absolute left-1.5 top-1/2 -translate-y-1/2 text-[10px] text-muted-foreground">
                          R$
                        </span>
                        <input
                          type="text"
                          placeholder="0,00"
                          value={row[col.key] ? formatBRL(row[col.key]) : ''}
                          onChange={(e) =>
                            updateCell(idx, col.key, e.target.value)
                          }
                          className="w-full min-w-[90px] rounded border border-input bg-background pl-6 pr-1 py-1 text-xs text-right text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/40"
                        />
                      </div>
                    </td>
                  ))}
                  <td className="px-2 py-1.5 text-right font-semibold text-foreground whitespace-nowrap">
                    {moneyBRL(totalFolha(row))}
                  </td>
                </tr>
              ))}
            </tbody>
            {/* Totals row */}
            <tfoot>
              <tr className="border-t-2 border-border bg-muted/30 font-semibold text-foreground">
                <td className="sticky left-0 z-10 bg-muted/30 px-2 py-2">
                  Total
                </td>
                {INPUT_COLUMNS.map((col) => (
                  <td key={col.key} className="px-2 py-2 text-right">
                    {moneyBRL(rows.reduce((s, r) => s + r[col.key], 0))}
                  </td>
                ))}
                <td className="px-2 py-2 text-right">
                  {moneyBRL(rows.reduce((s, r) => s + totalFolha(r), 0))}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* ---------- Action buttons ---------- */}
      <div className="flex flex-wrap gap-3">
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleImportExcel}
          accept=".xlsx"
          className="hidden"
        />
        <button
          type="button"
          onClick={handleCalculate}
          className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 transition-all"
        >
          <Calculator className="h-4 w-4" />
          Calcular Fator R
        </button>
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="flex items-center gap-2 rounded-lg border border-border bg-card px-5 py-2.5 text-sm font-semibold text-foreground hover:bg-muted/50 transition-all"
        >
          <Upload className="h-4 w-4" />
          Importar Planilha
        </button>
        <button
          type="button"
          onClick={handleReset}
          className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted/50 transition"
        >
          <RotateCcw className="h-4 w-4" />
          Limpar
        </button>
      </div>

      {/* ---------- Results ---------- */}
      <AnimatePresence>
        {result && (
          <motion.div
            key="fator-r-results"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.4 }}
            className="space-y-5"
          >
            <h3 className="text-sm font-semibold uppercase tracking-widest text-muted-foreground">
              Resultado do Fator R
            </h3>

            {/* Summary cards */}
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
              {/* RBT12 */}
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  RBT12
                </p>
                <p className="text-lg font-bold text-foreground">
                  {moneyBRL(result.rbt12)}
                </p>
              </div>

              {/* Folha 12M */}
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Folha 12M
                </p>
                <p className="text-lg font-bold text-foreground">
                  {moneyBRL(result.folha12m)}
                </p>
              </div>

              {/* Fator R */}
              <div className="rounded-xl border border-border bg-card p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Fator R
                </p>
                <p
                  className={`text-lg font-bold ${
                    result.fatorR >= 0.28
                      ? 'text-emerald-500'
                      : 'text-red-500'
                  }`}
                >
                  {pctBR(result.fatorR)}
                </p>
              </div>

              {/* Anexo */}
              <div
                className={`rounded-xl border p-4 ${
                  result.anexo === 'III'
                    ? 'border-emerald-500/40 bg-emerald-500/5'
                    : 'border-red-500/40 bg-red-500/5'
                }`}
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
                  Anexo Determinado
                </p>
                <p
                  className={`text-lg font-bold ${
                    result.anexo === 'III'
                      ? 'text-emerald-500'
                      : 'text-red-500'
                  }`}
                >
                  Anexo {result.anexo}
                </p>
                <p className="text-[11px] text-muted-foreground mt-1">
                  {result.anexo === 'III'
                    ? 'Fator R ≥ 28% — alíquotas reduzidas'
                    : 'Fator R < 28% — alíquotas mais altas'}
                </p>
              </div>
            </div>

            {/* Monthly DAS table */}
            <div className="rounded-xl border border-border bg-card overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-muted/50 text-muted-foreground">
                      <th className="px-3 py-2 text-left font-semibold">
                        Mês
                      </th>
                      <th className="px-3 py-2 text-right font-semibold">
                        Receita
                      </th>
                      <th className="px-3 py-2 text-right font-semibold">
                        Alíq. Efetiva
                      </th>
                      <th className="px-3 py-2 text-right font-semibold">
                        DAS
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.monthlyDAS.map((m) => (
                      <tr
                        key={m.mes}
                        className="border-t border-border/50 hover:bg-muted/20 transition-colors"
                      >
                        <td className="px-3 py-1.5 font-medium text-foreground">
                          {m.mes}
                        </td>
                        <td className="px-3 py-1.5 text-right text-foreground">
                          {moneyBRL(m.receita)}
                        </td>
                        <td className="px-3 py-1.5 text-right text-foreground">
                          {pctBR(m.aliquotaEfetiva)}
                        </td>
                        <td className="px-3 py-1.5 text-right font-semibold text-foreground">
                          {moneyBRL(m.das)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                  <tfoot>
                    <tr className="border-t-2 border-border bg-muted/30 font-bold text-foreground">
                      <td className="px-3 py-2" colSpan={3}>
                        Total DAS Anual
                      </td>
                      <td className="px-3 py-2 text-right">
                        {moneyBRL(result.totalDAS)}
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            </div>

            {/* Comparison */}
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="rounded-xl border border-border bg-card p-5"
            >
              <h4 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                {result.savings > 0 ? (
                  <TrendingDown className="h-4 w-4 text-emerald-500" />
                ) : (
                  <TrendingUp className="h-4 w-4 text-red-500" />
                )}
                Comparação com Anexo {result.otherAnexo}
              </h4>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    DAS anual no Anexo {result.anexo} (atual)
                  </p>
                  <p className="text-lg font-bold text-foreground">
                    {moneyBRL(result.totalDAS)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Alíq. efetiva: {pctBR(result.aliquotaEfetiva)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">
                    DAS anual no Anexo {result.otherAnexo}
                  </p>
                  <p className="text-lg font-bold text-foreground">
                    {moneyBRL(result.otherTotalDAS)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Alíq. efetiva: {pctBR(result.otherAliquotaEfetiva)}
                  </p>
                </div>
              </div>

              <div
                className={`mt-4 flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold ${
                  result.savings > 0
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                    : 'bg-red-500/10 text-red-600 dark:text-red-400'
                }`}
              >
                {result.savings > 0 ? (
                  <>
                    <TrendingDown className="h-4 w-4 shrink-0" />
                    Você economiza {moneyBRL(result.savings)}/ano com o Anexo{' '}
                    {result.anexo}
                  </>
                ) : (
                  <>
                    <TrendingUp className="h-4 w-4 shrink-0" />
                    Seria {moneyBRL(Math.abs(result.savings))}/ano mais barato no
                    Anexo {result.otherAnexo}
                  </>
                )}
              </div>
            </motion.div>

            {/* Optimization tip */}
            {showOptTip && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/5 px-5 py-4"
              >
                <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" />
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    Fator R próximo ao limite de 28%
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Seu Fator R está em {pctBR(result.fatorR)}, que é{' '}
                    {result.fatorR >= 0.28
                      ? 'pouco acima'
                      : 'pouco abaixo'}{' '}
                    do limite de 28%. Considere ajustar sua folha de pagamento
                    (pró-labore, benefícios, etc.) para otimizar seu
                    enquadramento tributário. Um contador pode ajudá-lo a
                    planejar a melhor estratégia.
                  </p>
                </div>
              </motion.div>
            )}

            {/* Action buttons */}
            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
              >
                {saving ? (
                  <span className="flex items-center gap-2">
                    <svg
                      className="h-4 w-4 animate-spin"
                      viewBox="0 0 24 24"
                      fill="none"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v8H4z"
                      />
                    </svg>
                    Salvando...
                  </span>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Salvar simulação
                  </>
                )}
              </button>
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-2 rounded-lg border border-border bg-card px-4 py-2.5 text-sm font-medium text-muted-foreground hover:bg-muted/50 transition"
              >
                <Copy className="h-4 w-4" />
                Copiar resultado
              </button>
            </div>

            {/* Save feedback */}
            {saveSuccess && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-sm text-emerald-600 dark:text-emerald-400 font-medium"
              >
                ✅ Simulação salva com sucesso!
              </motion.p>
            )}
            {saveError && (
              <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2.5 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{saveError}</span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
