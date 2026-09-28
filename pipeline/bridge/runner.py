#!/usr/bin/env python3
"""Исполнитель моста MAOS (macOS, нативно).
Ждёт задания в bridge/jobs/*.json и выполняет ТОЛЬКО скрипты конвейера из белого списка. Лог — bridge/logs/.
Задания:
  {"kind": "py", "script": "analyze.py", "args": ["--src", "..."], "timeout": 3600}
  {"kind": "sh", "script": "bridge/render_remotion.sh", "args": ["..."]}
  {"kind": "montage", "args": {...}}   (старый формат)   {"kind": "selftest"}
Сам перезапускается, когда runner.py обновлён (окно Терминала перезапускать не нужно).
Живость: bridge/heartbeat.json каждые ~2 с.
"""
import json, os, subprocess, sys, time, datetime, traceback

HERE = os.path.dirname(os.path.abspath(__file__)); PIPE = os.path.dirname(HERE)
ME = os.path.abspath(__file__); MTIME = os.path.getmtime(ME)
D = {k: os.path.join(HERE, k) for k in ("jobs", "running", "done", "logs")}
for p in D.values():
    os.makedirs(p, exist_ok=True)
PY_OK = {"montage.py", "cut.py", "bridge/selftest.py", "bridge/diag.py", "bridge/lipsync.py", "bridge/refs.py", "bridge/fetch_assets.py", "bridge/avcheck.py", "remotion/sync_fix.py", "bridge/moovinfo.py", "bridge/avsync.py", "bridge/clap.py", "bridge/media.py"}
SH_OK = {"bridge/setup_remotion.sh", "bridge/render_remotion.sh", "bridge/setup_hyperframes.sh", "bridge/render_hf.sh"}
MONTAGE_FLAGS = {"src", "proxy", "name", "plan", "words", "transcribe_only"}

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

def build(job):
    kind = job.get("kind")
    args = [str(a) for a in job.get("args", [])] if isinstance(job.get("args"), list) else []
    if kind == "py":
        s = job.get("script")
        if s not in PY_OK:
            raise ValueError(f"скрипт не разрешён: {s}")
        return [sys.executable, os.path.join(PIPE, s)] + args
    if kind == "sh":
        s = job.get("script")
        if s not in SH_OK:
            raise ValueError(f"скрипт не разрешён: {s}")
        return ["/bin/bash", os.path.join(PIPE, s)] + args
    if kind == "montage":
        argv = [sys.executable, os.path.join(PIPE, "montage.py")]
        for k, v in job.get("args", {}).items():
            if k not in MONTAGE_FLAGS:
                raise ValueError(f"параметр не разрешён: {k}")
            flag = "--" + k.replace("_", "-")
            if v is True:
                argv.append(flag)
            elif v not in (False, None):
                argv += [flag, str(v)]
        return argv
    if kind == "selftest":
        return [sys.executable, os.path.join(HERE, "selftest.py")]
    raise ValueError(f"неизвестный тип задания: {kind}")

def beat(state, job=None):
    tmp = os.path.join(HERE, "heartbeat.tmp")
    json.dump({"alive": now(), "state": state, "job": job, "pid": os.getpid(), "runner": "v3"}, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, os.path.join(HERE, "heartbeat.json"))

def main():
    print(f"[{now()}] Мост MAOS v3 запущен. Задания: {D['jobs']}", flush=True)
    while True:
        beat("idle")
        try:
            if os.path.getmtime(ME) != MTIME:
                print(f"[{now()}] runner.py обновлён — перезапускаюсь", flush=True)
                os.execv(sys.executable, [sys.executable, ME])
        except OSError:
            pass
        jobs = sorted(f for f in os.listdir(D["jobs"]) if f.endswith(".json"))
        for f in jobs:
            jid = f[:-5]; src = os.path.join(D["jobs"], f); run = os.path.join(D["running"], f)
            os.replace(src, run)
            logp = os.path.join(D["logs"], jid + ".log")
            t0 = time.time(); rc = 99
            with open(logp, "w") as log:
                try:
                    job = json.load(open(run))
                    argv = build(job); tmo = float(job.get("timeout", 3600))
                    log.write(f"[{now()}] старт: {' '.join(argv)}\n"); log.flush()
                    print(f"[{now()}] задание {jid}: {job.get('kind')} {job.get('script','')}", flush=True)
                    env = dict(os.environ, PYTHONUNBUFFERED="1", MAOS_PIPE=PIPE)
                    p = subprocess.Popen(argv, cwd=PIPE, stdout=log, stderr=subprocess.STDOUT, env=env)
                    while p.poll() is None:
                        beat("running", jid); time.sleep(2)
                        if time.time() - t0 > tmo:
                            p.kill(); log.write(f"\n[{now()}] превышен лимит времени {tmo:.0f} с — остановлено\n")
                    rc = p.returncode
                except Exception:
                    log.write(traceback.format_exc()); rc = 99
                log.write(f"\n[{now()}] конец, код {rc}, {time.time()-t0:.0f} с\n")
            json.dump({"id": jid, "rc": rc, "finished": now(), "seconds": round(time.time() - t0)},
                      open(os.path.join(D["done"], jid + ".result.json"), "w"), ensure_ascii=False)
            os.replace(run, os.path.join(D["done"], f))
            print(f"[{now()}] задание {jid} готово, код {rc}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    main()
