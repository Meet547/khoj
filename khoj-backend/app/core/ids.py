from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def next_case_number(db: AsyncSession) -> str:
    row = (
        await db.execute(
            text(
                "SELECT nextval('case_number_seq'), EXTRACT(YEAR FROM CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Kolkata')::integer"
            )
        )
    ).one()
    return f"KHJ-{row[1]}-{row[0]:05d}"
