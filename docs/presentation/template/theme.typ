#import "@preview/touying:0.6.1": *
#import themes.stargazer: *

#let forest-deep = rgb("#0d3b2e")
#let forest-main = rgb("#1b5e20")
#let forest-soft = rgb("#e8f5e9")
#let amber = rgb("#f6c453")
#let slate = rgb("#263238")
#let paper = rgb("#fafaf8")

#let logo-badge = box(
  fill: forest-main,
  radius: 10pt,
  inset: (x: 10pt, y: 6pt),
)[
  #set text(fill: white, weight: "bold", size: 11pt)
  DG
]

#let deck-theme(meta) = stargazer-theme.with(
  aspect-ratio: "16-9",
  config-info(
    title: meta.title,
    subtitle: meta.subtitle,
    author: meta.author,
    date: meta.date,
    institution: meta.institution,
    logo: logo-badge,
  ),
  config-common(
    new-section-slide-fn: none,
  ),
  config-colors(
    primary: forest-main,
    primary-dark: forest-deep,
    secondary: forest-soft,
    tertiary: amber,
    neutral-lightest: paper,
    neutral-darkest: slate,
  ),
  alpha: 42%,
)
