import datetime
from django.core.management.base import BaseCommand
from apps.payments.services.settlement import run_weekly_settlement


class Command(BaseCommand):
    help = 'Run weekly settlement for the most recently completed week (TC-012)'

    def handle(self, *args, **kwargs):
        today = datetime.date.today()
        # Most recent Monday (last completed week's start)
        last_monday = today - datetime.timedelta(days=today.weekday() + 7)

        self.stdout.write(f'Running settlement for week starting {last_monday}...')
        results = run_weekly_settlement(last_monday)
        self.stdout.write(
            self.style.SUCCESS(f'Done. {len(results)} settlement(s) processed.')
        )
        for s in results:
            self.stdout.write(
                f'  - {s.producer} | payout: {s.payout_pence}p '
                f'| commission: {s.commission_pence}p | status: {s.status}'
            )