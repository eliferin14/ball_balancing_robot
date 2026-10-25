from pathlib import Path
from typing import TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def load_config(file_path: Path | str, model_cls: type[T]) -> T:
    """
    Load a YAML configuration file and validate it against the given Pydantic model.

    Args:
        file_path: Path to the YAML configuration file.
        model_cls: Pydantic model class used to validate the loaded data.

    Returns:
        Validated Pydantic model instance.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        ValueError: If the file contains invalid YAML or does not match the schema.
    """
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        try:
            raw_data = yaml.safe_load(file)
        except yaml.YAMLError as err:
            raise ValueError(f"Failed to parse YAML file at {path}: {err}") from err

    # If the YAML file is empty, use an empty dict to let Pydantic apply defaults
    if raw_data is None:
        raw_data = {}

    return model_cls.model_validate(raw_data)
