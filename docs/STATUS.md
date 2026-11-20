## 2026-11-20 — AI demo cloud deployment preparation

### Backend improvements

- Verified the fictional RAG backend using the live OpenAI provider with `gpt-5-mini`.
- Increased the supported maximum completion token limit from 1000 to 3000 while retaining the default of 400.
- Verified a successful enrollment-related answer with trusted document citations.
- Observed abstention responses for unsupported questions.
- Improved database readiness validation and safe failure handling.
- Standardized the local AI backend port to 8001.
- Preserved document eligibility, source revalidation, and bounded answer validation safeguards.

### Deployment configuration

- Added `start-ai.sh` for Linux-based cloud deployment.
- Configured fictional database initialization before starting the FastAPI server.
- Configured the backend to use the hosting provider's assigned `PORT`.
- Added `.gitattributes` to enforce LF line endings for the startup script.
- Verified executable Git permissions (`100755`) for the startup script.
- Added `requirements-test.txt` to separate testing dependencies from runtime requirements.
- Updated the GitHub Actions workflow to install the declared testing dependencies.
- Fixed Alembic logging configuration to preserve existing application loggers.

### Local verification before main integration

| Verification | Result |
|---|---|
| Python unittest | 124 passed |
| Pytest | 124 passed |
| Pytest subtests | 212 passed |
| Failed Python tests | 0 |
| Skipped Python tests | 0 |
| Deprecation warnings | 6 |
| Frontend proxy tests | 7 passed |
| ESLint | Passed |
| TypeScript validation | Passed |
| Next.js production build | Passed |
| Python dependency check | Passed |

Local frontend verification used Node.js 24.14.0 and npm 11.9.0. The production build succeeded with a non-blocking multiple-lockfile warning. Actual Linux CI execution remains unverified.

### Repository integration

- Created the dedicated deployment branch `feature/ai-demo-deployment`.
- Created deployment checkpoint commit `fc6cb4f`.
- Preserved a local backup branch `backup/ai-demo-deployment-pre-merge`.
- Confirmed that the previous AI retrieval milestone was merged into main through PR #28.
- Initiated integration with remote main at commit `b5f6e8e`.
- Source changes merged automatically; the documentation conflict is being reconciled while preserving previous engineering checkpoints.

### Remaining tasks

- Complete the main branch integration.
- Install incoming authentication dependencies.
- Rerun the expanded backend and frontend regression suites.
- Verify access controls, rate limits, and spending safeguards for the fictional AI endpoint.
- Push the deployment branch and verify GitHub Actions.
- Deploy the fictional AI backend to Render.
- Configure the Vercel frontend integration.
- Perform online end-to-end verification.

### Known limitations

The AI assistant remains a fictional demonstration, not a production-ready university information system. Live multi-part answer completeness, semantic relevance, paraphrase retrieval robustness, and public deployment security require further verification. Pre-merge test results do not establish the correctness of the integrated authentication baseline.