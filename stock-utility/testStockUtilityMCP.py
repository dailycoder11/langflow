import httpx
import json
import asyncio
from mcp.client.sse import sse_client

# ---------------- CONFIG ----------------
MCP_SERVER_URL = "http://127.0.0.1:8020/sse"
# ----------------------------------------

def print_test_header(test_name: str):
    """Print a formatted test header"""
    print("\n" + "="*60)
    print(f"TEST: {test_name}")
    print("="*60)

def print_result(result):
    """Print formatted result"""
    if hasattr(result, 'content'):
        for content in result.content:
            if hasattr(content, 'text'):
                data = json.loads(content.text)
                print(json.dumps(data, indent=2))
    else:
        print(json.dumps(result, indent=2, default=str))

# ============================================================
# TEST CASES
# ============================================================

async def test_1_buy_stocks(session):
    """Test buying stocks"""
    print_test_header("Test 1: Buy Stocks")
    
    # Buy AAPL
    print("\n📈 Buying 10 shares of AAPL...")
    result = await session.call_tool("buy_stock", {"stock_id": "AAPL", "quantity": 10})
    print_result(result)
    
    # Buy GOOGL
    print("\n📈 Buying 5 shares of GOOGL...")
    result = await session.call_tool("buy_stock", {"stock_id": "GOOGL", "quantity": 5})
    print_result(result)
    
    # Buy more AAPL
    print("\n📈 Buying 15 more shares of AAPL...")
    result = await session.call_tool("buy_stock", {"stock_id": "AAPL", "quantity": 15})
    print_result(result)
    
    data = json.loads(result.content[0].text)
    assert data.get("quantity") == 25, "Should have 25 AAPL shares (10+15)"
    
    print("\n✅ Buy Test PASSED")

async def test_2_list_stocks(session):
    """Test listing all stocks"""
    print_test_header("Test 2: List Stocks")
    
    print("\n📋 Listing all stocks in portfolio...")
    result = await session.call_tool("list_stocks", {})
    print_result(result)
    
    data = json.loads(result.content[0].text)
    
    print(f"\n📊 Portfolio Summary:")
    print(f"   Total Positions: {data.get('total_positions')}")
    print(f"   Total Shares: {data.get('total_shares')}")
    print(f"\n   Holdings:")
    for stock in data.get('stocks', []):
        print(f"   - {stock['stock_id']}: {stock['quantity']} shares")
    
    assert data.get("total_positions") == 2, "Should have 2 positions"
    assert data.get("total_shares") == 30, "Should have 30 total shares"
    
    print("\n✅ List Test PASSED")

async def test_3_sell_stocks(session):
    """Test selling stocks"""
    print_test_header("Test 3: Sell Stocks")
    
    # Sell partial AAPL
    print("\n📉 Selling 10 shares of AAPL...")
    result = await session.call_tool("sell_stock", {"stock_id": "AAPL", "quantity": 10})
    print_result(result)
    data = json.loads(result.content[0].text)
    assert data.get("quantity") == 15, "Should have 15 AAPL shares remaining"
    
    # Sell all GOOGL
    print("\n📉 Selling all 5 shares of GOOGL...")
    result = await session.call_tool("sell_stock", {"stock_id": "GOOGL", "quantity": 5})
    print_result(result)
    data = json.loads(result.content[0].text)
    assert data.get("quantity") == 0, "Should have 0 GOOGL shares"
    
    # List final portfolio
    print("\n📋 Final portfolio after sells...")
    result = await session.call_tool("list_stocks", {})
    print_result(result)
    data = json.loads(result.content[0].text)
    
    print(f"\n📊 Final Portfolio:")
    for stock in data.get('stocks', []):
        print(f"   - {stock['stock_id']}: {stock['quantity']} shares")
    
    assert data.get("total_positions") == 1, "Should have 1 position remaining"
    assert data.get("total_shares") == 15, "Should have 15 total shares"
    
    print("\n✅ Sell Test PASSED")

async def test_4_get_stock_price(session):
    """Test fetching stock price"""
    print_test_header("Test 4: Get Stock Price")

    print("\n💲 Fetching stock price for AAPL...")
    result = await session.call_tool("get_stock_price", {"symbol": "AAPL"})
    print_result(result)

    data = json.loads(result.content[0].text)

    # Core validations
    assert data.get("success") is True, "Price fetch should succeed"
    assert "price" in data, "Response must contain price"
    assert isinstance(data["price"], (int, float)), "Price must be numeric"
    assert data["price"] > 0, "Price must be positive"

    print(
        f"\n✅ Price fetched successfully: "
        f"{data['symbol']} = {data['price']} {data.get('currency', '')}"
    )
    print("\n✅ Price Test PASSED")


# ============================================================
# RUN ALL TESTS
# ============================================================

async def run_all_tests():
    """Run all test cases"""
    print("\n" + "🚀 "*20)
    print("STOCK MCP SERVER - SIMPLE TESTS")
    print("🚀 "*20)
    
    print(f"\nConnecting to MCP server at: {MCP_SERVER_URL}")
    print("⚠️  Make sure the server is running: python stockUtilityMCP.py\n")
    
    tests = [
        ("Buy Stocks", test_1_buy_stocks),
        ("List Stocks", test_2_list_stocks),    
        ("Sell Stocks", test_3_sell_stocks),
        ("Get Stock Price", test_4_get_stock_price),
    ]
    
    passed = 0
    failed = 0
    
    try:
        async with sse_client(MCP_SERVER_URL) as (read, write):
            from mcp import ClientSession
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                for test_name, test_func in tests:
                    try:
                        await test_func(session)
                        passed += 1
                    except AssertionError as e:
                        print(f"\n❌ {test_name} FAILED: {e}")
                        failed += 1
                    except Exception as e:
                        print(f"\n❌ {test_name} ERROR: {e}")
                        import traceback
                        traceback.print_exc()
                        failed += 1
                    
                    await asyncio.sleep(0.3)
    except Exception as e:
        print(f"\n❌ Failed to connect to server: {e}")
        print("Make sure the server is running with: python stockUtilityMCP.py")
        return
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(tests)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print("="*60)
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! 🎉\n")
    else:
        print(f"\n⚠️  {failed} TEST(S) FAILED ⚠️\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())