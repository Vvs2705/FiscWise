/**
 * PrivacyPage — Política de Privacidade do FiscWise
 * LGPD compliance: public page, no auth required.
 * Covers Art. 18 rights (access, portability, correction, erasure).
 */
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield } from 'lucide-react';
import { Logo } from '@/components/Logo';

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Logo variant="full" theme="light" size={28} />
          <Link
            to="/register"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar ao cadastro
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="mx-auto max-w-3xl px-4 py-10 pb-20">
        <div className="mb-2 flex items-center gap-2">
          <Shield className="h-7 w-7 text-primary" />
          <h1 className="text-3xl font-bold">Política de Privacidade</h1>
        </div>
        <p className="mb-1 text-sm text-muted-foreground">
          Versão 1.0 — Última atualização: maio de 2026
        </p>
        <p className="mb-8 text-xs text-muted-foreground">
          Em conformidade com a Lei Geral de Proteção de Dados — <strong>LGPD (Lei 13.709/2018)</strong>
        </p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground">

          <section>
            <h2 className="text-lg font-semibold">1. Controlador de Dados</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              <strong>VStack Solutions Ltda</strong> é a controladora dos dados pessoais coletados
              pelo FiscWise. Para questões relacionadas à privacidade, entre em contato com nosso
              DPO (Encarregado de Proteção de Dados) pelo e-mail{' '}
              <a href="mailto:privacidade@fiscwise.com.br" className="text-primary hover:underline">
                privacidade@fiscwise.com.br
              </a>.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">2. Dados Coletados</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Coletamos os seguintes dados pessoais:
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground list-disc list-inside">
              <li><strong>Cadastro:</strong> nome completo, e-mail, telefone, CNPJ/CPF</li>
              <li><strong>Uso da plataforma:</strong> logs de acesso, endereço IP, dispositivo e navegador</li>
              <li><strong>Dados de clientes:</strong> informações inseridas pelo escritório sobre seus clientes (dados de terceiros sob responsabilidade do escritório contábil)</li>
              <li><strong>Dados financeiros:</strong> histórico de pagamentos de honorários (não armazenamos dados de cartão de crédito — processados por Asaas)</li>
              <li><strong>Comunicações:</strong> histórico de e-mails e notificações enviadas pelo sistema</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">3. Finalidade e Base Legal do Tratamento</h2>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border">
                    <th className="py-2 pr-4 text-left font-semibold">Finalidade</th>
                    <th className="py-2 text-left font-semibold">Base Legal (LGPD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-muted-foreground">
                  <tr>
                    <td className="py-2 pr-4">Prestação do serviço contratado</td>
                    <td className="py-2">Art. 7º, V — execução de contrato</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Faturamento e gestão financeira</td>
                    <td className="py-2">Art. 7º, V — execução de contrato</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Comunicações de segurança e suporte</td>
                    <td className="py-2">Art. 7º, IX — legítimo interesse</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Melhorias no produto (analytics anonimizados)</td>
                    <td className="py-2">Art. 7º, IX — legítimo interesse</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Obrigações fiscais e legais da plataforma</td>
                    <td className="py-2">Art. 7º, II — cumprimento de obrigação legal</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Marketing e novidades do produto</td>
                    <td className="py-2">Art. 7º, I — consentimento (opt-in)</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section>
            <h2 className="text-lg font-semibold">4. Compartilhamento de Dados</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Seus dados são compartilhados apenas com:
            </p>
            <ul className="mt-2 space-y-1 text-sm text-muted-foreground list-disc list-inside">
              <li><strong>Asaas</strong> — processamento de pagamentos (dados mínimos necessários)</li>
              <li><strong>Supabase/PostgreSQL</strong> — hospedagem de banco de dados (Brasil/EUA, com DPA)</li>
              <li><strong>Fly.io / Vercel</strong> — infraestrutura de hospedagem (com DPA)</li>
              <li><strong>Resend</strong> — envio de e-mails transacionais (somente e-mail e nome)</li>
              <li><strong>Autoridades públicas</strong> — quando exigido por lei ou decisão judicial</li>
            </ul>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Não vendemos, alugamos ou comercializamos seus dados pessoais com terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">5. Retenção de Dados</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Dados de conta são mantidos enquanto a conta estiver ativa e por até 5 anos após
              o encerramento, conforme exigido pela legislação tributária brasileira (RFB).
              Logs de acesso são retidos por 6 meses. Após os prazos legais, os dados são
              eliminados ou anonimizados.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">6. Segurança</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Adotamos medidas técnicas e organizacionais para proteger seus dados, incluindo:
              criptografia em trânsito (TLS 1.3), senhas armazenadas com bcrypt (hash unidirecional),
              autenticação JWT com expiração curta, isolamento de dados por tenant, e controle de
              acesso baseado em papéis (RBAC). Tokens de acesso temporário (ex: portal do cliente)
              são armazenados apenas como hash SHA-256.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">7. Seus Direitos (LGPD, Art. 18)</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Como titular de dados, você tem os seguintes direitos:
            </p>
            <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground list-disc list-inside">
              <li><strong>Acesso:</strong> solicitar cópia de todos os dados pessoais que mantemos sobre você</li>
              <li><strong>Correção:</strong> atualizar dados incompletos, inexatos ou desatualizados</li>
              <li><strong>Anonimização ou bloqueio:</strong> para dados desnecessários ou tratados em desconformidade</li>
              <li><strong>Portabilidade:</strong> exportar seus dados em formato estruturado</li>
              <li><strong>Eliminação:</strong> solicitar exclusão dos dados tratados com base em consentimento</li>
              <li><strong>Revogação de consentimento:</strong> retirar o consentimento a qualquer momento</li>
              <li><strong>Oposição:</strong> opor-se ao tratamento realizado com base em legítimo interesse</li>
            </ul>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Para exercer esses direitos, acesse <strong>Configurações → Conta</strong> no painel
              do FiscWise ou envie e-mail para{' '}
              <a href="mailto:privacidade@fiscwise.com.br" className="text-primary hover:underline">
                privacidade@fiscwise.com.br
              </a>. Respondemos em até 15 dias úteis.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">8. Cookies</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Utilizamos apenas cookies estritamente necessários para funcionamento da autenticação
              (token JWT em localStorage). Não utilizamos cookies de rastreamento ou publicidade
              de terceiros.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">9. Transferência Internacional</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Alguns dados podem ser processados em servidores fora do Brasil (EUA), por provedores
              de infraestrutura (Fly.io, Vercel). Todas essas transferências são realizadas com
              garantias contratuais adequadas (DPA — Data Processing Agreements).
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">10. Menores de Idade</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise é destinado exclusivamente a profissionais e empresas. Não coletamos
              intencionalmente dados de menores de 18 anos.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">11. Alterações nesta Política</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Esta Política de Privacidade pode ser atualizada periodicamente. Notificaremos os
              usuários por e-mail sobre alterações materiais com antecedência mínima de 15 dias.
              A versão vigente sempre estará disponível nesta página com a data de atualização.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">12. Contato e DPO</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Encarregado de Proteção de Dados (DPO):{' '}
              <a href="mailto:privacidade@fiscwise.com.br" className="text-primary hover:underline">
                privacidade@fiscwise.com.br
              </a>
              <br />
              Também aceitamos reclamações à Autoridade Nacional de Proteção de Dados (ANPD):{' '}
              <a
                href="https://www.gov.br/anpd"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                www.gov.br/anpd
              </a>
            </p>
          </section>

          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
            <p className="text-xs text-muted-foreground">
              Consulte também nossos{' '}
              <Link to="/termos" className="font-medium text-primary hover:underline">
                Termos de Uso
              </Link>{' '}
              para informações completas sobre o uso da plataforma FiscWise.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
