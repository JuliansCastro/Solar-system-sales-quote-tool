# Checklist tecnico para reviewers

- [ ] No hay breaking changes en endpoints legacy.
- [ ] Endpoints /api/v1 funcionales y documentados en OpenAPI.
- [ ] Headers de deprecacion presentes en rutas legacy.
- [ ] Servicios desacoplan logica de negocio de las views.
- [ ] Tests unitarios/integracion/contrato ejecutan en CI.
- [ ] Lint y formato en verde (ruff, black, isort).
- [ ] Pipeline build/deploy-staging habilitado.
- [ ] Plan de rollback validado.
- [ ] Benchmarks P95/P99 adjuntos.
