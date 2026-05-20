"""Compile .po → .mo without GNU gettext tools (Windows-friendly).

Usage: python manage.py compile_translations
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Compile all .po files into .mo using polib (no GNU gettext required).'

    def handle(self, *args, **options):
        try:
            import polib
        except ImportError:
            self.stderr.write('polib is not installed. Run: pip install polib')
            return

        compiled = 0
        for locale_dir in settings.LOCALE_PATHS:
            for po_path in Path(locale_dir).rglob('*.po'):
                mo_path = po_path.with_suffix('.mo')
                po = polib.pofile(str(po_path))
                po.save_as_mofile(str(mo_path))
                self.stdout.write(f'  {po_path.relative_to(Path(locale_dir))} -> {len(po)} entries')
                compiled += 1
        self.stdout.write(self.style.SUCCESS(f'Compiled {compiled} .po file(s).'))
