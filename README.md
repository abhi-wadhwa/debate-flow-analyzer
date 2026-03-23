# AI Debate Flow Analyzer

AI-powered debate analysis tool that extracts arguments from debate transcripts, generates flow sheets, detects dropped arguments, performs impact calculus, and estimates win probability.

## Features

- **Speech Parsing** -- Automatically segment debate transcripts by speaker/role using format-aware label detection
- **Argument Extraction** -- LLM-based decomposition of speeches into structured arguments (claim / warrant / impact)
- **Flow Sheet Generation** -- Arguments organized in columns by speech, with rebuttal arrows linking responses
- **Dropped Argument Detection** -- Identify arguments the opposing side never responded to, with severity ratings
- **Impact Calculus** -- Assess argument significance across four dimensions: magnitude, timeframe, probability, reversibility
- **Win Probability Estimation** -- Weighted scoring model combining argument coverage, rebuttal quality, dropped arguments, and impact comparison
- **Multi-Format Support** -- Policy/CX, Lincoln-Douglas, and British Parliamentary debate formats

## Quick Start

### Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

### Run the Streamlit UI

```bash
streamlit run src/viz/app.py
```

The web interface includes:
- Transcript input (paste or file upload)
- Flow sheet visualization with colour-coded columns per team
- Dropped argument highlights with severity indicators
- Impact calculus breakdown for each argument
- Win probability gauge with per-side scoring

### Command-Line Interface

```bash
# With a real LLM (requires OPENAI_API_KEY)
python -m src.cli examples/sample_transcript.txt --format policy

# With mock LLM (no API key needed)
python -m src.cli examples/sample_transcript.txt --format policy --mock

# JSON output
python -m src.cli examples/sample_transcript.txt --mock --json
```

### Docker

```bash
docker build -t debate-flow-analyzer .
docker run -p 8501:8501 debate-flow-analyzer
```

## Architecture

### Debate Analysis Pipeline

```
Transcript
    |
    v
[Speech Parser] -- Segments by speaker labels (regex-based)
    |
    v
[Argument Extractor] -- LLM extracts claim/warrant/impact per speech
    |
    v
[Flow Sheet Generator] -- Columns by speech, arrows for rebuttals
    |
    +---> [Dropped Argument Detector] -- Finds unrebutted arguments
    |
    +---> [Impact Calculus] -- LLM scores magnitude/timeframe/probability/reversibility
    |
    v
[Win Probability Estimator] -- Weighted composite of all signals
```

### Argument Structure

Every argument is decomposed into three components following the Toulmin model:

| Component | Description | Example |
|-----------|-------------|---------|
| **Claim** | The central assertion | "Renewable energy creates jobs" |
| **Warrant** | Evidence or reasoning | "Clean energy employs 5x more workers per MW" |
| **Impact** | Consequence or significance | "2 million new jobs by 2035" |

Arguments also carry metadata: a unique ID, the speech label they appeared in, the side (affirmative/negative), optional tags, and a `parent_id` linking rebuttals to the argument they respond to.

### Flow Sheet

A flow sheet is the standard note-taking format in competitive debate. Arguments are arranged in columns (one per speech), read left to right. Rebuttal arrows connect responses to the arguments they address:

```
  1AC              1NC              2AC              2NC
+-----------+   +-----------+   +-----------+   +-----------+
| Econ grows| ->| Debt DA   |   | Subsidies |   | Grid risk |
| with trade|   |           | ->| fund plan |   |           |
+-----------+   +-----------+   +-----------+   +-----------+
| Climate   |   | Fed'lism  |   | Fed coord |   |           |
| action    |   |           | ->| needed    |   |           |
+-----------+   +-----------+   +-----------+   +-----------+
```

### Impact Calculus

Impact calculus evaluates how significant each argument's consequences are across four dimensions:

| Dimension | Scale | Meaning |
|-----------|-------|---------|
| **Magnitude** | 0-10 | How large is the effect? (10 = existential) |
| **Timeframe** | 0-10 | How soon? (10 = immediate) |
| **Probability** | 0-10 | How likely? (10 = certain) |
| **Reversibility** | 0-10 | How irreversible? (10 = permanent) |

The composite score is a weighted average: `0.35 * magnitude + 0.15 * timeframe + 0.30 * probability + 0.20 * reversibility`.

### Win Probability

Win probability is estimated using four weighted signals:

| Signal | Default Weight | Description |
|--------|---------------|-------------|
| Argument coverage | 0.25 | Number of independent arguments raised |
| Rebuttal coverage | 0.20 | Fraction of opponent's arguments responded to |
| Dropped argument penalty | 0.25 | Arguments left unanswered by this side |
| Impact calculus | 0.30 | Average composite impact score |

Weights are configurable in both the CLI and UI.

## Supported Debate Formats

### Policy / Cross-Examination (CX)
- 2 teams of 2 speakers
- 12 speech slots: 4 constructive, 4 cross-examination, 4 rebuttal
- Labels: `1AC`, `CX-1AC`, `1NC`, `CX-1NC`, `2AC`, `CX-2AC`, `2NC`, `CX-2NC`, `1NR`, `1AR`, `2NR`, `2AR`

### Lincoln-Douglas (LD)
- 1-on-1 value debate
- 7 speech slots: 2 constructive, 2 cross-examination, 3 rebuttal
- Labels: `AC`, `CX-AC`, `NC`, `CX-NC`, `1AR`, `NR`, `2AR`

### British Parliamentary (BP)
- 4 teams of 2 speakers
- 8 speech slots
- Labels: `PM`, `LO`, `DPM`, `DLO`, `MG`, `MO`, `GW`, `OW`

## Development

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Lint
make lint

# Format code
make format
```

## Project Structure

```
debate-flow-analyzer/
├── src/
│   ├── core/
│   │   ├── parser.py        # Speech segmentation
│   │   ├── extractor.py     # LLM argument extraction
│   │   ├── flow_sheet.py    # Flow sheet generation
│   │   ├── dropped.py       # Dropped argument detection
│   │   ├── impact.py        # Impact calculus assessment
│   │   ├── win_prob.py      # Win probability estimation
│   │   ├── formats.py       # Debate format definitions
│   │   └── llm_client.py    # LLM API interface + mock
│   ├── viz/
│   │   └── app.py           # Streamlit web interface
│   └── cli.py               # Command-line interface
├── tests/                   # Pytest test suite
├── examples/
│   ├── demo.py              # Demo script
│   └── sample_transcript.txt
├── pyproject.toml
├── Makefile
├── Dockerfile
└── .github/workflows/ci.yml
```

## License

MIT
