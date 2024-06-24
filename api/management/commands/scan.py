"""Django manager integration for scanning the directory."""

import uuid

from django.conf import settings
from django.core.management.base import BaseCommand

from api.directory_watcher import scan_photos
from api.models import User
from api.models.user import get_deleted_user


class Command(BaseCommand):
    """Django manager command."""

    help = "scan directory for all users"

    def add_arguments(self, parser):
        parser_group = parser.add_mutually_exclusive_group()
        parser_group.add_argument(
            "-f", "--full-scan", help=("Run full directory scan"), action="store_true"
        )
        parser_group.add_argument(
            "-s", "--scan-files", help=("Scan a list of files"), nargs="+", default=[]
        )

    def handle(self, *args, **options):

        # Add a single file.
        if options["scan_files"]:
            scan_files = options["scan_files"]
            deleted_user: User = get_deleted_user()
            for user in User.objects.all():
                user_files = []
                if user == deleted_user:
                    continue
                for scan_file in scan_files:
                    if scan_file.startswith(settings.CONSUME_DIR):
                        user_files.append(scan_file)
                if user_files:
                    scan_photos(user, False, uuid.uuid4(), scan_files=user_files)
            return

        # Directory scan
        deleted_user: User = get_deleted_user()
        for user in User.objects.all():
            if user != deleted_user:
                scan_photos(
                    user, options["full_scan"], uuid.uuid4(), settings.CONSUME_DIR
                )
