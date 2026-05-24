/**
 * TermsPage — Termos de Uso do FiscWise
 * LGPD compliance: public page, no auth required.
 */
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Logo } from '@/components/Logo';

export function TermsPage() {
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
        <h1 className="mb-2 text-3xl font-bold">Termos de Uso</h1>
        <p className="mb-8 text-sm text-muted-foreground">
          Versão 1.0 — Última atualização: maio de 2026
        </p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground">

          <section>
            <h2 className="text-lg font-semibold">1. Aceitação dos Termos</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Ao criar uma conta no FiscWise, você (o "Usuário" ou "Contratante") concorda com
              estes Termos de Uso em sua totalidade. Se não concordar, não utilize o serviço.
              Estes termos constituem um contrato juridicamente vinculante entre você e
              <strong> VStack Solutions Ltda</strong>, CNPJ XX.XXX.XXX/0001-XX, com sede em São Paulo/SP.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">2. Descrição do Serviço</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise é uma plataforma SaaS de gestão contábil e fiscal voltada a escritórios
              de contabilidade brasileiros. O serviço inclui funcionalidades de gestão de clientes,
              controle de documentos, agenda de prazos fiscais, emissão de DAS/DARF, gestão de
              certificados digitais e relatórios financeiros.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">3. Cadastro e Responsabilidades</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O Usuário é responsável pela veracidade das informações fornecidas no cadastro e pelo
              sigilo de suas credenciais de acesso. É vedado compartilhar senha ou ceder o acesso
              a terceiros não autorizados. Qualquer atividade realizada com sua conta é de sua
              responsabilidade.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">4. Planos e Pagamentos</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise oferece planos gratuito e pagos. Os planos pagos são cobrados mensalmente
              mediante cartão de crédito ou boleto bancário, processados por gateway de pagamento
              terceirizado (Asaas). O cancelamento pode ser solicitado a qualquer momento, sem multa,
              com encerramento ao fim do período vigente.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">5. Propriedade Intelectual</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Todos os direitos sobre a plataforma, interface, código-fonte, marca e materiais do
              FiscWise pertencem à VStack Solutions. Os dados inseridos pelo Usuário permanecem de
              propriedade do Usuário; o FiscWise não reivindica posse sobre eles.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">6. Uso Permitido e Proibições</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              É proibido utilizar o FiscWise para atividades ilegais, fraudulentas, de lavagem de
              dinheiro ou que violem a legislação brasileira. É vedado realizar engenharia reversa,
              tentar acessar dados de outros tenants ou sobrecarregar intencionalmente a infraestrutura
              da plataforma.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">7. Disponibilidade e Suporte</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise se esforça para manter disponibilidade de 99,5% mensal (excluindo
              manutenções programadas). Não garantimos disponibilidade ininterrupta. O suporte é
              prestado via e-mail e chat durante horário comercial (seg–sex, 9h–18h, horário de Brasília).
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">8. Limitação de Responsabilidade</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise não se responsabiliza por decisões fiscais ou contábeis tomadas com base nas
              informações da plataforma. A responsabilidade técnica e legal pelos atos contábeis
              permanece com o profissional habilitado. Em nenhuma hipótese nossa responsabilidade
              excederá o valor pago pelo Usuário nos últimos 3 meses.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">9. Proteção de Dados (LGPD)</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O tratamento de dados pessoais segue a{' '}
              <strong>Lei Geral de Proteção de Dados (Lei 13.709/2018 — LGPD)</strong>. Consulte nossa{' '}
              <Link to="/privacidade" className="text-primary hover:underline">
                Política de Privacidade
              </Link>{' '}
              para detalhes sobre coleta, uso, retenção e seus direitos como titular de dados.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">10. Rescisão</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              O FiscWise pode suspender ou encerrar sua conta em caso de violação destes termos,
              inadimplência ou determinação judicial. O Usuário pode solicitar o encerramento a
              qualquer momento em <strong>Configurações → Conta → Solicitar exclusão de dados</strong>.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">11. Alterações nos Termos</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Podemos atualizar estes termos periodicamente. Notificaremos os usuários por e-mail
              com 30 dias de antecedência para alterações materiais. O uso continuado após a
              data de vigência constitui aceitação dos novos termos.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">12. Lei Aplicável e Foro</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Estes termos são regidos pela legislação brasileira. Fica eleito o foro da comarca
              de São Paulo/SP para dirimir quaisquer controvérsias, com renúncia a qualquer outro,
              por mais privilegiado que seja.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">13. Contato</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
              Dúvidas sobre estes Termos de Uso podem ser enviadas para:{' '}
              <a href="mailto:juridico@fiscwise.com.br" className="text-primary hover:underline">
                juridico@fiscwise.com.br
              </a>
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
