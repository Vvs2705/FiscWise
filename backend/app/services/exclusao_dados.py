"""Exclusão automática dos dados de contas vencidas (pedido do dono, 14/11/2026).

Regra (Termos de Uso, seção 4; Política de Privacidade, seção 5):
conta vencida (teste acabou sem assinatura, assinatura cancelada/suspensa com o
período pago encerrado ou pré-pago vencido — ``plan_access.acesso_expirado``)
fica só para leitura e os dados ficam disponíveis por 60 dias. Depois disso são
excluídos automaticamente, com aviso por e-mail pelo menos 72 horas antes.

Rotina diária (scheduler ``excluir_dados_vencidos``):

1. AVISO — vencida há 57 dias ou mais, ainda vencida, sem aviso e sem exclusão:
   e-mail ao dono e aos administradores. ``tenants.exclusao_avisada_em`` só é
   gravado se o provedor aceitou o envio; sem aviso nada é excluído.
2. EXCLUSÃO — só quando TODAS valem:
   - a conta continua vencida agora (quem assinou depois do aviso é poupado);
   - vencida há 60 dias ou mais;
   - aviso aceito há 72 horas ou mais;
   - dados ainda não excluídos;
   - não é conta da equipe (``TEST_SUPERUSER_EMAILS``) nem tem pedido de
     exclusão LGPD em tratamento (``deletion_requested_at``);
   - interruptor ``EXCLUSAO_AUTOMATICA_ATIVA`` ligado (padrão "true").
3. Quem voltou a ter acesso depois do aviso tem o aviso apagado: se vencer de
   novo, recebe outro aviso antes de qualquer exclusão.

O que é apagado: as linhas do escritório em todas as tabelas com ``tenant_id``
e os arquivos dele no Storage. O que fica: o registro do escritório (nome e
CNPJ/CPF, que impedem um novo teste no mesmo documento), a assinatura, os
eventos de cobrança e a oferta (histórico financeiro). Usuários são
anonimizados e desativados.

Roda SEM contexto de escritório: com a RLS forçada (migração u7w8forcerls),
sem contexto as policies liberam tudo, como em qualquer rotina do sistema.
Cada escritório é uma transação própria; falha num não para os outros.
"""

from __future__ import annotations

import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

DIAS_ATE_EXCLUIR = 60  # RETENCAO_APOS_VENCER_DIAS (Termos v1.3, seção 4)
DIAS_ATE_AVISAR = DIAS_ATE_EXCLUIR - 3
ANTECEDENCIA_MINIMA = timedelta(hours=72)

# Ficam: registro do escritório (nome/CNPJ), histórico financeiro e usuários
# (anonimizados à parte, para não quebrar referências).
TABELAS_MANTIDAS = frozenset({
    "tenants", "tenant_subscriptions", "billing_webhook_events", "retention_offers", "users",
})


def exclusao_ativa() -> bool:
    return os.getenv("EXCLUSAO_AUTOMATICA_ATIVA", "true").strip().lower() not in ("false", "0", "no", "off")


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:  # SQLite devolve sem fuso
        return dt.replace(tzinfo=timezone.utc)
    return dt


def data_vencimento(tenant: Any) -> Optional[datetime]:
    """Quando a conta perdeu o acesso (início dos 60 dias). None = não vencida.

    Usa o mesmo critério de ``acesso_expirado``; a data vem da assinatura:
    teste → ``trial_ends_at``; demais → fim do período pago, ou o cancelamento.
    """
    from app.core.plan_access import acesso_expirado

    if not acesso_expirado(tenant):
        return None
    sub = getattr(tenant, "subscription", None)
    if sub is None:
        return None
    if getattr(sub, "status", None) == "trialing" and getattr(sub, "trial_ends_at", None):
        return _aware(sub.trial_ends_at)
    for campo in ("current_period_end", "cancelled_at", "trial_ends_at", "updated_at"):
        valor = _aware(getattr(sub, campo, None))
        if valor is not None:
            return valor
    return None


