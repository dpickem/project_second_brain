"""
Daily Note Generator

Generates daily notes using Jinja2 templates from config/templates/.
Template filename is configured via content_registry ('daily' content type).
Provides methods for creating daily notes and adding inbox items.
"""

from datetime import date
from pathlib import Path
import aiofiles
import aiofiles.os
import logging

from jinja2 import Environment, FileSystemLoader

from app.config.settings import TEMPLATES_DIR
from app.content_types import content_registry
from app.services.obsidian.vault import VaultManager

logger = logging.getLogger(__name__)


class DailyNoteGenerator:
    """Generates daily notes using template configured in content_registry."""

    def __init__(self, vault: VaultManager):
        self.vault = vault
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=False,
        )

    async def generate_daily_note(self, target_date: date | None = None) -> str:
        """Generate a daily note for the given date.

        Args:
            target_date: Date for the note (defaults to today)

        Returns:
            Path to the created/existing note
        """
        target_date = target_date or date.today()
        daily_folder = self.vault.get_daily_folder()
        await aiofiles.os.makedirs(daily_folder, exist_ok=True)

        filename = target_date.strftime("%Y-%m-%d.md")
        note_path = daily_folder / filename

        # Don't overwrite existing daily notes
        if note_path.exists():
            logger.debug(f"Daily note already exists: {note_path}")
            return str(note_path)

        # Render from template (template name from content registry)
        template_name = content_registry.get_jinja_template("daily")
        if not template_name:
            raise ValueError("No jinja_template configured for 'daily' content type")

        template = self._env.get_template(template_name)
        context = {
            "date_iso": target_date.strftime("%Y-%m-%d"),
            "date_full": target_date.strftime("%A, %B %d, %Y"),
            "date": target_date,
            "year": target_date.year,
            "month": target_date.strftime("%B"),
            "day": target_date.day,
            "weekday": target_date.strftime("%A"),
        }
        content = template.render(**context)

        async with aiofiles.open(note_path, "w", encoding="utf-8") as f:
            await f.write(content)

        logger.info(f"Created daily note: {note_path}")
        return str(note_path)

    async def add_inbox_item(self, target_date: date, item: str) -> None:
        """Add an item to the inbox section of a daily note.

        Creates the daily note if it doesn't exist.
        """
        note_path = Path(await self.generate_daily_note(target_date))

        content = await self.vault.read_note(note_path)

        # Find inbox section and append item
        inbox_marker = "## 📥 Inbox"
        if inbox_marker in content:
            parts = content.split(inbox_marker, 1)
            if len(parts) == 2:
                parts[1] = f"\n- {item}" + parts[1]
                content = inbox_marker.join(parts)
                await self.vault.write_note(note_path, content)
                logger.debug(f"Added inbox item to {note_path}")

    async def get_today_note_path(self) -> Path:
        """Get the path to today's daily note."""
        daily_folder = self.vault.get_daily_folder()
        filename = date.today().strftime("%Y-%m-%d.md")
        return daily_folder / filename

    async def ensure_today_note(self) -> str:
        """Ensure today's daily note exists, creating if needed."""
        return await self.generate_daily_note(date.today())
