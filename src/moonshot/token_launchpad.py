from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.instruction import Instruction
from solders.message import MessageV0
from solders.hash import Hash
from solders.signature import Signature
from solders.rpc.responses import SendTransactionResp
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed, Confirmed
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solders.system_program import ID as SYS_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from anchorpy import Program, Context, Idl, Provider, Wallet
from pathlib import Path
from typing import Optional, Iterable, Union

import moonshot
from moonshot.constants import MOONSHOT_PROGRAM_ID, HELIO_FEE_ID, DEX_FEE_ID, CONFIG_ACCOUNT_ID
from moonshot.types import is_variant, CurveAccount, TradeType, FixedSide, TradeParams
from moonshot.curve import AbstractCurve, ConstantProductCurveV1, LinearCurveV1
from moonshot.get_accounts import get_curve_account

DEFAULT_TX_OPTIONS = TxOpts(skip_confirmation=False, skip_preflight=False, preflight_commitment=Processed)
DEFAULT_FIXED_SIDE = FixedSide.ExactIn()

class TokenLaunchpad:
    def __init__(
        self, 
        connection : AsyncClient, 
        wallet : Wallet, 
        token_mint : Pubkey,
        opts: TxOpts = DEFAULT_TX_OPTIONS,
    ):
        self.connection = connection
        self.wallet = wallet
        self.authority = wallet.public_key
        self.token_mint = token_mint
        self.opts = opts

        file = Path(str(moonshot.__path__[0]) + "/moonshot.json")
        raw = file.read_text()
        idl = Idl.from_json(raw)

        provider = Provider(connection, wallet, opts)
        self.program_id = MOONSHOT_PROGRAM_ID
        self.program = Program(
            idl,
            self.program_id,
            provider,
        )

        self.curve_account_pubkey = Pubkey.find_program_address(
            [b"token", bytes(token_mint)],
            MOONSHOT_PROGRAM_ID,
        )[0]
        self.curve_token_account_pubkey = get_associated_token_address(self.curve_account_pubkey, token_mint)
        self.token_account_pubkey = get_associated_token_address(self.authority, token_mint)

        self.curve = None

    async def get_token_amount_by_collateral(
        self,
        amount: int,
        trade_direction: TradeType,
        curve_account: Optional[CurveAccount] = None
    ) -> int:
        if curve_account is None:
            curve_account = await self.get_curve_account()
        if self.curve is None:
            self.curve = self.get_curve(curve_account)
        return self.curve.get_tokens_amount_from_collateral(amount, curve_account, trade_direction)

    async def get_collateral_amount_by_tokens(
        self,
        amount: int,
        trade_direction: TradeType,
        curve_account: Optional[CurveAccount] = None
    ) -> int:
        if curve_account is None:
            curve_account = await self.get_curve_account()
        if self.curve is None:
            self.curve = self.get_curve(curve_account)
        return self.curve.get_collateral_amount_from_tokens(amount, curve_account, trade_direction)

    async def get_curve_account(self) -> CurveAccount:
        return await get_curve_account(self.program, self.curve_account_pubkey)
    
    def get_curve(self, curve_account: CurveAccount) -> AbstractCurve:
        if is_variant(curve_account.curve_type, "ConstantProductV1"):
            return ConstantProductCurveV1()
        elif is_variant(curve_account.curve_type, "LinearV1"):
            return LinearCurveV1()
        else:
            raise NotImplementedError("Invalid curve type")

    async def get_buy_ix(
        self,
        amount: int,
        fixed_side: Optional[FixedSide] = None,
        slippage_bps: int = 100,
        curve_account: Optional[CurveAccount] = None
    ) -> Instruction:
        if fixed_side is None:
            fixed_side = DEFAULT_FIXED_SIDE

        if is_variant(fixed_side, "ExactIn"):
            collateral_amount = amount
            token_amount = await self.get_token_amount_by_collateral(collateral_amount, TradeType.Buy(), curve_account)
        else:
            token_amount = amount
            collateral_amount = await self.get_collateral_amount_by_tokens(token_amount, TradeType.Buy(), curve_account)

        trade_params = TradeParams(
            token_amount=token_amount,
            collateral_amount=collateral_amount,
            fixed_side=fixed_side.index,
            slippage_bps=slippage_bps
        )

        ix = self.program.instruction["buy"](
            trade_params,
            ctx=Context(
                accounts={
                    "sender": self.authority,
                    "sender_token_account": self.token_account_pubkey,
                    "curve_account": self.curve_account_pubkey,
                    "curve_token_account": self.curve_token_account_pubkey,
                    "dex_fee": DEX_FEE_ID,
                    "helio_fee": HELIO_FEE_ID,
                    "mint": self.token_mint,
                    "config_account": CONFIG_ACCOUNT_ID,
                    "token_program": TOKEN_PROGRAM_ID,
                    "associated_token_program": ASSOCIATED_TOKEN_PROGRAM_ID,
                    "system_program": SYS_PROGRAM_ID,
                },
            ),
        )
        return ix

    async def get_sell_ix(
        self,
        amount: int,
        fixed_side: Optional[FixedSide] = None,
        slippage_bps: int = 100,
        curve_account: Optional[CurveAccount] = None
    ) -> Instruction:
        if fixed_side is None:
            fixed_side = DEFAULT_FIXED_SIDE

        if is_variant(fixed_side, "ExactOut"):
            collateral_amount = amount
            token_amount = await self.get_token_amount_by_collateral(collateral_amount, TradeType.Sell(), curve_account)
        else:
            token_amount = amount
            collateral_amount = await self.get_collateral_amount_by_tokens(token_amount, TradeType.Sell(), curve_account)

        trade_params = TradeParams(
            token_amount=token_amount,
            collateral_amount=collateral_amount,
            fixed_side=fixed_side.index,
            slippage_bps=slippage_bps
        )

        ix = self.program.instruction["sell"](
            trade_params,
            ctx=Context(
                accounts={
                    "sender": self.authority,
                    "sender_token_account": self.token_account_pubkey,
                    "curve_account": self.curve_account_pubkey,
                    "curve_token_account": self.curve_token_account_pubkey,
                    "dex_fee": DEX_FEE_ID,
                    "helio_fee": HELIO_FEE_ID,
                    "mint": self.token_mint,
                    "config_account": CONFIG_ACCOUNT_ID,
                    "token_program": TOKEN_PROGRAM_ID,
                    "associated_token_program": ASSOCIATED_TOKEN_PROGRAM_ID,
                    "system_program": SYS_PROGRAM_ID,
                },
            ),
        )
        return ix

    async def fetch_latest_blockhash(self) -> Hash:
        return (
            await self.connection.get_latest_blockhash(Confirmed)
        ).value.blockhash

    async def send_ix(
        self,
        ix : Union[Instruction, Iterable[Instruction]],
        compute_unit_price: int = 20_000,
        compute_unit_limit: int = 100_000,
    ) -> Signature:
        compute_price_ix = set_compute_unit_price(compute_unit_price)
        compute_limit_ix = set_compute_unit_limit(compute_unit_limit)
        if isinstance(ix, Instruction):
            ixs = [compute_limit_ix, compute_price_ix, ix]
        else:
            ixs = [compute_limit_ix, compute_price_ix] + list(ix)

        latest_blockhash = await self.fetch_latest_blockhash()
        msg = MessageV0.try_compile(
            self.authority, ixs, [], latest_blockhash
        )
        tx = VersionedTransaction(msg, [self.wallet.payer])
        body = self.connection._send_raw_transaction_body(bytes(tx), self.opts)
        resp = await self.connection._provider.make_request(body, SendTransactionResp)
        return resp.value







