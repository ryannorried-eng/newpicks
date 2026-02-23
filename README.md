# newpicks

## Dev smoke check for odds ingestion

1. Start services:

```bash
docker compose up -d --build
```

2. Wait ~1-2 minutes, then verify snapshots are being ingested:

```bash
docker compose exec db psql -U postgres -d sharppicks -c "select count(*) from odds_snapshots;"
```

Expected: `count` should be greater than `0`.

3. Optional status check from backend API:

```bash
curl -s http://localhost:8000/api/v1/system/health
```

Expected fields include `snapshot_count` and `last_snapshot_time`.

## Worker logs when polling is active

```bash
docker compose logs -f worker
```

You should see cycle lines similar to:

- `odds polling cycle complete: games=12 snapshots_inserted=84 next_sleep_seconds=600`
- `odds polling cycle failed: games=0 snapshots_inserted=0 next_sleep_seconds=60` (after provider error)
- `ODDS_API_KEY is missing; skipping ingestion cycle until it is configured`
