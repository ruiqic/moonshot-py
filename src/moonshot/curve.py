from abc import ABC, abstractmethod
from typing import Tuple, Dict
from solders.pubkey import Pubkey

from moonshot.types import is_variant, CurveType, TradeType
from moonshot.constants import PLATFORM_FEE_BPS


class AbstractCurve(ABC):
    @abstractmethod
    def get_tokens_amount_from_collateral(
        self, 
        amount: int,
        curve_position: int,
        trade_direction: TradeType
    ):
        pass

    @abstractmethod
    def get_collateral_amount_from_tokens(
        self, 
        amount: int,
        curve_position: int,
        trade_direction: TradeType 
    ):
        pass

class ConstantProductCurveV1(AbstractCurve):
    def __init__(self):
        self.initial_virtual_token_reserves = 1073000000000000000
        self.initial_virtual_collateral_reserves = 30000000000
        self.collateral_decimals = 9
        self.constant_product = self.initial_virtual_token_reserves * self.initial_virtual_collateral_reserves
        self.dynamic_threshold = 80
        self.max_threshold = 82
        self.curve_defaults = {
            "type": CurveType.ConstantProductV1(),
            "total_supply": 10**18,
            "token_decimals": 9,
            "min_allocation_token_amount": (10**18 * self.dynamic_threshold) // 100,
            "max_allocation_token_amount": (10**18 * self.max_threshold) // 100,
            "address": Pubkey.from_string("11111111111111111111111111111111"),
        }

    def get_tokens_amount_from_collateral(
            self,
            amount: int,
            curve_position: int,
            trade_direction: TradeType 
        ) -> int:
        if is_variant(trade_direction, "Buy"):
            collateral_amount = amount - (amount * int(PLATFORM_FEE_BPS)) // 10000
            return self.buy_in_collateral(collateral_amount, curve_position)
        else:
            collateral_amount = amount + (amount * int(PLATFORM_FEE_BPS)) // 10000
            return self.sell_in_collateral(collateral_amount, curve_position)

    def get_collateral_amount_from_tokens(
            self,
            amount: int,
            curve_position: int,
            trade_direction: TradeType 
        ) -> int:
        if is_variant(trade_direction, "Buy"):
            collateral_amount = self.buy_in_token(amount, curve_position)
            return collateral_amount + (collateral_amount * int(PLATFORM_FEE_BPS)) // 10000
        else:
            collateral_amount = self.sell_in_token(amount, curve_position)
            return collateral_amount - (collateral_amount * int(PLATFORM_FEE_BPS)) // 10000

    def buy_in_token(self, token_amount: int, curve_position: int) -> int:
        current_virtual_token_reserves, current_virtual_collateral_reserves = self.get_current_reserves(curve_position)
        new_token_reserves = current_virtual_token_reserves - token_amount
        ratio = self.constant_product // new_token_reserves
        lamports_to_spend = ratio - current_virtual_collateral_reserves
        return lamports_to_spend

    def buy_in_collateral(self, collateral_amount: int, curve_position: int) -> int:
        current_virtual_token_reserves, current_virtual_collateral_reserves = self.get_current_reserves(curve_position)
        new_collateral_reserves = current_virtual_collateral_reserves + collateral_amount
        ratio = self.constant_product // new_collateral_reserves
        tokens_to_buy = current_virtual_token_reserves - ratio
        return tokens_to_buy

    def sell_in_token(self, token_amount: int, curve_position: int) -> int:
        current_virtual_token_reserves, current_virtual_collateral_reserves = self.get_current_reserves(curve_position)
        new_token_reserves = current_virtual_token_reserves + token_amount
        ratio = self.constant_product // new_token_reserves
        lamports_to_receive = current_virtual_collateral_reserves - ratio
        return lamports_to_receive

    def sell_in_collateral(self, collateral_amount: int, curve_position: int) -> int:
        current_virtual_token_reserves, current_virtual_collateral_reserves = self.get_current_reserves(curve_position)
        new_collateral_reserves = current_virtual_collateral_reserves - collateral_amount
        ratio = self.constant_product // new_collateral_reserves
        tokens_to_sell = ratio - current_virtual_token_reserves
        return tokens_to_sell

    def get_current_reserves(self, curve_position: int) -> Tuple[int, int]:
        current_virtual_token_reserves = self.initial_virtual_token_reserves - curve_position
        current_virtual_collateral_reserves = self.constant_product // current_virtual_token_reserves
        return current_virtual_token_reserves, current_virtual_collateral_reserves