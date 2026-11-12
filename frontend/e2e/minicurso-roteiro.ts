/**
 * Roteiro narrado do Minicurso FiscWise.
 *
 * Cada aula é uma lista de capítulos: `label` aparece na lista de passos da
 * página do Minicurso e `fala` é o que a narradora diz (e vira a legenda).
 * A narração de cada aula é gerada de uma vez no ElevenLabs, com uma pausa
 * longa entre as falas, e depois cortada nas pausas em
 * e2e/minicurso-audio/<aula>-<n>.mp3 (ver scripts no gravador).
 *
 * Mudou uma fala? Gere de novo a narração daquela aula antes de regravar.
 */

export interface Capitulo {
  label: string
  fala: string
}

export const VOZ = { nome: 'Juliana - Bright and Encouraging', voice_id: 'nczLZ6GvJGozyc3FlLte', modelo: 'eleven_multilingual_v2' }

export const ROTEIRO: Record<string, Capitulo[]> = {
  'primeiros-passos': [
    { label: 'O tour de boas-vindas no primeiro acesso', fala: 'Olá! Boas-vindas ao FiscWise, a central do contador. No primeiro acesso, um tour rápido mostra onde fica cada coisa.' },
    { label: 'Painel, Foco de hoje, Clientes, Obrigações e Fechamento no menu', fala: 'No menu da esquerda ficam o Painel, o Foco de hoje, a carteira de clientes, as obrigações e o fechamento mensal. É tudo o que o escritório faz no dia a dia.' },
    { label: 'O botão Ajuda acompanha você em todas as telas', fala: 'Repare no botão Ajuda, lá no topo. Ele acompanha você em todas as telas.' },
    { label: 'O painel resume o dia do escritório', fala: 'Este é o painel. Num só lugar, você vê o que vence, o que está atrasado e quais clientes precisam de atenção. Cada número é um atalho direto para o assunto.' },
    { label: 'Foco de hoje: tudo que pede ação, por prioridade', fala: 'O Foco de hoje junta tudo o que pede ação, em ordem de prioridade: primeiro o que é crítico, depois o que vence hoje e na semana.' },
    { label: 'Ajuda: o passo a passo de cada página', fala: 'Ficou com dúvida em alguma tela? Clique em Ajuda. Aparece o passo a passo daquela página e o atalho para a aula em vídeo.' },
    { label: 'Todas as aulas ficam no Minicurso', fala: 'E todas as aulas ficam aqui, no Minicurso. Na próxima, você cadastra o seu primeiro cliente.' },
  ],
  'cadastrar-cliente': [
    { label: 'Abra Clientes e clique em Novo cliente', fala: 'Nesta aula, você cadastra um cliente em menos de um minuto. Abra Clientes no menu e clique em Novo cliente.' },
    { label: 'Digite o CNPJ: os dados vêm da Receita', fala: 'Não precisa digitar tudo. Digite só o CNPJ: a razão social, o e-mail e o telefone chegam direto da Receita Federal.' },
    { label: 'Escolha o regime tributário', fala: 'Escolha o regime tributário. É com ele que o FiscWise gera, todo mês, as obrigações certas para este cliente.' },
    { label: 'Complete e clique em Salvar cliente', fala: 'Complete o telefone, deixe uma observação para a equipe e clique em Salvar cliente.' },
    { label: 'O cliente já aparece na carteira', fala: 'Pronto! O cliente já aparece na carteira, e você encontra qualquer um pelo nome, CNPJ ou e-mail.' },
    { label: 'Vários clientes? Importe uma planilha Excel ou CSV', fala: 'Tem vários clientes para cadastrar? Use Importar planilha. Vale o nosso modelo em Excel ou um arquivo CSV exportado do seu sistema antigo.' },
    { label: 'Todos entram de uma vez, com relatório', fala: 'Em segundos, todos entram na carteira de uma vez, e um relatório mostra cada linha importada.' },
  ],
  obrigacoes: [
    { label: 'O resumo das obrigações da competência', fala: 'Em Obrigações, você vê tudo o que vence na competência: o que está pendente, o que já foi entregue e o que venceu.' },
    { label: 'As obrigações são geradas pelo regime do cliente', fala: 'As obrigações nascem sozinhas. O FiscWise lê o regime de cada cliente e cria o DAS, a DCTFWeb, a EFD-Reinf e as demais, já com o vencimento certo.' },
    { label: 'Filtre por prioridade para focar no urgente', fala: 'Para focar no urgente, filtre por prioridade. Aqui, só as críticas.' },
    { label: 'Busque pelo cliente ou pela obrigação', fala: 'Ou busque direto pelo cliente.' },
    { label: 'Clique em Iniciar quando começar', fala: 'Começou a trabalhar? Clique em Iniciar, e a equipe sabe que essa obrigação está com você.' },
    { label: 'Entregou? Clique no visto para dar baixa', fala: 'Entregou? Clique no visto. A obrigação vai para Entregues e o painel atualiza na hora.' },
  ],
  'fechamento-mensal': [
    { label: 'A esteira de fechamento de todos os clientes', fala: 'O fechamento mensal mostra a esteira de todos os clientes na competência, com um score de zero a cem para cada um.' },
    { label: 'Bloqueios mostram o que está faltando', fala: 'Quando falta alguma coisa, como o extrato bancário do cliente, o fechamento fica bloqueado e o motivo aparece aqui.' },
    { label: 'Abra o fechamento do cliente', fala: 'Abra o cliente que você vai fechar. Notas, guias, obrigações e documentos aparecem resumidos logo no topo.' },
    { label: 'Marque cada etapa do checklist', fala: 'Marque cada etapa do checklist conforme avança. O score sobe junto.' },
    { label: 'Com 100%, gere o dossiê em PDF', fala: 'Chegou a cem por cento? Clique em Gerar dossiê. O PDF reúne o mês do cliente, pronto para enviar.' },
  ],
  certificados: [
    { label: 'A validade de todos os certificados', fala: 'Certificado vencido trava o escritório. Aqui você acompanha a validade dos certificados digitais de todos os clientes.' },
    { label: 'Alerta 30 dias antes de vencer', fala: 'A barra mostra quanto tempo falta. Com menos de trinta dias, o cartão fica laranja e o alerta aparece no Foco de hoje.' },
    { label: 'Novo certificado: cliente e nome', fala: 'Para cadastrar, clique em Novo certificado, escolha o cliente e dê um nome fácil de reconhecer.' },
    { label: 'Tipo, vencimento e Salvar', fala: 'Informe o tipo, A1 ou A3, e a data de vencimento. Depois, é só salvar.' },
    { label: 'Avise o cliente com um clique', fala: 'Para pedir a renovação ao cliente, basta um clique em Avisar cliente.' },
  ],
  'portal-cliente': [
    { label: 'Escolha o cliente e veja o portal como ele vê', fala: 'O portal do cliente mostra exatamente o que o seu cliente vê. Escolha o cliente aqui em cima.' },
    { label: 'Fechamento, guias e pendências para o cliente', fala: 'Ele acompanha o andamento do fechamento, as guias para pagar e as pendências, sem precisar ligar nem mandar e-mail.' },
    { label: 'Clique em Enviar link de acesso ao portal', fala: 'Para dar acesso, clique em Enviar link de acesso ao portal.' },
    { label: 'Confira o e-mail e envie o link', fala: 'Confira o e-mail e envie. O cliente entra pelo link, sem precisar criar senha.' },
  ],
}

/** Texto enviado ao ElevenLabs: as falas da aula separadas por pausas longas. */
export function textoParaNarracao(aula: string): string {
  return ROTEIRO[aula].map((c) => c.fala).join(' <break time="2.5s" /> ')
}
