# Approved language artwork

`language-source.png` is the source artwork used by the approved, uniformly scaled
language-button preview. `build_language_assets.cjs` uses the approved top-left
group as a common alpha mask for both languages and both color schemes.

The four clipped parts preserve their source geometry. They are recolored and
rendered together into 380 × 410 sprites, so the engine can scale the whole mark
with `scaleAspectFit` independently of the native keycap background. Active
Chinese and English use the same black/white color; inactive labels and corners
use the same gray. The source is kept here for reproducible resource builds and
is not needed by the imported skin.

The offline HTML embeds each 380 × 410 sprite separately and displays it with
`object-fit: contain`. It must not show the two-state atlas through an SVG
viewBox: the letterboxed area can expose the neighboring sprite.
