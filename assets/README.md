# Brand assets

fathom's visual identity, part of a shared house system across the project family.
The SVGs are self-contained - every glyph and shape is an outlined path, so nothing
depends on an installed font or a network fetch - and they are the source of truth:
edit them as code rather than re-exporting from a design tool.

| File | What | Where it is used |
|---|---|---|
| `fathom-mark-{light,dark}.svg` | The mark alone: accent tile with the three widening soundings cut out as true transparency | Favicon / avatar; anything down to 16 px |
| `fathom-wordmark-{light,dark}.svg` | The wordmark alone | Inline naming |
| `fathom-lockup-{light,dark}.svg` | Mark + wordmark | Headers |
| `fathom-hero-{light,dark}.svg` | 1280x240 banner: framed, centered lockup | Top of [README.md](../README.md) |
| `fathom-social-card.svg` / `.png` | 1280x640 dark card: lockup over a figure watermark | GitHub Settings -> Social preview (upload the PNG) |

## Embedding

GitHub renders READMEs in both light and dark; embed the theme pair with `<picture>`:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/fathom-hero-dark.svg">
  <img alt="fathom" src="assets/fathom-hero-light.svg" width="100%">
</picture>
```

The same pattern applies to the mark and the lockup.

## Tokens and rules

- Accent (sounding teal): tile `#00868E` on light, `#00A2AA` on dark; the accent
  rule is `#00666D` on light and `#4FBEC4` on dark. House neutrals: ink `#171B1F`, paper
  `#FBFBFA`, muted `#5C666E`, badge-label `#2A3238`.
- A rule ticked like a sounding scale sits under the wordmark.
- Badges: shields.io `flat-square`, always `labelColor=2A3238`; version and meta
  badges use `00666D`; CI and status badges keep shields' semantic defaults; at most
  five in the row.
- The tile is never outlined, recolored per context, or rotated; minimum mark size
  16 px.
- The assets carry no text beyond the wordmark.
