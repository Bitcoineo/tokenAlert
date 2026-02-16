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

Aave Supply alerts show the transaction sender (EOA) and, when different, the intermediary contract address via which the supply was routed.

Press `Ctrl+C` to stop.
