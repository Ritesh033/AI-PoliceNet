# FIR Service

Manages First Information Reports (FIRs) with tamper-proof records and full audit trail.

## Features
- **FIR Creation**: Digital FIR registration with unique ID and timestamp
- **FIR Verification**: AI-assisted verification and validation
- **FIR Tracking**: Real-time status tracking for all parties
- **FIR Audit**: Complete audit trail (not editable without court order)

## Key Rules
1. FIRs are **immutable** once registered — no officer can edit without court authorization
2. Every status change is logged with timestamp, actor, and reason
3. AI validates FIR details for completeness and consistency
4. False FIR detection triggers independent review
5. Proven false FIRs result in fines for responsible officers

## FIR ID Format
```
FIR-{STATE}-{DISTRICT}-{YEAR}-{SEQUENCE}
Example: FIR-UP-PRY-2026-000456
```

## Port: 8003
