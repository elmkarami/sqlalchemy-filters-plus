"""
This module defined all exceptions used by the library.
"""
from typing import Dict
from typing import List
from typing import Optional
from typing import Type


class BaseError(Exception):
    """
    Base Exception for all exceptions.
    """


class InvalidParamError(BaseError):
    """
    Raised during the call of the :meth:`check_params <sqlalchemy_filters.operators.BaseOperator.check_params>` method
    of the Operator class.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class FieldMethodNotFound(BaseError):
    """
    Raised when a method specified using string is not found in the filter class.
    """

    def __init__(self, parent_filter: Type, field_name: str, method_name: str) -> None:
        self.parent_filter = parent_filter
        self.field_name = field_name
        self.method_name = method_name
        super().__init__(f"Method {self.parent_filter.__name__}.{method_name}")


class FieldValidationError(BaseError):
    #: default error message
    default_error: str = "error validating this field."

    def __init__(self, message: Optional[str] = None):
        """
        :param message: Optional string representing the error message. If not supplied the the default
                        :attr:`default_error` will be used.
        """
        self.field_name: Optional[str] = None
        self.message = message or self.default_error
        super().__init__(message)

    def set_field_name(self, field_name: str) -> None:
        """
        sets :attr:`field_name`

        :param field_name: The field name of the errored field name.
        :return: None
        """
        self.field_name = field_name

    def json(self) -> Dict[Optional[str], str]:
        """
        Converts the error into a dictionary {field_name: error_message}
        :return: dict
        """
        return {self.field_name: self.message}

    def __repr__(self):
        return f"{self.__class__.__name__}({self.field_name}='{self.message}')"


class FilterValidationError(BaseError):
    #: List of :attr:`FieldValidationError`
    field_errors: List[FieldValidationError]

    def __init__(self, field_errors: List[FieldValidationError]):
        self.field_errors = field_errors

    def json(self) -> List[Dict[Optional[str], str]]:
        """
        Jsonify all the :attr:`sqlalchemy_filters.exceptions.FieldValidationError` exceptions

        :return: List of dictionary representing the errors for each field

            Example:

            >>> exc.json()
            [
                {"age": "Expected to be of type int"},
                {"last_name": "Expected to be of type str"}
            ]
        """
        return [error.json() for error in self.field_errors]


class OrderByException(BaseError):
    """
    Raised when trying to order by a field that does not belong to the filter's model.
    """

    pass
