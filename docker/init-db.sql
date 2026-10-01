-- Schema initialization for financial exchange migration
CREATE TABLE IF NOT EXISTS trades (
    trade_id VARCHAR(64) PRIMARY KEY,
    instrument VARCHAR(32) NOT NULL,
    price DOUBLE PRECISION NOT NULL,
    quantity INTEGER NOT NULL,
    buy_order_id VARCHAR(64) NOT NULL,
    sell_order_id VARCHAR(64) NOT NULL,
    timestamp VARCHAR(64) NOT NULL
);

-- B-Tree indexes for fast point-lookup and range aggregations
CREATE INDEX IF NOT EXISTS idx_trades_instrument ON trades(instrument);
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_volume ON trades(price, quantity);
