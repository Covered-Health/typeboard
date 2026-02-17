import enum
from datetime import date, datetime
from typing import Annotated

from typeboard.fields import (
    AdminField,
    extract_admin_field,
    get_enum_choices,
    infer_widget,
    label_from_name,
    unwrap_annotated,
)


def test_infer_widget_str():
    assert infer_widget(str) == "text"


def test_infer_widget_int():
    assert infer_widget(int) == "number"


def test_infer_widget_bool():
    assert infer_widget(bool) == "checkbox"


def test_infer_widget_date():
    assert infer_widget(date) == "date"


def test_infer_widget_datetime():
    assert infer_widget(datetime) == "datetime"


def test_infer_widget_list():
    assert infer_widget(list[int]) == "multiselect"


def test_infer_widget_optional_str():
    assert infer_widget(str | None) == "text"


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


def test_infer_widget_enum():
    assert infer_widget(Color) == "select"


def test_extract_admin_field():
    ann = Annotated[str, AdminField(label="Name")]
    af = extract_admin_field(ann)
    assert af is not None
    assert af.label == "Name"


def test_extract_admin_field_none():
    assert extract_admin_field(str) is None


def test_unwrap_annotated():
    assert unwrap_annotated(Annotated[str, AdminField()]) is str
    assert unwrap_annotated(int) is int


def test_get_enum_choices():
    choices = get_enum_choices(Color)
    assert choices == [("red", "Red"), ("blue", "Blue")]


def test_label_from_name():
    assert label_from_name("iam_org_id") == "Iam Org Id"
    assert label_from_name("name") == "Name"
