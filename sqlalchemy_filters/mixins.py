import inspect
from typing import Optional, Type, Dict, Any

from sqlalchemy_filters.utils import Empty


def get_fk_remote_side_column(fk):
    return next(iter(fk.property.remote_side))


class ForeignKeyFieldMixin:
    def __init__(self, *, field_name=None, **kwargs):
        super().__init__(**kwargs)
        self.field_name = field_name
        self.is_foreign_key = False
        self.foreign_model = None
        self.parent_filter = None
        self.fk_model_pk = None
        if field_name and field_name.count(".") > 1:
            raise ValueError("Dept greater than 2 not supported yet.")
        if "." in (field_name or ""):
            self.is_foreign_key = True

    def resolve_fk(self):
        attribute_name, column_name = self.field_name.split(".")
        attribute = getattr(self.parent_filter.Meta.model, attribute_name)
        if inspect.isclass(attribute.property.argument):
            self.foreign_model = attribute.property.argument
        else:
            # TODO: we assume now it's a sqlalchemy.ext.declarative.clsregistry._class_resolver
            self.foreign_model = attribute.property.argument()
        self.fk_model_pk = get_fk_remote_side_column(
            getattr(self.parent_filter.Meta.model, attribute_name)
        )
        self._column = getattr(self.foreign_model, column_name)
        self.join = self.join or attribute

    def post_init(self, filter_obj):
        if self.is_foreign_key:
            self.resolve_fk()
        super().post_init(filter_obj)


class MarshmallowValidatorFilterMixin:
    def __init__(self, *, marshmallow_schema: Optional[Type] = None, **kwargs):
        super().__init__(**kwargs)
        self.marshmallow_schema = marshmallow_schema
        self.validated = False

    def get_values(self) -> Dict[str, Any]:
        data = dict(
            (field.get_data_source_name(), field.get_field_value(self.data))
            for field in self.fields.values()
            if field.get_field_value(self.data) is not Empty
        )
        for nested in self.nested.values():
            data.update(nested.get_data(self))
        return data

    def validate(self):
        schema = self.marshmallow_schema or self.__class__.marshmallow_schema
        if schema:
            values = self.get_values()
            schema().load(values)
            self.validated = True
        else:
            super().validate()
