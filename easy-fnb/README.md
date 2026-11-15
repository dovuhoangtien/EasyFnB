# easy-fnb: web app and server

The part of [Easy FnB](../README.md) that staff and owners actually use, plus the server behind it.

| Folder | What it is |
|---|---|
| `src/` | React 19 + TypeScript web app: owner dashboard (`/`), assistant (`/tro-ly`), shift report (`/ca`), settings (`/cai-dat`), staff phone app (`/nv/<id>`), phone-as-camera page (`/phat`) |
| `server/` | FastAPI server: receives camera events, assigns tasks, verifies images with Gemini, stores the timeline, serves the built web app |
| `server/tests/` | Unit tests, no network or API key needed |
| `server/du_lieu_demo/` | Bundled demo data and face-blurred clips, copied in on first start |
| `deploy/`, `Dockerfile` | Container image for Cloud Run |

## Run

```
chay_may_chu.bat
```

First run installs everything and builds the web app, then serves `http://localhost:8080`. Set `DEMO_LIVE=1` beforehand to replay the demo clips as a live camera.

While working on the UI, run `npm run dev` (port 5173, proxies `/api` to 8080).

## Test and check

```
.venv\Scripts\python -m unittest discover -s server/tests -t . -v
npx tsc -b --noEmit
npm run lint
```

## More

- Full run guide (Vietnamese): [HUONG_DAN.md](HUONG_DAN.md)
- HTTP API: [server/API.md](server/API.md)
- Configuration: [.env.example](.env.example)
