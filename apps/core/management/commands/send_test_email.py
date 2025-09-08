from django.core.management.base import BaseCommand
from django.conf import settings

try:
    from apps.core.email_utils import send_email
except Exception:
    send_email = None


class Command(BaseCommand):
    help = 'Trimite un email de test folosind SendGrid'

    def add_arguments(self, parser):
        parser.add_argument('--to', required=True, help='Adresa destinatarului')
        parser.add_argument('--subject', default='Test SendGrid', help='Subiectul emailului')
        parser.add_argument('--html', default='<p>Acesta este un email de test.</p>', help='Conținut HTML')

    def handle(self, *args, **options):
        to_addr = options['to']
        subject = options['subject']
        html = options['html']

        if not send_email:
            self.stderr.write(self.style.ERROR('send_email indisponibil (dependință lipsă)'))
            return

        api_key = getattr(settings, 'SENDGRID_API_KEY', '')
        if not api_key:
            self.stderr.write(self.style.ERROR('Lipsește SENDGRID_API_KEY în environment'))
            return

        try:
            send_email([to_addr], subject, html)
            self.stdout.write(self.style.SUCCESS(f'Trimis email de test către {to_addr}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Eroare la trimiterea emailului: {e}'))


