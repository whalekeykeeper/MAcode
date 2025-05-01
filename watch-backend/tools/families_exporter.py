import csv
from pathlib import Path
from typing import List

from sqlalchemy import select

from app.core.logger import logger
from app.core.session import async_session
from app.models import Families, Word

EXPORT_PATH = Path(__file__).parent / "families_export.csv"


async def export_families_to_csv(user_id: int):
    async with async_session() as session:
        logger.info(f"Fetching Families for user {user_id}...")
        stmt = select(Families).where(Families.user_id == user_id)
        families = (await session.execute(stmt)).scalars().all()

        if not families:
            logger.warning(f"No families found for user {user_id}.")
            return

        logger.info(f"Found {len(families)} families. Preparing export...")

        data_to_export = []
        for family in families:
            word_infos: List[str] = []
            for word_id in family.word_ids:
                stmt_word = select(Word).where(Word.id == word_id)
                word = (await session.execute(stmt_word)).scalar_one_or_none()
                if word:
                    cefr_level = word.cefr if word.cefr else ""
                    word_infos.append(f"{word.lemma};{word.word};{word.pos};{cefr_level}")
                else:
                    logger.warning(f"Word with id {word_id} not found.")
            word_infos_str = " | ".join(word_infos)

            data_to_export.append({
                "lemma": family.lemma,
                "word_infos": word_infos_str,
            })

        # Write to CSV
        with EXPORT_PATH.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["lemma", "word_infos"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for row in data_to_export:
                writer.writerow(row)

        logger.info(f"✅ Families exported to {EXPORT_PATH.absolute()}")


if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) != 2:
        print("Usage: poetry run python -m tools.families_exporter <user_id>")
    else:
        user_id = int(sys.argv[1])
        asyncio.run(export_families_to_csv(user_id))
