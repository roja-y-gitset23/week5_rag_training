# Enterprise RAG Pipeline

A small RAG project built in two tasks:

| Task | What it does |
|---|---|
| **Task 1: Multi-Source Ingestion** | Ingests PDF policy documents and CSV data exports into text chunks with metadata. Uses SHA-256 hashing so unchanged files are skipped. |
| **Task 2: Mock SQL via Function Calling** | A mock HR database with 3 safe SQL tools and a router that sends each question to RAG (policy), SQL (data) or both (mixed). Includes route and timing logs (bonus). |

Branch: `feature/enterprise-rag`

---

## Project structure

```
enterprise-rag/
├── data/
│   ├── pdfs/                 # 3 policy PDFs (generated)
│   └── csv/                  # employees.csv, leave_records.csv (generated)
├── store/                    # Task 1 output: chunks.jsonl, manifest.json (git-ignored)
├── sample_data.py            # Task 1: creates the sample PDFs and CSVs
├── ingest.py                 # Task 1: ingestion pipeline
├── mock_db.py                # Task 2: mock database + 3 safe tools
├── rag.py                    # Task 2: policy search (RAG)
├── router.py                 # Task 2: router + route/time logging
├── run_tests.py              # Task 2: 8-question test + results table
├── results.md                # Task 2: submission table
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Setup

**Requirements:** Python 3.9 or newer.

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Mac or Linux, activate with `source venv/bin/activate`.

`requirements.txt`:
```
pypdf>=4.3.1
reportlab>=4.2.2
```

Task 1 needs both packages. **Task 2 needs no packages**: it uses only the Python standard library.

---

# Task 1: Multi-Source Ingestion

## What it does

1. **PDF loader:** reads each page and splits the text into chunks (up to 1000 characters, 100 characters of overlap).
2. **CSV loader:** converts each row into one text chunk, for example `employees record: employee_id: 1, name: Employee 1, ...`.
3. **Metadata:** every chunk carries metadata so answers can cite their source.
4. **Incremental hashing:** each file gets a SHA-256 hash stored in `store/manifest.json`. On later runs, files with an unchanged hash are skipped. A changed file has its old chunks removed and is re-ingested.
5. **Summary:** prints a per-source ingestion summary.

## Chunk metadata

| Source | Metadata fields |
|---|---|
| PDF | `source_type`, `source`, `page`, `chunk_index`, `file_hash` |
| CSV | `source_type`, `source`, `row`, `file_hash` |

## Run

```powershell
python sample_data.py
python ingest.py
```

`sample_data.py` creates 3 PDFs (60 pages each, 180 pages total) and 2 CSVs (220 and 200 rows, 420 rows total).

## Expected output (first run)

```
  ingested: code_of_conduct.pdf -> 60 chunks
  ingested: hr_policy.pdf -> 60 chunks
  ingested: leave_policy.pdf -> 60 chunks
  ingested: employees.csv -> 220 chunks
  ingested: leave_records.csv -> 200 chunks

PDF: 3 files, 180 chunks
CSV: 2 files, 420 chunks
Skipped (unchanged): 0 | Time: 0m 1s
```

The chunk counts match the sample data exactly. The time depends on your machine (this pipeline has no embedding step, so it is fast).

## Prove incremental hashing

Run it a second time:

```powershell
python ingest.py
```

```
PDF: 0 files, 0 chunks
CSV: 0 files, 0 chunks
Skipped (unchanged): 5 | Time: 0m 0s
```

To start fresh and repeat the first-run output:

```powershell
Remove-Item -Recurse -Force store
python ingest.py
```

## Output files

| File | Content |
|---|---|
| `store/chunks.jsonl` | All chunks, one JSON object per line (`text` and `metadata`) |
| `store/manifest.json` | `{file name: SHA-256 hash}` used to skip unchanged files |

---

# Task 2: Mock SQL via Function Calling

## What it does

A question is routed to the right data source before it is answered:

| Question type | Example | Route |
|---|---|---|
| Policy | "What is the notice period for resignation?" | **RAG** |
| Specific data | "What is the leave balance of employee 3?" | **SQL** tool |
| Mixed | "What is the sick leave policy and what is the leave balance of employee 2?" | **BOTH** |

```
run_tests.py
   -> setup_db()                      builds the mock database
   -> answer_question()               router.py
        -> classify()                 RAG, SQL or BOTH
        -> search_policy()            rag.py (policy snippets)
        -> run_sql() -> call_tool()   one of 3 whitelisted tools -> mock_db.py
        -> log_route()                appends to route_log.csv
