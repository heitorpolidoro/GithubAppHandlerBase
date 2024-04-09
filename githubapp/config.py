"""
Config module

This module handles loading configuration values from a YAML file
and provides access to those values via the ConfigValue class.
"""

from functools import wraps
from typing import NoReturn, TypeVar, Union

import yaml
from github import UnknownObjectException
from github.Repository import Repository

AnyBasic = Union[int, float, bool, str, list, dict, tuple]
ConfigValueType = TypeVar("ConfigValueType", bound="ConfigValue")


class ConfigError(AttributeError):
    """
    Exception raised for errors in the configuration.

    Attributes:
        message - explanation of the error
    """


class ConfigValue:
    """The configuration loaded from the config file"""

    def __init__(self, value: AnyBasic = None) -> NoReturn:
        self._value = value

    def set_values(self, data: dict[str, AnyBasic]) -> NoReturn:
        """Set the attributes from a data dict"""
        for attr, value in data.items():
            if isinstance(value, dict):
                config_value = getattr(self, attr, ConfigValue())
                config_value.set_values(value)
                setattr(self, attr, config_value)
            else:
                setattr(self, attr, value)

    def create_config(self, name: str, *, default: AnyBasic = None, **values: AnyBasic) -> ConfigValueType:
        """
        Create a configuration value and nested values.

        Args:
            name (str): The name of the configuration value
            default: The default value. If set, values cannot be provided
            values (dict): Nested configuration values

        Returns:
            ConfigValue: The created configuration value
        """
        if default is not None and values:
            raise ConfigError("You cannot set the default value AND default values for sub values")
        default = default or ConfigValue()
        if values:
            default.set_values(values)
        self.set_values({name: default})

        return self

    def load_config_from_file(self, filename: str, repository: Repository) -> NoReturn:
        """Load the config from a file"""
        try:
            raw_data = (
                yaml.safe_load(repository.get_contents(filename, ref=repository.default_branch).decoded_content) or {}
            )
            self.set_values(raw_data)
        except UnknownObjectException:
            pass

    def __getattr__(self, item: str) -> AnyBasic:
        raise ConfigError(f"No such config value: {item}. And there is no default value for it")

    def get(self, config_name: str, default: AnyBasic = "__NO_DEFAULT__"):
        value = self
        for name in config_name.split("."):
            if default == "__NO_DEFAULT__":
                value = getattr(value, name)
            else:
                value = getattr(value, name, default)
        return value

    @staticmethod
    def call_if(config_name: str, value: AnyBasic = None):
        config_value = Config.get(config_name)

        def decorator(method):
            @wraps(method)
            def wrapper(*args, **kwargs):
                if value is not None and config_value == value or value is None and config_value:
                    return method(*args, **kwargs)

            return wrapper

        return decorator


Config = ConfigValue()
