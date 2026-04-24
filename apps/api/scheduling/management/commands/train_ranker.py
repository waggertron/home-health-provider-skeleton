from django.core.management.base import BaseCommand

from scheduling.training import generate_synthetic_history, train_ranker


class Command(BaseCommand):
    help = "Train the re-ranker on synthetic history and write the pickle artifact."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--seed", type=int, default=0)

    def handle(self, *args, **options) -> None:
        history = generate_synthetic_history(days=options["days"], seed=options["seed"])
        path = train_ranker(history)
        self.stdout.write(self.style.SUCCESS(f"Wrote {path} ({len(history)} rows)"))
