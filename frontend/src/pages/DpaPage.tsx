/**
 * DpaPage — Acordo de Tratamento de Dados (DPA) do FiscWise.
 * Página pública, sem login. Faz parte dos Termos de Uso (seção 9).
 *
 * O escritório contábil é o CONTROLADOR dos dados da carteira dele; o FiscWise
 * é o OPERADOR (LGPD, art. 5º, VI e VII; arts. 37 a 40).
 *
 * Texto jurídico gerado na auditoria COMPLIANCE-40 (21/11/2026).
 * Revisar com advogado antes de considerar definitivo.
 */
import { Link } from 'react-router-dom';
import { ArrowLeft, FileLock2 } from 'lucide-react';
import { Logo } from '@/components/Logo';
import { COMPANY_CITY, COMPANY_CNPJ, COMPANY_LEGAL_NAME } from '@/lib/company';

const P = 'mt-2 text-sm leading-relaxed text-muted-foreground';
const UL = 'mt-2 space-y-1 text-sm text-muted-foreground list-disc list-inside';

export function DpaPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <Logo variant="full" theme="auto" size={28} />
          <Link
            to="/termos"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Voltar aos Termos
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-10 pb-20">
        <div className="mb-2 flex items-center gap-2">
          <FileLock2 className="h-7 w-7 text-primary" />
          <h1 className="text-3xl font-bold">Acordo de Tratamento de Dados</h1>
        </div>
        <p className="mb-8 text-sm text-muted-foreground">
          Versão 1.0 — Vigente desde 21/11/2026 · Anexo dos{' '}
          <Link to="/termos" className="text-primary hover:underline">
            Termos de Uso
          </Link>
        </p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground">
          <section>
            <h2 className="text-lg font-semibold">1. Partes e papéis</h2>
            <p className={P}>
              Este acordo vale entre o escritório contratante do FiscWise (<strong>Controlador</strong>) e{' '}
              <strong>{COMPANY_LEGAL_NAME}</strong>, nome comercial do empresário individual inscrito no CNPJ{' '}
              {COMPANY_CNPJ}, com sede em {COMPANY_CITY} (<strong>Operador</strong>). Ele se aplica aos dados
              pessoais que o Controlador cadastra ou envia ao FiscWise sobre os clientes dele, sócios,
              responsáveis, funcionários e usuários do Portal do Cliente (os <strong>Dados da Carteira</strong>).
              O aceite dos Termos de Uso no cadastro vale como aceite deste acordo.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">2. Objeto e finalidade</h2>
            <p className={P}>
              O Operador trata os Dados da Carteira somente para prestar o serviço contratado e conforme as
              instruções do Controlador, que são dadas pelo uso das funções do sistema e por escrito. O
              Operador não usa os Dados da Carteira para finalidade própria, não os vende e não os usa para
              treinar modelos de inteligência artificial.
            </p>
            <p className={P}>Tipos de dados tratados:</p>
            <ul className={UL}>
              <li>identificação e contato: nome, CPF, CNPJ, e-mail, telefone e endereço;</li>
              <li>dados societários e fiscais: regime tributário, CNAE, faturamento, notas fiscais, guias e obrigações;</li>
              <li>documentos enviados pelo Controlador ou pelos clientes dele no Portal do Cliente;</li>
              <li>certificados digitais A1 e suas senhas, guardados criptografados.</li>
            </ul>
            <p className={P}>
              O FiscWise não foi feito para tratar dados pessoais sensíveis (art. 5º, II da LGPD). O
              Controlador não deve cadastrá-los.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">3. Obrigações do Controlador</h2>
            <ul className={UL}>
              <li>ter base legal para o tratamento e informar os titulares, como exige a LGPD;</li>
              <li>cadastrar só os dados necessários para o serviço contábil;</li>
              <li>controlar quem da equipe tem acesso, por meio dos papéis de usuário do sistema;</li>
              <li>atender os pedidos dos titulares sobre os Dados da Carteira;</li>
              <li>guardar documentos fiscais pelo prazo legal, exportando-os antes do encerramento da conta.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">4. Obrigações do Operador</h2>
            <ul className={UL}>
              <li>tratar os dados somente conforme as instruções do Controlador e este acordo;</li>
              <li>
                manter medidas de segurança adequadas: criptografia em trânsito e em repouso, criptografia
                própria para certificados digitais e senhas, isolamento de dados por escritório, controle de
                acesso por papéis e registro de uso dos certificados;
              </li>
              <li>exigir sigilo de todas as pessoas autorizadas a acessar os dados;</li>
              <li>repassar ao Controlador, em até 5 (cinco) dias úteis, qualquer pedido de titular que receber;</li>
              <li>ajudar o Controlador a responder à ANPD e aos titulares, no que depender do sistema;</li>
              <li>
                avisar o Controlador sem demora injustificada, e em até 48 (quarenta e oito) horas da
                confirmação, sobre incidente de segurança que afete os Dados da Carteira, informando o que
                se sabe sobre a natureza do incidente, os dados e titulares afetados e as medidas adotadas.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-semibold">5. Suboperadores</h2>
            <p className={P}>
              O Controlador autoriza o Operador a usar os suboperadores abaixo, cada um sob contrato com
              cláusulas de proteção de dados:
            </p>
            <ul className={UL}>
              <li><strong>Google Cloud (Cloud Run)</strong> — servidor da aplicação, Brasil (São Paulo)</li>
              <li><strong>Supabase</strong> — banco de dados e armazenamento de arquivos</li>
              <li><strong>Cloudflare</strong> — hospedagem do site e cópias de segurança criptografadas (R2)</li>
              <li><strong>Resend</strong> — envio de e-mails transacionais</li>
              <li><strong>Sentry</strong> — monitoramento de erros técnicos</li>
              <li>
                <strong>OpenAI</strong> — leitura automática dos documentos enviados (texto extraído, nome do
                arquivo e tipo), resumo do cliente, Calculadora Fiscal e assistente, com CPF e CNPJ mascarados
                antes do envio (detalhes na seção 3 da Política de Privacidade)
              </li>
            </ul>
            <p className={P}>
              Quando o Controlador liga uma integração com órgão público ou fornecedor externo (Portal Nacional
              da NFS-e, prefeituras, SERPRO, WhatsApp Business), os dados necessários para cada operação são
              enviados a esse destinatário por instrução do Controlador. O Operador avisará por e-mail, com
              pelo menos 15 (quinze) dias de antecedência, a inclusão ou troca de suboperador; o Controlador
              pode se opor e, nesse caso, encerrar o contrato sem multa.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">6. Transferência internacional</h2>
            <p className={P}>
              Alguns suboperadores processam dados fora do Brasil (por exemplo, nos EUA). Essas transferências
              são feitas com as cláusulas contratuais de proteção de dados desses fornecedores, conforme o
              art. 33 da LGPD e a regulamentação da ANPD.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">7. Fim do contrato: devolução e eliminação</h2>
            <p className={P}>
              Ao fim do teste grátis ou da assinatura, o Controlador tem 60 (sessenta) dias para consultar e
              exportar os Dados da Carteira (Configurações → Perfil → Exportar meus dados). Depois desse prazo, com
              aviso por e-mail pelo menos 72 (setenta e duas) horas antes, o Operador elimina os Dados da
              Carteira, inclusive os arquivos, e anonimiza os usuários. Cópias de segurança são sobrescritas
              em até 30 (trinta) dias. O Operador só mantém o que a lei o obriga a guardar.
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">8. Comprovação</h2>
            <p className={P}>
              A pedido do Controlador, até uma vez por ano, o Operador fornece por escrito informações sobre
              as medidas de segurança e o cumprimento deste acordo. Os pedidos podem ser enviados para{' '}
              <a href="mailto:privacidade@fiscwise.com.br" className="text-primary hover:underline">
                privacidade@fiscwise.com.br
              </a>
              .
            </p>
          </section>

          <section>
            <h2 className="text-lg font-semibold">9. Responsabilidade e vigência</h2>
            <p className={P}>
              Cada parte responde pelos danos que causar ao violar a LGPD ou este acordo, nos termos dos
              arts. 42 a 45 da LGPD. Este acordo vale enquanto houver Dados da Carteira com o Operador e segue
              a lei e o foro dos Termos de Uso.
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
