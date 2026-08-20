# Repository Guidance

## Commands

- Run commands from the repository root.
- Install runtime dependencies with `pip install -r requirements.txt`; install
  `requirements-dev.txt` before running tests, ngrok, training or data collection.
- Start the app with `python -m streamlit run app.py --server.port 8501`; on Windows, `run.bat` prefers `.venv311` and enables UTF-8.
- Start a temporary phone-accessible HTTPS tunnel with `python run_ngrok.py` or `run_ngrok.bat`; it requires `NGROK_AUTHTOKEN` in `.env` and must never print or commit the token.
- Run the release gate with `python -m pytest -q`; it includes pure logic, five-page AppTest rendering and the real Baseline B model fixture. The `live` LLM test is skipped unless `RUN_LIVE_LLM_TEST=1` is set.
- Use `python test_imports.py` only as a smaller smoke check; it now exits non-zero when any check fails.
- There is no configured linter, formatter, type checker, CI workflow or pre-commit hook.

## Architecture

- This is one Streamlit multipage app: `app.py` is the landing page, pages 1-3 own analysis/history/profile, and `pages/4_Danh_gia_mo_hinh.py` renders the frozen A0/A/B benchmark.
- `models/detector.py` wraps YOLO; `utils/nutrition.py`, `utils/llm.py`, `utils/images.py`, `utils/history.py`, and `utils/visualization.py` contain the non-UI logic. Shared UI styling lives in `assets/style.css` and is loaded separately by every page.
- Shared session-state defaults live in `utils/state.py`. Update that source when changing profile fields or cross-page state.

## Data Contracts

- Food class IDs must match across `config.FOOD_CLASSES`, the config display maps, keys in `data/nutrition_db.json`, class names in `training/dataset.yaml`, and collection queries in `training/data_collection.py`. The detector reports an error rather than silently dropping an unmapped model label.
- Vietnamese gender, activity, and goal labels are executable lookup keys in `utils/nutrition.py`. Keep page options and defaults exact; unknown activity and goal strings silently fall back to sedentary/maintenance behavior.
- Preserve Vietnamese accents in user-facing text and data.

## Runtime Files

- The app does not require secrets for local UI work. Without an LLM key it returns sample advice; `.env` supports `GEMINI_API_KEY`, `GOOGLE_MODEL`, `OPENAI_API_KEY`, and `LLM_PROVIDER=google|openai`. Google-hosted Gemini and Gemma models use the same Google GenAI adapter.
- Production inference uses `models/weights/best_baseline_B.pt` and validates SHA-256 plus the exact 12-label checkpoint contract. Randomized demo detections are disabled unless `ENABLE_RANDOM_DEMO=true` is explicitly set.
- Guest mode is the default and stores the profile and meal history only in Streamlit session state, cleared when the browser session ends. Never persist them to a server-side JSON file.
- Cloud sync is opt-in: the user presses "Bật đồng bộ" on the profile page, which calls `utils.repository.enable_sync()` to create a Supabase anonymous account and upload existing session data. `link_identity()` then upgrades it to Google without changing `user_id` (verified against the live project). Pages go through `get_repository()` and must not branch on auth state themselves.
- Nothing may construct a Supabase client just by rendering a page: `tests/test_pages.py` asserts every page stays guest-only, which is what keeps the release gate offline. `utils.auth` functions take `get_client().auth`; repositories take `get_client()`. See `STORAGE_PLAN.md` for the required Supabase settings (Anonymous sign-ins, Manual Linking, Redirect URLs).
- Never read cookies through `st.context.cookies`: it is always empty on Streamlit Community Cloud, which silently broke every persisted session. Go through `utils/cookies.py`, and treat `cookies_ready() == False` as "unknown", never as "no session" — `app.py` renders the cookie component once per run before anything reads it.
- A cookie write is only a request to write: `manager.set()` renders an iframe whose JS runs after the script ends, so an `st.rerun()` in the same run cancels it. `utils/cookies.py` therefore queues writes and replays them from `init_cookie_manager()` until the browser confirms — do not bypass it, and keep any new write going through `write_cookie()`/`delete_cookie()`.
- `datasets/`, `runs/`, and `models/weights/*.pt` are generated or large artifacts and are gitignored.

## Training

- `python training/data_collection.py --food <class-or-all> --count <n>` performs network scraping and writes under `datasets/raw/`; do not run it as a routine check.
- Default `python training/train.py` downloads from Roboflow, but `ROBOFLOW_WORKSPACE`, `ROBOFLOW_PROJECT`, and `ROBOFLOW_VERSION` are source placeholders and `ROBOFLOW_API_KEY` is required even though it is absent from `.env.example`.
- Train an existing dataset with `python training/train.py --skip-download --yaml <path/to/data.yaml>`; this script is a reference pipeline and must not overwrite the benchmark-selected production checkpoint without an explicit promotion decision.
- Evaluate only with `python training/train.py --skip-download --eval-only --yaml <path/to/data.yaml>`. Omitting `--skip-download` ignores `--yaml` and attempts a Roboflow download.
- Training defaults to CUDA device `0`; batch size, device, epochs, and Roboflow identifiers are module constants rather than CLI options.

## Safety

- Do not add or run root-wide cleanup/rename scripts as routine formatting or verification; they can recursively rewrite source, data, notebooks, and reports.