def exclusao_prevista(tenant: Any) -> Optional[datetime]:
    """Primeiro momento em que a exclusão pode acontecer (None = não prevista)."""
    if getattr(tenant, "dados_excluidos_em", None) is not None:
        return None
    venc = data_vencimento(tenant)
    if venc is None:
        return None
    prevista = venc + timedelta(days=DIAS_ATE_EXCLUIR)
    avisada = _aware(getattr(tenant, "exclusao_avisada_em", None))
    if avisada is not None:
        prevista = max(prevista, avisada + ANTECEDENCIA_MINIMA)
    return prevista


def _superusuarios() -> frozenset[str]:
    from app.core.plan_access import _SUPERUSER_EMAILS

    return _SUPERUSER_EMAILS


async def _usuarios(db: AsyncSession, tenant_id: uuid.UUID) -> list:
    from app.models.user import User

    return list((await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all())


def _destinatarios(usuarios: list) -> list[str]:
    from app.models.user import UserRole

    papeis = {UserRole.OWNER, UserRole.ADMIN}
    return sorted({
        u.email for u in usuarios
        if u.is_active and u.role in papeis and u.email and not u.email.endswith("@fiscwise.invalid")
    })


def _protegido(tenant: Any, usuarios: list) -> Optional[str]:
    """Motivo para nunca excluir automaticamente (None = pode)."""
    if getattr(tenant, "deletion_requested_at", None) is not None:
        return "pedido de exclusão LGPD em tratamento"
    supers = _superusuarios()
    if any((u.email or "").lower() in supers for u in usuarios):
        return "conta da equipe"
    return None


async def _caminhos_no_storage(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, list[str]]:
    """Arquivos do escritório por bucket (antes de apagar as linhas)."""
    from app.core import storage
    from app.core.document_links import DOCUMENTS_BUCKET, object_path_for
    from app.domain.guias.models import TaxGuide
    from app.models.operations import ClientDocument, CompanyDocument

    caminhos: dict[str, set[str]] = {DOCUMENTS_BUCKET: set(), "guides": set(), "receipts": set()}
    for model in (ClientDocument, CompanyDocument):
        for (url,) in (await db.execute(select(model.file_url).where(model.tenant_id == tenant_id))).all():
            path = object_path_for(url, tenant_id)
            if path:
                caminhos[DOCUMENTS_BUCKET].add(path)
    for pdf, comp in (
        await db.execute(
            select(TaxGuide.pdf_storage_path, TaxGuide.comprovante_storage_path).where(TaxGuide.tenant_id == tenant_id)
        )
    ).all():
        if pdf:
            caminhos["guides"].add(pdf)
        if comp:
            caminhos["receipts"].add(comp)
    # Uploads do bucket de documentos ficam em `<tenant_id>/...`: pega também os
    # que não estão mais ligados a nenhuma linha.
    listados = await storage.list_prefix(DOCUMENTS_BUCKET, f"{tenant_id}/")
    if listados:
        caminhos[DOCUMENTS_BUCKET].update(listados)
    return {bucket: sorted(paths) for bucket, paths in caminhos.items() if paths}


def _tabelas_do_escritorio() -> list:
    """Tabelas do modelo com `tenant_id`, filhas antes das mães (para as FKs)."""
    import app.domain.guias.models  # noqa: F401  (tax_guides fora de app.models)
    import app.models  # noqa: F401  (registra todos os modelos no metadata)
    from app.models.base import Base

    return [
        t for t in reversed(Base.metadata.sorted_tables)
        if "tenant_id" in t.c and t.name not in TABELAS_MANTIDAS
    ]


async def _tabelas_fora_do_modelo(db: AsyncSession, conhecidas: set[str]) -> list[str]:
    """No PostgreSQL, tabelas com `tenant_id` criadas só por migração."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return []
    rows = await db.execute(text(
        "SELECT table_name FROM information_schema.columns "
        "WHERE table_schema = 'public' AND column_name = 'tenant_id'"
    ))
    return sorted({r[0] for r in rows} - conhecidas - TABELAS_MANTIDAS)


async def _tabelas_existentes(db: AsyncSession) -> Optional[set[str]]:
    """Tabelas que existem no PostgreSQL (None em outro banco = confiar no modelo)."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return None
    rows = await db.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    ))
    return {r[0] for r in rows}


