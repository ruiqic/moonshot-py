from dataclasses import dataclass, field
from typing import Optional, TypeVar, Generic
from solders.pubkey import Pubkey
from borsh_construct.enum import _rust_enum
from sumtypes import constructor

def is_variant(enum, type: str) -> bool:
    return type in str(enum)


def is_one_of_variant(enum, types):
    return any(type in str(enum) for type in types)


T = TypeVar("T")


@dataclass
class DataAndSlot(Generic[T]):
    slot: int
    data: T


@_rust_enum
class Currency:
    Sol = constructor()


@_rust_enum
class CurveType:
    LinearV1 = constructor()
    ConstantProductV1 = constructor()


@_rust_enum
class MigrationTarget:
    Raydium = constructor()
    Meteora = constructor()


@_rust_enum
class TradeType:
    Buy = constructor()
    Sell = constructor()


@_rust_enum
class FixedSide:
    ExactIn = constructor()
    ExactOut = constructor()


@dataclass
class ConfigAccount:
    migration_authority: Pubkey
    backend_authority: Pubkey
    config_authority: Pubkey
    helio_fee: Pubkey
    dex_fee: Pubkey
    fee_bps: int
    dex_fee_share: int
    migration_fee: int
    marketcap_threshold: int
    marketcap_currency: Currency
    min_supported_decimal_places: int
    max_supported_decimal_places: int
    min_supported_token_supply: int
    max_supported_token_supply: int
    bump: int
    coef_b: int


@dataclass
class CurveAccount:
    total_supply: int
    curve_amount: int
    mint: Pubkey
    decimals: int
    collateral_currency: Currency
    curve_type: CurveType
    marketcap_threshold: int
    marketcap_currency: Currency
    migration_fee: int
    coef_b: int
    bump: int
    migration_target: MigrationTarget


@dataclass
class TokenMintParams:
    name: str
    symbol: str
    uri: str
    decimals: int
    collateral_currency: int
    amount: int
    curve_type: int
    migration_target: int


@dataclass
class TradeParams:
    token_amount: int
    collateral_amount: int
    fixed_size: int
    slippage_bps: int


@dataclass
class ConfigParams:
    migration_authority: Optional[Pubkey]
    backend_authority: Optional[Pubkey]
    config_authority: Optional[Pubkey]
    helio_fee: Optional[Pubkey]
    dex_fee: Optional[Pubkey]
    fee_bps: Optional[int]
    dex_fee_share: Optional[int]
    migration_fee: Optional[int]
    marketcap_threshold: Optional[int]
    marketcap_currency: Optional[int]
    min_supported_decimal_places: Optional[int]
    max_supported_decimal_places: Optional[int]
    min_supported_token_supply: Optional[int]
    max_supported_token_supply: Optional[int]
    coef_b: Optional[int]

