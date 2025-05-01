from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import STATIC_DIR
from app.core.utils.subtitle_processor import SubtitleProcessor
from app.core.video_service import process_user_specific_data
from app.models import User, Video

VIDEOS_TO_PROCESS = [
    {"url": "https://www.youtube.com/watch?v=0gks6ceq4eQ", "ytb_id": "0gks6ceq4eQ"},
    {"url": "https://www.youtube.com/watch?v=3Va3oY8pfSI", "ytb_id": "3Va3oY8pfSI"},
    {"url": "https://www.youtube.com/watch?v=8KkKuTCFvzI", "ytb_id": "8KkKuTCFvzI"},
    {"url": "https://www.youtube.com/watch?v=arj7oStGLkU", "ytb_id": "arj7oStGLkU"},
    {"url": "https://www.youtube.com/watch?v=Kcq-FxK-GK0", "ytb_id": "Kcq-FxK-GK0"},
    {"url": "https://www.youtube.com/watch?v=LMt8xm4t7XQ", "ytb_id": "LMt8xm4t7XQ"},
    {"url": "https://www.youtube.com/watch?v=ONs9FCY74p0", "ytb_id": "ONs9FCY74p0"},
    {"url": "https://www.youtube.com/watch?v=qwCBEgjUluU", "ytb_id": "qwCBEgjUluU"},
    {"url": "https://www.youtube.com/watch?v=W0GpIMNTPYg", "ytb_id": "W0GpIMNTPYg"},
    {"url": "https://www.youtube.com/watch?v=wr6fQ4KpbRM", "ytb_id": "wr6fQ4KpbRM"}, ]


async def initialize_user_resources(user_uuid: str, session: AsyncSession):
    stmt = select(User).where(User.uuid == user_uuid)
    user = (await session.execute(stmt)).scalar_one_or_none()

    if not user:
        print(f"User {user_uuid} does not exist, cannot initialize.")
        return

    if user.video_ids:
        print(f"User {user_uuid} already initialized.")
        return

    for video_info in VIDEOS_TO_PROCESS:
        url = video_info["url"]
        ytb_id = video_info["ytb_id"]

        static_folder = STATIC_DIR / ytb_id
        mp4_file = static_folder / f"{ytb_id}.mp4"
        bilingual_vtt_file = static_folder / f"{ytb_id}_bilingual.vtt"

        if mp4_file.exists() and bilingual_vtt_file.exists():
            video = Video(
                url=url,
                ytb_id=ytb_id,
                video_path=str(mp4_file),
                vtt_path=str(bilingual_vtt_file),
            )
            session.add(video)
            await session.flush()

            processor = SubtitleProcessor()
            await processor.process_subtitles(
                ytb_id=ytb_id,
                user_uuid=user.uuid,
                session=session
            )

            user.video_ids.append(video.id)
            session.add(user)
            await session.commit()

            await process_user_specific_data(session, user, video.id, video.word_ids)

            print(f"Injected video {ytb_id} for user {user_uuid}.")

        url = video_info["url"]
        ytb_id = video_info["ytb_id"]

        static_folder = STATIC_DIR / ytb_id
        mp4_file = static_folder / f"{ytb_id}.mp4"
        bilingual_vtt_file = static_folder / f"{ytb_id}_bilingual.vtt"

        if mp4_file.exists() and bilingual_vtt_file.exists():
            video = Video(
                url=url,
                ytb_id=ytb_id,
                video_path=str(mp4_file),
                vtt_path=str(bilingual_vtt_file),
            )
            session.add(video)
            await session.flush()

            processor = SubtitleProcessor()
            await processor.process_subtitles(
                ytb_id=ytb_id,
                user_uuid=user.uuid,
                session=session
            )

            user.video_ids.append(video.id)
            session.add(user)
            await session.commit()

            await process_user_specific_data(session, user, video.id, video.word_ids)

            print(f"Injected video {ytb_id} for user {user_uuid}.")
