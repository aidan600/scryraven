# AG-96I3AF6A Broker Alignment Operator Snippet

Private-broker placeholder only. Do not commit private broker files, provider
module paths, secrets, or `.env` behavior.

```python
"ag96i3af6a-live-author-lane-smoke-once": {"output": "output/ag96i3af6a_live_author_lane_smoke_packet.json", "max_provider_search_calls": 0, "max_fetch_read_attempts": 0, "max_retrieval_calls": 0, "max_model_calls": 1, "retries_allowed": False, "operator_private_setup_required": True, "template_command": ["py", "scripts\\ag96i3af6a_brokered_author_lane_smoke.py", "--job-id", "ag96i3af6a-live-author-lane-smoke-once", "--output", "output\\ag96i3af6a_live_author_lane_smoke_packet.json", "--broker-live-mode", "--confirm-live-provider-call", "--adapter-factory", "<private_broker_module>:<factory>"]}
```

`<private_broker_module>:<factory>` is an operator-private injection point; the
tracked repo intentionally ships no provider adapter or environment loader.
