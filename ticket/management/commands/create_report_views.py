from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Cria ou recria as views de relatorios para Power BI."

    SQL_FILES = {
        "postgresql": "reports_views.sql",
        "sqlite": "reports_views_sqlite.sql",
    }

    def handle(self, *args, **options):
        vendor = connection.vendor
        filename = self.SQL_FILES.get(vendor)

        if not filename:
            raise CommandError(
                f"Banco '{vendor}' nao suportado. Use PostgreSQL em producao "
                "ou SQLite no ambiente de desenvolvimento."
            )

        sql_path = Path(settings.BASE_DIR) / "database" / filename
        if not sql_path.exists():
            raise CommandError(f"Arquivo SQL nao encontrado: {sql_path}")

        statements = [
            statement.strip()
            for statement in sql_path.read_text(encoding="utf-8").split(";")
            if statement.strip()
        ]

        try:
            with transaction.atomic(), connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
        except Exception as exc:
            raise CommandError(
                f"Nao foi possivel aplicar as views de relatorios: {exc}"
            ) from exc

        if vendor == "sqlite":
            self.stdout.write(
                self.style.WARNING(
                    "Views SQLite criadas apenas para desenvolvimento. "
                    "Use PostgreSQL para a camada oficial do Power BI."
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Views de relatorios aplicadas com sucesso ({vendor}, {len(statements)} comandos)."
            )
        )
