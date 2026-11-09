from django.core.management.base import BaseCommand

from cmnsd import login_links


class Command(BaseCommand):
  help = (
    "Delete login links (cmnsd.models.LoginLink) that are used, revoked or "
    "expired and older than --days (30): nothing to keep them for once the "
    "admin history has the send and the use. Safe to repeat."
  )

  def add_arguments(self, parser):
    parser.add_argument('--days', type=int, default=30)

  def handle(self, *args, **options):
    gone = login_links.cleanup(options['days'])
    self.stdout.write(f"{gone} old login link(s) deleted.")
