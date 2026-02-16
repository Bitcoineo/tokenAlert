#!/usr/bin/env python3
"""
Ethereum Transfer Monitor

Monitors an Ethereum address for incoming ETH, ERC-20 token,
and ERC-721 NFT transfers using the Etherscan API.
Optionally monitors Aave V3 for WETH Supply events.
Plays a distinct sound alert for each event type.

Usage:
    python monitor.py 0xYourEthereumAddressHere
    python monitor.py 0xYourEthereumAddressHere --watch-aave
"""

import argparse
import os
import subprocess
import sys
import time
from decimal import Decimal

import requests
from dotenv import load_dotenv

ETHERSCAN_API_URL = "https://api.etherscan.io/v2/api"
POLL_INTERVAL = 5
MAX_SEEN_HASHES = 1000

TRANSFER_TYPES = {
    "ETH":   {"action": "txlist",      "sound": "/System/Library/Sounds/Ping.aiff"},
    "TOKEN": {"action": "tokentx",     "sound": "/System/Library/Sounds/Glass.aiff"},
    "NFT":   {"action": "tokennfttx",  "sound": "/System/Library/Sounds/Funk.aiff"},
}

# --- Aave V3 WETH Supply monitoring ---
AAVE_V3_POOL = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
# keccak256("Supply(address,address,address,uint256,uint16)")
SUPPLY_EVENT_TOPIC = "0x2b627736bca15cd5381dcf80b0bf11fd197d01a037c52b927a881a10fb73ba61"
# Canonical WETH address left-padded to 32 bytes
WETH_TOPIC = "0x000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2"
AAVE_SOUND = "/System/Library/Sounds/Hero.aiff"
AAVE_LOOKBACK_BLOCKS = 200  # ~40 minutes at ~12s/block


def format_token_amount(raw_value: str, token_decimal: str) -> str:
    """Convert raw token value to human-readable string using token decimals."""
    try:
        decimals = int(token_decimal)
    except (ValueError, TypeError):
        decimals = 18
    if decimals == 0:
        return raw_value
    amount = Decimal(raw_value) / (Decimal(10) ** decimals)
    return str(amount.normalize())


