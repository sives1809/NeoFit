# AI Fitness Frontend — Build Plan (v2)

Frontend-only React + TypeScript + Tailwind app (TanStack Start template — Lovable's Next.js-equivalent). Backend live at `http://127.0.0.1:8000`, API prefix `/api/v1`. No fake backend, no mock server.

## Design language
- Premium dark futuristic fitness SaaS
- Neon green primary accent (`#00FF94`) on near-black canvas (`#07090C`)
- Glassmorphism: backdrop-blur, subtle white-alpha borders, soft neon glow shadows
- Space Grotesk headings, Inter body, JetBrains Mono for numeric/data
- Mobile-first responsive: sticky bottom nav on mobile, sidebar on desktop
- Subtle motion (fade/slide on mount, neon pulse on active states)

## Pages & routes
| Route | Purpose |
|---|---|
| `/` | Landing — public |
| `/login` | Login form (UI + state, no backend POST) |
| `/signup` | Signup form (UI + state, no backend POST) |
| `/dashboard` | Latest measurements, diet snapshot, prediction, recent sessions |
| `/measure` | Webcam stage + MediaPipe-ready capture/combine/reset workflow |
| `/diet` | Diet plan + refresh |
| `/history` | Sessions list with detail drawer + delete |
| `/reminders` | Client-side CRUD via localStorage |
| `/profile` | View / create / update profile |

Authed routes guarded; missing/invalid JWT → redirect to `/login`. After login, `GET /auth/profile-check` decides redirect to `/profile` (first-time) or `/dashboard`.

## Auth (corrected)
Backend exposes only `GET /auth/me` and `GET /auth/profile-check` — no login/signup POST endpoints exist. To avoid fake hardcoded endpoints:

- **Swappable auth service abstraction**: `src/lib/auth/auth-service.ts` exports an `AuthService` interface (`login`, `signup`, `logout`, `getToken`).
- **Default implementation**: `MockAuthAdapter` — clearly isolated, lives in `src/lib/auth/mock-adapter.ts`, generates a local-only dev token so navigation flow works end-to-end. Marked with prominent `// MOCK ADAPTER — replace when backend login/signup ships` banner.
- **Swap path**: when backend ships `/auth/login` + `/auth/signup`, create `HttpAuthAdapter` implementing the same interface and change one import in `src/lib/auth/index.ts`.
- JWT stored in `localStorage.fit_token`, attached as `Authorization: Bearer <token>` by the API client interceptor.
- `GET /auth/me` and `GET /auth/profile-check` ARE wired against the real backend.
- Zustand store holds `{ token, user, status }`; 401 from any real endpoint clears token and redirects.

## API integration
- `src/lib/api/client.ts` — fetch wrapper, hardcoded base `http://127.0.0.1:8000/api/v1`
- Request interceptor: attach `Authorization` header if token present
- Response interceptor: on 401 clear token + redirect to `/login`
- Typed resource modules: `auth.ts`, `measure.ts`, `sessions.ts`, `profile.ts`, `diet.ts`, `predict.ts`, `validate.ts`
- React Query for caching / mutations

## Measurement page (corrected)
Backend does NOT accept image uploads. Payload contract:
```json
{
  "height_cm": 175,
  "landmarks": [{ "x": 0, "y": 0, "z": 0, "visibility": 0.9 }]
}
```

UI/architecture:
- **WebcamStage** component: `<video>` getUserMedia preview + `<canvas>` overlay placeholder labeled "MediaPipe Pose landmarks render here".
- **HUD overlay**: live readout slots for landmark count, FPS, capture state — wired to a `useLandmarkSource()` hook that currently returns empty/dummy landmarks shaped like the real MediaPipe output.
- **Height input** (cm) — required before capture.
- **Capture workflow buttons**:
  - `Capture frame` → `POST /measure/frame` with `{ height_cm, landmarks }` from `useLandmarkSource`
  - `Combine` → `POST /measure/combine`
  - `Reset` → `POST /measure/reset`
- **Results panel**: neon stat tiles for measurements returned by `/combine`.
- **MediaPipe TODO block**: clearly marked spot in `useLandmarkSource()` where `@mediapipe/tasks-vision` PoseLandmarker will be initialized and stream landmarks. No MediaPipe code shipped yet — just the seam.
- No image bytes ever sent to the backend.

## Reminders
Pure client-side CRUD persisted to `localStorage` (`fit_reminders` key). No backend calls. Easy to swap to a real endpoint later.

## File structure
```text
src/
  routes/
    __root.tsx
    index.tsx                 # landing
    login.tsx, signup.tsx
    _app.tsx                  # auth-guarded layout shell
    _app/dashboard.tsx
    _app/measure.tsx
    _app/diet.tsx
    _app/history.tsx
    _app/reminders.tsx
    _app/profile.tsx
  lib/
    api/client.ts
    api/{auth,measure,sessions,profile,diet,predict,validate}.ts
    auth/auth-service.ts      # interface
    auth/mock-adapter.ts      # isolated dev-only login/signup
    auth/index.ts             # picks adapter
    auth/store.ts             # zustand: token, user, status
    reminders/store.ts        # localStorage CRUD
    measure/use-landmark-source.ts  # MediaPipe seam
  components/
    layout/{Sidebar,Topbar,MobileNav,AppShell}.tsx
    ui/{GlassCard,NeonButton,StatTile,Spinner,EmptyState,Input}.tsx
    measure/{WebcamStage,MeasurementHUD,ResultsPanel}.tsx
  index.css                   # tokens + glass utilities
```

## Out of scope
- No backend code, no MSW, no fake `/auth/login` HTTP endpoint
- No real MediaPipe wiring (placeholder + typed seam only)
- No payments, no Lovable Cloud

## Deliverable
Exportable codebase. `npm install && npm run dev`. Expects FastAPI at `127.0.0.1:8000`.

## Final correction (approved)
- Capture / Combine buttons are **disabled** until MediaPipe is wired.
- WebcamStage shows a clean "MediaPipe integration pending" placeholder badge.
- No dummy landmark payloads are ever POSTed to `/measure/*`.
- Reset stays enabled (safe no-op against backend state).
