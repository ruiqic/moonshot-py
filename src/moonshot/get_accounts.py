from typing import cast, Optional, Callable
from solders.pubkey import Pubkey
from anchorpy import Program, ProgramAccount
from solana.rpc.commitment import Commitment, Processed, Confirmed

from moonshot.types import *


async def get_account_data_and_slot(
    address: Pubkey,
    program: Program,
    commitment: Commitment = Processed,
    decode: Optional[Callable[[bytes], T]] = None,
) -> Optional[DataAndSlot[T]]:
    account_info = await program.provider.connection.get_account_info(
        address,
        encoding="base64",
        commitment=commitment,
    )

    if not account_info.value:
        return None

    slot = account_info.context.slot
    data = account_info.value.data

    decoded_data = (
        decode(data) if decode is not None else program.coder.accounts.decode(data)
    )

    return DataAndSlot(slot, decoded_data)

async def get_config_account(
    program: Program,
    config_account_pubkey: Pubkey,
) -> ConfigAccount:
    data_and_slot = await get_account_data_and_slot(config_account_pubkey, program)
    return cast(ConfigAccount, data_and_slot.data)


async def get_curve_account(
    program: Program,
    curve_account_pubkey: Pubkey,
) -> CurveAccount:
    data_and_slot = await get_account_data_and_slot(curve_account_pubkey, program)
    if data_and_slot is None:
        raise ValueError("Curve finalized: liquidity migrated from Moonshot.")
    return cast(CurveAccount, data_and_slot.data)

