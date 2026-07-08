from django.core.management.base import BaseCommand

from ticket.services import auto_close_expired_solution_proposals


class Command(BaseCommand):
    help = "Conclui chamados em proposta de solucao ha mais de 7 dias e atribui nota 5."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Quantidade de dias de espera antes da conclusao automatica.",
        )

    def handle(self, *args, **options):
        closed_count = auto_close_expired_solution_proposals(days=options["days"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{closed_count} chamado(s) concluido(s) automaticamente."
            )
        )
