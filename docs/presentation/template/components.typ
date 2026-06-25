#import "@preview/showybox:2.0.4": showybox

#let forest-deep = rgb("#0d3b2e")
#let forest-main = rgb("#1b5e20")
#let forest-soft = rgb("#e8f5e9")
#let amber = rgb("#f6c453")
#let slate = rgb("#263238")
#let paper = rgb("#fafaf8")
#let mist = rgb("#f2f5f3")

#let stat-card(title, value, note: none, fill: forest-soft, accent: forest-main) = {
  block(
    width: 100%,
    inset: 14pt,
    radius: 14pt,
    stroke: 0.6pt + accent.lighten(35%),
    fill: fill,
  )[
    #set text(fill: accent, weight: "bold", size: 12pt)
    #title
    #v(0.45em)
    #set text(fill: forest-deep, weight: "bold", size: 24pt)
    #value
    #if note != none [
      #v(0.35em)
      #set text(fill: slate.lighten(15%), size: 10pt)
      #note
    ]
  ]
}

#let chip(label, fill: forest-soft, stroke: forest-main.lighten(40%), fg: forest-main) = {
  box(
    inset: (x: 10pt, y: 5pt),
    radius: 999pt,
    fill: fill,
    stroke: 0.6pt + stroke,
  )[
    #set text(fill: fg, size: 10pt, weight: "medium")
    #label
  ]
}

#let insight-box(title: "", body) = {
  showybox(
    title: title,
    frame: (
      border-color: forest-main,
      title-color: forest-main.lighten(25%),
      body-color: paper,
      radius: 12pt,
    ),
    title-style: (
      boxed-style: (
        radius: 12pt,
      ),
    ),
  )[
    #set text(fill: slate, size: 14pt)
    #body
  ]
}

#let accent-box(title: "", body) = {
  showybox(
    title: title,
    frame: (
      border-color: amber.darken(20%),
      title-color: amber,
      body-color: rgb("#fffaf0"),
      radius: 12pt,
    ),
    title-style: (
      boxed-style: (
        radius: 12pt,
      ),
    ),
  )[
    #set text(fill: slate, size: 14pt)
    #body
  ]
}
