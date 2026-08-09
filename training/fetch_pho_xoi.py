"""One-off Bing collector retained to document the Pho/Xoi data supplement."""

import hashlib
import shutil
import warnings
from pathlib import Path

from icrawler.builtin import BingImageCrawler
from PIL import Image

warnings.filterwarnings("ignore")

FOOD_QUERIES = {
    "pho": [
        "phở bò",
        "phở gà",
        "Vietnamese beef pho noodle soup",
        "pho bo Vietnam",
        "beef noodle soup Vietnam",
        "Vietnamese chicken pho",
    ],
    "xoi": [
        "xôi",
        "Vietnamese xoi sticky rice",
        "xoi sticky rice",
        "xôi mỡ hành",
    ],
}

TARGETS = {"pho": 150, "xoi": 250}
ROOT_DIR = Path(__file__).parent.parent
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _list_images(directory: Path) -> list[Path]:
    return [path for path in directory.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS]


def fetch() -> None:
    for food, target in TARGETS.items():
        output_dir = ROOT_DIR / "datasets" / "raw" / food
        output_dir.mkdir(parents=True, exist_ok=True)

        while True:
            existing = _list_images(output_dir)
            needed = target - len(existing)
            if needed <= 0:
                print(f"{food}: Already have {len(existing)}. Skipping.")
                break

            print(f"{food}: Have {len(existing)}, need {needed} more.")
            for query in FOOD_QUERIES[food]:
                if needed <= 0:
                    break

                print(f" -> Querying Bing for: {query} (Target up to {needed})")
                temp_dir = output_dir / "temp_bing"
                temp_dir.mkdir(exist_ok=True)
                try:
                    crawler = BingImageCrawler(
                        storage={"root_dir": str(temp_dir)},
                        log_level=50,
                    )
                    crawler.crawl(
                        keyword=query,
                        max_num=min(needed * 3 + 20, 150),
                        min_size=(224, 224),
                    )

                    saved = 0
                    for image_file in temp_dir.iterdir():
                        if needed <= 0:
                            break
                        if image_file.suffix.lower() not in IMAGE_EXTENSIONS:
                            continue
                        try:
                            with Image.open(image_file) as source_image:
                                image = source_image.convert("RGB")
                            image_hash = hashlib.md5(image.tobytes()).hexdigest()[:12]
                            destination = output_dir / f"{food}_{image_hash}.jpg"
                            if not destination.exists():
                                image.save(destination, "JPEG", quality=90)
                                saved += 1
                                needed -= 1
                        except OSError:
                            pass
                        finally:
                            image_file.unlink(missing_ok=True)
                    print(f"    Saved {saved} images.")
                finally:
                    shutil.rmtree(temp_dir, ignore_errors=True)

            if len(_list_images(output_dir)) == len(existing):
                print(f"Could not find any more images for {food}. Stopping.")
                break


if __name__ == "__main__":
    fetch()
