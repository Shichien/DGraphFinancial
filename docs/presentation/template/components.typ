#import "@preview/showybox:2.0.4": showybox

#let forest-deep = rgb("#003300")
#let forest-main = rgb("#1B5E20")
#let forest-soft = rgb("#E8F5E9")
#let amber = rgb("#FFD54F")
#let slate = rgb("#263238")
#let paper = rgb("#FAFAFA")
#let mist = rgb("#F6F6F6")

#let stat-card(title, value, note: none, fill: forest-soft, accent: forest-main) = {
  block(
    width: 100%,
    inset: (x: 12pt, y: 10pt),
    radius: 5pt,
    stroke: 0.5pt + accent.lighten(42%),
    fill: fill,
  )[
    #set text(fill: accent, weight: "bold", size: 12pt)
    #set text(font: ("Times New Roman", "Source Han Serif SC", "SimSun"))
    #title
    #v(0.45em)
    #set text(fill: forest-deep, weight: "bold", size: 24pt)
    #set text(font: ("Times New Roman", "Source Han Serif SC", "SimSun"))
    #value
    #if note != none [
      #v(0.35em)
      #set text(fill: slate.lighten(12%), size: 10pt)
      #set text(font: ("Times New Roman", "Source Han Serif SC", "SimSun"))
      #note
    ]
  ]
}

#let chip(label, fill: forest-soft, stroke: forest-main.lighten(40%), fg: forest-main) = {
  box(
    inset: (x: 10pt, y: 5pt),
    radius: 4pt,
    fill: fill,
    stroke: 0.6pt + stroke,
  )[
    #set text(fill: fg, size: 10pt, weight: "medium")
    #set text(font: ("Times New Roman", "Source Han Serif SC", "SimSun"))
    #label
  ]
}

#let note-box(title: "", body, primary: forest-main, fill: forest-soft) = {
  block(
    width: 100%,
    inset: 0pt,
    fill: fill,
    stroke: (left: 5pt + primary),
  )[
    #pad(
      left: 10pt,
      right: 10pt,
      top: 8pt,
      bottom: 8pt,
    )[
      #if title != "" [
        #set text(font: ("Source Han Serif SC", "SimSun", "Times New Roman"), fill: primary, weight: "bold", size: 15pt)
        #title
        #v(0.45em)
      ]
      #set text(fill: slate, size: 14pt)
      #set text(font: ("Times New Roman", "Source Han Serif SC", "SimSun"))
      #body
    ]
  ]
}

#let insight-box(title: "", body) = {
  note-box(title: title, body, primary: forest-main, fill: forest-soft)
}

#let accent-box(title: "", body) = {
  note-box(title: title, body, primary: amber.darken(30%), fill: rgb("#FFFDE8"))
}
