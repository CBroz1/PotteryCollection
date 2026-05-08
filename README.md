# PotteryCollection

A poetry collection typeset with LaTeX. `src.md` is the source of truth — edit it for content; edit `config.yaml` for style. The PDF is built from those two files.

## Dependencies

- **pdflatex** — TeX Live 2020+ (or MiKTeX). Required LaTeX packages: `verse`, `geometry`, `newpxtext` (or `ebgaramond`/`newtxtext`), `microtype`, `setspace`, `titlesec`, `emptypage`, `hyperref`.
- **Python 3.9+** with **pyyaml** — used by `md2tex.py` to convert Markdown to LaTeX. Install via `pip install pyyaml` or use the `fun` conda environment.

## Build

```bash
make          # generate main.tex and compile PotteryCollection.pdf
make tex      # generate main.tex only (no LaTeX compile)
make clean    # remove all generated files (aux/, main.tex, PDF)
```

If the `fun` conda environment is not active, override the Python interpreter:

```bash
make PYTHON=python3
```

Aux files (`.aux`, `.toc`, `.log`, etc.) are written to `aux/` to keep the project root clean. `main.tex` is also a generated artifact — do not edit it directly.

## Configuration

All style options live in `config.yaml`:

| Key | Options | Description |
|-----|---------|-------------|
| `document.font_size` | `10`, `11`, `12` | Base font size (pt) |
| `document.paper` | `letterpaper`, `a4paper` | Paper size |
| `style.font` | `palatino`, `garamond`, `times`, `default` | Body font |
| `style.poem_title_align` | `left`, `center` | Poem title alignment |
| `style.spread` | e.g. `1.1` | Line spread multiplier |
| `style.include_toc` | `true`, `false` | Include table of contents |
| `geometry.*` | e.g. `"1.25in"` | Page margins (top/bottom/inner/outer) |

## Source format

`src.md` uses standard Markdown headings to define structure:

- `# Title` — chapbook title
- `## I` — section/part (Roman numeral)
- `### Poem Title` — individual poem
- Blank lines separate stanzas; trailing spaces on lines are ignored (LaTeX handles line breaks).
