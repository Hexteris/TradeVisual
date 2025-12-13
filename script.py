
# First, let me create a comprehensive IBKR Flex XML sample to validate the parser
# This will be included in sample_data/

sample_ibkr_xml = """<?xml version="1.0" encoding="UTF-8"?>
<FlexQueryResponse queryName="Trade Summary">
    <FlexStatements>
        <FlexStatement accountId="U12345678" fromDate="2025-01-01" toDate="2025-12-31" period="MONTHLY">
            <Trades>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL" 
                       buySell="BUY" tradeID="123001" orderTime="2025-01-15 09:30:00" tradeTime="2025-01-15 09:31:22"
                       quantity="100" tradePrice="150.25" ibCommission="-10.00" ibCommissionCurrency="USD"
                       netCash="-15035.00" closePrice="150.25" fifoPnlRealized="0.00" 
                       mtmPnl="100.00" notes="" exchange="SMART" orderType="LMT" deliveryType="">
                </Trade>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL" 
                       buySell="SELL" tradeID="123002" orderTime="2025-01-20 14:15:00" tradeTime="2025-01-20 14:16:45"
                       quantity="50" tradePrice="151.80" ibCommission="-5.00" ibCommissionCurrency="USD"
                       netCash="7585.00" closePrice="151.80" fifoPnlRealized="75.25" 
                       mtmPnl="75.25" notes="" exchange="SMART" orderType="LMT" deliveryType="">
                </Trade>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="265598" symbol="AAPL" 
                       buySell="SELL" tradeID="123003" orderTime="2025-01-25 10:00:00" tradeTime="2025-01-25 10:01:15"
                       quantity="50" tradePrice="152.50" ibCommission="-5.00" ibCommissionCurrency="USD"
                       netCash="7620.00" closePrice="152.50" fifoPnlRealized="112.50" 
                       mtmPnl="112.50" notes="" exchange="SMART" orderType="LMT" deliveryType="">
                </Trade>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="1606611" symbol="MSFT" 
                       buySell="BUY" tradeID="123004" orderTime="2025-02-01 10:30:00" tradeTime="2025-02-01 10:31:10"
                       quantity="50" tradePrice="320.10" ibCommission="-8.00" ibCommissionCurrency="USD"
                       netCash="-16013.00" closePrice="320.10" fifoPnlRealized="0.00" 
                       mtmPnl="50.00" notes="" exchange="SMART" orderType="LMT" deliveryType="">
                </Trade>
                <Trade accountId="U12345678" assetCategory="STOCKS" currency="USD" conid="1606611" symbol="MSFT" 
                       buySell="SELL" tradeID="123005" orderTime="2025-02-10 15:45:00" tradeTime="2025-02-10 15:46:30"
                       quantity="50" tradePrice="325.80" ibCommission="-8.00" ibCommissionCurrency="USD"
                       netCash="16282.00" closePrice="325.80" fifoPnlRealized="285.00" 
                       mtmPnl="285.00" notes="" exchange="SMART" orderType="LMT" deliveryType="">
                </Trade>
            </Trades>
        </FlexStatement>
    </FlexStatements>
</FlexQueryResponse>
"""

# Save sample for reference
with open("/tmp/sample_ibkr_flex.xml", "w") as f:
    f.write(sample_ibkr_xml)

print("✅ Sample IBKR XML created")
print("\nSample structure preview:")
print(sample_ibkr_xml[:800] + "...\n")
