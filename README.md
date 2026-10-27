# AI Ad Agent + Product Finder

AI-agent som hittar vinnande dropshipping-produkter, skapar annonsmanus, analyserar annonser, redigerar video och tar bort vattenmarken. Byggt for att vara sa billigt som mojligt.

## Kostnad

| Funktion | Motor | Kostnad per anrop |
|----------|-------|-------------------|
| Hitta produkter | Claude Haiku 5.5 | ~$0.002 |
| Analysera produkt | Claude Haiku 5.5 | ~$0.002 |
| Produktrapport | Claude Haiku 5.5 | ~$0.003 |
| Validera produkt | Claude Haiku 5.5 | ~$0.001 |
| Jamfor produkter | Claude Haiku 5.5 | ~$0.001 |
| Skriv annonsmanus | Claude Haiku 5.5 | ~$0.001 |
| Generera hooks | Claude Haiku 5.5 | ~$0.001 |
| Iterera vinnande manus | Claude Haiku 5.5 | ~$0.001 |
| Analysera annons | Claude Haiku 5.5 | ~$0.0007 |
| Jamfor annonser | Claude Haiku 5.5 | ~$0.001 |
| Videoredigering | FFmpeg (lokalt) | $0.00 |
| Ta bort vattenmarke | OpenCV (lokalt) | $0.00 |
| Ta bort undertexter | OpenCV (lokalt) | $0.00 |
| Bildredigering | Pillow (lokalt) | $0.00 |

**Typiskt arbetsflode:** Hitta produkter + analysera + skriv manus + generera hooks = ~$0.007 (under 1 cent).

ALLT anvander Haiku (billigaste modellen). Ingen Sonnet-kostnad alls.

## Krav

- Python 3.10+
- FFmpeg (systeminstallation)
- Anthropic API-nyckel

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Redigera .env och lagg till din ANTHROPIC_API_KEY
```

## Anvandning

### Agent-lage (fritext — routen automatiskt)

```bash
python -m cli.main agent "Hitta vinnande produkter inom fitness"
python -m cli.main agent "Analysera om denna produkt ar bra for dropshipping: posture corrector"
python -m cli.main agent "Skriv ett 30s TikTok-manus for en hudvardskram"
python -m cli.main agent "Ta bort vattenmarket fran video.mp4 och trimma till 15 sekunder"
```

### Hitta vinnande dropshipping-produkter

```bash
# Hitta 10 produkter i en nisch
python -m cli.main find-products "fitness och halsa"

# Hitta 5 produkter i en specifik nisch
python -m cli.main find-products "husdjurstillbehor" -n 5
```

### Djupanalysera en produkt

```bash
# Full analys: efterfragan, marginaler, konkurrens, annonsideer, risker
python -m cli.main analyze-product "posture corrector"
python -m cli.main analyze-product "LED sunset lamp" --niche "home decor"
```

### Produktforskningsrapport

```bash
# Komplett rapport med strategi och handlingsplan
python -m cli.main product-report "skonhet och hudvard"
python -m cli.main product-report "kitchen gadgets" --budget 500 -o rapport.md
```

### Validera en produktide

```bash
# Snabbvalidering: ar marginalerna tillrackliga?
python -m cli.main validate-product "massage gun" --price 49.99 --cost 12.00
```

### Jamfor produkter

```bash
# Ranka produkter mot varandra
python -m cli.main compare-products "posture corrector" "massage gun" "LED sunset lamp"
```

### Skriv annonsmanus

```bash
# Komplett manus med hook, voiceover, visuella anvisningar och CTA
python -m cli.main write-script "Hudvardskram for unga kvinnor, fokus pa naturliga ingredienser" --platform tiktok --duration 30

# Pa Instagram
python -m cli.main write-script "Proteintillskott for gymmare" --platform instagram --duration 15
```

### Generera hooks for A/B-testning

```bash
# 10 olika hook-variationer
python -m cli.main hooks "Hudvardskram med 50% rabatt"

# 15 hooks for YouTube
python -m cli.main hooks "Onlinekurs i daytrading" --num 15 --platform youtube
```

### Iterera pa vinnande manus

```bash
# Skapa variationer av ett manus som funkar bra
python -m cli.main iterate-script --script vinnande_manus.txt "hooken och social proof" -n 5
```

### Analysera annonser

```bash
# Analysera en annons
python -m cli.main analyze -i "30s TikTok med produktdemo och social proof"
python -m cli.main analyze -i annons_beskrivning.txt -m metrics.json

# Jamfor flera annonser
python -m cli.main compare -i annonser.json

# Forslag pa forbattringar
python -m cli.main iterate -i "beskrivning av annonsen" -n 5
```

### Videoredigering

```bash
python -m cli.main edit -op trim -i video.mp4 -o trimmed.mp4 -s 00:00:05 -e 00:00:20
python -m cli.main edit -op merge --inputs v1.mp4 v2.mp4 -o merged.mp4
python -m cli.main edit -op overlay-text -i video.mp4 -o output.mp4 -t "Kop nu!" -p bottom
python -m cli.main edit -op resize -i video.mp4 -o output.mp4 --width 1080 --height 1920
python -m cli.main edit -op speed -i video.mp4 -o output.mp4 --speed 1.5
```

### Ta bort vattenmarken och undertexter

```bash
python -m cli.main remove-watermark -i bild.png -o ren.png
python -m cli.main remove-watermark -i video.mp4 -o ren.mp4
python -m cli.main remove-subtitles -i video.mp4 -o ren.mp4
```

## Arkitektur

```
agent/
  orchestrator.py      - Huvudagent som router uppgifter (Haiku, ~$0.0004/anrop)
  script_writer.py     - Skriver annonsmanus, hooks, variationer (Haiku)
  planner.py           - Bryter ner komplexa uppgifter i steg (Haiku)
tools/
  product_researcher.py - Hittar och analyserar dropshipping-produkter (Haiku)
  video_editor.py       - FFmpeg-wrapper (gratis)
  watermark_remover.py  - OpenCV inpainting (gratis)
  image_processor.py    - Pillow/OpenCV (gratis)
  ad_analyzer.py        - Annonsanalys (Haiku)
```

100% av LLM-anrop gar genom Haiku (~20x billigare an Sonnet). All mediebearbetning ar lokal och gratis.

## Tester

```bash
pip install pytest
pytest tests/ -v
```
