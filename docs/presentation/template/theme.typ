#import "@preview/touying:0.6.1": *
#import themes.stargazer: *

#let forest-deep = rgb("#191970")
#let forest-main = rgb("#4169E1")
#let forest-soft = rgb("#F0F8FF")
#let amber = rgb("#FF6347")
#let slate = rgb("#263238")
#let paper = rgb("#FAFAFA")

#let logo-badge = image("../assets/raicom-logo.png", height: 20pt)

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
  alpha: 45%,
)
