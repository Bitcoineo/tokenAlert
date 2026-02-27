# tokenAlert

CLI tool that monitors any Ethereum address for incoming transfers in real time. Detects ETH, ERC-20 tokens, ERC-721 NFTs, and Aave V3 WETH supply events. Plays a distinct system sound for each type.

**Stack:** `Python 3 · Etherscan API · python-dotenv · requests`

---

## Why I built this

I was manually refreshing Etherscan to watch for incoming transfers to wallets I was tracking. That gets old fast. This tool polls every 5 seconds and plays a different sound depending on what came in, so you can work on something else and know immediately what type of transfer just landed.

## Features

- Monitors ETH, ERC-20, and ERC-721 transfers on any address
- Optional Aave V3 WETH supply event tracking via on-chain log filtering
- Distinct macOS system sound per transfer type (Ping, Glass, Funk, Hero)
- Syncs with recent activity on startup so no false alerts on launch
- Resolves Aave supply sender through intermediary contracts whapplicable

## Sound Alerts

| Event | Sound |
|-------|-------|
| ETH transfer | Ping |
| ERC-20 token | Glass |
| ERC-721 NFT | Funk |
| Aave V3 WETH Supply | Hero |

## Setup

    python3 -m venv venv
    source venv/bin/activate
    pip install requests python-dotenv

Create a .env file with your Etherscan API key:

    ETHERSCAN_API_KEY=your_key_here

Get a free key at https://etherscan.io/myapikey

## Usage

    python monitor.py 0xYourEthereumAddress
    python monitor.py 0xYourEthereumAddress --watch-aave

Press Ctrl+C to stop.

## Example Output

    NEW ETH TRANSFER DETECTED
    Amount: 1.5 ETH
    From:   0x28c6c06298d514db089934071355e5743bf21d60
    Tx:     0x7a8f...3b2e

    NEW TOKEN TRANSFER DETECTED
    Token:  Tether USD (USDT)
    Amount: 5000 USDT
    From:   0x28c6c06298d514db089934071355e5743bf21d60
    Tx:     0x3c1d...9f4a

    AAVE V3 WETH SUPPLY DETECTED
    Amount: 8 WETH
    Sender: 0x519f7709577c94999e4c7cfacb539cacb9edb7b8
    Via:    0xd01607c3c5ecaba394d8be377a08590149325722
    Tx:     0x08f9...117d

## GitHub Topics

`ethereum` `python` `cli` `etherscan` `erc20` `nft` `aave` `web3` `crypto` `monitoring`