def play_alert(sound_path: str):
    """Play a macOS system sound asynchronously. Fails silently."""
    try:
        subprocess.Popen(
            ["afplay", sound_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def get_current_block(api_key: str) -> int | None:
    """Fetch the latest block number via Etherscan proxy endpoint."""
    params = {
        "chainid": 1,
        "module": "proxy",
        "action": "eth_blockNumber",
        "apikey": api_key,
    }
    try:
        resp = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")
        if result and result.startswith("0x"):
            return int(result, 16)
        print(f"  [eth_blockNumber] unexpected result: {result}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"  [eth_blockNumber network error] {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"  [eth_blockNumber parse error] {e}")
        return None


def fetch_transfers(address: str, api_key: str, action: str) -> list | None:
    """
    Fetch latest transfers for the given address and action type.
    Returns list of transaction dicts on success, None on error.
    """
    params = {
        "chainid": 1,
        "module": "account",
        "action": action,
        "address": address,
        "page": 1,
        "offset": 10,
        "sort": "desc",
        "apikey": api_key,
    }
    try:
        resp = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            if "No transactions found" in data.get("message", ""):
                return []
            print(f"  [{action}] {data.get('message', 'Unknown error')}")
            return None

        return data.get("result", [])

    except requests.exceptions.RequestException as e:
        print(f"  [{action} network error] {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"  [{action} parse error] {e}")
        return None


def fetch_aave_supply_logs(api_key: str, from_block: int) -> list | None:
    """Fetch Aave V3 WETH Supply event logs from from_block onward."""
    params = {
        "chainid": 1,
        "module": "logs",
        "action": "getLogs",
        "address": AAVE_V3_POOL,
        "fromBlock": from_block,
        "toBlock": 99999999,
        "topic0": SUPPLY_EVENT_TOPIC,
        "topic0_1_opr": "and",
        "topic1": WETH_TOPIC,
        "page": 1,
        "offset": 1000,
        "apikey": api_key,
    }
    try:
        resp = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("status") != "1":
            msg = data.get("message", "")
            if "No records found" in msg or "No transactions found" in msg:
                return []
            print(f"  [aave getLogs] {msg or 'Unknown error'}")
            return None

        return data.get("result", [])

    except requests.exceptions.RequestException as e:
        print(f"  [aave getLogs network error] {e}")
        return None
    except (ValueError, KeyError) as e:
        print(f"  [aave getLogs parse error] {e}")
        return None


def get_tx_sender(api_key: str, tx_hash: str) -> str | None:
    """Fetch the from address of a transaction via Etherscan proxy endpoint."""
    params = {
        "chainid": 1,
        "module": "proxy",
        "action": "eth_getTransactionByHash",
        "txhash": tx_hash,
        "apikey": api_key,
    }
    try:
        resp = requests.get(ETHERSCAN_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")
        if result and isinstance(result, dict):
            return result.get("from")
        return None
    except Exception:
        return None


def decode_supply_event(log: dict, api_key: str) -> dict:
    """Decode an Aave V3 Supply event log into a structured dict.

    Supply(address indexed reserve, address user, address indexed onBehalfOf,
           uint256 amount, uint16 indexed referralCode)

    Non-indexed params in data: user (bytes 0-31), amount (bytes 32-63)
    """
    data = log.get("data", "0x")
    tx_hash = log.get("transactionHash", "")

    user = "0x" + data[26:66] if len(data) >= 66 else "unknown"
    amount_wei = int(data[66:130], 16) if len(data) >= 130 else 0
    amount_display = format_token_amount(str(amount_wei), "18")

    sender = get_tx_sender(api_key, tx_hash) if tx_hash else None

    return {
        "tx_hash": tx_hash,
        "block_number": int(log.get("blockNumber", "0x0"), 16),
        "sender": sender,
        "user": user,
        "amount_display": amount_display,
    }


def print_supply_event(event: dict):
    """Print a formatted alert for an Aave V3 WETH Supply event."""
    print(f"\n{'=' * 60}")
    print(f"  AAVE V3 WETH SUPPLY DETECTED")
    print(f"  Amount: {event['amount_display']} WETH")
    if event["sender"]:
        print(f"  Sender: {event['sender']}")
        if event["user"].lower() != event["sender"].lower():
            print(f"  Via:    {event['user']}")
    else:
        print(f"  User:   {event['user']}")
    print(f"  Tx:     {event['tx_hash']}")
    print(f"{'=' * 60}\n")


def filter_incoming(transfers: list, address: str, transfer_type: str) -> list:
    """Filter transfers to only incoming ones for the given address."""
    addr_lower = address.lower()
    incoming = [tx for tx in transfers if tx.get("to", "").lower() == addr_lower]

    if transfer_type == "ETH":
        incoming = [
            tx for tx in incoming
            if tx.get("isError") != "1" and int(tx.get("value", "0")) > 0
        ]

    return incoming


def print_transfer(tx: dict, transfer_type: str):
    """Print a formatted alert for a single incoming transfer."""
    sender = tx.get("from", "unknown")
    tx_hash = tx.get("hash", "")

    print(f"\n{'=' * 60}")
    print(f"  NEW {transfer_type} TRANSFER DETECTED")

    if transfer_type == "ETH":
        amount = format_token_amount(tx.get("value", "0"), "18")
        print(f"  Amount: {amount} ETH")

    elif transfer_type == "TOKEN":
        token_name = tx.get("tokenName", "Unknown")
        token_symbol = tx.get("tokenSymbol", "???")
        amount = format_token_amount(
            tx.get("value", "0"), tx.get("tokenDecimal", "18")
        )
        print(f"  Token:  {token_name} ({token_symbol})")
        print(f"  Amount: {amount} {token_symbol}")

    elif transfer_type == "NFT":
        token_name = tx.get("tokenName", "Unknown")
        token_id = tx.get("tokenID", "?")
        print(f"  Token:  {token_name} #{token_id}")

    print(f"  From:   {sender}")
    print(f"  Tx:     {tx_hash}")
    print(f"{'=' * 60}\n")


def monitor(address: str, api_key: str, watch_aave: bool = False):
    """Main polling loop. Seeds seen hashes on first run, then alerts on new transfers."""
    seen: dict[str, set[str]] = {t: set() for t in TRANSFER_TYPES}
    first_run = True

    # Aave state
    aave_seen: set[str] = set()
    aave_from_block = 0
    if watch_aave:
        block = get_current_block(api_key)
        if block is not None:
            aave_from_block = max(0, block - AAVE_LOOKBACK_BLOCKS)
        else:
            print("Warning: Could not fetch current block. Aave monitoring starts from block 0.")

    print(f"Monitoring address: {address}")
    features = "ETH, ERC-20 tokens, ERC-721 NFTs"
    if watch_aave:
        features += ", Aave V3 WETH Supply events"
    print(f"Tracking: {features}")
    print(f"Polling every {POLL_INTERVAL} seconds. Press Ctrl+C to stop.\n")

    while True:
        # --- Wallet transfer polling ---
        for transfer_type, config in TRANSFER_TYPES.items():
            transfers = fetch_transfers(address, api_key, config["action"])

            if transfers is None:
                continue

            incoming = filter_incoming(transfers, address, transfer_type)

            if first_run:
                for tx in incoming:
                    seen[transfer_type].add(tx["hash"])
            else:
                new_transfers = []
                for tx in incoming:
                    if tx["hash"] not in seen[transfer_type]:
                        new_transfers.append(tx)
                        seen[transfer_type].add(tx["hash"])

                for tx in reversed(new_transfers):
                    print_transfer(tx, transfer_type)
                    play_alert(config["sound"])

            if len(seen[transfer_type]) > MAX_SEEN_HASHES:
                seen[transfer_type] = {tx["hash"] for tx in incoming}

        # --- Aave V3 Supply event polling ---
        if watch_aave:
            logs = fetch_aave_supply_logs(api_key, aave_from_block)

            if logs is not None:
                if first_run:
                    for log in logs:
                        aave_seen.add(log.get("transactionHash", ""))
                else:
                    new_events = []
                    for log in logs:
                        tx_hash = log.get("transactionHash", "")
                        if tx_hash and tx_hash not in aave_seen:
                            new_events.append(log)
                            aave_seen.add(tx_hash)

                    for log in new_events:
                        event = decode_supply_event(log, api_key)
                        print_supply_event(event)
                        play_alert(AAVE_SOUND)

                # Advance from_block to max block seen
                for log in logs:
                    block_num = int(log.get("blockNumber", "0x0"), 16)
                    if block_num > aave_from_block:
                        aave_from_block = block_num

                if len(aave_seen) > MAX_SEEN_HASHES:
                    aave_seen = {log.get("transactionHash", "") for log in logs}

        if first_run:
            first_run = False

        try:
            time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Monitor an Ethereum address for incoming ETH, ERC-20, and NFT transfers."
    )
    parser.add_argument("address", help="Ethereum wallet address to monitor (0x...)")
    parser.add_argument(
        "--watch-aave",
        action="store_true",
        default=False,
        help="Also monitor Aave V3 Pool for WETH Supply events",
    )
    args = parser.parse_args()

    if not args.address.startswith("0x") or len(args.address) != 42:
        print("Error: Invalid Ethereum address. Must be 42 characters starting with 0x.")
        sys.exit(1)

    load_dotenv()
    api_key = os.getenv("ETHERSCAN_API_KEY")
    if not api_key:
        print("Error: ETHERSCAN_API_KEY not found in .env file.")
        print("Create a .env file with: ETHERSCAN_API_KEY=your_key_here")
        sys.exit(1)

    try:
        monitor(args.address, api_key, watch_aave=args.watch_aave)
    except KeyboardInterrupt:
        print("\nMonitor stopped. Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
