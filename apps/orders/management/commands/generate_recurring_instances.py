"""
Django management command to generate upcoming recurring order instances.

Usage:
    python manage.py generate_recurring_instances
    python manage.py generate_recurring_instances --days=14
    python manage.py generate_recurring_instances --verbose

This command should be run daily (e.g., via crontab or Celery Beat) to ensure
customers always have upcoming instances they can modify or skip before placement.

TC-018: Recurring Orders - Scheduler Implementation
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.orders.models import RecurringOrderTemplate
from apps.orders.services.recurring import generate_upcoming_instances


class Command(BaseCommand):
    help = 'Generate upcoming recurring order instances from active templates'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days ahead to generate instances (default: 7)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Print detailed output',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually creating instances',
        )

    def handle(self, *args, **options):
        days_ahead = options['days']
        verbose = options['verbose']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(f'🔄 Generating recurring order instances ({days_ahead} days ahead)...')
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('⚠️  DRY RUN MODE - No instances will be created'))

        # Get all active recurring templates
        templates = RecurringOrderTemplate.objects.filter(active=True)
        total_templates = templates.count()

        self.stdout.write(f'Found {total_templates} active templates')

        if total_templates == 0:
            self.stdout.write(self.style.WARNING('ℹ️  No active templates found'))
            return

        total_created = 0
        total_skipped = 0

        for template in templates:
            if verbose:
                self.stdout.write(f'  Processing: {template.name} (customer: {template.customer.user.email})')

            try:
                if not dry_run:
                    # Generate instances for this template
                    created = generate_upcoming_instances(template, days_ahead=days_ahead)
                else:
                    # In dry-run mode, just count what would be created
                    from datetime import datetime, time, timedelta
                    from dateutil.rrule import rrulestr
                    from django.db.models import F

                    today = timezone.localdate()
                    window_end = today + timedelta(days=days_ahead)
                    dtstart = datetime.combine(today, time.min)

                    rule = rrulestr(template.rrule, dtstart=dtstart)
                    upcoming_datetimes = rule.between(
                        dtstart,
                        datetime.combine(window_end, time.max),
                        inc=True,
                    )
                    upcoming_dates = {dt.date() for dt in upcoming_datetimes}
                    existing_dates = set(
                        template.instances
                        .filter(scheduled_for__in=upcoming_dates)
                        .values_list('scheduled_for', flat=True)
                    )
                    new_dates = sorted(upcoming_dates - existing_dates)
                    created = [f'Would create for {d}' for d in new_dates]

                created_count = len(created)
                total_created += created_count

                if created_count > 0:
                    if verbose:
                        for instance in created:
                            if dry_run:
                                self.stdout.write(f'    {instance}')
                            else:
                                self.stdout.write(f'    ✓ Created: {instance.scheduled_for}')
                    self.stdout.write(
                        self.style.SUCCESS(f'  ✓ {template.name}: {created_count} instance(s) created')
                    )
                else:
                    total_skipped += 1
                    if verbose:
                        self.stdout.write(f'  ⊘ {template.name}: No new instances needed')

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Error processing {template.name}: {str(e)}')
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write(f'  Total templates processed: {total_templates}')
        self.stdout.write(self.style.SUCCESS(f'  Total instances created: {total_created}'))
        self.stdout.write(f'  Templates with no new instances: {total_skipped}')

        if dry_run:
            self.stdout.write(self.style.WARNING('  (DRY RUN - No actual changes made)'))

        self.stdout.write(self.style.SUCCESS('✅ Done!'))


# ============================================================================
# SETUP INSTRUCTIONS
# ============================================================================
"""
To set up automatic daily generation of recurring instances, choose one:

OPTION 1: Linux Cron Job
  Edit crontab: crontab -e
  Add line: 0 1 * * * cd /path/to/project && python manage.py generate_recurring_instances --days=14
  (Runs daily at 1 AM, generates instances 14 days ahead)

OPTION 2: Windows Task Scheduler
  Create scheduled task with:
  Program: C:\\path\\to\\python.exe
  Arguments: manage.py generate_recurring_instances --days=14
  Schedule: Daily at 1:00 AM

OPTION 3: Celery Beat (Recommended for multi-server setups)
  settings/celery.py:
    from celery.schedules import crontab
    
    CELERY_BEAT_SCHEDULE = {
        'generate-recurring-instances': {
                        'task': 'your_project.tasks.run_generate_recurring_instances',
            'schedule': crontab(hour=1, minute=0),  # 1 AM daily
        },
    }
  
    your_project/tasks.py:
    from celery import shared_task
    
    @shared_task
        def run_generate_recurring_instances():
        from django.core.management import call_command
        call_command('generate_recurring_instances', days=14)

OPTION 4: Django APScheduler
  Install: pip install django-apscheduler
  
  settings.py:
    INSTALLED_APPS += ['django_apscheduler']
  
  tasks.py or management/commands/schedule_tasks.py:
    from django_apscheduler.models import DjangoJobExecution
    from django_apscheduler.schedulers import DjangoScheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    
    def start_scheduler():
        scheduler = DjangoScheduler()
        scheduler.add_job(
            generate_recurring_instances_task,
            'cron',
            hour=1,
            minute=0,
            id='generate-recurring-instances',
            name='Generate Recurring Order Instances',
            replace_existing=True,
        )
        scheduler.start()

Test the command:
  python manage.py generate_recurring_instances --dry-run --verbose
  python manage.py generate_recurring_instances --days=7 --verbose
"""