async def _apagar_linhas(db: AsyncSession, tenant_id: uuid.UUID) -> dict[str, int]:
    contagem: dict[str, int] = {}
    tabelas = _tabelas_do_escritorio()
    existentes = await _tabelas_existentes(db)
    if existentes is not None:
        # Modelo à frente da migração (deploy no meio): não tenta tabela que não existe.
        tabelas = [t for t in tabelas if t.name in existentes]
    for tabela in tabelas:
        res = await db.execute(delete(tabela).where(tabela.c.tenant_id == tenant_id))
        if res.rowcount:
            contagem[tabela.name] = int(res.rowcount)
    for nome in await _tabelas_fora_do_modelo(db, {t.name for t in tabelas}):
        res = await db.execute(text(f'DELETE FROM public."{nome}" WHERE tenant_id = :t'), {"t": tenant_id})
        if res.rowcount:
            contagem[nome] = int(res.rowcount)
    return contagem


async def _anonimizar(db: AsyncSession, tenant: Any, usuarios: list, agora: datetime) -> None:
    from app.core.security import get_password_hash

    for u in usuarios:
        u.email = f"excluido+{uuid.uuid4().hex}@fiscwise.invalid"
        u.full_name = None
        u.phone = None
        u.hashed_password = get_password_hash(secrets.token_urlsafe(32))
        u.is_active = False
        if hasattr(u, "marketing_opt_out_at"):
            u.marketing_opt_out_at = agora
        if hasattr(u, "tokens_valid_after"):
            u.tokens_valid_after = agora  # derruba sessões e tokens antigos
    for campo in ("phone", "address", "website"):
        if hasattr(tenant, campo):
            setattr(tenant, campo, None)
    tenant.dados_excluidos_em = agora


async def _enviar(destinos: list[str], assunto: str, html: str, chave: str) -> bool:
    from app.services.email_service import send_email

    ok = False
    for email in destinos:
        if await send_email(to=email, subject=assunto, html=html, idempotency_key=f"{chave}:{email}"):
            ok = True
    return ok


async def avisar(db: AsyncSession, tenant: Any, agora: datetime) -> bool:
    """Envia o aviso de exclusão. True se algum destinatário foi aceito."""
    import pytz

    from app.core.config import settings
    from app.services.email_service import render_exclusao_aviso_email

    usuarios = await _usuarios(db, tenant.id)
    destinos = _destinatarios(usuarios)
    if not destinos:
        logger.warning("exclusao_aviso_sem_destinatario tenant=%s", tenant.id)
        return False
    venc = data_vencimento(tenant)
    quando = max(venc + timedelta(days=DIAS_ATE_EXCLUIR), agora + ANTECEDENCIA_MINIMA)
    label = quando.astimezone(pytz.timezone("America/Sao_Paulo")).strftime("%d/%m/%Y")
    base = settings.APP_URL.rstrip("/")
    assunto, html = render_exclusao_aviso_email(
        data_exclusao_label=label,
        link_assinar=f"{base}/assinatura",
        link_exportar=f"{base}/configuracoes?aba=perfil",
    )
    if not await _enviar(destinos, assunto, html, f"exclusao_aviso:{tenant.id}:{venc.date().isoformat()}"):
        return False
    tenant.exclusao_avisada_em = agora
    return True


