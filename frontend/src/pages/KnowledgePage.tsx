import { useState } from 'react';
import { useKnowledge } from '@/lib/hooks/useKnowledge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Plus, Link as LinkIcon, FileText, Trash2 } from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

export function KnowledgePage() {
  const { sources, ingestUrl, ingestText, deleteSource } = useKnowledge();
  const [showUrlModal, setShowUrlModal] = useState(false);
  const [showTextModal, setShowTextModal] = useState(false);
  const [url, setUrl] = useState('');
  const [urlTitle, setUrlTitle] = useState('');
  const [text, setText] = useState('');
  const [textTitle, setTextTitle] = useState('');

  const handleAddUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    await ingestUrl.mutateAsync({ url, title: urlTitle || undefined });
    setUrl('');
    setUrlTitle('');
    setShowUrlModal(false);
  };

  const handleAddText = async (e: React.FormEvent) => {
    e.preventDefault();
    await ingestText.mutateAsync({ text, title: textTitle });
    setText('');
    setTextTitle('');
    setShowTextModal(false);
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, 'success' | 'warning' | 'error' | 'info'> = {
      processed: 'success',
      processing: 'info',
      pending: 'warning',
      failed: 'error',
    };
    return <Badge variant={variants[status] || 'default'}>{status}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Base de Conhecimento</h1>
          <p className="text-muted-foreground">Gerencie os documentos da sua base de conhecimento</p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowUrlModal(true)}>
            <LinkIcon className="h-4 w-4 mr-2" />
            Adicionar URL
          </Button>
          <Button onClick={() => setShowTextModal(true)}>
            <FileText className="h-4 w-4 mr-2" />
            Adicionar Texto
          </Button>
        </div>
      </div>

      {showUrlModal && (
        <Card>
          <CardHeader>
            <CardTitle>Adicionar URL</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddUrl} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="url" className="text-sm font-medium">
                  URL
                </label>
                <Input
                  id="url"
                  type="url"
                  placeholder="https://exemplo.com/artigo"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="urlTitle" className="text-sm font-medium">
                  Título (opcional)
                </label>
                <Input
                  id="urlTitle"
                  type="text"
                  placeholder="Título do documento"
                  value={urlTitle}
                  onChange={(e) => setUrlTitle(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setShowUrlModal(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={ingestUrl.isPending}>
                  {ingestUrl.isPending ? 'Adicionando...' : 'Adicionar'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {showTextModal && (
        <Card>
          <CardHeader>
            <CardTitle>Adicionar Texto</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAddText} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="textTitle" className="text-sm font-medium">
                  Título
                </label>
                <Input
                  id="textTitle"
                  type="text"
                  placeholder="Título do documento"
                  value={textTitle}
                  onChange={(e) => setTextTitle(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <label htmlFor="text" className="text-sm font-medium">
                  Texto
                </label>
                <textarea
                  id="text"
                  className="flex min-h-[200px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                  placeholder="Cole ou digite o texto aqui..."
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  required
                />
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setShowTextModal(false)}>
                  Cancelar
                </Button>
                <Button type="submit" disabled={ingestText.isPending}>
                  {ingestText.isPending ? 'Adicionando...' : 'Adicionar'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      <div className="space-y-4">
        {sources.isLoading && <div>Carregando documentos...</div>}
        {sources.data?.map((source) => (
          <Card key={source.id}>
            <CardContent className="flex items-center justify-between p-6">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h3 className="font-semibold">{source.title}</h3>
                  {getStatusBadge(source.status)}
                </div>
                {source.source_url && (
                  <p className="text-sm text-muted-foreground mt-1">{source.source_url}</p>
                )}
                <div className="flex gap-4 mt-2 text-sm text-muted-foreground">
                  <span>{source.chunk_count} chunks</span>
                  <span>
                    Criado em {format(new Date(source.created_at), 'dd/MM/yyyy HH:mm', { locale: ptBR })}
                  </span>
                </div>
                {source.error_message && (
                  <p className="text-sm text-red-600 mt-2">{source.error_message}</p>
                )}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => deleteSource.mutate(source.id)}
                disabled={deleteSource.isPending}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
        {sources.data?.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center p-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">Nenhum documento ainda</h3>
              <p className="text-muted-foreground mb-4">
                Adicione URLs ou textos para construir sua base de conhecimento
              </p>
              <div className="flex gap-2">
                <Button onClick={() => setShowUrlModal(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar URL
                </Button>
                <Button onClick={() => setShowTextModal(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  Adicionar Texto
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
