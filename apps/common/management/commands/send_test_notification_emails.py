from django.core.management.base import BaseCommand, CommandError

from apps.common.test_notification_emails import send_sample_notification_emails


class Command(BaseCommand):
    help = "Send all booking and payment notification templates to a target email address."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            required=True,
            help="Email address that should receive all test notifications.",
        )
        parser.add_argument(
            "--guest-name",
            default="Test Guest",
            help="Display name to use for the guest in the sample emails.",
        )
        parser.add_argument(
            "--host-name",
            default="Test Host",
            help="Display name to use for the host in the sample emails.",
        )
        parser.add_argument(
            "--listing-title",
            default="Demo Forest Cabin",
            help="Listing title to use in the sample emails.",
        )

    def handle(self, *args, **options):
        target_email = options["to"].strip()
        if not target_email:
            raise CommandError("--to is required.")

        send_sample_notification_emails(
            target_email=target_email,
            guest_name=options["guest_name"],
            host_name=options["host_name"],
            listing_title=options["listing_title"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Sent sample notification emails to {target_email}. "
                "Check the inbox or backend console output."
            )
        )
