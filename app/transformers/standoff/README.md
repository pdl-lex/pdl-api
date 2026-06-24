# XML to Standoff Transformation

## Motivation

XML is a suitable format for *representing* lexicographic data in general and digitizing written
dictionaries in particular. However, its structucal properties (verbosity, arbitrary nesting, lack
of rigid schemas, etc.) render XML suboptimal for performing data analytical work at scale. Tags
containing both text and inline tags (so-called *mixed content*) is particularly challenging because
it merges distinct conceptual layers (the source text and markup/annotation) into a single
representation, e.g.:

```xml
<comment>Vgl. auch ahd. <ref target="hunt_123" type="lemma">hunt</ref>.</comment>
```

For quantitative research, this is not ideal: If the source text is of interest (e.g., as input for
NLP pipelines) it needs to be reconstructed first, which may require time-consuming
normalization, cleaning and postprocessing. If annotations encoded as inline markup are to be
examined instead, recursive extraction procedures may be required in preparation of statistical
analyses.

For reasons like these, modern corpus linguistics and NLP prefer data formats that keep annotations
separate from the source text. Text is stored as a plain string, e.g.,

```txt
Vgl. auch ahd. hunt.
```

and markup as a separate table of annotation spans with character offsets defining which range of
text they apply to, similar to:

| Tag     | Start | End | Depth | Text                | Attributes                            |
|---------|-------|-----|-------|---------------------|---------------------------------------|
| comment | 0     | 20  |     0 | Vgl. auch ahd. hunt.| —                                     |
| ref     | 16    | 20  |     1 | hunt                | `{target: hunt_123, type: lemma}`     |

Alternatively, the data can be represented as a character map where each character is associated
with all of its surrounding tags, resulting in a kind of **coordinate system**:

| Char. |  Layer 0| Layer 1|
|-------|---------|--------|
| V     | comment |        |
| g     | comment |        |
| l     | comment |        |
| .     | comment |        |
|       | comment |        |
| a     | comment |        |
| u     | comment |        |
| c     | comment |        |
| h     | comment |        |
|       | comment |        |
| a     | comment |        |
| h     | comment |        |
| d     | comment |        |
| .     | comment |        |
|       | comment |        |
| h     | comment | ref    |
| u     | comment | ref    |
| n     | comment | ref    |
| t     | comment | ref    |
| .     | comment |        |

Such a representation comes with a number of benefits. First, it is particularly useful for
modifying the source text (i.e., for normalizing whitespace, inserting or extracting spans) by
adding or removing rows, leaving the mappings of surrounding spans intact. Although this kind of
modification is possible by manipulating XML directly, the latter often requires complex nested
loops that are hard to understand and maintain. To illustrate, deleting extra whitespace on an XML
node in Python requires a recursive function:

```python
import re
from lxml import etree

def normalize_whitespace(node):
    # Normalize text before first child
    if node.text:
        node.text = re.sub(r" {2,}", " ", node.text)
    
    # Normalize tail text and recurse for each child
    for child in node:
        if child.tail:
            child.tail = re.sub(r" {2,}", " ", child.tail)
        normalize_whitespace(child)
```

In addition to its complexity, this approach fails to merge consecutive whitespace across tags when
adjacent siblings contain leading and trailing whitespace, respectively. As a result, normalizing,
e.g.,

```xml
<!-- spaces marked by "•" -->
<a>lorem•</a>•<b>•ipsum</b>
```

results in `"lorem•••ipsum"` instead of the intended `"lorem•ipsum"`.

In contrast, a character map allows us to cleanly normalize the text globally by removing all
whitespace rows preceded by a whitespace row. If stored as a pandas dataframe, this becomes:

```python
def normalize_whitespace(charmap):
    # select space characters where the last row is also a space
    m = (charmap["char"] == " ") & (charmap["char"].shift() == " ")
    return charmap[~m]
```

A second property of standoff representations is that by decoupling the annotation structure from
the primary data they allow serialization in structurally flat, tabular, or graph-based formats
**while fully preserving the linear order and structural hierarchy of the underlying XML**.
This approach offers several crucial advantages:

1. **Infrastructural Compatibility:** By avoiding proprietary or niche data structures, standoff
   data can be stored, indexed, and queried using mature, mainstream database technologies (SQL,
   NoSQL, Document stores), which are highly optimized for horizontal scalability.
2. **Non-Destructive Extensibility:** New annotation layers can be added indefinitely while leaving
   the original source text completely untouched. This allows standard NLP pipelines to
   independently enrich a text with, e.g., tokenization, lemmatization, named entities, and syntax,
   layering these structures on top of one another to build multi-dimensional search interfaces.
3. **Interoperability and Reuse:** Because the primary data remains immutable, independent research
   teams can create parallel annotation layers that refer back to the exact same stable coordinates,
   facilitating easier data sharing and collaborative curation.

In comparison, XML databases remain a niche solution. While query languages like XQuery are
exceptionally powerful for strict trees, they scale poorly when forced to handle complex,
multi-layered data. Furthermore, inline XML cannot natively represent concurrent, intersecting
hierarchies. This creates a massive hurdle for collaboration: if two independent research teams
inject their own inline tags (such as tokens or lemmas) into separate copies of an XML file, the
resulting files cannot be directly merged or compared due to tag collisions and altered document
structures. With standoff representation, because the base text remains completely untouched, the
two teams' annotations exist as independent tables anchored to the exact same character offsets.
Their results can easily be placed side by side, joined, and compared without any destructive
reconciliation.

To employ the whitespace normalization problem again, imagine we do not want to delete whitespace
but merely mark consecutive whitespace characters as "extra" in order to hide them in an online
interface. With inline XML, that would mean injecting a tag into the original data, thereby
increasing its structural complexity and reducing its human-readability. With a standoff
representation, however, we may add a new layer to mark whitespace to be visually hidden, leaving
both the source text and existing annotations intact.
