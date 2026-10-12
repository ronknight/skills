---
name: print-tiff-to-web-images
description: Turn print-ready product TIFFs (CMYK, layered, 16-bit, clipping paths) into correct web images with ImageMagick or Pillow - right colours, real transparency without holes, white-background JPGs, sized and compressed PNG/JPG/WebP, normalized filenames, batch runs that never touch the masters, and a bulk check that the published CDN URLs resolve. Use when converting TIF/TIFF product photos for a website, email or marketplace, when converted images look dull, dark or have holes, when ImageMagick commands behave differently on Windows, or when checking which product images are missing online.
license: MIT
---

# Print TIFFs to web images

Product photos usually start as print masters: CMYK, sometimes layered,
sometimes 16-bit, often with a clipping path. A naive conversion gives dull or
inverted colours, white holes in the product, or files ten times too big.

## Rules before any batch

- **Masters are read-only.** Read from the master folder or share, write to a
  separate output folder, and never write next to the source.
- **Call `magick`, never `convert`.** In ImageMagick 7 the command is
  `magick in out`; `magick convert` is the deprecated v6 form. On Windows a bare
  `convert` can resolve to the system's `convert.exe`, a disk filesystem
  converter. Use the full path to `magick` from an environment variable or
  config.
- Take one sample per source type (CMYK, RGB, layered, with clipping path)
  through the pipeline and look at the results before running the whole set.

## Colour

Print TIFFs are often CMYK. Browsers expect sRGB.

```bash
# Accurate: convert through ICC profiles (embedded CMYK profile, or a standard one)
magick in.tif[0] -profile USWebCoatedSWOP.icc -profile sRGB.icc -strip out.png

# Acceptable when no profile is available
magick in.tif[0] -colorspace sRGB -strip out.png
```

- `[0]` reads only the first image. Layered or multi-page TIFFs otherwise turn
  into several output files or a stack of layers.
- `-depth 8` for 16-bit masters; the web doesn't need 16 bits per channel.
- `-strip` removes metadata and embedded profiles after conversion. Strip only
  after converting to sRGB, or the colours shift again.
- In Pillow, `Image.convert("RGB")` on a CMYK image ignores profiles and
  usually looks wrong. Use `PIL.ImageCms` with the source and sRGB profiles.

## Transparency without holes

`-transparent white` makes **every** white pixel transparent, including white
labels, packaging and highlights inside the product. Better options, in order:

1. **Use the clipping path** if the TIFF has one (common in product
   photography):

   ```bash
   magick in.tif[0] -alpha transparent -clip -alpha opaque +clip -colorspace sRGB -strip out.png
   ```

2. **Flood-fill from the corners** so only the connected background goes:

   ```bash
   magick in.tif[0] -colorspace sRGB -fuzz 3% -fill none \
     -draw "color 0,0 floodfill" -draw "color %[fx:w-1],%[fx:h-1] floodfill" out.png
   ```

   `-draw "alpha 0,0 floodfill"` does the same in ImageMagick 7. Raise
   `-fuzz` for off-white or JPEG-noisy backgrounds, a little at a time:
   too high and the fill leaks into light parts of the product.
3. Use a background-removal model only when the background isn't plain.

Check the result on a dark background, where holes and halos show.

## White-background JPG

```bash
magick in.tif[0] -colorspace sRGB -background white -alpha remove -alpha off \
  -resize "1200x1200>" -quality 85 -strip out.jpg
```

`-flatten` also composites layers onto the background colour. `>` in the
resize geometry only shrinks and never enlarges.

## Size and format

- Size by **pixels**, not DPI; the 300 DPI print setting means nothing on
  screen. Pick the largest size the page shows (2x for retina), and resize
  with `>` so small sources aren't upscaled.
- **JPG** for photos on white, **PNG** when you need transparency, **WebP**
  for both at smaller sizes (`-quality 80`) where every consumer supports it.
  Email clients have patchy WebP support; use JPG or PNG there.
- Compress after resizing: `pngquant` or `oxipng` for PNG, or a hosted
  compressor (keep its API key in an environment variable and watch its
  monthly quota).

## Filenames

- Derive the output name from the product identifier, not from whatever the
  photographer typed. Normalize variants such as `12345 (1).tif` to
  `12345-1.png`: lowercase extension, no spaces or parentheses.
- Check for collisions after normalizing; two sources mapping to one name
  means one image silently overwrites the other.

## Batch runs

- Skip outputs that already exist unless `--force` is passed, so reruns are
  cheap and resumable.
- Run a few processes in parallel at most. ImageMagick is already
  multi-threaded, and network shares are the usual bottleneck.
- Log every failure with the source path and the ImageMagick error, and keep
  going. Report the counts at the end: converted, skipped, failed.

## Check what's published

To find missing images on a CDN or site, check each expected URL:

```python
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def url_status(url: str, timeout: int = 15) -> int:
    try:
        with urlopen(Request(url, method="HEAD"), timeout=timeout) as r:
            return r.status
    except HTTPError as e:
        if e.code not in (403, 405):
            return e.code
    # Some CDNs reject HEAD; ask for one byte instead.
    req = Request(url, headers={"Range": "bytes=0-0"})
    try:
        with urlopen(req, timeout=timeout) as r:
            return r.status            # 206 or 200 both mean it exists
    except HTTPError as e:
        return e.code
```

Use a small thread pool (8 to 16 workers), write results to a dated CSV, and
compare it with the previous run to see what changed. Check only URLs on sites
you're responsible for.
