/**
 * PrivacyPage — Política de Privacidade do FiscWise
 * LGPD compliance: public page, no auth required.
 *
 * Texto jurídico revisado na auditoria COMPLIANCE-40 (21/11/2026).
 * Revisar com advogado antes de considerar definitivo.
 */
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { COMPANY_ADDRESS, COMPANY_CNPJ, COMPANY_LEGAL_NAME } from '@/lib/company';

const P = 'mt-2 text-sm leading-relaxed text-muted-foreground';
const UL = 'mt-2 space-y-1 text-sm text-muted-foreground list-disc list-inside';

function Email({ to }: { to: string }) {
  return (
    <a href={`mailto:${to}`} className="text-primary hover:underline">
      {to}
    </a>
  );
}

export function PrivacyPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Logo variant="full" theme="auto" size={28} />
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
          Versão 1.5 — Última atualização: 21/11/2026
        </p>
        <p className="mb-8 text-xs text-muted-foreground">
          Em conformidade com a Lei Geral de Proteção de Dados — <strong>LGPD (Lei 13.709/2018)</strong>
        </p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground">

          <section>
            <h2 className="text-lg font-semibold">1. Quem trata os dados</h2>
            <p className={P}>
              <strong>{COMPANY_LEGAL_NAME}</strong>, nome comercial do empresário individual inscrito
              no CNPJ {COMPANY_CNPJ}, com sede em {COMPANY_ADDRESS}, oferece o FiscWise e atua em dois papéis
              diferentes, conforme o dado:
            </p>
            <ul className={UL}>
              <li>
                <strong>Controladora</strong> dos dados de quem usa o sistema: o escritório contratante,
                seus usuários e o responsável pela assinatura (cadastro, acesso, cobrança e suporte).
              </li>
              <li>
                <strong>Operadora</strong> dos dados que o escritório cadastra sobre os clientes dele
                (empresas, sócios, responsáveis, documentos, notas e guias). Nesse caso quem decide o que
                é feito com os dados é o escritório, que é o controlador, e o FiscWise trata os dados
                somente para prestar o serviço, conforme o{' '}
                <Link to="/dpa" className="text-primary hover:underline">
                  Acordo de Tratamento de Dados
                </Link>
                . Pedidos de titulares sobre esses dados devem ser feitos ao escritório; se chegarem até
                nós, repassamos ao escritório.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">2. Dados coletados e para que servem</h2>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border">
                    <th className="py-2 pr-4 text-left font-semibold">Dado</th>
                    <th className="py-2 pr-4 text-left font-semibold">Finalidade</th>
                    <th className="py-2 text-left font-semibold">Base legal (LGPD)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-muted-foreground">
                  <tr>
                    <td className="py-2 pr-4">Nome, e-mail, telefone, CNPJ/CPF do escritório e dos usuários</td>
                    <td className="py-2 pr-4">Criar a conta, dar acesso e prestar o serviço contratado</td>
                    <td className="py-2">Art. 7º, V — execução de contrato</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Assinatura, pagamentos e histórico de cobrança</td>
                    <td className="py-2 pr-4">Cobrar o plano e cumprir obrigações fiscais da {COMPANY_LEGAL_NAME}</td>
                    <td className="py-2">Art. 7º, V — contrato; Art. 7º, II — obrigação legal</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Registros de acesso (data, hora, IP), dispositivo e navegador</td>
                    <td className="py-2 pr-4">Segurança da conta, prevenção a fraude e guarda exigida pelo Marco Civil da Internet</td>
                    <td className="py-2">Art. 7º, II — obrigação legal; Art. 7º, IX — legítimo interesse</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">E-mails e notificações enviados pelo sistema</td>
                    <td className="py-2 pr-4">Avisos de segurança, prazos, cobrança e suporte</td>
                    <td className="py-2">Art. 7º, V — contrato; Art. 7º, IX — legítimo interesse</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Métricas de uso agregadas, sem identificar a pessoa</td>
                    <td className="py-2 pr-4">Melhorar o produto</td>
                    <td className="py-2">Art. 7º, IX — legítimo interesse</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">E-mail de quem fez o teste grátis e não assinou</td>
                    <td className="py-2 pr-4">
                      Uma oferta por tempo limitado, uma vez por escritório, com link de descadastro em todo e-mail
                    </td>
                    <td className="py-2">Art. 7º, IX — legítimo interesse (relacionamento existente)</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">E-mail para novidades do produto</td>
                    <td className="py-2 pr-4">Marketing</td>
                    <td className="py-2">Art. 7º, I — consentimento (opt-in), revogável a qualquer momento</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">
                      Dados da carteira do escritório: razão social, CNPJ, CPF, nome, e-mail, telefone e
                      endereço de sócios e responsáveis, documentos, notas fiscais, guias e certificados digitais
                    </td>
                    <td className="py-2 pr-4">
                      Executar o serviço contábil e fiscal a pedido do escritório (como operadora)
                    </td>
                    <td className="py-2">Definida pelo escritório controlador (em regra, art. 7º, II e V)</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-4">Nome e e-mail de quem acessa o Portal do Cliente</td>
                    <td className="py-2 pr-4">Dar ao cliente do escritório acesso aos documentos e guias dele</td>
                    <td className="py-2">Definida pelo escritório controlador (em regra, art. 7º, V)</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className={P}>
              Não tratamos dados pessoais sensíveis (art. 5º, II da LGPD), como dados de saúde, biometria,
              religião ou opinião política. Não armazenamos dados de cartão de crédito: o pagamento da
              assinatura é processado pelo Mercado Pago.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">3. Inteligência artificial</h2>
            <p className={P}>
              O FiscWise usa a <strong>OpenAI</strong> (EUA) como suboperadora em quatro recursos:
            </p>
            <ul className={UL}>
              <li>
                <strong>Leitura automática de documentos:</strong> quando um documento é enviado (pelo escritório
                ou pelo cliente no Portal), o texto extraído dele (até 5.000 caracteres), o nome do arquivo e o
                tipo informado são enviados para identificar o tipo de documento, a competência, o valor e o
                vencimento. Isso acontece automaticamente, dentro do saldo mensal de IA do plano;
              </li>
              <li>
                <strong>Resumo operacional do cliente:</strong> dados cadastrais e pendências do cliente, quando o
                escritório pede o resumo;
              </li>
              <li>
                <strong>Calculadora Fiscal:</strong> os números de cada simulação (faturamento, custos, folha, atividade), sem dados pessoais, nos planos que incluem a recomendação por IA;
              </li>
              <li>
                <strong>Assistente fiscal:</strong> a pergunta digitada e o contexto da conversa.
              </li>
            </ul>
            <p className={P}>
              Antes de qualquer envio, CPF e CNPJ são mascarados automaticamente. Nomes e outros dados que
              estiverem no texto do documento não são mascarados. Pelos termos da API da OpenAI, esse conteúdo
              não é usado para treinar os modelos dela.
            </p>
            <p className={P}>
              As respostas da IA são apoio, não parecer: podem conter erros e não substituem a análise do
              profissional contábil responsável. Nenhuma decisão sobre você ou seus clientes é tomada de forma
              automatizada pelo FiscWise.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">4. Com quem compartilhamos</h2>
            <p className={P}>
              Seus dados são compartilhados apenas com os fornecedores abaixo, cada um só com o necessário
              para a sua função e sob contrato com cláusulas de proteção de dados (DPA):
            </p>
            <ul className={UL}>
              <li><strong>Google Cloud Run</strong> — servidor da aplicação (região São Paulo, Brasil)</li>
              <li><strong>Supabase</strong> — banco de dados e armazenamento de arquivos</li>
              <li><strong>Cloudflare</strong> — hospedagem do site (Pages), cópias de segurança criptografadas (R2) e métricas de acesso sem cookies (Web Analytics)</li>
              <li><strong>Mercado Pago</strong> — pagamento da assinatura (dados mínimos necessários)</li>
              <li><strong>Resend</strong> — envio de e-mails transacionais (nome e e-mail)</li>
              <li><strong>Sentry</strong> — monitoramento de erros técnicos da aplicação</li>
              <li><strong>OpenAI</strong> — leitura automática de documentos e recursos de inteligência artificial (ver seção 3)</li>
            </ul>
            <p className={P}>
              Quando o escritório usa uma integração com órgãos públicos — como a emissão de NFS-e pelo
              Portal Nacional ou por prefeituras, consultas à Receita Federal pelo SERPRO ou o envio de
              mensagens pelo WhatsApp Business (Meta) — os dados necessários para aquela operação são enviados
              a esse órgão ou fornecedor, a pedido do escritório. Essas integrações só funcionam quando ligadas
              pelo escritório e algumas ainda estão em implantação.
            </p>
            <p className={P}>
              Também podemos fornecer dados a autoridades públicas quando exigido por lei ou decisão judicial.
              Não vendemos, alugamos ou comercializamos dados pessoais.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">5. Por quanto tempo guardamos</h2>
            <ul className={UL}>
              <li>
                <strong>Conta ativa:</strong> os dados ficam guardados enquanto houver assinatura ou teste grátis.
              </li>
              <li>
                <strong>Conta vencida:</strong> ao fim do teste grátis ou do período pago, sem assinatura, a conta
                fica somente para leitura e os dados ficam disponíveis por 60 (sessenta) dias para consulta e
                exportação. Depois desse prazo, os dados da carteira são excluídos automaticamente, com aviso por
                e-mail ao responsável pelo escritório pelo menos 72 (setenta e duas) horas antes. Os usuários são
                anonimizados e desativados.
              </li>
              <li>
                <strong>Registro do escritório e cobrança:</strong> nome, CNPJ/CPF do escritório e o histórico de
                cobrança continuam guardados depois do encerramento da conta, pelo menos pelo prazo da legislação
                tributária (5 anos), e servem também para impedir um novo teste grátis no mesmo documento.
              </li>
              <li>
                <strong>Registros de acesso:</strong> 6 (seis) meses, como exige o Marco Civil da Internet
                (Lei 12.965/2014, art. 15).
              </li>
              <li>
                <strong>Cópias de segurança:</strong> diárias, criptografadas, guardadas por até 30 (trinta) dias.
                Dados excluídos podem permanecer nelas até o fim desse prazo, sem uso para nenhuma outra
                finalidade além da recuperação do serviço em caso de falha.
              </li>
            </ul>
            <p className={P}>
              <strong>Atenção, escritório:</strong> a guarda por 5 anos de livros, notas fiscais, guias e demais
              documentos fiscais dos seus clientes é obrigação do escritório e dos clientes, não do FiscWise.
              Antes do fim do prazo de 60 dias, exporte o que precisar manter em{' '}
              <strong>Configurações → Perfil → Exportar meus dados</strong>.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">6. Segurança</h2>
            <p className={P}>
              Adotamos medidas técnicas e organizacionais para proteger os dados, incluindo: criptografia em
              trânsito (TLS), criptografia do banco e das cópias de segurança, senhas armazenadas com bcrypt
              (hash unidirecional), autenticação com expiração curta, isolamento de dados por escritório e
              controle de acesso por papéis. Tokens de acesso temporário (ex.: portal do cliente) são
              armazenados apenas como hash.
            </p>
            <p className={P}>
              Certificados digitais A1 enviados pelo escritório (do próprio escritório ou de seus clientes)
              ficam guardados criptografados, assim como a senha de cada certificado. Ninguém consegue
              baixá-los de volta, nem a equipe FiscWise. Eles são usados somente para emitir, consultar e
              cancelar notas fiscais a pedido do escritório, cada uso fica registrado, e o escritório pode
              bloqueá-los ou removê-los a qualquer momento.
            </p>
            <p className={P}>
              Se acontecer um incidente de segurança que possa causar risco ou dano relevante, avisamos a
              Autoridade Nacional de Proteção de Dados (ANPD), os escritórios afetados e os titulares, nos prazos
              da regulamentação da ANPD.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">7. Seus Direitos (LGPD, Art. 18)</h2>
            <p className={P}>Como titular de dados, você pode pedir:</p>
            <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground list-disc list-inside">
              <li><strong>Confirmação e acesso:</strong> saber se tratamos seus dados e receber uma cópia</li>
              <li><strong>Correção:</strong> atualizar dados incompletos, inexatos ou desatualizados</li>
              <li><strong>Anonimização, bloqueio ou eliminação:</strong> de dados desnecessários, excessivos ou tratados em desconformidade</li>
              <li><strong>Portabilidade:</strong> exportar seus dados em formato estruturado</li>
              <li><strong>Eliminação:</strong> dos dados tratados com base em consentimento</li>
              <li><strong>Informação sobre compartilhamento:</strong> com quem seus dados são compartilhados</li>
              <li><strong>Revogação do consentimento</strong> e <strong>oposição</strong> ao tratamento por legítimo interesse</li>
            </ul>
            <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
              Para exercer esses direitos, use <strong>Configurações → Perfil → Privacidade e dados</strong> no painel (exportar dados
              ou pedir exclusão) ou envie e-mail para <Email to="privacidade@fiscwise.com.br" />. Respondemos em
              até 15 (quinze) dias, como prevê o art. 19 da LGPD. Dados que a lei obriga a guardar só são
              eliminados depois do prazo legal.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">8. Cookies</h2>
            <p className={P}>
              Não usamos cookies de rastreamento, publicidade ou analytics de terceiros. O login usa apenas
              armazenamento local do navegador, estritamente necessário para manter você conectado. As métricas
              de acesso (Cloudflare Web Analytics) não usam cookies nem identificam a pessoa. Por isso não
              exibimos banner de consentimento de cookies.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">9. Transferência Internacional</h2>
            <p className={P}>
              O servidor da aplicação fica no Brasil (Google Cloud, região São Paulo). Alguns dados podem ser
              processados fora do Brasil (por exemplo, nos EUA) por fornecedores como Cloudflare, Supabase,
              Resend, Sentry e OpenAI. Essas transferências são feitas com cláusulas contratuais de proteção de
              dados desses fornecedores, como prevê o art. 33 da LGPD.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">10. Menores de Idade</h2>
            <p className={P}>
              O FiscWise é destinado exclusivamente a profissionais e empresas. Não coletamos
              intencionalmente dados de menores de 18 anos.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">11. Alterações nesta Política</h2>
            <p className={P}>
              Esta Política de Privacidade pode ser atualizada periodicamente. Notificaremos os
              usuários por e-mail sobre alterações materiais com antecedência mínima de 15 dias.
              A versão vigente sempre estará disponível nesta página com a data de atualização.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">12. Encarregado (DPO) e contato</h2>
            <p className={P}>
              Encarregado de Proteção de Dados: {COMPANY_LEGAL_NAME} —{' '}
              <Email to="privacidade@fiscwise.com.br" />
              <br />
              Você também pode reclamar à Autoridade Nacional de Proteção de Dados (ANPD):{' '}
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
              Consulte também os{' '}
              <Link to="/termos" className="font-medium text-primary hover:underline">
                Termos de Uso
              </Link>{' '}
              e o{' '}
              <Link to="/dpa" className="font-medium text-primary hover:underline">
                Acordo de Tratamento de Dados
              </Link>{' '}
              do FiscWise.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
