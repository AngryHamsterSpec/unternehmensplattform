"""Synthetisches, vollständig editierbares Unternehmensszenario."""

from typing import Any


def demo_scenario() -> dict[str, Any]:
    return {
        "name": "Musterwerk: Büro und Zusammenarbeit",
        "company_profile": {
            "industry": "IT-Dienstleistungen",
            "employee_count": 35,
            "it_staff_fte": "2",
            "monthly_budget": "12000",
            "initial_budget": "20000",
            "currency": "EUR",
        },
        "workloads": [
            {
                "workload_key": "office",
                "name": "Dokumente und Zusammenarbeit",
                "workload_type": "BUSINESS_APP",
                "user_count": 35,
                "vcpu_count": "4",
                "memory_gib": "16",
                "storage_gib": "250",
                "max_latency_ms": "80",
                "availability_percent": "99.5",
                "rto_seconds": 14400,
                "rpo_seconds": 3600,
                "sensitivity": "INTERNAL",
                "internet_dependency_allowed": True,
            }
        ],
        "infrastructure_assets": [],
        "requirements": {"region": "EU", "hard_budget": False},
    }
