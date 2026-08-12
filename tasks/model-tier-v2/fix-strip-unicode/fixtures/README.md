# textnorm

Text normalisation helpers for search keys and display labels.

- `strip_accents(text)` — return `text` with **accents removed** and **every other
  character preserved unchanged**. "Accent" means a Unicode combining mark: the
  acute in `café`, the diaeresis in `naïve`, the macron in `ā`. Everything that is
  not a combining mark survives untouched — that includes punctuation, currency
  symbols, and text in non-Latin scripts such as `東京` or `Ωμέγα`, which have no
  accents to remove and must come back exactly as they went in.
  The result is returned in composed (NFC) form, so equal-looking inputs written in
  composed and decomposed form give the same output.

Run the tests: `python -m unittest discover -s tests -t .`
