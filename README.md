# Moonshot
Unofficial [Moonshot](https://github.com/wen-moon-ser/moonshot-sdk) Python SDK

Requires `python=3.10`. Clone and install:
```console
git clone https://github.com/ruiqic/moonshot-py.git
cd moonshot-py
pip install -e .
```

## Example Usage
```python
import os
from solders.pubkey import Pubkey
from anchorpy import Wallet
from solana.rpc.async_api import AsyncClient

from moonshot.token_launchpad import TokenLaunchpad
from moonshot.keypair import load_keypair
from moonshot.constants import TOKEN_PRECISION
from moonshot.types import FixedSide

connection = AsyncClient("https://api.mainnet-beta.solana.com/") # mainnet RPC
keypair_file = os.environ.get('FILLER_KEY_FILE_PATH')
keypair = load_keypair(keypair_file) # your keypair.json file
wallet = Wallet(keypair)

# choose a token to buy or sell
token_mint = Pubkey.from_string("C1SHmyVLzhWRbXCh2zGYV9n5Wmn8suVGUTt3xedL6Etb") 
launchpad = TokenLaunchpad(connection, wallet, token_mint)

# buy 0.1 SOL worth of tokens
buy_amount = int(0.1 * TOKEN_PRECISION)
buy_ix = await launchpad.get_buy_ix(buy_amount, fixed_side=FixedSide.ExactIn(), slippage_bps=500)
buy_sig = await launchpad.send_ix(buy_ix)
print("Buy sig:", buy_sig)

# sell 0.05 SOL worth of tokens
sell_amount = int(0.05 * TOKEN_PRECISION)
sell_ix = await launchpad.get_sell_ix(sell_amount, fixed_side=FixedSide.ExactOut(), slippage_bps=500)
sell_sig = await launchpad.send_ix(sell_ix)
print("Sell sig:", sell_sig)
```