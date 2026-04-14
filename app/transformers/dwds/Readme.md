# Overview


### Run & Validate

```bash
uv run python -m app.transformers.lex_transformer dwds -p app\transformers\dwds\data -o app\transformers\dwds\output\output.jsonl

uv run python -m app.transformers.dwds.validate_output
```

This module contains the DwdsXmlTransformer class, which transforms DWDS XML data into a structured format suitable for the target model.

It supports the following fields, as specified in the Lexoterm-Lemma-Kopfdaten-Modell:


## Umfang: Minimal
- Lemma/Stichwort:
      def headword
- Vollständige URL zum Eintrag im Ursprungs-WB:
      def _build_source_url


## Umfang: Basis
- Grammatik-Angaben: Wortart, [kein Numerus], Genus:
      def pos, def gender; gender wird zudem in postprocess normalisiert zu nGender
- Erste Bedeutung, Hauptbedeutung oder Anrisstext davon:
      def transform_sense, dort ggf. nur die erste ausgeben
- Anzahl der vorhandenen Bedeutungen:
      möglich über len(flat_senses)
- Sachgruppe:
      nicht vorhanden, da DWDS keine Sachgruppen angibt
- Liste weiterer vorhandener Rubriken, z.B.: Etymologie, Synonyme, Komposita, etc. (aber ohne deren Inhalte):
      def _detect_additional_info_types


## Umfang: Detail
- Alle Bedeutungen:
      def transform_sense
- evtl. einzelne Mediendateien:
      def _extract_media_files (wertet nur Illustrationen aus)


## Umfang: Maximal
- Alle Textinformationen zu Etymologie, Synonyme, Komposita, etc.:
       TODO Implementation fehlt; aufwändig. Zieldatenstruktur fehlt.
- ausgewählte Belege:
      def extract_constructed_examples: Extrahiert die DWDS-Standardform: Beispiele ohne Belege (aus Leasart)
      def extract_attested_examples: Extrahiert Belege mit Fundstellen (aus Lesart)
      def _extract_corpus_examples: Extrahiert Belege aus dem Rohdaten-Abschnitt, die nicht an eine Lesart gebunden sind, sondern aus dem Gesamtkorpus erzeugt werden. (NICHT aus Lesart, sondern zum Entry gehörend)
      Hinweis: def extract_eamples wertet die ersten beiden für Sense aus. Korpusbelege werden auf Entry-Ebene in postprocess hinzugefügt.
- ausgewählte Mediendateien:
      def _extract_media_files (wertet nur Illustrationen aus) TODO: evtl. noch weitere Medientypen ergänzen
- Enthält NICHT: Aussprache, Literaturquellen, Grafiken, Statistiken, weitere Rubriken


# Notes

### POS Mapping
The DWDS sample data set uses standardized POS tags that are compatible with the target model. No mapping required.
However, only "Substantiv" and "Verb" appear in the sample. Additional data sets may contain differing POS tags.
pos_map_path = Path(__file__).parent / "pos_mapping.csv"
with open(pos_map_path, newline="") as csvfile
    reader = csv.DictReader(csvfile)
    POS_MAPPING = {row["bdo_tag"]: row["normalized"] for row in reader}


### Different senses
Note: DWDS has more types of senses which do not rely on a given, textual "Definition",
but are generated via types such as Grammatik/Einschränkung oder Antonym.
TODO: Check if these can be ommitted or need transformation

### Variants
The DWDS sample data set does not contain any variants. For further data, re-check. (Is there a "Nebenform" or similar in <Formangabe> that can be extracted here?)


### Numerus
Numerus does not appear in the DWDS sample data set