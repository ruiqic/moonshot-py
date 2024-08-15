from abc import ABC, abstractmethod
from typing import Tuple, Dict, Optional
from decimal import Decimal
from solders.pubkey import Pubkey

from moonshot.types import is_variant, CurveType, TradeType, CurveAccount
from moonshot.constants import PLATFORM_FEE_BPS, get_currency_decimals


class AbstractCurve(ABC):
    @abstractmethod
    def get_tokens_amount_from_collateral(
        self, 
        amount: int,
        curve_account: CurveAccount,
        trade_direction: TradeType
    ):
        pass

    @abstractmethod
    def get_collateral_amount_from_tokens(
        self, 
        amount: int,
        curve_account: CurveAccount,
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
            curve_account: CurveAccount,
            trade_direction: TradeType 
        ) -> int:
        curve_position = curve_account.total_supply - curve_account.curve_amount
        if is_variant(trade_direction, "Buy"):
            collateral_amount = amount - (amount * int(PLATFORM_FEE_BPS)) // 10000
            return self.buy_in_collateral(collateral_amount, curve_position)
        else:
            collateral_amount = amount + (amount * int(PLATFORM_FEE_BPS)) // 10000
            return self.sell_in_collateral(collateral_amount, curve_position)

    def get_collateral_amount_from_tokens(
            self,
            amount: int,
            curve_account: CurveAccount,
            trade_direction: TradeType 
        ) -> int:
        curve_position = curve_account.total_supply - curve_account.curve_amount
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
    

class BaseCurve(ABC):
    @abstractmethod
    def get_coef_b(self, coef_b_minimal_units: int, collateral_decimals_nr: int) -> Decimal:
        pass

    @abstractmethod
    def get_coef_a(self, coef_b: Decimal, total_supply: int, decimal_nr: int, marketcap_threshold: int, marketcap_decimal_nr: int) -> Decimal:
        pass

    @abstractmethod
    def calculate_cost_for_n_tokens(self, options: Dict) -> Optional[Decimal]:
        pass

    @abstractmethod
    def calculate_tokens_nr_from_collateral(self, options: Dict) -> Optional[int]:
        pass

    @abstractmethod
    def calculate_curve_price(self, coef_a: Decimal, coef_b: Decimal, curve_position: int, collateral_decimals_nr: int, token_decimals_nr: int) -> Optional[Decimal]:
        pass

    def get_collateral_price(self, options: Dict) -> Decimal:
        coef_b = self.get_coef_b(options['coefB'], options['collateralDecimalsNr'])
        coef_a = self.get_coef_a(coef_b, options['totalSupply'], options['tokenDecimalsNr'], options['marketCapThreshold'], options['marketCapDecimalsNr'])
        collateral_price = self.calculate_cost_for_n_tokens({
            'coefA': coef_a,
            'coefB': coef_b,
            'nAmount': options['tokensAmount'],
            'curvePosition': options['curvePosition'],
            'decimalsNr': options['tokenDecimalsNr'],
            'collateralDecimalsNr': options['collateralDecimalsNr'],
        })
        if collateral_price is None:
            raise ValueError('Expected collateral amount is 0 or undefined!')
        return collateral_price

    def get_tokens_nr_from_collateral(self, options: Dict) -> int:
        coef_b = self.get_coef_b(options['coefB'], options['collateralDecimalsNr'])
        coef_a = self.get_coef_a(coef_b, options['totalSupply'], options['tokenDecimalsNr'], options['marketCapThreshold'], options['marketCapDecimalsNr'])
        tokens_nr = self.calculate_tokens_nr_from_collateral({
            'coefA': coef_a,
            'coefB': coef_b,
            'collateralAmount': options['collateralAmount'],
            'curvePosition': options['curvePosition'],
            'decimalsNr': options['tokenDecimalsNr'],
            'collateralDecimalsNr': options['collateralDecimalsNr'],
            'tradeDirection': options['direction'],
        })
        if tokens_nr is None:
            raise ValueError('Expected collateral amount is 0 or undefined!')
        return tokens_nr

    def get_price_for_curve_position(self, options: Dict) -> Decimal:
        coef_b = self.get_coef_b(options['coefB'], options['collateralDecimalsNr'])
        coef_a = self.get_coef_a(coef_b, options['totalSupply'], options['tokenDecimalsNr'], options['marketCapThreshold'], options['marketCapDecimalsNr'])
        price = self.calculate_curve_price(coef_a, coef_b, options['curvePosition'], options['collateralDecimalsNr'], options['tokenDecimalsNr'])
        if price is None:
            raise ValueError('Price cannot be calculated!')
        return price
    

