# pipeline — конвейер монтажа MAOS

Как работать: навык **montazh-rolika** и проектный документ «Монтаж — правила и конвейер». Карта папок и правила хранения — `Личный бренд/Навигация.md`.

- `montage.py` — расшифровка (GigaAM), ревью дублей, база (рез по кадрам, кадр, цвет, звук, темп), таймлайн для графики.
- `remotion/` — графика и субтитры (Reel.tsx, Blocks.tsx, Cartoon.tsx), `build_props.py`, `sync_fix.py`.
- `bridge/` — мост: задания `bridge/jobs/*.json` выполняет `runner.py` (запуск: «Запустить мост.command»).
- `assets/` — шрифты, звуки (Kenney CC0), HyperFrames, музыка под ролик.
- `models/` — GigaAM, YuNet. `config.json` — настройки.
- `reels/output/`, `plans/` — только рабочие файлы текущего ролика; итог — в `Личный бренд/Ролики/…`.
