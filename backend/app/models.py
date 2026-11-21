from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RuleConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    effective_from: date
    bhm_amount: int = Field(ge=1, le=1_000_000_000, strict=True)
    car_bhm_multiplier: Decimal = Field(ge=Decimal('0.001'), le=100)
    motorcycle_bhm_multiplier: Decimal = Field(ge=Decimal('0.001'), le=100)
    relative_pay_percent: Decimal = Field(ge=0, le=100)
    bank_pay_percent: Decimal = Field(ge=0, le=100)
    outside_multiplier: Decimal = Field(ge=1, le=10)
    law_url: str = Field(max_length=500)
    law_article: str = Field(min_length=3, max_length=250)
    bhm_source_url: str = Field(max_length=500)
    verified_at: date
    change_note: str = Field(min_length=10, max_length=1500)

    @field_validator('law_url', 'bhm_source_url')
    @classmethod
    def official_source(cls, value):
        url = urlsplit(value)
        if url.scheme != 'https' or url.hostname not in {'lex.uz', 'www.lex.uz'} or url.username or url.password or url.port:
            raise ValueError('Manba https://lex.uz/ havolasi bo‘lishi kerak.')
        return value


RELATIVES = {'spouse', 'parent', 'child', 'spouse_parent', 'child_spouse', 'grandchild', 'grandparent', 'sibling'}


class Answers(BaseModel):
    model_config = ConfigDict(extra='forbid')
    vehicle_type: Literal['car', 'motorcycle'] | None = None
    transaction_kind: Literal['sale', 'exchange'] = 'sale'
    relative_type: Literal['spouse', 'parent', 'child', 'spouse_parent', 'child_spouse', 'grandchild', 'grandparent', 'sibling', 'other'] | None = None
    bank_credit: Literal['yes', 'no'] | None = None
    damaged: Literal['yes', 'no'] | None = None
    damage_assessed: Literal['yes', 'no'] | None = None
    residual_percent: Decimal | None = Field(default=None, ge=0, le=100, max_digits=7, decimal_places=4)
    location: Literal['office', 'outside', 'outreach'] | None = None
    special_status: Literal['none', 'unsure', 'needs_review', 'disability_organization', 'islamic_finance'] | None = None
    exemption_parties: Literal['one', 'both'] | None = None


class CalculateRequest(BaseModel):
    service_id: str = Field(default='notary_car', max_length=60)
    answers: dict = Field(default_factory=dict)
    as_of_date: date | None = None






class ReportRequest(BaseModel):
    calculation_id: str = Field(min_length=1, max_length=100)
    service_id: str = Field(min_length=1,max_length=60)
    standard_amount: int | None = Field(default=None, ge=0, le=10**15, strict=True)
    paid_amount: int | None = Field(default=None, ge=0, le=10**15, strict=True)

    @model_validator(mode='after')
    def paired_amounts(self):
        if (self.standard_amount is None) != (self.paid_amount is None):
            raise ValueError('Ikkala summani kiriting yoki ikkalasini bo‘sh qoldiring.')
        if self.standard_amount is not None and self.paid_amount > self.standard_amount:
            raise ValueError('Amalda to‘langan summa imtiyozsiz summadan katta.')
        return self


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=200)


class CatalogRuleConfig(BaseModel):
    model_config = ConfigDict(extra='forbid')
    effective_from: date
    bhm_amount: int = Field(ge=1,le=1_000_000_000,strict=True)
    parameters: dict[str, Decimal]
    law_url: str = Field(max_length=2000)
    law_article: str = Field(min_length=3,max_length=250)
    bhm_source_url: str = Field(max_length=2000)
    verified_at: date
    change_note: str = Field(min_length=10,max_length=1500)

    @field_validator('law_url','bhm_source_url')
    @classmethod
    def official_source(cls,value):
        return RuleConfig.official_source(value)
