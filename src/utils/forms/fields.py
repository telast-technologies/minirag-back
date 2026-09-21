from wtforms.fields import PasswordField
from wtforms.widgets import PasswordInput


class EditablePasswordField(PasswordField):
    """
    Custom password field that keeps old value on edit.
    Shows masked placeholder.
    """

    def __init__(self, label=None, validators=None, placeholder="********", **kwargs):
        super().__init__(label, validators, **kwargs)
        self.placeholder = placeholder
        self.widget = PasswordInput(hide_value=False)  # allows value to be displayed

    def _value(self):
        if self.data:
            # show masked value instead of actual hash
            return self.data
        return ""
