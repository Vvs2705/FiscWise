import { api } from '@/lib/api';

export type FocusGroup = 'critical' | 'today' | 'week' | 'waiting_client' | 'waiting_organ';
export type FocusItemType =
  | 'obligation' | 'invoice' | 'guide' | 'ecac'
  | 'document' | 'closing' | 'certificate' | 'power';

export interface FocusItem {
  id: string;
  group: FocusGroup;
  type: FocusItemType;
  title: string;
  client: string;
  competence: string;
  deadline: string;
  risk: 'critical' | 'high' | 'medium' | 'low';
  status: string;
  responsible: string;
  primaryAction: { label: string; href?: string };
  secondaryAction?: { label: string; href?: string };
}

interface ApiFocusItem {
  id: string;
  group: FocusGroup;
  type: FocusItemType;
  title: string;
  client: string;
  competence: string | null;
  deadline: string | null;
  risk: FocusItem['risk'];
  status: string;
  responsible: string;
  primary_action: { label: string; href: string };
  secondary_action?: { label: string; href: string };
}

const MONTH_LABELS = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];

function formatCompetence(competence: string | null): string {
  if (!competence || competence.length < 7) return '—';
  const month = Number(competence.slice(5, 7));
  return `${MONTH_LABELS[month - 1] ?? competence}/${competence.slice(0, 4)}`;
}

function formatDeadline(deadline: string | null): string {
  if (!deadline) return '—';
  const today = new Date().toISOString().slice(0, 10);
  if (deadline === today) return 'Hoje';
  const [y, m, d] = deadline.split('-');
  return `${d}/${m}/${y}`;
}

function mapItem(item: ApiFocusItem): FocusItem {
  return {
    id: item.id,
    group: item.group,
    type: item.type,
    title: item.title,
    client: item.client,
    competence: formatCompetence(item.competence),
    deadline: formatDeadline(item.deadline),
    risk: item.risk,
    status: item.status,
    responsible: item.responsible,
    primaryAction: { label: item.primary_action.label, href: item.primary_action.href },
    secondaryAction: item.secondary_action
      ? { label: item.secondary_action.label, href: item.secondary_action.href }
      : undefined,
  };
}

export async function fetchFocusItems(): Promise<FocusItem[]> {
  const { data } = await api.get<{ items: ApiFocusItem[] }>('/api/v1/focus');
  return data.items.map(mapItem);
}
