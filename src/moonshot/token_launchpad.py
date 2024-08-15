import json
import os
import anchorpy
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.transaction import TransactionVersion, Legacy
from solders.instruction import Instruction
from solders.system_program import ID
from solders.sysvar import RENT
from solders.signature import Signature
from solders.address_lookup_table_account import AddressLookupTableAccount
from solana.rpc.async_api import AsyncClient
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed
from solana.transaction import AccountMeta
from solders.compute_budget import set_compute_unit_limit, set_compute_unit_price
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from solders.system_program import ID as SYS_PROGRAM_ID
from spl.token.instructions import get_associated_token_address
from anchorpy import Program, Context, Idl, Provider, Wallet
from pathlib import Path

import moonshot
from moonshot.constants import MOONSHOT_PROGRAM_ID, HELIO_FEE_ID, DEX_FEE_ID, CONFIG_ACCOUNT_ID
from moonshot.get_accounts import get_curve_account

DEFAULT_TX_OPTIONS = TxOpts(skip_confirmation=False, preflight_commitment=Processed)

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

        file = Path(str(moonshot.__path__[0]) + "/moonshot.json")
        with file.open() as f:
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

    async def get_curve_account(self):
        return await get_curve_account(self.program, self.curve_account_pubkey)







