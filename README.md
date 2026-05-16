# vedisa-crm

CRM Vedisa — Pipeline comercial con drawer IA contextual y proveedores LLM intercambiables.

## Stack

| Capa | Tecnología |
|---|---|
| Frontend | React 18 + TypeScript + Vite |
| UI / Estilos | Tailwind CSS + shadcn/ui |
| Tabla CRM | TanStack Table v8 (server-side) |
| Kanban Pipeline | @hello-pangea/dnd |
| Estado cliente | Zustand + TanStack Query |
| Backend | FastAPI + Python 3.11 |
| Base de datos | PostgreSQL 16 |
| ORM | SQLModel + Alembic |
| IA / LLM | Abstracción multi-proveedor (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter) |
| Auth | JWT + roles |
| Observabilidad IA | OpenTelemetry + tabla audit |

## Estructura del proyecto

```
vedisa-crm/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── crm/          # Endpoints CRM (solicitudes, pipeline, dashboard)
│   │   │   └── ai/           # Endpoints IA (analyze, context, providers)
│   │   ├── core/
│   │   │   ├── config.py     # Settings y variables de entorno
│   │   │   ├── database.py   # Engine + sesión PostgreSQL
│   │   │   └── security.py   # JWT + permisos
│   │   ├── models/
│   │   │   ├── crm.py        # Modelos OLTP: Solicitud, Contacto, Actuacion...
│   │   │   └── ai.py         # Modelos audit: AIRequest, AIResponse...
│   │   ├── schemas/
│   │   │   ├── crm.py        # Pydantic DTOs: SolicitudListItem, SolicitudFront...
│   │   │   └── ai.py         # Pydantic DTOs: LLMRequest, LLMResponse, AIContextBundle
│   │   ├── services/
│   │   │   ├── crm_service.py       # Lógica de negocio CRM
│   │   │   ├── context_builder.py   # Construye AIContextBundle desde BBDD
│   │   │   ├── prompt_service.py    # Plantillas de prompt versionadas
│   │   │   └── llm_router.py        # Router multi-proveedor con fallback
│   │   └── providers/
│   │       ├── base.py          # Protocol LLMProvider
│   │       ├── openai_provider.py
│   │       ├── anthropic_provider.py
│   │       ├── gemini_provider.py
│   │       ├── deepseek_provider.py
│   │       └── gateway_provider.py  # OpenRouter / LiteLLM
│   ├── alembic/              # Migraciones
│   ├── tests/
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppShell.tsx      # Sidebar + Header + zona principal
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   └── FilterBar.tsx     # Filtros con estado en URL
│   │   │   ├── crm/
│   │   │   │   ├── SolicitudesTable.tsx   # TanStack Table server-side
│   │   │   │   ├── PipelineBoard.tsx      # Kanban drag-and-drop
│   │   │   │   ├── SolicitudCard.tsx      # Tarjeta kanban
│   │   │   │   └── SolicitudDetail.tsx    # Detalle expandido
│   │   │   └── ai/
│   │   │       ├── AIDrawer.tsx           # Drawer lateral contextual
│   │   │       ├── AIContextPanel.tsx     # Tabs: Resumen / Riesgos / Acción / Traza
│   │   │       └── AIProviderBadge.tsx    # Badge proveedor activo
│   │   ├── pages/
│   │   │   ├── PipelinePage.tsx
│   │   │   ├── SolicitudesPage.tsx
│   │   │   └── DashboardPage.tsx
│   │   ├── stores/
│   │   │   ├── crmStore.ts      # Zustand: filtros, selección, vista activa
│   │   │   └── aiStore.ts       # Zustand: proveedor activo, historial drawer
│   │   ├── hooks/
│   │   │   ├── useSolicitudes.ts
│   │   │   ├── usePipeline.ts
│   │   │   └── useAIContext.ts
│   │   ├── types/
│   │   │   ├── crm.ts           # SolicitudFront, SolicitudListItem, ObraRef...
│   │   │   └── ai.ts            # AIContextBundle, AIAnalysis, LLMProvider...
│   │   ├── lib/
│   │   │   ├── api.ts           # Cliente HTTP base
│   │   │   └── utils.ts
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── tsconfig.json
└── README.md
```

## Endpoints API

### CRM

