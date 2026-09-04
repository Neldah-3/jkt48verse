"""Bootstrap PostgreSQL lokal untuk dev/preview (fallback karena sandbox tidak
bisa TCP ke cloud). Memakai binary Postgres milik paket pip `pgserver`.

Menjalankan:  .venv/bin/python -m scripts.dev_pg
Hasil:        postgres berjalan di 127.0.0.1:5433 (user/pass: postgres/postgres,
              database: jkt48verse). Data di /tmp/jkt48verse-pg (di luar workspace).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

PGDATA = Path("/tmp/jkt48verse-pg2")
PORT = 5433


def bin_dir() -> Path:
    from pgserver._commands import POSTGRES_BIN_PATH

    return Path(POSTGRES_BIN_PATH)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def main() -> None:
    b = bin_dir()
    PGDATA.mkdir(parents=True, exist_ok=True)
    if not (PGDATA / "PG_VERSION").exists():
        r = run([str(b / "initdb"), "-D", str(PGDATA), "-U", "postgres", "--auth=trust"])
        if r.returncode != 0:
            print(r.stderr)
            sys.exit(1)

    # matikan instance lama bila ada
    run([str(b / "pg_ctl"), "-D", str(PGDATA), "stop", "-m", "fast"])

    r = run(
        [
            str(b / "pg_ctl"),
            "-D", str(PGDATA),
            "-o", f"-p {PORT} -c listen_addresses=127.0.0.1 -c unix_socket_directories={PGDATA}",
            "-l", str(PGDATA / "pg.log"),
            "start",
        ]
    )
    if r.returncode != 0:
        print(r.stderr)
        log = (PGDATA / "pg.log")
        if log.exists():
            print(log.read_text()[-2000:])
        sys.exit(1)

    env = {**os.environ, "PGPASSWORD": "postgres"}
    for _ in range(30):
        ok = run([str(b / "pg_isready"), "-h", "127.0.0.1", "-p", str(PORT)], env=env)
        if ok.returncode == 0:
            break
        time.sleep(0.5)

    run(
        [str(b / "psql"), "-h", "127.0.0.1", "-p", str(PORT), "-U", "postgres", "-d", "postgres",
         "-c", "ALTER USER postgres WITH PASSWORD 'postgres';",
         "-c", "CREATE DATABASE jkt48verse;"],
        env=env,
    )
    print(f"Postgres lokal siap: postgresql://postgres:postgres@127.0.0.1:{PORT}/jkt48verse")
    print("Proses ini menjaga server tetap hidup. Ctrl+C untuk berhenti.")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