async def excluir(db: AsyncSession, tenant: Any, agora: datetime) -> dict[str, Any]:
    """Apaga os dados do escritório (arquivos, linhas) e anonimiza os usuários."""
    from app.core import storage
    from app.services.email_service import render_exclusao_confirmacao_email

    usuarios = await _usuarios(db, tenant.id)
    destinos = _destinatarios(usuarios)  # capturado ANTES de anonimizar

    arquivos = 0
    for bucket, paths in (await _caminhos_no_storage(db, tenant.id)).items():
        # Arquivos primeiro: se o banco falhar depois, a rotina repete amanhã
        # (apagar o que já não existe não dá erro).
        arquivos += await storage.remove_objects(bucket, paths) or 0

    linhas = await _apagar_linhas(db, tenant.id)
    await _anonimizar(db, tenant, usuarios, agora)
    await db.flush()

    resumo = {"linhas": linhas, "arquivos": arquivos, "usuarios_anonimizados": len(usuarios)}
    if destinos:
        assunto, html = render_exclusao_confirmacao_email()
        await _enviar(destinos, assunto, html, f"exclusao_feita:{tenant.id}")
    return resumo


async def processar(db_factory, agora: Optional[datetime] = None) -> dict[str, int]:
    """Rotina diária: avisa, exclui e limpa avisos de quem voltou a assinar."""
    from app.models.tenant import Tenant

    agora = agora or datetime.now(timezone.utc)
    ativa = exclusao_ativa()
    counts = {"avisados": 0, "aviso_falhou": 0, "excluidos": 0, "falhas": 0,
              "poupados": 0, "protegidos": 0, "aviso_cancelado": 0}

    async with db_factory() as db:
        ids = [
            r[0] for r in await db.execute(select(Tenant.id).where(Tenant.dados_excluidos_em.is_(None)))
        ]

    for tenant_id in ids:
        # Sessão própria por escritório: transação isolada e sem contexto de RLS
        # herdado de outro escritório.
        async with db_factory() as db:
            try:
                tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
                if tenant is None:
                    continue
                venc = data_vencimento(tenant)
                avisada = _aware(tenant.exclusao_avisada_em)
                if venc is None:
                    if avisada is not None:  # assinou depois do aviso
                        tenant.exclusao_avisada_em = None
                        await db.commit()
                        counts["aviso_cancelado"] += 1
                    continue
                if agora < venc + timedelta(days=DIAS_ATE_AVISAR):
                    continue
                usuarios = await _usuarios(db, tenant_id)
                motivo = _protegido(tenant, usuarios)
                if motivo:
                    counts["protegidos"] += 1
                    logger.info("exclusao_protegida tenant=%s motivo=%s", tenant_id, motivo)
                    continue
                if avisada is None:
                    if await avisar(db, tenant, agora):
                        await db.commit()
                        counts["avisados"] += 1
                    else:
                        await db.rollback()
                        counts["aviso_falhou"] += 1
                    continue
                pode = (
                    agora >= venc + timedelta(days=DIAS_ATE_EXCLUIR)
                    and agora >= avisada + ANTECEDENCIA_MINIMA
                )
                if not pode:
                    continue
                if not ativa:
                    counts["poupados"] += 1
                    logger.info("exclusao_desligada tenant=%s (EXCLUSAO_AUTOMATICA_ATIVA=false)", tenant_id)
                    continue
                resumo = await excluir(db, tenant, agora)
                await db.commit()
                counts["excluidos"] += 1
                logger.warning("dados_excluidos tenant=%s resumo=%s", tenant_id, resumo)
                await _auditar(db, tenant_id, resumo)
            except Exception as exc:  # noqa: BLE001 — um escritório não para os outros
                await db.rollback()
                counts["falhas"] += 1
                logger.error("exclusao_falhou tenant=%s: %s", tenant_id, exc, exc_info=True)

    logger.info("Exclusão automática de contas vencidas: %s", counts)
    return counts


async def _auditar(db: AsyncSession, tenant_id: uuid.UUID, resumo: dict[str, Any]) -> None:
    """Registro sem dados pessoais: só contagens."""
    from app.services.audit import log_audit_event

    await log_audit_event(
        db=db, tenant_id=tenant_id, action="lgpd.exclusao_automatica",
        entity_type="tenant", entity_id=tenant_id, actor_role="system", after_data=resumo,
    )


__all__ = [
    "ANTECEDENCIA_MINIMA", "DIAS_ATE_AVISAR", "DIAS_ATE_EXCLUIR", "data_vencimento",
    "exclusao_ativa", "exclusao_prevista", "processar",
]
