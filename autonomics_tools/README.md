# Autonomics Shell Tools

These scripts provide shell entry points for the existing RedBus Streamlit app and pytest suite. They live separately from the original `scripts/` directory and do not alter the app or its behavior.

Run them from the repository root with Git Bash, Linux Bash, or another Bash shell:

```bash
bash autonomics_tools/start_app.sh
bash autonomics_tools/run_tests.sh
bash autonomics_tools/health_check.sh
```

Each script also locates the repository root relative to itself, so it can be invoked from another working directory when given its path.

## App startup

`start_app.sh` runs `streamlit run app.py` in the foreground. It uses the project virtual environment when available, otherwise `python3` or `python` from `PATH`. It checks for an already healthy Streamlit app before starting and refuses to use a port occupied by a non-healthy service.

The default address is `127.0.0.1:8501`. Override it with:

```bash
STREAMLIT_HOST=127.0.0.1 STREAMLIT_PORT=8502 bash autonomics_tools/start_app.sh
```

Use Ctrl+C in the terminal to stop the app.

## Tests

`run_tests.sh` copies the app, package, data, and existing tests to a temporary directory before running pytest. This keeps test-generated logs and reports out of the working project. The temporary copy is removed when pytest exits. The script prints a PASS or FAIL result and exits with pytest's actual status code. Additional pytest arguments can be appended:

```bash
bash autonomics_tools/run_tests.sh -q
```

The script disables bytecode generation and pytest's cache provider as well, so it does not create cache files in the repository.

## HTTP health check

`health_check.sh` requests Streamlit's `/_stcore/health` endpoint and succeeds only for a 2xx HTTP response. It uses the same default host and port as the startup script; set `STREAMLIT_HOST` and `STREAMLIT_PORT` to match a server started with overrides. A stopped app, unreachable endpoint, or non-2xx response produces a FAIL and non-zero exit status.

## Windows notes

In PowerShell, invoke Git Bash explicitly if it is not on `PATH`:

```powershell
& 'C:\Program Files\Git\bin\bash.exe' -lc './autonomics_tools/run_tests.sh'
```

The scripts use the Python runtime and standard library for HTTP checks; `curl` is not required.
