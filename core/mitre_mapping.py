"""Hardcoded MITRE ATLAS / NIST CSF threat signatures for dangerous agent actions."""

from typing import Any, Dict, List

# Each signature matches on action_type + target (case-insensitive substring or exact).
# Framework tags are best-effort, approximate mappings (not an official crosswalk) and can be refined here.
DANGEROUS_SIGNATURES: List[Dict[str, Any]] = [
    {
        "action_type": "EXECUTE",
        "target": "rm -rf /",
        "match": "exact",
        "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
        "NIST_CSF": "PR.AC-4 (Access Control)",
        "description": "Destructive filesystem wipe attempt",
    },
    {
        "action_type": "EXECUTE",
        "target": "format c:",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0048 (External Denial of Service)",
        "NIST_CSF": "PR.DS-1 (Data-at-Rest Protection)",
        "description": "Disk format / data destruction",
    },
    {
        "action_type": "EXECUTE",
        "target": "powershell -enc",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0010 (AI Supply Chain Compromise)",
        "NIST_CSF": "PR.AC-3 (Remote Access)",
        "description": "Encoded PowerShell execution",
    },
    {
        "action_type": "EXECUTE",
        "target": "cmd.exe /c del",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
        "NIST_CSF": "PR.AC-4 (Access Control)",
        "description": "Bulk delete via command shell",
    },
    {
        "action_type": "WRITE",
        "target": "/etc/passwd",
        "match": "exact",
        "MITRE_ATLAS": "AML.T0015 (Evade ML Model)",
        "NIST_CSF": "PR.AC-4 (Access Control)",
        "description": "Unauthorized credential store modification",
    },
    {
        "action_type": "WRITE",
        "target": "/etc/shadow",
        "match": "exact",
        "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
        "NIST_CSF": "PR.AC-1 (Identity Management)",
        "description": "Shadow password file write",
    },
    {
        "action_type": "WRITE",
        "target": "authorized_keys",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
        "NIST_CSF": "PR.AC-3 (Remote Access)",
        "description": "SSH authorized_keys tampering",
    },
    {
        "action_type": "NETWORK",
        "target": "0.0.0.0/0",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0024 (Exfiltration via AI Inference API)",
        "NIST_CSF": "PR.DS-2 (Data-in-Transit Protection)",
        "description": "Unrestricted network egress",
    },
    {
        "action_type": "NETWORK",
        "target": "pastebin.com",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0024 (Exfiltration via AI Inference API)",
        "NIST_CSF": "DE.CM-1 (Network Monitoring)",
        "description": "Suspected data exfiltration endpoint",
    },
    {
        "action_type": "NETWORK",
        "target": "metadata.google.internal",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0012 (Valid Accounts)",
        "NIST_CSF": "PR.AC-5 (Network Integrity)",
        "description": "Cloud metadata service access",
    },
    {
        "action_type": "READ",
        "target": "/etc/shadow",
        "match": "exact",
        "MITRE_ATLAS": "AML.T0006 (Active Scanning)",
        "NIST_CSF": "PR.AC-4 (Access Control)",
        "description": "Sensitive credential file read",
    },
    {
        "action_type": "READ",
        "target": ".aws/credentials",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0006 (Active Scanning)",
        "NIST_CSF": "PR.AC-1 (Identity Management)",
        "description": "Cloud credential harvesting",
    },
    {
        "action_type": "READ",
        "target": "id_rsa",
        "match": "contains",
        "MITRE_ATLAS": "AML.T0006 (Active Scanning)",
        "NIST_CSF": "PR.AC-1 (Identity Management)",
        "description": "Private key file access",
    },
]


def match_threat(action_type: str, target: str) -> Dict[str, Any] | None:
    """Return the first matching threat signature, or None if the action is clean."""
    action_type_norm = (action_type or "").upper()
    target_norm = (target or "").strip().lower()

    for sig in DANGEROUS_SIGNATURES:
        if sig["action_type"].upper() != action_type_norm:
            continue

        sig_target = sig["target"].lower()
        match_mode = sig.get("match", "exact")

        if match_mode == "exact" and target_norm == sig_target:
            return sig
        if match_mode == "contains" and sig_target in target_norm:
            return sig

    return None
