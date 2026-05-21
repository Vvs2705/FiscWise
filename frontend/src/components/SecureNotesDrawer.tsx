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
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/Button';
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
// Preset groups — cada grupo adiciona N campos de uma vez
// ---------------------------------------------------------------------------

interface PresetGroup {
  label: string;
  icon: string;
  fields: string[];
}

const PRESET_GROUPS: PresetGroup[] = [
  {
    label: 'Gov.br',
    icon: '🏛️',
    fields: ['Gov.br — Login (CPF)', 'Gov.br — Senha'],
  },
  {
    label: 'e-CAC',
    icon: '📋',
    fields: ['e-CAC — Usuário', 'e-CAC — Senha'],
  },
  {
    label: 'eSocial',
    icon: '👥',
    fields: ['eSocial — Usuário', 'eSocial — Senha'],
  },
  {
    label: 'Simples Nacional',
    icon: '📊',
    fields: ['Simples Nacional — Usuário', 'Simples Nacional — Senha'],
  },
  {
    label: 'Nota Fiscal Eletrônica',
    icon: '🧾',
    fields: ['NF-e — Usuário', 'NF-e — Senha'],
  },
  {
    label: 'Prefeitura',
    icon: '🏙️',
    fields: ['Prefeitura — Login', 'Prefeitura — Senha'],
  },
  {
    label: 'Certificado Digital',
    icon: '🔏',
    fields: ['Certificado Digital — Senha'],
  },
  {
    label: 'SPED',
    icon: '🗂️',
    fields: ['SPED — Usuário', 'SPED — Senha'],
  },
  {
    label: 'Campo personalizado',
    icon: '✏️',
    fields: [''],
  },
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
        <input
          value={field.label}
          onChange={(e) => onChange(field.id, { label: e.target.value })}
          placeholder="Descrição do campo"
          className="flex-1 rounded border bg-background px-2 py-1 text-xs font-medium text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
        />
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
        <input
          type={hidden ? 'password' : 'text'}
          value={field.value}
          onChange={(e) => onChange(field.id, { value: e.target.value })}
          placeholder="Valor"
          className="flex-1 rounded border bg-background px-2 py-1.5 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-ring"
          autoComplete="off"
          autoCorrect="off"
          spellCheck={false}
        />
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
// Sub-component: Add credential dropdown button
// ---------------------------------------------------------------------------

interface AddCredentialButtonProps {
  onAdd: (fields: string[]) => void;
}

function AddCredentialButton({ onAdd }: AddCredentialButtonProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-center gap-2 rounded-lg border-2 border-dashed border-border py-3 text-sm text-muted-foreground hover:border-primary/40 hover:text-foreground transition-colors"
      >
        <Plus className="h-4 w-4" />
        Adicionar credencial
        <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute bottom-full left-0 right-0 mb-1 rounded-lg border bg-popover shadow-lg overflow-hidden z-50">
          <p className="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground border-b">
            Selecione o tipo de acesso
          </p>
          <div className="max-h-64 overflow-y-auto py-1">
            {PRESET_GROUPS.map((group) => (
              <button
                key={group.label}
                type="button"
                className="w-full flex items-center gap-3 px-3 py-2.5 text-left hover:bg-muted transition-colors"
                onMouseDown={() => {
                  onAdd(group.fields);
                  setOpen(false);
                }}
              >
                <span className="text-base leading-none">{group.icon}</span>
                <div>
                  <p className="text-sm font-medium">{group.label}</p>
                  <p className="text-[11px] text-muted-foreground">
                    {group.fields.length === 1
                      ? group.fields[0] || 'Campo em branco'
                      : group.fields.join(' · ')}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
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

  function handleAddGroup(fields: string[]) {
    setNotes((prev) => {
      const newFields = fields.map((label) => newField(label));
      const updated = [...prev, ...newFields];
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
            <div className="flex flex-col items-center justify-center py-10 text-center">
              <Lock className="h-10 w-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">Nenhuma nota ainda</p>
              <p className="text-xs text-muted-foreground/70 mt-1">
                Selecione o tipo de acesso abaixo para adicionar as credenciais do cliente.
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

          <AddCredentialButton onAdd={handleAddGroup} />
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
