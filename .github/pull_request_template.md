## Summary

Describe the purpose of this PR.

## What Changed

- 

## Why

Explain the problem this PR solves or the improvement it introduces.

## Affected Areas

- [ ] CSV import / parsing
- [ ] Spectrum analysis
- [ ] FFT / Welch behavior
- [ ] Filter preview
- [ ] STM32 C code generation
- [ ] GUI interaction
- [ ] Documentation
- [ ] Tests

## Validation

List the commands or checks you ran.

```powershell
python -m unittest discover -s tests -v
```

## Screenshots / Output

If the PR changes the GUI or generated C code, include screenshots or representative snippets.

## Interface / Compatibility Notes

Please mention if this PR changes:

- public data models in `models.py`
- generated C header/function signatures
- numerical defaults or analysis behavior

## Checklist

- [ ] I reviewed the related docs (`README.md`, `docs/VIBE_CODING.md`)
- [ ] I kept business logic out of the GUI where possible
- [ ] I added or updated tests where behavior changed
- [ ] I verified the generated C code path if the PR touched code generation
