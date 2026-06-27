PYTHON   ?= conda run -n fun python3
LATEX    ?= pdflatex
LFLAGS   = -interaction=batchmode -halt-on-error -output-directory=aux
TARGET   = PotteryCollection.pdf
SPREAD   = PotteryCollection-spread.pdf
PRINT    = PotteryCollection-print.pdf

.PHONY: all tex clean

# 'all' is phony so pdflatex always runs.
# 'main.tex' is a real target so it is only regenerated when its sources change.
all: main.tex | aux
	$(LATEX) $(LFLAGS) main.tex
	$(LATEX) $(LFLAGS) main.tex
	mv aux/main.pdf $(TARGET)
	$(MAKE) $(SPREAD)
	$(MAKE) $(PRINT)

# Two 6×9 pages imposed side-by-side on a 12×9 landscape sheet.
# A leading '{}' inserts a blank page so the title page sits on the right
# (recto) of the first spread, mirroring how it would appear in the bound book.
$(SPREAD): $(TARGET)
	pdfjam --nup 2x1 --noautoscale true --papersize '{12in,9in}' \
	       $(TARGET) '{},1-' -o $(SPREAD)

# Saddle-stitch imposition for center-fold binding.
# pdfjam --booklet true reorders pages so that printing double-sided and folding
# at the center produces a correctly sequenced booklet.  For N pages the sheet
# order is: front [N,1], back [2,N-1], front [N-2,3], back [4,N-3], …
# N must be a multiple of 4; pdfjam pads with blank pages if needed.
$(PRINT): $(TARGET)
	pdfjam --booklet true --noautoscale true --papersize '{12in,9in}' \
	       $(TARGET) -o $(PRINT)

main.tex: src.md config.yaml md2tex.py
	$(PYTHON) md2tex.py

aux:
	mkdir -p aux

tex: main.tex

clean:
	rm -rf aux main.tex $(TARGET) $(SPREAD) $(PRINT)