```
GET  /crm/solicitudes              Lista server-side con filtros, orden y paginación
GET  /crm/solicitudes/{id}         Ficha completa SolicitudFront
GET  /crm/pipeline                 Columnas + tarjetas para kanban
PATCH /crm/solicitudes/{id}/estado Transición de estado con historial
GET  /crm/dashboard               Snapshot de KPIs y métricas
```

### IA

```
GET  /crm/solicitudes/{id}/context   Contexto CRM para IA (AIContextBundle)
POST /ai/analyze/solicitud           Análisis IA de una solicitud
POST /ai/analyze/list                Análisis IA sobre lista filtrada
GET  /ai/providers                   Proveedores disponibles y estado
POST /ai/providers/test              Test de conectividad por proveedor
```

## Respuesta IA (contrato estable frontend)

```json
{
  "summary": "Solicitud en riesgo por aging > 15 días sin movimiento.",
  "risks": [
    "Sin visita programada con límite en 3 días.",
    "Oferta enviada sin confirmación de recepción."
  ],
  "next_actions": [
    "Llamar al contacto técnico antes del jueves.",
    "Solicitar confirmación de lectura de oferta."
  ],
  "confidence": 0.82,
  "provider": "anthropic/claude-3-5-sonnet",
  "sources": ["crm_context", "timeline", "financials"],
  "latency_ms": 1240,
  "tokens_used": 820
}
```

## Proveedores LLM soportados

| Provider | Modelo por defecto | Fallback |
|---|---|---|
| OpenAI | gpt-4o | gpt-4o-mini |
| Anthropic | claude-3-5-sonnet | claude-3-haiku |
| Gemini | gemini-1.5-pro | gemini-1.5-flash |
| DeepSeek | deepseek-chat | — |
| OpenRouter | configurable | configurable |
| LiteLLM Gateway | cualquier modelo | configurable |

El `LLMRouterService` selecciona proveedor por política: coste, latencia, disponibilidad o tarea. Fallback automático si el proveedor primario falla o supera timeout.

## Variables de entorno

```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/vedisa_crm

# Auth
SECRET_KEY=changeme
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Proveedores LLM
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
DEEPSEEK_API_KEY=
OPENROUTER_API_KEY=
LITELLM_BASE_URL=

# Proveedor primario por defecto
LLM_PRIMARY_PROVIDER=anthropic
LLM_FALLBACK_PROVIDER=openai
LLM_TIMEOUT_SECONDS=30
```

## Arranque rápido

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Roadmap piloto

- [x] Repositorio base y estructura
- [x] Modelos OLTP PostgreSQL (SQLModel: Usuario, Solicitud)
- [x] Auth JWT + roles (login, /me, register admin-only)
- [x] Endpoints CRM (solicitudes, pipeline, dashboard) con PostgreSQL real
- [x] Abstraccion LLM multi-proveedor (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter, LiteLLM)
- [x] Endpoints IA (analyze/solicitud, chat, test, health, providers)
- [x] Frontend: AppShell + Sidebar + FilterBar
- [x] Frontend: TanStack Table server-side (SolicitudesPage)
- [x] Frontend: Kanban Pipeline (PipelineBoard)
- [x] Frontend: Drawer IA contextual (AIDrawer)
- [x] Observabilidad IA (audit log, metricas por proveedor)

---

## Entorno de desarrollo

> **SO**: Windows 10/11  
> **Shell**: PowerShell  
> **Python**: 3.11 (venv local en `backend\.venv`)  
> **Node**: 18+  
> **BD**: PostgreSQL 16 corriendo en local (puerto 5432)  
> **Repo local**: clonar en la ruta deseada, p.ej. `C:\dev\vedisa-crm`

### Pull y arranque (PowerShell)

```powershell
# --- Pull ---
cd C:\dev\vedisa-crm
git pull origin main

# --- Backend (terminal 1) ---
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# --- Frontend (terminal 2) ---
cd ..
cd frontend
npm install
npm run dev
```

### URLs locales

| Servicio | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger docs | http://localhost:8000/docs |
| Frontend | http://localhost:5173 |

### Test rapido de endpoints (PowerShell)

