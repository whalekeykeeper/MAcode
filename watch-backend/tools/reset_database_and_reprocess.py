# tools/reset_database.py
import asyncio

from sqlalchemy import delete

from app.core.session import async_session
from app.models import Video, Word, Families, Graph, GraphNode, GraphEdge, Vocabulary, Line, Sentence, \
    ChosenWords, GapFillingTable, User

TABLES_TO_CLEAR = [
    GapFillingTable,
    ChosenWords,
    GraphEdge,
    GraphNode,
    Graph,
    Families,
    Vocabulary,
    Word,
    Line,
    Sentence,
    Video,
    User,
]


async def reset_db():
    async with async_session() as session:
        for table in TABLES_TO_CLEAR:
            try:
                await session.execute(delete(table))
                print(f"✅ Cleared table {table.__tablename__}")
            except Exception as e:
                print(f"❌ Failed to clear {table.__tablename__}: {e}")
        await session.commit()


if __name__ == "__main__":
    asyncio.run(reset_db())
