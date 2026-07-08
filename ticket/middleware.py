import logging

from django.conf import settings
from django.core.cache import cache

from ticket.services import auto_close_expired_solution_proposals


logger = logging.getLogger(__name__)


class AutoCloseSolutionProposalsMiddleware:
    """
    Executa periodicamente a regra de fechamento automatico de propostas.

    A verificacao e disparada por uso autenticado do sistema e limitada por cache
    para evitar consultas desnecessarias ao banco a cada request.
    """

    cache_key = "ticket:auto_close_solution_proposals:last_run"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)

        if user and user.is_authenticated:
            interval = getattr(settings, "TICKET_SOLUTION_AUTO_CLOSE_CHECK_SECONDS", 300)

            if cache.add(self.cache_key, True, timeout=interval):
                try:
                    auto_close_expired_solution_proposals()
                except Exception:
                    logger.exception("Erro ao concluir propostas de solucao automaticamente.")

        return self.get_response(request)