```powershell
# Health
Invoke-RestMethod http://localhost:8000/health

# Register admin
Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/register `
  -ContentType 'application/json' `
  -Body '{"email":"admin@vedisa.com","nombre":"Admin","password":"admin123","rol":"admin"}'

# Login -> guarda token
$r = Invoke-RestMethod -Method Post -Uri http://localhost:8000/auth/login `
  -ContentType 'application/json' `
  -Body '{"email":"admin@vedisa.com","password":"admin123"}'
$token = $r.access_token

# Pipeline
Invoke-RestMethod -Uri http://localhost:8000/crm/pipeline `
  -Headers @{Authorization="Bearer $token"}

# IA metrics
Invoke-RestMethod -Uri http://localhost:8000/ai/metrics `
  -Headers @{Authorization="Bearer $token"}

# IA audit log
Invoke-RestMethod -Uri http://localhost:8000/ai/audit `
  -Headers @{Authorization="Bearer $token"}
```

## Roadmap

### Fase 1 — Core CRM (completado ✅)
- [x] Modelos SQLModel: Solicitud, Contacto, Actuacion, Etapa
- [x] Auth JWT + roles (admin / comercial)
- [x] Endpoints CRUD solicitudes con paginación server-side
- [x] Endpoint pipeline Kanban
- [x] TanStack Table v8 (server-side) en frontend
- [x] PipelineBoard drag & drop (@hello-pangea/dnd)
- [x] AppShell con sidebar + routing React

### Fase 2 — IA Contextual (completado ✅)
- [x] Abstracción multi-proveedor LLM (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter)
- [x] AIContextBundle: carga contexto de solicitud desde BBDD
- [x] Prompt versionado (prompt_service.py)
- [x] Drawer IA contextual en frontend
- [x] Modelo AIAuditLog + servicio ai_audit.py
- [x] Endpoints /ai/audit y /ai/metrics
- [x] OpenTelemetry básico + tabla audit

### Fase 3 — Productización (completado ✅)
- [x] Dashboard KPIs (conversión, tiempo medio, forecast)
- [x] Notificaciones en tiempo real (SSE — `useSSE.ts` hook)
- [x] Exportación CSV / Excel de solicitudes (`openpyxl`)
- [x] Tests E2E — Playwright config + `auth.spec.ts`
- [x] Docker Compose producción (`docker-compose.prod.yml`)
- [x] CI/CD GitHub Actions (`.github/workflows/ci.yml`)
- [[x] Documentación OpenAPI exportada

### Fase 4 — Escala (futuro 🔭)
- [ ] Multi-tenant (organizaciones aisladas)
- [ ] Rate limiting y cuotas por proveedor LLM
- [ ] Caché semántica de respuestas IA (Redis)
- [ ] Fine-tuning de prompts por vertical de negocio
- [ ] SDK cliente TypeScript autogenerado (openapi-typescript)



---

## Changelog

### v0.3.0 — Fase 3 Productización (2025)
- Kanban Pipeline Board con UI estilo Minority Report (`PipelineBoard.tsx`)
- CRUD completo de Solicitudes con drawer lateral (`SolicitudSheet.tsx`) usando `react-hook-form`
- Dashboard KPIs: conversión, tiempo medio, forecast (`/dashboard`)
- Notificaciones en tiempo real SSE (`notifications.py` + `useSSE.ts`)
- Exportación CSV / Excel con `openpyxl` (`/solicitudes/export`)
- Tests E2E Playwright (`e2e/auth.spec.ts`, `playwright.config.ts`)
- Docker Compose producción (`docker-compose.prod.yml`)
- CI/CD GitHub Actions (`.github/workflows/ci.yml`)
- Script exportación OpenAPI (`backend/scripts/export_openapi.py`)

### v0.2.0 — Fase 2 IA Contextual
- Drawer IA contextual multi-proveedor (OpenAI, Anthropic, Gemini, DeepSeek, OpenRouter)
- `AIContextBundle` con carga de contexto de solicitud desde BBDD
- Prompts versionados (`prompt_service.py`)
- Modelo `AIAuditLog` y endpoints `/ai/audit`, `/ai/metrics`
- OpenTelemetry básico

### v0.1.0 — Fase 1 Core CRM
- Modelos SQLModel: Solicitud, Contacto, Actuacion, Etapa
- Auth JWT + roles (admin / comercial)
- Endpoints CRUD solicitudes con paginación server-side
- Endpoint pipeline Kanban
- TanStack Table v8 server-side en frontend
- AppShell con sidebar + routing React
