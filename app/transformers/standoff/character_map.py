import pandas as pd


def mark_span_edges(col):
    "Mark starts and ends of annotation spans"
    is_annotated = ~col.isna()
    is_span_start = col != col.shift()
    is_span_end = col != col.shift(-1)

    return is_annotated & (is_span_start | is_span_end)


class CharacterMap:
    def __init__(self, charmap: pd.DataFrame, span_attributes=None):
        if "char" not in charmap.columns:
            raise ValueError("Missing 'char' column")
        self.df = charmap
        self.span_attributes = {} if span_attributes is None else span_attributes

    @classmethod
    def from_spans(cls, span_frame):
        root_text = span_frame.loc[span_frame.depth.eq(0), "text"].squeeze()
        df = pd.DataFrame({"char": list(root_text)})

        for depth, subgroup in span_frame.groupby("depth"):
            for _, row in subgroup.iterrows():
                df.loc[row.start : row.end - 1, f"depth_{depth}"] = row.span_id

        span_attributes = span_frame.set_index("span_id").attributes.to_dict()

        return cls(df, span_attributes=span_attributes)

    @property
    def text(self):
        return "".join(self.df.char)

    def normalize_ws(self):
        """Merge consecutive whitespace into single spaces"""
        df = self.df.assign(char=self.df.char.str.replace(r"\s", " ", regex=True))
        is_ws = self.df.char.str.strip() == ""
        self.df = df[~(is_ws & is_ws.shift())]

        return self

    def tighten_spans(self):
        """
        Move leading and trailing whitespace within spans into parent span. E.g., transforms

        `<outer><inner> foobar </inner></outer>`

        into

        `<outer> <inner>foobar</inner> </outer>`.
        """
        df = self.normalize_ws().df.copy()
        is_ws = df.char.str.strip() == ""

        columns = df.filter(like="depth").columns

        tightened = df[columns].transform(
            lambda col: col[~(is_ws & mark_span_edges(col))]
        )

        df[columns] = tightened

        is_empty_span = is_ws & df[columns].isna().all(axis=1)

        self.df = df[~is_empty_span]

        return self.reset_index()

    def pop_span(self, span_id):
        is_target_span = self.df.eq(span_id).any(axis=1)
        span = self.df[is_target_span]
        self.df = self.df[~is_target_span]

        return CharacterMap(span, span_attributes=dict(self.span_attributes.items()))

    def reset_index(self):
        self.df = self.df.reset_index(drop=True)
        return self

    def _fill_interrupted_spans(self, df):
        """Recover spans interrupted by inserted text"""

        # Ensure the root span covers the entire text
        root_span = df.depth_0.dropna().iloc[0]
        df = df.assign(depth_0=df.depth_0.fillna(root_span))

        # Fill interrupted spans, i.e., sequences of NaN surrounded by the same span id
        ffill = df.ffill()
        bfill = df.bfill()

        return df.where(df.notna(), ffill.where(ffill == bfill))

    def _fill_host_spans(self, df, host_span, insertion_start, text):
        """Recover spans adjacent to inserted text"""
        if host_span is None:
            return df

        df = df.copy()
        is_host = df.eq(host_span)

        if not is_host.stack().any():
            return

        columns = slice("depth_0", is_host.any().idxmax())
        host_start, *_, host_end = df[is_host.any(axis=1)].index
        insertion_end = insertion_start + len(text)

        if host_end + 1 == insertion_start:
            df.update(df.loc[insertion_start - 1 : insertion_end - 1, columns].ffill())

        elif host_start == insertion_end:
            df.update(df.loc[insertion_start:insertion_end, columns].bfill())

        return df

    def insert(self, index, text, host_span=None):
        """
        Insert text at index into root text. Optionally include the inserted text into the specified
        host span.
        """
        df = pd.concat(
            [
                self.df.iloc[:index],
                pd.DataFrame({"char": list(text)}),
                self.df.iloc[index:],
            ]
        ).reset_index(drop=True)

        df = self._fill_interrupted_spans(df)
        df = self._fill_host_spans(df, host_span, index, text)
        self.df = df

        return self

    def get_span_range(self, span_id):
        is_span_id = self.df.eq(span_id).any(axis=1)

        assert is_span_id.any(), f"Span {span_id!r} not found"

        start, *_, end = self.df[is_span_id].index

        return start, end + 1

    def spans(self, tag: str | None = None):
        unique = pd.Series(self.df.filter(like="depth_").stack().unique())

        if tag is None:
            return unique

        return unique[unique.str.rsplit("_", n=1).str[0].eq(tag)]

    def add_span(self, tag, start, end, attributes=None):
        # determine next available id
        in_use = self.spans(tag).str.rsplit("_", n=1).str[-1].astype(int).values
        i = 1

        while i in in_use:
            i += 1

        span_id = f"{tag}_{i}"

        self.span_attributes[span_id] = {} if attributes is None else attributes

        target_range = self.df.iloc[start:end]

        # find target depth
        free_layers = target_range.isna().all()

        if free_layers.any():
            target_layer = free_layers.idxmax()
        else:
            d = (
                self.df.filter(like="depth")
                .columns.str.split("_", n=1)
                .str[-1]
                .astype(int)
                .max()
                + 1
            )
            target_layer = f"depth_{d}"

        self.df.loc[target_range.index, target_layer] = span_id

        return self

    def __str__(self):
        return str(self.df)

    def __repr__(self):
        return repr(str(self))

    def _repr_html_(self):
        """Return HTML representation for Jupyter notebooks"""
        return self.df._repr_html_()

    def to_spans(self):
        df = self.df
        text = self.text

        # stack annotation layers
        stacked = (
            pd.concat([df[col] for col in df.columns], keys=df.columns)
            .rename("span_id")
            .drop("char")
        )
        stacked = stacked.rename_axis(["depth", "index"]).reset_index()

        # extract start and end indexes
        spans = stacked.groupby("span_id")["index"].agg(start="min", end="max")
        spans["end"] += 1

        spans["tag"] = spans.index.str.rsplit("_", n=1).str[0]
        spans["depth"] = (
            stacked.drop_duplicates(subset="span_id")
            .set_index("span_id")
            .depth.str.removeprefix("depth_")
            .astype(int)
        )

        spans["text"] = spans.apply(lambda row: text[row.start : row.end], axis=1)

        # populate attribute columns
        spans["attributes"] = pd.Series(self.span_attributes)
        spans = spans.join(
            pd.DataFrame(spans.pop("attributes").to_list(), index=spans.index)
        )

        return spans.sort_values(["depth", "start"]).reset_index()

    def rename_tag(self, tag, value):
        def rename_series(col):
            col = col.str.rsplit("_", n=1)
            return col.str[0].replace(tag, value) + "_" + col.str[1]

        def rename(old_tag):
            old_tag, index = old_tag.rsplit("_", maxsplit=1)
            return f"{value if old_tag == tag else old_tag}_{index}"

        self.df.loc[:, "depth_0":] = self.df.loc[:, "depth_0":].transform(rename_series)
        self.span_attributes = {rename(k): v for k, v in self.span_attributes.items()}

        return self

    def get_subspans(self, span_id):
        df = self.df.filter(like="depth")

        is_superspan = df.eq(span_id)
        start_column = [*df.columns[is_superspan.any()], None][0]

        if start_column is None:
            return []

        return [
            tag
            for tag in df.loc[is_superspan.any(axis=1), start_column:].stack().unique()
            if tag != span_id
        ]
