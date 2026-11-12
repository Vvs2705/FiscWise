"""Paginação com teto para as listagens que devolvem lista simples.

O formato da resposta continua sendo a lista (o front não muda). Quem quiser
paginar passa ``limit``/``offset`` e lê o total no header ``X-Total-Count``.
"""

from dataclasses import dataclass, field

from fastapi import Query, Response
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIMIT = 200
MAX_LIMIT = 500
TOTAL_COUNT_HEADER = "X-Total-Count"


@dataclass(frozen=True)
class Page:
    limit: int
    offset: int
    # Resposta da requisição, para o header com o total (headers de uma
    # Response recebida por dependência entram na resposta final).
    response: Response | None = field(default=None, compare=False, repr=False)


def page_params(
    response: Response,
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Itens por página (máx. 500)"),
    offset: int = Query(default=0, ge=0, description="Quantos itens pular"),
) -> Page:
    return Page(limit=limit, offset=offset, response=response)


async def paginate(db: AsyncSession, statement: Select, page: Page) -> list:
    """Executa ``statement`` (já ordenado de forma determinística) com limit/offset.

    O total só custa um ``count(*)`` quando a página veio cheia ou vazia com
    offset: nos demais casos ele sai do próprio tamanho da página.
    """
    rows = list((await db.execute(statement.limit(page.limit).offset(page.offset))).scalars().all())
    if len(rows) < page.limit and (rows or page.offset == 0):
        total = page.offset + len(rows)
    else:
        count_stmt = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int((await db.execute(count_stmt)).scalar_one() or 0)
    if page.response is not None:
        page.response.headers[TOTAL_COUNT_HEADER] = str(total)
    return rows


def paginate_list(items: list, page: Page) -> list:
    """Mesma paginação para listas já carregadas (catálogos em cache)."""
    if page.response is not None:
        page.response.headers[TOTAL_COUNT_HEADER] = str(len(items))
    return list(items[page.offset : page.offset + page.limit])
