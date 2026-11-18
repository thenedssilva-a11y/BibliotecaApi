from datetime import date
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AdminSetup(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    senha: str = Field(min_length=12, max_length=128)

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, value):
        if not (re.search(r"[A-Z]", value) and re.search(r"[a-z]", value) and
                re.search(r"\d", value) and re.search(r"[^A-Za-z0-9]", value)):
            raise ValueError("A senha deve conter maiúscula, minúscula, número e símbolo")
        return value


class LoginInput(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class LivroInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    titulo: str = Field(min_length=1, max_length=200)
    autor: str = Field(min_length=1, max_length=160)
    isbn: str = Field(min_length=10, max_length=17)
    editora: str = Field(min_length=1, max_length=160)
    ano_publicacao: int = Field(ge=0, le=date.today().year + 1)
    categoria: str = Field(min_length=1, max_length=80)
    preco: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    quantidade_estoque: int = Field(ge=0, le=1_000_000)
    descricao: str = Field(default="", max_length=2000)


class LivroPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    titulo: str | None = Field(default=None, min_length=1, max_length=200)
    autor: str | None = Field(default=None, min_length=1, max_length=160)
    isbn: str | None = Field(default=None, min_length=10, max_length=17)
    editora: str | None = Field(default=None, min_length=1, max_length=160)
    ano_publicacao: int | None = Field(default=None, ge=0, le=date.today().year + 1)
    categoria: str | None = Field(default=None, min_length=1, max_length=80)
    preco: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    quantidade_estoque: int | None = Field(default=None, ge=0, le=1_000_000)
    descricao: str | None = Field(default=None, max_length=2000)


class EstoqueInput(BaseModel):
    quantidade_estoque: int = Field(ge=0, le=1_000_000)
