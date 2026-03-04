# Plan: Implement Steps 2, 3, 4, 6

Date: 2026-03-03

## Scope
Implement requested actions from prior recommendation:
1. Step 2: ATS throughput sweep execution capability and run
2. Step 3: Follow-up debt handling execution workflow
3. Step 4: Deferred drift handling + concrete state updates
4. Step 6: Extensibility stack
   - daily_pipeline_health.py
   - multi-operator governance fields + workflow
   - CI rubric validation + ID-map generation
   - outcome-risk classifier integrated into preflight

## Execution Order
1. Add command passthrough in run.py so commands can receive flags.
2. Implement governance primitives (review metadata + submission metadata + review gate).
3. Implement rubric validation and ID map autogeneration.
4. Implement risk model script and preflight integration.
5. Add daily pipeline health script and run command binding.
6. Add/adjust tests.
7. Run targeted test suites.
8. Execute ops commands for steps 2, 3, 4 and apply needed YAML updates.
