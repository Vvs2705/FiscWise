import { useState } from 'react';
import { getTenantId } from '@/lib/auth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Copy, Check } from 'lucide-react';
import toast from 'react-hot-toast';

export function WidgetPage() {
  const [copied, setCopied] = useState(false);
  const tenantId = getTenantId();
  const apiUrl = import.meta.env.VITE_API_URL || 'https://solo-os-api-production.up.railway.app';

  const snippet = `<script src="${apiUrl}/api/v1/widget/${tenantId}.js"></script>`;

  const handleCopy = () => {
    navigator.clipboard.writeText(snippet);
    setCopied(true);
    toast.success('Código copiado!');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Widget de Chat</h1>
        <p className="text-muted-foreground">Configure e integre o chat em seu site</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Código de Integração</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Copie e cole este código no HTML do seu site, antes do fechamento da tag{' '}
            <code className="bg-muted px-1 py-0.5 rounded">&lt;/body&gt;</code>
          </p>
          <div className="relative">
            <pre className="bg-muted p-4 rounded-lg overflow-x-auto">
              <code>{snippet}</code>
            </pre>
            <Button
              size="sm"
              variant="outline"
              className="absolute top-2 right-2"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Copiado!
                </>
              ) : (
                <>
                  <Copy className="h-4 w-4 mr-2" />
                  Copiar
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preview do Widget</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border rounded-lg overflow-hidden" style={{ height: '500px' }}>
            <iframe
              src={`${apiUrl}/api/v1/widget/${tenantId}/chat`}
              className="w-full h-full"
              title="Widget Preview"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Informações</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Tenant ID</span>
            <code className="bg-muted px-2 py-1 rounded text-sm">{tenantId}</code>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">API URL</span>
            <code className="bg-muted px-2 py-1 rounded text-sm">{apiUrl}</code>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
