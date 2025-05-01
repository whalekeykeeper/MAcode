import asyncio
import time

from sqlalchemy import select

from app.core.config import STATIC_DIR
from app.core.session import async_session
from app.core.video_service import process_new_video
from app.core.video_service import process_user_specific_data
from app.models import User, Video

USER_UUID = "8f925804-da14-4ae5-a365-37a635955bc9"

VIDEOS_TO_PROCESS = [
    {"url": "https://www.youtube.com/watch?v=0gks6ceq4eQ", "ytb_id": "0gks6ceq4eQ"},
    {"url": "https://www.youtube.com/watch?v=3Va3oY8pfSI", "ytb_id": "3Va3oY8pfSI"},
    {"url": "https://www.youtube.com/watch?v=8KkKuTCFvzI", "ytb_id": "8KkKuTCFvzI"},
    {"url": "https://www.youtube.com/watch?v=arj7oStGLkU", "ytb_id": "arj7oStGLkU"},
    {"url": "https://www.youtube.com/watch?v=Kcq-FxK-GK0", "ytb_id": "Kcq-FxK-GK0"},
    {"url": "https://www.youtube.com/watch?v=ONs9FCY74p0", "ytb_id": "ONs9FCY74p0"},
    {"url": "https://www.youtube.com/watch?v=qwCBEgjUluU", "ytb_id": "qwCBEgjUluU"},
    {"url": "https://www.youtube.com/watch?v=W0GpIMNTPYg", "ytb_id": "W0GpIMNTPYg"},
    {"url": "https://www.youtube.com/watch?v=ros3INVOQEU", "ytb_id": "ros3INVOQEU"},
    {"url": "https://www.youtube.com/watch?v=GRgqbsP_-uw", "ytb_id": "GRgqbsP_-uw"},
    {"url": "https://www.youtube.com/watch?v=g3AU44HfpfE", "ytb_id": "g3AU44HfpfE"},
    {"url": "https://www.youtube.com/watch?v=hTnJYRMixKs", "ytb_id": "hTnJYRMixKs"},
    {"url": "https://www.youtube.com/watch?v=jx4q82a6jHc", "ytb_id": "jx4q82a6jHc"},
    {"url": "https://www.youtube.com/watch?v=g9Szzb2YBXY", "ytb_id": "g9Szzb2YBXY"},
    {"url": "https://www.youtube.com/watch?v=NiKtZgImdlY", "ytb_id": "NiKtZgImdlY"},
    {"url": "https://www.youtube.com/watch?v=LMt8xm4t7XQ", "ytb_id": "LMt8xm4t7XQ"},
    {"url": "https://www.youtube.com/watch?v=wr6fQ4KpbRM", "ytb_id": "wr6fQ4KpbRM"},
    {"url": "https://www.youtube.com/watch?v=AxxMiihvKgg", "ytb_id": "AxxMiihvKgg"},
    {"url": "https://www.youtube.com/watch?v=3jIW5wW2WC0", "ytb_id": "3jIW5wW2WC0"},
    {"url": "https://www.youtube.com/watch?v=f2O6mQkFiiw", "ytb_id": "f2O6mQkFiiw"},
]


async def batch_process():
    start_time = time.time()
    async with async_session() as session:

        stmt = select(User).where(User.uuid == USER_UUID)
        user = (await session.execute(stmt)).scalar_one_or_none()

        if not user:
            user = User(uuid=USER_UUID, video_ids=[], word_ids=[])
            session.add(user)
            await session.commit()
            print(f"✅ Created new user with UUID {USER_UUID}")
        else:
            print(f"✅ Found existing user with ID {user.id}")

        for video_info in VIDEOS_TO_PROCESS:
            url = video_info["url"]
            ytb_id = video_info["ytb_id"]

            print(f"\n🚀 Starting processing video: {ytb_id}")

            try:
                static_folder = STATIC_DIR
                static_video_folder = static_folder / ytb_id
                mp4_file = static_video_folder / f"{ytb_id}.mp4"
                bilingual_vtt_file = static_video_folder / f"{ytb_id}_bilingual.vtt"

                if mp4_file.exists() and bilingual_vtt_file.exists():
                    print(f"📂 Found local video and subtitles for {ytb_id}. Skipping download.")
                    video = Video(
                        url=url,
                        ytb_id=ytb_id,
                        video_path=str(mp4_file),
                        vtt_path=str(bilingual_vtt_file),
                    )
                    session.add(video)
                    await session.flush()

                    from app.core.utils.subtitle_processor import SubtitleProcessor

                    processor = SubtitleProcessor()
                    await processor.process_subtitles(
                        ytb_id=ytb_id,
                        user_uuid=user.uuid,
                        session=session
                    )

                    user.video_ids.append(video.id)
                    session.add(user)
                    await session.commit()

                    stmt = select(Video.word_ids).where(Video.id == video.id)
                    video_word_ids = (await session.execute(stmt)).scalar_one_or_none()
                    if video_word_ids:
                        await process_user_specific_data(session, user, video.id, video_word_ids)
                    else:
                        print(f"⚠️ Warning: No word IDs found for video {ytb_id}")

                    print(f"✅ Local video {ytb_id} processed successfully!")

                else:
                    await process_new_video(
                        url=url,
                        ytb_id=ytb_id,
                        static_folder=STATIC_DIR,
                        user=user,
                        session=session
                    )
                    print(f"✅ Downloaded and processed video {ytb_id} successfully!")

            except Exception as e:
                print(f"❌ Error processing video {ytb_id}: {e}")

        print("\n🎉 All videos processed!")
    end_time = time.time()  # Record the end time
    elapsed_time = end_time - start_time  # Calculate elapsed time
    print(f"\n⏱️ Batch processing completed in {elapsed_time:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(batch_process())
