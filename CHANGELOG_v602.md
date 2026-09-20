# v6.0.2 — Windows Operational Integrity

- Fixed the PyInstaller spec root path; the Windows build now resolves project files from the repository root rather than the `packaging` directory.
- Enforced operational submission lifecycle: authorized API submission requires `APPROVAL_PENDING`; guided browser preparation no longer falsely records the opportunity as `SUBMITTED`.
- Delivery checks the supplied checksum against the actual artifact SHA-256 instead of trusting caller input.
- Delivery and payment recording are transactional; partial operational records are rolled back on failure.
- Tightened provider/source binding and endpoint validation.
- Tightened the operational gate so `execution_ready` requires an approval-pending opportunity with usable evidence.
- Added regression coverage for the Windows/build and operational integrity fixes.

External Internet access, real provider credentials, live source health, real account actions, actual delivery, payment verification, and execution of the final EXE on a Windows host remain external runtime checks.
