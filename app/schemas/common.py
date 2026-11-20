"""Shared response shapes published on Swagger."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiModel(BaseModel):
    # ORM rows are returned as-is. Swagger still sees the field list.
    model_config = ConfigDict(from_attributes=True)


class ItemList(BaseModel, Generic[T]):
    items: list[T]
    total: int
