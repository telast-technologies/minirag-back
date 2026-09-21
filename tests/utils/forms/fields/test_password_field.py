from wtforms import Form
from wtforms.widgets import PasswordInput

from src.utils.forms.fields import EditablePasswordField


class PasswordForm(Form):
    password = EditablePasswordField(placeholder="********")


def test_editable_password_field_sets_placeholder_and_widget():
    form = PasswordForm()
    field = form.password

    assert field.placeholder == "********"
    assert isinstance(field.widget, PasswordInput)
    assert field.widget.hide_value is False


def test_value_returns_data_when_present():
    form = PasswordForm()
    field = form.password
    field.data = "********"

    assert field._value() == "********"


def test_value_returns_empty_string_when_data_is_none():
    form = PasswordForm()
    field = form.password
    field.data = None

    assert field._value() == ""


def test_value_returns_empty_string_when_data_is_empty():
    form = PasswordForm()
    field = form.password
    field.data = ""

    assert field._value() == ""
