from solders.pubkey import Pubkey
from moonshot.types import is_variant, Currency

MOONSHOT_PROGRAM_ID = Pubkey.from_string("MoonCVVNZFSYkqNXP6bxHLPL6QQJiMagDL3qcqUQTrG")
HELIO_FEE_ID = Pubkey.from_string("5K5RtTWzzLp4P8Npi84ocf7F1vBsAu29N1irG4iiUnzt")
DEX_FEE_ID = Pubkey.from_string("3udvfL24waJcLhskRAsStNMoNUvtyXdxrWQz4hgi953N")
CONFIG_ACCOUNT_ID = Pubkey.from_string("36Eru7v11oU5Pfrojyn5oY3nETA1a1iqsw2WUu6afkM9")

TOKEN_PRECISION = 1_000_000_000
PLATFORM_FEE_BPS = 100

def get_currency_decimals(currency: Currency):
    if is_variant(currency, "Sol"):
        return 9