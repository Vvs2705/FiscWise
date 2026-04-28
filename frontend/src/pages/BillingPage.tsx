import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

export function BillingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="text-muted-foreground">Gerencie seu plano e assinatura</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Plano Atual</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-2xl font-bold">Free</h3>
              <p className="text-muted-foreground">10.000 tokens/mês</p>
            </div>
            <Badge variant="success">Ativo</Badge>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Tokens usados</span>
              <span className="font-medium">0 / 10.000</span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div className="bg-primary h-2 rounded-full" style={{ width: '0%' }} />
            </div>
          </div>
        </CardContent>
      </Card>

      <div>
        <h2 className="text-2xl font-bold mb-4">Planos Disponíveis</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>Free</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-3xl font-bold">R$ 0</div>
                <div className="text-muted-foreground">/mês</div>
              </div>
              <ul className="space-y-2 text-sm">
                <li>✓ 10.000 tokens/mês</li>
                <li>✓ Base de conhecimento básica</li>
                <li>✓ Chat com IA</li>
              </ul>
              <Button variant="outline" className="w-full" disabled>
                Plano Atual
              </Button>
            </CardContent>
          </Card>

          <Card className="border-primary">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Starter
                <Badge>Popular</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-3xl font-bold">R$ 49</div>
                <div className="text-muted-foreground">/mês</div>
              </div>
              <ul className="space-y-2 text-sm">
                <li>✓ 100.000 tokens/mês</li>
                <li>✓ Base de conhecimento avançada</li>
                <li>✓ Chat com IA</li>
                <li>✓ Widget personalizável</li>
                <li>✓ Suporte prioritário</li>
              </ul>
              <Button className="w-full">Fazer Upgrade</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Pro</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <div className="text-3xl font-bold">R$ 149</div>
                <div className="text-muted-foreground">/mês</div>
              </div>
              <ul className="space-y-2 text-sm">
                <li>✓ 500.000 tokens/mês</li>
                <li>✓ Base de conhecimento ilimitada</li>
                <li>✓ Chat com IA</li>
                <li>✓ Widget personalizável</li>
                <li>✓ Suporte prioritário</li>
                <li>✓ API dedicada</li>
                <li>✓ Analytics avançado</li>
              </ul>
              <Button className="w-full">Fazer Upgrade</Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
