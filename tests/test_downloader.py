import pandas as pd

from hushine_debugger.downloader.binance_futures import download_klines, parse_klines, save_to_cache


def test_parse_binance_klines_to_dataframe():
    raw = [[1735689600000, "100", "101", "99", "100.5", "12", 1735689659999, "0", 1, "0", "0", "0"]]
    df = parse_klines(raw, symbol="BTCUSDT", interval="1m")
    assert df.iloc[0]["timestamp"] == 1735689600000
    assert df.iloc[0]["close"] == 100.5
    assert df.iloc[0]["symbol"] == "BTCUSDT"
    assert df.iloc[0]["market"] == "perpetual_futures"


class _FakeResponse:
    def __init__(self, raw):
        self._raw = raw

    def raise_for_status(self):
        return None

    def json(self):
        return self._raw


class _FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, *, params, timeout):
        self.calls.append((url, params, timeout))
        if len(self.calls) == 1:
            return _FakeResponse(
                [
                    [1735689600000, "100", "101", "99", "100", "12", 1735689659999, "0", 1, "0", "0", "0"],
                    [1735689660000, "101", "102", "100", "101", "13", 1735689719999, "0", 1, "0", "0", "0"],
                ]
            )
        return _FakeResponse([])


def test_download_klines_uses_injected_session():
    session = _FakeSession()
    df = download_klines(
        symbol="btcusdt",
        interval="1m",
        start_ms=1735689600000,
        end_ms=1735689720000,
        session=session,
    )
    assert len(df) == 2
    assert session.calls[0][1]["symbol"] == "BTCUSDT"
    assert session.calls[0][1]["limit"] == 1500


def test_download_klines_reports_progress():
    session = _FakeSession()
    events = []
    df = download_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=1735689600000,
        end_ms=1735689720000,
        session=session,
        on_progress=events.append,
    )

    assert len(df) == 2
    assert events
    assert events[-1].downloaded_bars == 2
    assert events[-1].expected_bars == 2
    assert events[-1].percent == 100.0


def test_save_to_cache_writes_parquet(tmp_path):
    df = pd.DataFrame(
        [
            {
                "timestamp": 1735689600000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "perpetual_futures",
                "interval": "1m",
            }
        ]
    )
    path = save_to_cache(tmp_path, df, symbol="BTCUSDT", interval="1m")
    assert path.exists()
    assert path.relative_to(tmp_path).as_posix() == "data/cache/binance/perpetual_futures/1m/BTCUSDT/klines.parquet"


def test_save_to_cache_merges_existing_rows(tmp_path):
    first = pd.DataFrame(
        [
            {
                "timestamp": 1735689600000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "perpetual_futures",
                "interval": "1m",
            }
        ]
    )
    second = pd.DataFrame(
        [
            {
                "timestamp": 1735689600000,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
                "volume": 10.0,
                "symbol": "BTCUSDT",
                "market": "perpetual_futures",
                "interval": "1m",
            },
            {
                "timestamp": 1735689660000,
                "open": 101.0,
                "high": 102.0,
                "low": 100.0,
                "close": 101.0,
                "volume": 11.0,
                "symbol": "BTCUSDT",
                "market": "perpetual_futures",
                "interval": "1m",
            },
        ]
    )

    path = save_to_cache(tmp_path, first, symbol="BTCUSDT", interval="1m")
    save_to_cache(tmp_path, second, symbol="BTCUSDT", interval="1m")

    merged = pd.read_parquet(path)
    assert merged["timestamp"].tolist() == [1735689600000, 1735689660000]
