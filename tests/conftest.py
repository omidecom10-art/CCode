import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from studio.data import load_brand  # noqa: E402
from studio.schemas import AdCopy, Beat, Claim, Quote, StaticAd, VideoScript  # noqa: E402

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


@pytest.fixture
def kit():
    return load_brand(ROOT / "data" / "sample_brand")


@pytest.fixture
def good_copy(kit):
    """Copy that should pass every deterministic check."""
    ad = StaticAd(id="A1", angle="Ice that lasts", headline="Still ice at the end of the day",
                  subhead="Cold for up to 24 hours. Fits most car cup holders.",
                  offer_line=kit.brand["offer"], cta=kit.brand["cta"],
                  claims=[Claim(text="Cold for up to 24 hours", evidence_ids=["B-claim-1"]),
                          Claim(text="Fits most car cup holders", evidence_ids=["B-claim-4"])],
                  testimonial=Quote(text="There was still ice rattling around when I got home.", review_id="R01"))
    video = VideoScript(id="V1", angle="One bottle all day", end_card="One bottle. Every stop.", beats=[
        Beat(line="Ice at seven in the morning.", caption="7am: fill it with ice", broll_id="broll_ice", evidence_ids=["R01"]),
        Beat(line="Still rattling when you get home.", caption="Still ice at 5pm", broll_id="broll_road", evidence_ids=["R01"]),
        Beat(line="Cold for up to twenty four hours in our lab tests.", caption="Cold up to 24 hours", broll_id="broll_trail", evidence_ids=["B-claim-1"]),
        Beat(line="From the desk to the gym to the trail.", caption="Desk. Gym. Trail.", broll_id="broll_gym", evidence_ids=["R16"]),
    ])
    return AdCopy(static_ads=[ad, ad.model_copy(update={"id": "A2"}), ad.model_copy(update={"id": "A3"})], video=video)
