# PR #40: feat: Nautilus-Trader

**Repo**: DeevsDeevs/agent-system  
**URL**: https://github.com/DeevsDeevs/agent-system/pull/40

**@yk4r2**: Pipeline-ordered navigation? Like data -> storage -> hypothesis -> backtest -> fronttest -> analyze?


**@yk4r2**: zero post-hoc analytics covered for now
no references/analytics.md


**@yk4r2**: adapter dev files are about 1/2 compressible


**@yk4r2**: ???Missing testing guidance: no references/testing.md; the only test is the __main__ script???


**@yk4r2**: No deployment guidance: Docker, systemd, process management


**@yk4r2**: ???State persistence patterns???
Like now if we restart = we'll totally loose the state


**@yk4r2**: Fill / latency / slippage metrics are necessary


**@yk4r2**: optimal log rotation guidance?


**@yk4r2**: multi-instrument backtest example is clearly needed


**@yk4r2**: no bar-based rust bt example (may be of less importance though)


**@yk4r2**: backtest -> live migration guidance?
at least a checklist?


**@yk4r2**: Custom indicator development pattern is needed


**@yk4r2**: Hot path optimization isn't addressed anywhere


**@yk4r2**: MessageBus internals aren't covered at all; need more opacity


**@yk4r2**: Too much of AI slop too :(

I've stopped commenting on useless comments/strings/etc, it's too many of those


**@yk4r2**: 13+ identical blocks across 10 Rust examples (~200 lines) -> macro or "see canonical example" note


**@yk4r2**: Deduplicate anti-hallucination tables: SKILL.md = master; reference files = topic-specific deltas only.

PLEASE TRY TO MAKE YOUR SKILL TO AS LOW LINES AS POSSIBLE


**@yk4r2**: add references/data_pipeline.md -> validation, gap detection, timestamp audit, quality grading



## Inline Review Comments

### `nautilus-trader/examples/binance_enrichment_actor.py`

- **L60** (@yk4r2): `super().__init__()`



### `nautilus-trader/examples/bracket_order_backtest.py`

- **L34** (@yk4r2): None guard?



### `nautilus-trader/examples/bracket_order_backtest.rs`

- **L116** (@yk4r2): enters on every flat while python enters just once — spec divergence



### `nautilus-trader/examples/custom_data_backtest.rs`

- **L30** (@yk4r2): never use vpin please

- **L118** (@yk4r2): never use vpin please
also the formula's wrong, it's `abs(x-0.5)*2`-transformed



### `nautilus-trader/examples/ema_crossover_backtest.py`

- **L39** (@yk4r2): None guard?



### `nautilus-trader/examples/ema_crossover_backtest.rs`

- **L152** (@yk4r2): ??? let's do something with this???



### `nautilus-trader/examples/live_data_collector.rs`

- **L36** (@yk4r2): unbounded vec growth + triple-clone in collector || ?Possible OOM?

- **L37** (@yk4r2): same here

- **L38** (@yk4r2): same here

- **L197** (@yk4r2): unbounded vec growth + triple-clone in collector || ?Possible OOM? Till 237 line



### `nautilus-trader/examples/live_modify_order_test.rs`

- **L109** (@yk4r2): this boilerplace for deref/derefmut/debug is widely duplicated in many files my man, we need to write good code, not just copy/paste things

- **L136** (@yk4r2): No cancel path -> may leave orphaned orders on timeout

- **L155** (@yk4r2): here too

- **L175** (@yk4r2): Like wtf is wrong with you man? 1.0 price fallback on live???



### `nautilus-trader/examples/live_order_test.rs`

- **L116** (@yk4r2): here



### `nautilus-trader/examples/market_maker_backtest.py`

- **L38** (@yk4r2): None guard?

- **L45** (@yk4r2): nearly identical with `spread_capture_live.py` -> code duplication

- **L95** (@yk4r2): Canonical MM pattern: on_order_filled resets _bid_id/_ask_id
Not tested too



### `nautilus-trader/examples/market_maker_backtest.rs`

- **L55** (@yk4r2): Price::from(format!()) -> heap alloc per tick is too slow my ni👀a



### `nautilus-trader/examples/signal_pipeline_backtest.py`

- **L76** (@yk4r2): None guard?



### `nautilus-trader/examples/spread_capture_live.py`

- **L1** (@yk4r2): Missing `on_order_rejected` + `on_order_modify_rejected`

- **L34** (@yk4r2): `key_type=BinanceKeyType.ED25519`? Required for exec



### `nautilus-trader/examples/test_enrichment_actor_backtest.py`

- **L106** (@yk4r2): `InstrumentProviderConfig(load_ids=…)?`
like the first documented silent failure is missing?



### `nautilus-trader/references/actors_and_signals.md`

- **L159** (@yk4r2): `super().__init__()`

- **L512** (@yk4r2): Broken md rendering of this table



### `nautilus-trader/references/backtesting.md`

- **L511** (@yk4r2): bruv that's twice the midprice

- **L711** (@yk4r2): Broken md rendering of this table



### `nautilus-trader/references/derivatives.md`

- **L304** (@yk4r2): super().__init__()



### `nautilus-trader/references/market_making.md`

- **L95** (@yk4r2): Canonical MM pattern: `on_order_filled` resets `_bid_id`/`_ask_id`
No sign of any reset here however