```

## Mock database

Three tables, written in PostgreSQL-compatible SQL. SQLite is used by default so nothing needs to be installed.

| Table | Columns |
|---|---|
| `employees` | `emp_id`, `name`, `department`, `role`, `join_date` |
| `leaves` | `leave_id`, `emp_id`, `leave_type`, `quota`, `used` |
| `payslips` | `payslip_id`, `emp_id`, `pay_month`, `basic`, `hra`, `deductions`, `net_pay` |

The sample data has 10 employees, 30 leave rows and 30 payslips (3 months each: 2026-08, 2026-09, 2026-10).

## The 3 safe tools

| Tool | Purpose |
|---|---|
| `get_leave_balance(emp_id)` | Remaining Annual, Sick and Casual days plus the total |
| `get_payslip(emp_id, month)` | Basic, HRA, deductions and net pay for a month such as `2026-09` |
| `count_employees(department)` | Number of employees in a department (or all employees) |

**Why they are safe:**
- Every query is read-only (`SELECT`).
- Values are passed as parameters (`?`), never joined into the SQL string, which prevents SQL injection.
- Inputs are validated (employee id present, month format `YYYY-MM`).
- `call_tool()` only runs the 3 whitelisted functions. Any other tool name is refused.

## Routing rules

| Policy words found? | Data words found? | Route |
|---|---|---|
| Yes | No | RAG |
| No | Yes | SQL |
| Yes | Yes | BOTH |
| No | No | RAG (default) |

- **Policy words:** policy, rules, guidelines, notice period, allowed, handbook, work from home, dress code.
- **Data words:** balance, payslip, net pay, "how many employees", or a specific employee such as "employee 3".

## Sources printed for each answer

- RAG: `RAG: leave_policy.pdf p.3`
- SQL: `SQL: get_leave_balance() on tables leaves, employees`
- BOTH: both sources, with the answer labeled `[Policy]` and `[Data]`

## Run

```powershell
python run_tests.py
```

This rebuilds the database, runs the 8 test questions (3 policy, 3 data, 2 mixed), prints the route, time, answer and sources for each, then prints the results table and a per-route timing summary.

## Test results

| Question | Route chosen | Correct route (Y/N) | Answer correct (Y/N) |
|---|---|---|---|
| What is the carry forward policy for annual leave? | RAG | Y | Y |
| What is the notice period for resignation? | RAG | Y | Y |
| What is the work from home policy? | RAG | Y | Y |
| What is the leave balance of employee 3? | SQL | Y | Y |
| Show the payslip of employee 5 for 2026-09 | SQL | Y | Y |
| How many employees are in the Engineering department? | SQL | Y | Y |
| What is the sick leave policy and what is the leave balance of employee 2? | BOTH | Y | Y |
| Explain the payslip deduction policy and show the payslip of employee 1 for 2026-09. | BOTH | Y | Y |

"Answer correct" is checked automatically against known values in the mock data (for example, employee 3 has a total leave balance of 28 days).

## Bonus: route and time logging

Every routed question is logged to `route_log.csv`, and `run_tests.py` prints the time taken per question and a summary per route.

`route_log.csv` columns:

| Column | Meaning |
|---|---|
| `timestamp` | When the question was routed |
| `question` | The question text |
| `route` | RAG, SQL or BOTH |
| `tool` | SQL tool used (`-` for RAG only) |
| `sources` | Sources used, separated by ` | ` |
| `time_ms` | Time taken in milliseconds |

Example summary (your numbers will differ by machine):

```
Time per route
Route  Questions    Avg ms  Total ms
RAG            3      0.12      0.35
SQL            3      0.28      0.85
BOTH           2      0.20      0.40
```

`run_tests.py` deletes the old log at the start of each run, so the file always holds exactly the 8 questions from the latest run.

## Optional: use real PostgreSQL

The code supports PostgreSQL through an environment variable. Create an empty database first (`CREATE DATABASE hrdb;`), then:

```powershell
pip install psycopg2-binary
$env:PG_DSN = "dbname=hrdb user=postgres password=YOUR_PASSWORD host=localhost"
python run_tests.py
```

Remove the setting to go back to SQLite:

```powershell
Remove-Item Env:PG_DSN
```

---

## Design notes and limitations

- **Rule-based router:** keyword and regex matching gives the same result on every run and needs no API key. A production system would let an LLM choose the tool through function calling. The tool whitelist and dispatcher (`call_tool`) would stay the same; only `classify()` and `run_sql()` would change.
- **Keyword RAG:** `rag.py` scores 7 built-in policy snippets by keyword overlap. It is not embedding-based, and the snippets are separate from the Task 1 sample PDFs, which contain generic filler text.
- **Mock data:** all employees, leave records and payslips are made-up sample data.
- **Task 1 has no embedding step**, so ingestion time reflects only reading, chunking and hashing.

---

## Git workflow

```powershell
git checkout -b feature/enterprise-rag
# commit each file separately, then:
git push -u origin feature/enterprise-rag
```

Ignored by `.gitignore`: `venv/`, `__pycache__/`, `.env`, `store/`, `mock_hr.db`, `route_log.csv`.