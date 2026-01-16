from mcp.server.fastmcp import FastMCP
import csv
import os
from pathlib import Path
import uvicorn
import requests
import re

# ---------------- CONFIG ----------------
CSV_PATH = "/tmp/stocks_portfolio.csv"
BALANCE_CSV_PATH = "/tmp/account_balance.csv"
PORT = 8020
# ----------------------------------------

mcp = FastMCP("stock-trading-mcp")

# ============================================================
# PORTFOLIO (shares = int)
# ============================================================

def init_portfolio_csv():
    if not os.path.exists(CSV_PATH):
        Path(CSV_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["stock_id", "quantity"])
        print(f"Created portfolio CSV at {CSV_PATH}")


def read_portfolio() -> dict:
    portfolio = {}
    try:
        with open(CSV_PATH, "r", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                portfolio[row["stock_id"]] = int(row["quantity"])
    except FileNotFoundError:
        init_portfolio_csv()
    return portfolio


def write_portfolio(portfolio: dict):
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["stock_id", "quantity"])
        for stock_id, qty in portfolio.items():
            if qty > 0:
                writer.writerow([stock_id, qty])

# ============================================================
# BALANCE (money = float)
# ============================================================

def init_balance_csv(initial_balance: float = 100000.0):
    if not os.path.exists(BALANCE_CSV_PATH):
        Path(BALANCE_CSV_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(BALANCE_CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["balance"])
            writer.writerow([f"{initial_balance:.2f}"])
        print(f"Created balance CSV with ₹{initial_balance:.2f}")


def read_balance() -> float:
    with open(BALANCE_CSV_PATH, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            return float(row["balance"])
    return 0.0


def write_balance(new_balance: float):
    with open(BALANCE_CSV_PATH, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["balance"])
        writer.writerow([f"{round(new_balance, 2):.2f}"])

# ============================================================
# MONEY TOOLS (FLOAT SCHEMA ✔)
# ============================================================

@mcp.tool()
def debit_money(amount: float, reason: str = "") -> dict:
    """
    Deduct money from account balance.
    """
    if amount <= 0.0:
        return {"success": False, "message": "Amount must be positive"}

    balance = read_balance()

    if amount > balance:
        return {
            "success": False,
            "message": "Insufficient balance",
            "current_balance": round(balance, 2)
        }

    new_balance = round(balance - amount, 2)
    write_balance(new_balance)

    return {
        "success": True,
        "balance": new_balance,
        "message": f"Debited ₹{amount:.2f}. {reason}"
    }


@mcp.tool()
def credit_money(amount: float, reason: str = "") -> dict:
    """
    Add money to account balance.
    """
    if amount <= 0.0:
        return {"success": False, "message": "Amount must be positive"}

    balance = read_balance()
    new_balance = round(balance + amount, 2)
    write_balance(new_balance)

    return {
        "success": True,
        "balance": new_balance,
        "message": f"Credited ₹{amount:.2f}. {reason}"
    }


@mcp.tool()
def get_balance() -> dict:
    """
    Get current account balance.
    """
    return {
        "success": True,
        "balance": round(read_balance(), 2)
    }

# ============================================================
# STOCK TOOLS (quantity = int)
# ============================================================

@mcp.tool()
def buy_stock(stock_id: str, quantity: int) -> dict:
    if quantity <= 0:
        return {"success": False, "message": "Quantity must be positive"}

    stock_id = stock_id.upper().strip()
    portfolio = read_portfolio()
    portfolio[stock_id] = portfolio.get(stock_id, 0) + quantity
    write_portfolio(portfolio)

    return {
        "success": True,
        "stock_id": stock_id,
        "quantity": portfolio[stock_id],
        "message": f"Bought {quantity} shares of {stock_id}"
    }


@mcp.tool()
def sell_stock(stock_id: str, quantity: int) -> dict:
    if quantity <= 0:
        return {"success": False, "message": "Quantity must be positive"}

    stock_id = stock_id.upper().strip()
    portfolio = read_portfolio()

    if stock_id not in portfolio:
        return {"success": False, "message": "Stock not found"}

    if quantity > portfolio[stock_id]:
        return {
            "success": False,
            "message": "Not enough shares",
            "available": portfolio[stock_id]
        }

    portfolio[stock_id] -= quantity
    if portfolio[stock_id] == 0:
        del portfolio[stock_id]

    write_portfolio(portfolio)

    return {
        "success": True,
        "stock_id": stock_id,
        "quantity": portfolio.get(stock_id, 0),
        "message": f"Sold {quantity} shares of {stock_id}"
    }


@mcp.tool()
def list_stocks() -> dict:
    portfolio = read_portfolio()
    return {
        "success": True,
        "total_positions": len(portfolio),
        "total_shares": sum(portfolio.values()),
        "stocks": [
            {"stock_id": k, "quantity": v}
            for k, v in sorted(portfolio.items())
        ]
    }

# ============================================================
# STOCK PRICE TOOL (FLOAT)
# ============================================================

@mcp.tool()
def get_stock_price(symbol: str) -> dict:
    """
    Fetch approximate stock price from Google Finance.
    """
    symbol = symbol.upper().strip()
    url = f"https://www.google.com/finance/quote/{symbol}:NASDAQ"

    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=10)

    match = re.search(r'\$([0-9,]+\.\d+)', r.text)
    if not match:
        return {"success": False, "message": "Unable to extract price"}

    price = float(match.group(1).replace(",", ""))

    return {
        "success": True,
        "symbol": symbol,
        "price": price,
        "currency": "USD",
        "source": "Google Finance"
    }

# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    print("Initializing Stock Trading MCP Server...")
    init_portfolio_csv()
    init_balance_csv(100000.0)

    print(f"Starting MCP server on http://127.0.0.1:{PORT}/sse")
    uvicorn.run(
        mcp.sse_app,
        host="127.0.0.1",
        port=PORT,
        log_level="info",
    )
