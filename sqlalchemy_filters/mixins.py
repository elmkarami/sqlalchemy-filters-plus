from typing import Any, Dict, Optional, Type

from sqlalchemy.inspection import inspect as sa_inspect

from sqlalchemy_filters.utils import Empty


class ForeignKeyFieldMixin:
    def __init__(self, *, field_name=None, **kwargs):
        super().__init__(**kwargs)
        self.field_name = field_name
        self.is_foreign_key = False
        self.foreign_model = None
        self.parent_filter = None
        self.fk_model_pk = None
        if "." in (field_name or ""):
            self.is_foreign_key = True

    def resolve_fk(self):
        self.joins = self.resolve_joins()
        self._column = getattr(self.joins[-1][0], self.field_name.split(".")[-1])

    def post_init(self, filter_obj):
        if self.is_foreign_key:
            self.resolve_fk()
        super().post_init(filter_obj)

    def resolve_joins(self):
        chained_attributes = self.field_name.split(".")
        model = self.parent_filter.Meta.model
        joins = []
        for attribute in chained_attributes[:-1]:
            mapper = sa_inspect(model)
            relationships = dict(mapper.relationships.items())
            relationship = relationships[attribute]
            model = relationship.mapper.class_
            joins.append((model, relationship.primaryjoin))
        return joins


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
