"""
training/data_collection.py — Image scraping utility for building the dataset
Collects images of Vietnamese dishes from search engines.

Usage:
    python training/data_collection.py --food pho_bo --count 400

Requirements:
    pip install icrawler requests pillow tqdm
"""

import argparse
import hashlib
import os
import shutil
import sys
import io
import time
import random
import concurrent.futures
from pathlib import Path

from PIL import Image
from tqdm import tqdm
import requests
from duckduckgo_search import DDGS

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Vietnamese food search queries (multi-lingual for better results)
FOOD_QUERIES = {
    "pho_bo": ["phở bò", "Vietnamese beef pho noodle soup", "pho bo Vietnam", "beef noodle soup Vietnam"],
    "bun_bo_hue": ["bún bò Huế", "bun bo Hue spicy noodle soup", "Vietnamese Hue beef noodle"],
    "bun_cha": ["bún chả Hà Nội", "bun cha Hanoi grilled pork noodle", "bun cha Vietnam"],
    "com_tam": ["cơm tấm sườn", "com tam broken rice Vietnam", "Vietnamese broken rice plate"],
    "banh_mi": ["bánh mì Việt Nam", "Vietnamese banh mi sandwich", "banh mi street food"],
    "goi_cuon": ["gỏi cuốn tôm thịt", "Vietnamese fresh spring rolls", "goi cuon nem cuon"],
    "nem_ran": ["nem rán Việt Nam", "Vietnamese fried spring rolls", "cha gio Vietnam"],
    "banh_cuon": ["bánh cuốn Hà Nội", "Vietnamese steamed rice rolls", "banh cuon Hanoi"],
    "chao_long": ["cháo lòng heo", "Vietnamese pork congee offal", "chao long Vietnam"],
    "xoi_ga": ["xôi gà", "Vietnamese sticky rice chicken", "xoi ga Vietnam sticky rice"],
}


def scrape_images(food_class: str, count: int = 350, output_dir: Path = None) -> int:
    """
    Scrape images for a specific food class.

    Parameters
    ----------
    food_class : str
        Food class ID (e.g. 'pho_bo').
    count : int
        Number of images to collect.
    output_dir : Path
        Output directory (default: datasets/raw/{food_class}/).

    Returns
    -------
    int
        Number of images successfully downloaded.
    """
    if output_dir is None:
        output_dir = ROOT_DIR / "datasets" / "raw" / food_class
    output_dir.mkdir(parents=True, exist_ok=True)

    # Count existing images in output_dir
    existing_images = list(output_dir.glob("*.jpg")) + list(output_dir.glob("*.png")) + list(output_dir.glob("*.jpeg"))
    if len(existing_images) >= count:
        print(f"   [SKIP] '{food_class}' already has {len(existing_images)} images. skipping.")
        return len(existing_images)

    needed_count = count - len(existing_images)
    queries = FOOD_QUERIES.get(food_class, [food_class])
    per_query = needed_count // len(queries) + 1

    print(f"   Target needed for '{food_class}': {needed_count} images ({per_query} per query)")
    total_saved = len(existing_images)
    ddgs = DDGS()

    # Create a helper function to download a single image
    def download_image(url):
        try:
            # Add a small user-agent to request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = requests.get(url, headers=headers, timeout=6)
            if res.status_code == 200:
                img = Image.open(io.BytesIO(res.content)).convert("RGB")
                img_hash = hashlib.md5(img.tobytes()).hexdigest()[:12]
                dest = output_dir / f"{food_class}_{img_hash}.jpg"
                if not dest.exists():
                    img.save(dest, "JPEG", quality=90)
                    return True
        except Exception:
            pass
        return False

    for query in queries:
        print(f"   Query: '{query}'")
        results = []
        
        # Add random delay to prevent rate limits
        delay = random.uniform(2.5, 4.5)
        time.sleep(delay)

        # Retry loop for DDG search rate limit
        for attempt in range(4):
            try:
                results = list(ddgs.images(query, max_results=per_query))
                break
            except Exception as e:
                err_str = str(e).lower()
                if "403" in err_str or "ratelimit" in err_str:
                    wait_time = (attempt + 1) * 15
                    print(f"    [RATELIMIT] Rate limited on '{query}'. Sleeping {wait_time}s before retry (Attempt {attempt+1}/4)...")
                    time.sleep(wait_time)
                else:
                    print(f"    DDG search failed for '{query}': {e}")
                    break
        else:
            print(f"    Failed to query '{query}' after retries. Moving to next query.")
            continue

        if not results:
            continue

        urls = [r['image'] for r in results]
        
        # Download images concurrently for speed
        saved_this_query = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(download_image, url) for url in urls]
            for future in concurrent.futures.as_completed(futures):
                if future.result():
                    total_saved += 1
                    saved_this_query += 1
        print(f"    -> Downloaded {saved_this_query} new images.")

    print(f"   Saved {total_saved} total unique images for '{food_class}'")
    return total_saved


def validate_dataset(raw_dir: Path) -> dict:
    """Check dataset statistics and flag issues."""
    stats = {}
    for food_dir in raw_dir.iterdir():
        if food_dir.is_dir():
            images = list(food_dir.glob("*.jpg")) + list(food_dir.glob("*.png"))
            stats[food_dir.name] = len(images)

    print("\n Dataset Statistics:")
    print(f"{'Food':<20} {'Count':>8} {'Status':>12}")
    print("-" * 45)
    for food, count in sorted(stats.items()):
        status = " OK" if count >= 200 else (" Low" if count >= 100 else " Insufficient")
        print(f"{food:<20} {count:>8} {status:>12}")
    print(f"\nTotal images: {sum(stats.values())}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NutriVision Image Scraper")
    parser.add_argument("--food", type=str, default="all",
                        help="Food class to scrape (or 'all')")
    parser.add_argument("--count", type=int, default=350,
                        help="Number of images per food class")
    parser.add_argument("--validate", action="store_true",
                        help="Only validate existing dataset stats")
    args = parser.parse_args()

    raw_dir = ROOT_DIR / "datasets" / "raw"

    if args.validate:
        validate_dataset(raw_dir)
        sys.exit(0)

    food_classes = list(FOOD_QUERIES.keys()) if args.food == "all" else [args.food]
    total = 0
    for food_class in food_classes:
        print(f"\n Collecting images for: {food_class}")
        n = scrape_images(food_class, count=args.count)
        total += n

    print(f"\n Total images collected: {total}")
    validate_dataset(raw_dir)
    print(
        "\n Next steps:\n"
        "  1. Review images, remove irrelevant/duplicate ones\n"
        "  2. Upload to Roboflow and label with bounding boxes\n"
        "  3. Enable augmentation and export in YOLOv8 format\n"
        "  4. Run: python training/train.py"
    )
