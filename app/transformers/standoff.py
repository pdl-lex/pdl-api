import pandas as pd

from app.data_processing.transformation.standoff.xml_standoff_converter import (
    xml_to_standoff,
)
from app.transformers.annotation_frame import AnnotationFrame


class StandoffTransformer:
    def __init__(self, span_data: list[dict]):
        self.aframe = AnnotationFrame(self._init_dataframe(span_data))

    @classmethod
    def load_xml(cls, xml_node) -> "StandoffTransformer":
        span_data = xml_to_standoff(xml_node)
        return cls(span_data)

    def _init_dataframe(self, span_data: list[dict]) -> pd.DataFrame:
        frame = pd.DataFrame(
            span_data, columns=["start", "end", "tag", "attributes", "text"]
        )
        extra_attributes = pd.DataFrame.from_records(frame.pop("attributes"))
        frame = pd.concat([frame, extra_attributes], axis=1)

        return self._add_unique_ids(frame)

    def _add_unique_ids(self, frame: pd.DataFrame) -> pd.DataFrame:
        tag_counters = frame.groupby("tag").cumcount() + 1
        repeated_tags = tag_counters > 1

        ids = frame.tag.iloc[::]
        ids[repeated_tags] + "_" + tag_counters[repeated_tags].astype(str)

        return frame.assign(span_id=ids).set_index("span_id")
