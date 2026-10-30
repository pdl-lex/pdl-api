# Overview

This module contains the AwbXmlTransformer class, which transforms AWB (Althochdeutsches Wörterbuch) XML data into a structured format suitable for the target model.

### Source data
The XML was provided by the Sächsische Akademie der Wissenschaften zu Leipzig (SAW):
https://cloud.saw-leipzig.de/s/3bdGE2r49M6yPFR

It is TEI-P5 (not Lex-0), created by the TCDH as the result of the retro-digitization. Each file contains only the `<entry>` container, without the surrounding TEI structure. The SAW is working on deeper markup and possibly a Lex-0 version.

### Folder layout
- `raw/`: original XML as delivered (gitignored)
- `data/`: preprocessed XML, input for the transformer (gitignored)
- `output/`: transformer output (gitignored)
- `entity_mapping.csv`: Unicode mapping for the TCDH-specific entities
- `gender_mapping.csv`, `pos_mapping.csv`: normalization of gender and POS


### Preprocess, Run & Validate

```bash
uv run python -m app.transformers.awb.preprocess

uv run python -m app.transformers.lex_transformer awb -p app/transformers/awb/data -o app/transformers/awb/output/output.jsonl

uv run python -m app.transformers.lex_validator app/transformers/awb/output/output.jsonl
```

The validator checks the output against the `Entry` model and writes errors to `validation_errors.tsv` (see `--errorfile`).


### Preprocessing (preprocess.py)
The raw XML uses named entities without a DTD, so it cannot be parsed. `preprocess.py` reads `raw/`, replaces the entities with Unicode characters and writes well-formed XML to `data/`:
- HTML5 entities (e.g. `&aelig;`) are resolved via the Python standard library.
- TCDH-specific entities (e.g. `&ovabove;`, `&lslash;`) are resolved via `entity_mapping.csv`. The `note` column records how each mapping was verified (checked on the AWB website, or derived from context / the entity name).
- The XML built-ins (`&amp;` `&lt;` `&gt;` `&quot;` `&apos;`) are kept.
- An unknown entity aborts the run and lists file and entity name. Add it to `entity_mapping.csv` and run again.


It supports the following fields, as specified in the Lexoterm-Lemma-Kopfdaten-Modell:


## Umfang: Minimal
- Lemma/Stichwort:
      def headword: aus form[@type='headword']/form[@type='lemma']
      TODO Homographen-Index ist immer 0; Kennzeichnung von Homographen im XML unklar (bei SAW nachfragen)
- Vollständige URL zum Eintrag im Ursprungs-WB:
      def _build_source_url: https://awb.saw-leipzig.de/AWB?lemid=<sourceId>


## Umfang: Basis
- Grammatik-Angaben: Wortart, [kein Numerus], Genus:
      def pos: Rohwert aus form[@type='lemma']/@n, z.B. "st. m.", "adj.", "pron. pers."
      def gender: aus demselben Wert abgeleitet ("m.", "f.", "n." oder None)
      beide werden in postprocess normalisiert zu nPos und nGender
- Erste Bedeutung, Hauptbedeutung oder Anrisstext davon:
      def transform_sense, dort ggf. nur die erste ausgeben
- Anzahl der vorhandenen Bedeutungen:
      möglich über len(flat_senses)
- Sachgruppe:
      nicht vorhanden, da AWB keine Sachgruppen angibt
- Liste weiterer vorhandener Rubriken (aber ohne deren Inhalte):
      def _detect_additional_info_types: Etymologie (verweisblock), Formen (formblock), Kommentar (kommentarblock)


## Umfang: Detail
- Alle Bedeutungen:
      def transform_sense
- evtl. einzelne Mediendateien:
      nicht vorhanden, AWB enthält keine Abbildungen


## Umfang: Maximal
- Alle Textinformationen zu Etymologie, Formen, Komposita, etc.:
       TODO Implementation fehlt. Zieldatenstruktur fehlt.
- ausgewählte Belege:
      def transform_sense: der Belegtext einer Bedeutung als ein einziger cit-Eintrag (type "attested"), nicht in einzelne Belege zerlegt
- Enthält NICHT: Formenteil, Kommentarteil, externe Verweise (DWB, Lexer), Literaturangaben


# Notes

### Senses
Only `<sense ana="bedeutungsblock">` is transformed. Sub-senses are nested `<sense>` elements; the nesting in the XML is used, not the `level` attribute (which is not always consistent, e.g. bringan).
- `n`: sense number from the `n` attribute (e.g. "1", "a", "α", "II"); missing for unnumbered blocks.
- `sourceId`: the `value` attribute (volume.column.line in the printed edition, e.g. "4.0126.31"). Senses have no xml:id; `value` is present and unique in all sample entries.

The XML has no separate element for the definition. Definition and citations are one running text; the definition is only recognizable by its formatting (italic/spaced at the start of the block). `split_sense_text` therefore takes the leading `<hi>`/`<lb>` elements up to the first plain text as definition and puts the rest into `cit`. This works for most senses but not all:
- truncated definitions where the italics are interrupted, e.g. thankôn 2 ("jmdm."), blint 1a ("körperlich blind, Gegensatz")
- empty definitions, e.g. bret 2a
- thû is structured by forms rather than meanings ("Nom. Sing.", "nach ..."). The case blocks ("Nom. Sing.", "Gen. Sing.", ...) are empty senses; their sub-senses 1/2 are siblings, not children, so `n` values repeat at the top level. Most of the content sits in `formblock`s nested in the senses and is therefore not part of `cit`.
- bringan starts with three `bedeutungsblock`s that actually contain forms ("Praes.:", "Praet.:", "Part. Praet.:"), so their definition reads e.g. "Praes.: prink-: 1. sg. -u" and they inflate the sense count.

Nested `formblock`/`kommentarblock` inside a meaning block are skipped (see "Enthält NICHT"), only text following them is kept.

`<choice>` contains both `<orig>` (hyphenated) and `<reg>`; only `<reg>` is used.

TODO Ask SAW whether definitions and citations can be marked up explicitly (e.g. `<def>`, `<cit>` in Lex-0).

In âband, 1a and 1b are not nested in sense 1 but siblings at the top level (data issue).

### POS Mapping
The AWB uses abbreviations that combine inflection class, POS and gender (e.g. "st. m." = starkes Maskulinum). `pos_mapping.csv` maps them to the normalized POS. Only the values in the sample are mapped; unknown values give nPos = None.
TODO Extend the mapping with the full list of AWB abbreviations (ask SAW).

### Variants
form[@type='headword']/form[@type='variant'], only thû (thu) in the sample.

### Numerus
Numerus does not appear in the AWB sample data set.
