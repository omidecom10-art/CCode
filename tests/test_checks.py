from studio.checks import check_copy, check_video_file
from studio.schemas import Claim, Quote


def test_clean_copy_passes(kit, good_copy):
    findings = check_copy(good_copy, kit)
    assert all(not v for v in findings.values()), findings


def _with(copy, **changes):
    ad = copy.static_ads[0].model_copy(update=changes)
    return copy.model_copy(update={"static_ads": [ad] + copy.static_ads[1:]})


def test_forbidden_phrase_is_caught(kit, good_copy):
    f = check_copy(_with(good_copy, subhead="Leak-proof lid, cold for 24 hours."), kit)["A1"]
    assert any("leak-proof" in x for x in f)


def test_superlative_best_is_caught_but_not_inside_words(kit, good_copy):
    assert any("'best'" in x for x in check_copy(_with(good_copy, headline="The best bottle you'll own"), kit)["A1"])
    assert not any("'best'" in x for x in check_copy(_with(good_copy, headline="Bestseller colours are back"), kit)["A1"])


def test_competitor_name_is_caught(kit, good_copy):
    assert any("competitor" in x for x in check_copy(_with(good_copy, subhead="Colder than SummitSip."), kit)["A1"])


def test_invented_number_is_caught(kit, good_copy):
    f = check_copy(_with(good_copy, subhead="Cold for up to 36 hours."), kit)["A1"]
    assert any("36" in x for x in f)


def test_unknown_evidence_and_competitor_only_claims(kit, good_copy):
    f = check_copy(_with(good_copy, claims=[Claim(text="Cold for 24 hours", evidence_ids=["R99"]),
                                           Claim(text="Unbreakable", evidence_ids=["C01"])]), kit)["A1"]
    assert any("R99" in x for x in f)
    assert any("competitor ad" in x for x in f)


def test_testimonial_must_be_verbatim_and_four_stars(kit, good_copy):
    f = check_copy(_with(good_copy, testimonial=Quote(text="Leaked a little in my backpack", review_id="R04")), kit)["A1"]
    assert any("2-star" in x for x in f)
    f = check_copy(_with(good_copy, testimonial=Quote(text="Best bottle ever made", review_id="R01")), kit)["A1"]
    assert any("not verbatim" in x for x in f)


def test_offer_and_cta_must_match_exactly(kit, good_copy):
    f = check_copy(_with(good_copy, offer_line="20% off today", cta="Buy"), kit)["A1"]
    assert any("Offer line" in x for x in f) and any("CTA" in x for x in f)


def test_video_rules(kit, good_copy):
    beats = good_copy.video.beats
    long_caption = beats[0].model_copy(update={"caption": "This caption is far too long for a phone screen", "broll_id": "nope"})
    v = good_copy.video.model_copy(update={"beats": [long_caption] + beats[1:]})
    f = check_copy(good_copy.model_copy(update={"video": v}), kit)["V1"]
    assert any("caption" in x for x in f) and any("unknown b-roll" in x for x in f)


def test_video_file_checks():
    ok = {"format": {"duration": "16.2"}, "streams": [{"codec_type": "video", "width": 1080, "height": 1920}, {"codec_type": "audio"}]}
    assert check_video_file(ok, 16.0) == []
    bad = {"format": {"duration": "40"}, "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]}
    assert len(check_video_file(bad, 16.0)) == 4