class LinearCurveV1(AbstractCurve, BaseCurve):
    def __init__(self):
        super().__init__()
        self.dynamic_threshold = 55
        self.max_threshold = 65
        self.curve_limit = 3300
        self.curve_defaults = {
            "type": CurveType.LinearV1(),
            "total_supply": 10**18,
            "token_decimals": 9,
            "min_allocation_token_amount": (10**18 * self.dynamic_threshold) // 100,
            "max_allocation_token_amount": (10**18 * self.max_threshold) // 100,
            "address": Pubkey.from_string('11111111111111111111111111111111'),
        }
        self.curve_type = CurveType.LinearV1()

    def calculate_cost_for_n_tokens(self, options: Dict) -> Optional[Decimal]:
        coef_a = options['coefA']
        coef_b = options['coefB']
        n_amount = options['nAmount']
        curve_position = options['curvePosition']
        decimals_nr = options['decimalsNr']
        collateral_decimals_nr = options['collateralDecimalsNr']

        token_decimals = Decimal(10) ** decimals_nr
        collateral_decimals = Decimal(10) ** collateral_decimals_nr
        n = Decimal(n_amount) / token_decimals
        m = Decimal(curve_position) / token_decimals
        two = Decimal(2)
        half = Decimal(0.5)

        try:
            result = (half * coef_a * n * (two * m + n) + coef_b * n) * collateral_decimals
            return result
        except Exception:
            return None

    def calculate_tokens_nr_from_collateral(self, options: Dict) -> Optional[int]:
        coef_a = options['coefA']
        coef_b = options['coefB']
        collateral_amount = options['collateralAmount']
        curve_position = options['curvePosition']
        decimals_nr = options['decimalsNr']
        collateral_decimals_nr = options['collateralDecimalsNr']
        trade_direction = options['tradeDirection']

        try:
            token_decimals = Decimal(10) ** decimals_nr
            collateral_decimals = Decimal(10) ** collateral_decimals_nr
            y = Decimal(collateral_amount) / collateral_decimals
            m = Decimal(curve_position) / token_decimals
            a = coef_a
            b = a * m + coef_b * 2
            c = y * -2

            if is_variant(trade_direction, "Sell"):
                b = -b
                c = -c

            discriminant = b**2 - a * c * 4
            if discriminant < 0:
                raise ValueError('Negative discriminant, no real roots for tokensNr from collateral calculation')

            sqrt_discriminant = discriminant.sqrt()
            two_a = a * 2
            x1 = (-b + sqrt_discriminant) / two_a
            x2 = (-b - sqrt_discriminant) / two_a
            x = x2 if is_variant(trade_direction, "Sell") else x1

            return int(x * token_decimals)
        except Exception:
            return None

    def calculate_curve_price(self, coef_a: Decimal, coef_b: Decimal, curve_position: int, 
                              collateral_decimals_nr: int, token_decimals_nr: int) -> Optional[Decimal]:
        collateral_decimals = Decimal(10) ** collateral_decimals_nr
        token_decimals = Decimal(10) ** token_decimals_nr
        x = Decimal(curve_position)
        
        try:
            price = (coef_a * x / token_decimals + coef_b) * collateral_decimals
            return price
        except Exception:
            return None

    def get_coef_a(self, coef_b: Decimal, total_supply: int, decimal_nr: int, 
                   marketcap_threshold: int, marketcap_decimal_nr: int) -> Decimal:
        token_decimals = Decimal(10) ** decimal_nr
        marketcap_decimals = Decimal(10) ** marketcap_decimal_nr
        dynamic_threshold = Decimal(self.dynamic_threshold) / 100
        dynamic_threshold_in_whole_unit = Decimal(total_supply) * dynamic_threshold / token_decimals
        marketcap_threshold_in_whole_unit = Decimal(marketcap_threshold) / marketcap_decimals

        return (marketcap_threshold_in_whole_unit / dynamic_threshold_in_whole_unit - coef_b) / dynamic_threshold_in_whole_unit

    def get_coef_b(self, coef_b_minimal_units: int, collateral_decimals_nr: int) -> Decimal:
        return Decimal(coef_b_minimal_units) / (Decimal(10) ** collateral_decimals_nr)
    
    def get_tokens_amount_from_collateral(
        self, 
        amount: int,
        curve_account: CurveAccount,
        trade_direction: TradeType
    ):
        collateral_amount = amount
        curve_position = curve_account.total_supply - curve_account.curve_amount
        
        return self.get_tokens_nr_from_collateral({
            'collateralAmount': collateral_amount,
            'collateralDecimalsNr': get_currency_decimals(curve_account.collateral_currency),
            'tokenDecimalsNr': curve_account.decimals,
            'marketCapDecimalsNr': get_currency_decimals(curve_account.marketcap_currency),
            'totalSupply': curve_account.total_supply,
            'marketCapThreshold': curve_account.marketcap_threshold,
            'curvePosition': curve_position,
            'coefB': curve_account.coef_b,
            'direction': trade_direction
        })

    def get_collateral_amount_from_tokens(
        self, 
        amount: int,
        curve_account: CurveAccount,
        trade_direction: TradeType 
    ):
        token_amount = amount
        current_curve_position = curve_account.total_supply - curve_account.curve_amount
        curve_position = (
            current_curve_position - token_amount
            if is_variant(trade_direction, "Sell")
            else current_curve_position
        )
        
        if curve_position < 0:
            raise ValueError('Insufficient tokens amount')
        
        price = self.get_collateral_price({
            'collateralDecimalsNr': get_currency_decimals(curve_account.collateral_currency),
            'tokenDecimalsNr': curve_account.decimals,
            'marketCapDecimalsNr': get_currency_decimals(curve_account.marketcap_currency),
            'totalSupply': curve_account.total_supply,
            'marketCapThreshold': curve_account.marketcap_threshold,
            'tokensAmount': token_amount,
            'curvePosition': curve_position,
            'coefB': curve_account.coef_b
        })
        
        return int(Decimal(price).to_integral_value())
