/**
 * SecureNotesDrawer — armazenamento LOCAL de credenciais sensíveis por cliente.
 *
 * Os dados ficam APENAS no localStorage do navegador.
 * Nunca são enviados ao servidor nem gravados no banco de dados.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  X,
  Lock,
  Plus,
  Trash2,
  Copy,
  Eye,
  EyeOff,
  Download,
  AlertTriangle,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { getTenantId } from '@/lib/auth';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface NoteField {
  id: string;
  label: string;
  value: string;
}

interface SecureNotesDrawerProps {
  open: boolean;
  onClose: () => void;
  clientId: string;
  clientName: string;
}

// ---------------------------------------------------------------------------
// Preset field labels
// ---------------------------------------------------------------------------

const PRESET_LABELS = [
  'Gov.br — Login (CPF)',
  'Gov.br — Senha',
  'e-CAC — Usuário',
  'e-CAC — Senha',
  'eSocial — Acesso',
  'Simples Nacional — Senha',
  'Certificado Digital — Senha',
  'Nota Fiscal Eletrônica',
  'Prefeitura — Login',
  'Prefeitura — Senha',
  'SPED — Senha',
  'Outro',
];

// ---------------------------------------------------------------------------
// Storage helpers
// ---------------------------------------------------------------------------

function storageKey(tenantId: string, clientId: string) {
  return `fw_secure_${tenantId}_${clientId}`;
}

function loadNotes(tenantId: string, clientId: string): NoteField[] {
  try {
    const raw = localStorage.getItem(storageKey(tenantId, clientId));
    if (!raw) return [];
    return JSON.parse(raw) as NoteField[];
  } catch {
    return [];
  }
}

function saveNotes(tenantId: string, clientId: string, notes: NoteField[]) {
  localStorage.setItem(storageKey(tenantId, clientId), JSON.stringify(notes));
}

function newField(label = ''): NoteField {
  return { id: crypto.randomUUID(), label, value: '' };
}

// ---------------------------------------------------------------------------
// Sub-component: single field row
// ---------------------------------------------------------------------------

interface FieldRowProps {
  field: NoteField;
  onChange: (id: string, patch: Partial<NoteField>) => void;
  onDelete: (id: string) => void;
}

function FieldRow({ field, onChange, onDelete }: FieldRowProps) {
  const [hidden, setHidden] = useState(true);
  const [copied, setCopied] = useState(false);
  const [showPresets, setShowPresets] = useState(false);
  const presetRef = useRef<HTMLDivElement>(null);

  // Close preset dropdown on outside click
  useEffect(() => {
    if (!showPresets) return;
    const handler = (e: MouseEvent) => {
      if (presetRef.current && !presetRef.current.contains(e.target as Node)) {
        setShowPresets(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showPresets]);

  async function handleCopy() {
    if (!field.value) return;
    await navigator.clipboard.writeText(field.value);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="group rounded-lg border bg-muted/30 p-3 space-y-2">
      {/* Label row */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1" ref={presetRef}>
          <input
            value={field.label}
            onChange={(e) => onChange(field.id, { label: e.target.value })}
            placeholder="Descrição (ex: Gov.br — Login)"
            className="w-full rounded border bg-background px-2 py-1 text-xs font-medium text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring cursor-text"
            onFocus={() => !field.label && setShowPresets(true)}
          />
          {showPresets && (
            <div className="absolute top-full left-0 z-50 mt-1 w-64 rounded-md border bg-popover shadow-md">
              {PRESET_LABELS.map((lbl) => (
                <button
                  key={lbl}
                  type="button"
                  className="w-full px-3 py-1.5 text-left text-xs hover:bg-muted"
                  onMouseDown={() => {
                    onChange(field.id, { label: lbl === 'Outro' ? '' : lbl });
                    setShowPresets(false);
                  }}
                >
                  {lbl}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          type="button"
          onClick={() => onDelete(field.id)}
          className="shrink-0 rounded p-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
          aria-label="Remover campo"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Value row */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type={hidden ? 'password' : 'text'}
            value={field.value}
            onChange={(e) => onChange(field.id, { value: e.target.value })}
            placeholder="Valor"
            className="w-full rounded border bg-background px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring pr-8"
            autoComplete="off"
            autoCorrect="off"
            spellCheck={false}
          />
        </div>
        <button
          type="button"
          onClick={() => setHidden((h) => !h)}
          className="shrink-0 rounded p-1.5 text-muted-foreground hover:text-foreground"
          aria-label={hidden ? 'Revelar' : 'Ocultar'}
          title={hidden ? 'Revelar' : 'Ocultar'}
        >
          {hidden ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
        <button
          type="button"
          onClick={handleCopy}
          className="shrink-0 rounded p-1.5 text-muted-foreground hover:text-foreground"
          aria-label="Copiar"
          title="Copiar"
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-600" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main drawer
// ---------------------------------------------------------------------------

export function SecureNotesDrawer({
  open,
  onClose,
  clientId,
  clientName,
}: SecureNotesDrawerProps) {
  const tenantId = getTenantId() ?? 'unknown';
  const [notes, setNotes] = useState<NoteField[]>([]);
  const [saved, setSaved] = useState(false);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load on open
  useEffect(() => {
    if (open) {
      setNotes(loadNotes(tenantId, clientId));
    }
  }, [open, tenantId, clientId]);

  // Auto-save with debounce
  const persistNotes = useCallback(
    (updated: NoteField[]) => {
      saveNotes(tenantId, clientId, updated);
      setSaved(true);
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
      saveTimerRef.current = setTimeout(() => setSaved(false), 2000);
    },
    [tenantId, clientId]
  );

  function handleChange(id: string, patch: Partial<NoteField>) {
    setNotes((prev) => {
      const updated = prev.map((f) => (f.id === id ? { ...f, ...patch } : f));
      persistNotes(updated);
      return updated;
    });
  }

  function handleDelete(id: string) {
    setNotes((prev) => {
      const updated = prev.filter((f) => f.id !== id);
      persistNotes(updated);
      return updated;
    });
  }

  function handleAdd() {
    setNotes((prev) => {
      const updated = [...prev, newField()];
      persistNotes(updated);
      return updated;
    });
  }

  function handleExport() {
    const lines = [
      `=== Notas Seguras — ${clientName} ===`,
      `Exportado em: ${new Date().toLocaleString('pt-BR')}`,
      '',
      ...notes.map((f) => `${f.label || '(sem rótulo)'}: ${f.value}`),
      '',
      '⚠ Este arquivo contém dados sensíveis. Guarde com segurança.',
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `notas-seguras-${clientName.replace(/\s+/g, '-').toLowerCase()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="secure-notes-title"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-sm flex-col border-l bg-background shadow-xl"
      >
        {/* Header */}
        <div className="flex shrink-0 items-start justify-between border-b px-5 py-4">
          <div className="flex items-center gap-2">
            <Lock className="h-4 w-4 text-amber-500" />
            <div>
              <h2 id="secure-notes-title" className="text-sm font-semibold">
                Notas Seguras
              </h2>
              <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                {clientName}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded p-1 opacity-70 hover:opacity-100"
            aria-label="Fechar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Warning banner */}
        <div className="shrink-0 bg-amber-50 border-b border-amber-200 px-5 py-2.5 flex gap-2 items-start">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-600 mt-0.5 shrink-0" />
          <p className="text-xs text-amber-800 leading-relaxed">
            Dados salvos <strong>apenas neste navegador</strong>. Nunca enviados ao servidor.
            Use o botão exportar para fazer backup.
          </p>
        </div>

        {/* Content — scrollable */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {notes.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Lock className="h-10 w-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">Nenhuma nota ainda</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Adicione credenciais de acesso e outras informações sensíveis do cliente.
              </p>
            </div>
          )}

          {notes.map((field) => (
            <FieldRow
              key={field.id}
              field={field}
              onChange={handleChange}
              onDelete={handleDelete}
            />
          ))}

          <button
            type="button"
            onClick={handleAdd}
            className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-3 text-sm text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors"
          >
            <Plus className="h-4 w-4" />
            Adicionar credencial
          </button>
        </div>

        {/* Footer */}
        <div className="shrink-0 border-t px-5 py-3 flex items-center justify-between gap-2">
          <span className="text-xs text-muted-foreground">
            {saved ? (
              <span className="text-green-600 flex items-center gap-1">
                <Check className="h-3 w-3" /> Salvo
              </span>
            ) : (
              `${notes.length} ${notes.length === 1 ? 'item' : 'itens'}`
            )}
          </span>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={notes.length === 0}
          >
            <Download className="mr-1.5 h-3.5 w-3.5" />
            Exportar
          </Button>
        </div>
      </div>
    </>
  );
}
