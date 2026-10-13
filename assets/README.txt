Optional portrait input:
Place your portrait photo at assets/profile-photo.jpg, then run:
  pip install -r scripts/requirements.txt
  python scripts/generate_ascii_portrait.py

The generator isolates a dark edge-connected background, converts the subject
to monochrome ASCII, and writes an SVG with a one-shot row-by-row reveal.
The photo is processed locally. Only the generated ASCII SVG is intended for
the profile. Pass a different input/output path as positional arguments, or
use --static to write a non-animated preview.
