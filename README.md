# Ethereum Transfer Monitor

CLI tool that monitors an Ethereum address for incoming ETH, ERC-20 token, and ERC-721 NFT transfers. Optionally watches Aave V3 for WETH Supply events. Plays a distinct sound alert for each type.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install requests python-dotenv
```

Create a `.env` file with your [Etherscan API key](https://etherscan.io/myapikey):

```
ETHERSCAN_API_KEY=your_key_here
```

## Usage

```bash
python monitor.py 0xYourEthereumAddress
python monitor.py 0xYourEthereumAddress --watch-aave
```

The tool will:
1. Sync with recent activity on startup (no alerts fired)
2. Poll every 5 seconds for new incoming transfers
3. Print transfer details and play a sound on each detection

| Type | Sound |
|---|---|
| ETH | Ping |
| ERC-20 Token | Glass |
| ERC-721 NFT | Funk |
| Aave V3 WETH Supply | Hero |

Aave Supply alerts show the transaction sender (EOA) and, when different, the intermediary contract via which the supply was routed. If the sender lookup fails, the contract user address is shown instead.

## Example output

```
============================================================
  NEW ETH TRANSFER DETECTED
  Amount: 1.5 ETH
  From:   0x28c6c06298d514db089934071355e5743bf21d60
  Tx:     0x7a8f...3b2e
============================================================

============================================================
  NEW TOKEN TRANSFER DETECTED
  Token:  Tether USD (USDT)
  Amount: 5000 USDT
  From:   0x28c6c06298d514db089934071355e5743bf21d60
  Tx:     0x3c1d...9f4a
============================================================

============================================================
  NEW NFT TRANSFER DETECTED
  Token:  CryptoPunks #7804
  From:   0x1919db36ca2fa2e15f9000fd9cdc2edcf863e685
  Tx:     0x9b2e...1c7f
============================================================

============================================================
  AAVE V3 WETH SUPPLY DETECTED
  Amount: 8 WETH
  Sender: 0x519f7709577c94999e4c7cfacb539cacb9edb7b8
  Via:    0xd01607c3c5ecaba394d8be377a08590149325722
  Tx:     0x08f9...117d
============================================================
```

Press `Ctrl+C` to stop.
