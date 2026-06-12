# Blockchain

Immutable ledger for evidence integrity, audit trails, and verification.

## Components

### Smart Contracts
- Evidence registration contract
- Audit log contract
- Chain-of-custody contract
- Digital signature verification contract

### Evidence Ledger
- Stores SHA-256 hashes of all evidence
- Timestamps for evidence submission
- Chain-of-custody records
- Tamper detection

### Audit Ledger
- FIR creation records
- Status change records
- Access log hashes
- Compliance verification

### Verification Services
- Hash verification API
- Chain-of-custody verification
- Evidence integrity checking
- Audit trail validation

## Technology
- Hyperledger Fabric (primary) or Ethereum (alternative)
- Solidity / Chaincode for smart contracts
- IPFS for large file referencing (optional)

## Purpose
The blockchain layer ensures that evidence and audit records cannot be tampered with by any party, including system administrators. Every piece of evidence has a cryptographic proof of its integrity stored on the blockchain.
