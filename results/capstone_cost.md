# Capstone cost measurement

`python measure_cost.py`: 10 requests to `serve.py` (port 8020, cache off), 9 s apart. Every number is read from that request's line in `logs/runs.jsonl`.

| # | request_id | query | status | model calls | prompt tokens | output tokens | total tokens | duration_ms |
|---|---|---|---|---|---|---|---|---|
| 1 | 8cab4a7bb98e | vintage graphic tee under $30 | ok | 2 | 785 | 300 | 1085 | 11216 |
| 2 | 9399f8602b04 | denim jacket | ok | 2 | 768 | 266 | 1034 | 3645 |
| 3 | 482e4f65f4b0 | black boots under $60 | ok | 2 | 772 | 288 | 1060 | 4676 |
| 4 | bf027c2ffaef | floral summer dress | ok | 2 | 861 | 340 | 1201 | 3318 |
| 5 | b4cb81f22638 | oversized hoodie size L | ok | 3 | 762 | 271 | 1033 | 6017 |
| 6 | 248c7dd020f0 | leather jacket | ok | 2 | 789 | 282 | 1071 | 11585 |
| 7 | e647066ac5fa | white sneakers | ok | 2 | 837 | 336 | 1173 | 7405 |
| 8 | dab5ced36651 | plaid skirt | ok | 2 | 798 | 308 | 1106 | 15748 |
| 9 | 9204d55f8704 | knit sweater | ok | 2 | 795 | 309 | 1104 | 6698 |
| 10 | ba1a83278d64 | cargo pants | ok | 2 | 818 | 307 | 1125 | 9727 |

- Average model calls per run: 2.1
- Average prompt tokens per run: 798.5
- Average output tokens per run: 300.7
- Average total tokens per run: 1099.2
- Average duration per run: 8.00 s (min 3.32, max 15.75)
