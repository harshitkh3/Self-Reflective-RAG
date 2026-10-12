import os

files = {
    "company/overview.md": """---
id: doc_company_overview
type: organization_profile
title: NexaAI Solutions Overview
founded: 2021
headquarters: Bengaluru, India
headcount: 85+
operating_regions:
  - India
  - Southeast Asia
  - Europe
target_sectors:
  - technology
  - finance
  - healthcare
  - education
related_docs:
  - company/leadership.md
  - products/pricing.md
---

# NexaAI Solutions Pvt. Ltd.

NexaAI Solutions Pvt. Ltd. is an enterprise-focused artificial intelligence company specializing in intelligent knowledge management, operational analytics, and process automation.

## Vision & Mission
- **Vision:** To become a trusted AI partner for organizations through reliable and explainable enterprise AI systems.
- **Mission:** Simplify organizational knowledge access, automate recurring workflows, and enable confident decision-making, emphasizing practical enterprise adoption over experimental research.

## Core Values
- **Customer Obsession:** Address practical business pain points.
- **Transparency:** Clear communication internally and externally.
- **Accountability:** End-to-end outcome ownership.
- **Security First:** Strict enterprise data protection standards.
- **Continuous Improvement:** Rapid, iterative refinement.
""",
    "company/leadership.md": """---
id: doc_company_leadership
type: organization_directory
title: NexaAI Leadership Team
parent_org: company/overview.md
governed_policies:
  - policies/hr_policies.md
  - policies/workplace_conduct.md
---

# Leadership Team

## Executive Profiles

### Aarav Mehta
- **Role:** CEO & Founder
- **Background:** Over a decade leading cloud infrastructure and enterprise data platforms at global consulting firms.

### Riya Kapoor
- **Role:** Chief Technology Officer (CTO)
- **Focus:** Distributed systems and AI platform architectures.

### Kunal Sharma
- **Role:** Head of Product
- **Scope:** Product roadmap across [NexaChat](../products/nexachat.md), [NexaInsight](../products/nexainsight.md), [NexaSupport](../products/nexasupport.md), and [NexaSecure](../products/nexasecure.md).

### Neha Verma
- **Role:** Head of Operations & HR
- **Scope:** Oversight of [HR Policies](../policies/hr_policies.md) and [Leave Regulations](../policies/leave_policy.md).

### Siddharth Rao
- **Role:** Head of Sales & Partnerships
- **Scope:** Enterprise customer acquisition and [Commercial Pricing](../products/pricing.md).
""",
    "policies/hr_policies.md": """---
id: doc_policy_hr
type: governance_policy
title: General HR Policies
department: People Operations
owner: company/leadership.md#neha-verma
applicable_to: all_employees
related_docs:
  - policies/leave_policy.md
  - policies/workplace_conduct.md
---

# Human Resources Framework

NexaAI operates under an inclusive, non-discriminatory, performance-centric organizational framework.

## Standards
- **Equal Opportunity:** Equal consideration across hiring and operational practices without bias.
- **Appraisals:** Bi-annual structured performance reviews.
- **Growth:** Documented career progression milestones.
- **Safety:** Zero-tolerance workplace anti-harassment policy.
""",
    "policies/leave_policy.md": """---
id: doc_policy_leave
type: internal_policy
title: Leave and Time-Off Policy
department: People Operations
owner: company/leadership.md#neha-verma
enforcement: internal_hr
related_docs:
  - policies/hr_policies.md
---

# Leave Policy

Structured allocations to sustain employee work-life balance.

## Allocations Per Annum
- **Annual Leave:** 18 working days
- **Sick Leave:** 10 working days
- **Casual Leave:** 6 working days
- **Maternity Leave:** Aligned with prevailing statutory mandates

## Rollover Rules
- Unused annual leave may roll forward up to a maximum cap of **30 calendar days**.
""",
    "policies/workplace_conduct.md": """---
id: doc_policy_conduct
type: compliance_policy
title: Workplace Conduct & Ethics
department: Legal & People Operations
owner: company/leadership.md#neha-verma
governed_by: products/nexasecure.md
---

# Workplace Ethics & Conduct

Defines obligatory ethical and operational standards for NexaAI staff.

## Code of Conduct
- Maintain strict confidentiality of proprietary company and client data.
- Disclose and prevent business conflicts of interest.
- Prohibit accepting gifts, favors, or financial inducements.
- Maintain compliance with organizational information security protocols.

## Disciplinary Escalation Matrix
Policy breaches result in graduated disciplinary measures:
1. Written formal reprimand
2. Operational suspension
3. Immediate employment termination for severe or willful violations
""",
    "products/nexachat.md": """---
id: doc_prod_nexachat
type: product_specification
title: NexaChat
category: Knowledge Management
tier_availability:
  - Starter
  - Growth
  - Enterprise
integrations:
  - products/nexasecure.md
pricing_reference: products/pricing.md
---

# NexaChat - Internal Knowledge Assistant

NexaChat enables natural-language retrieval over internal documents, technical wikis, policies, and enterprise files with direct citations.

## Capabilities
- Multi-format ingestion: PDFs, presentations, DOCX, and intranet pages.
- Role-based retrieval boundaries for HR, Finance, Engineering, and Sales teams.
- Verifiable inline source attribution with every response.
- Persistent session history and enterprise query auditing.
- Deployment modes: On-premise air-gapped or private/public cloud.
""",
    "products/nexainsight.md": """---
id: doc_prod_nexainsight
type: product_specification
title: NexaInsight
category: Analytics & Business Intelligence
tier_availability:
  - Growth
  - Enterprise
pricing_reference: products/pricing.md
---

# NexaInsight - Business Analytics & Reporting

Conversational querying interface built over structured operational databases and data warehouses.

## Capabilities
- Natural language query translation over SQL/relational schemas.
- Automated KPI aggregation and business trend summaries.
- Automated weekly and monthly reporting schedules.
- One-click exports to Microsoft Excel and PDF formats.
- Role-scoped data views segmented by management level.
""",
    "products/nexasupport.md": """---
id: doc_prod_nexasupport
type: product_specification
title: NexaSupport
category: Customer Automation
tier_availability:
  - Growth
  - Enterprise
pricing_reference: products/pricing.md
---

# NexaSupport - Customer Support Automation

Autonomous tier-1 support engine designed to resolve recurring customer inquiries and route complex issues to human specialists.

## Capabilities
- Automated dynamic FAQ resolution and troubleshooting flows.
- Omnichannel operation across live chat, web portals, and email.
- Confidence-threshold triggered escalation to live service reps.
- Automated ticket metadata tagging and queue prioritization.
- Analytics tracking Mean Time to Resolution (MTTR) and CSAT.
""",
    "products/nexasecure.md": """---
id: doc_prod_nexasecure
type: product_specification
title: NexaSecure
category: AI Governance & Security
tier_availability:
  - Enterprise
enforces_policies:
  - policies/workplace_conduct.md
pricing_reference: products/pricing.md
---

# NexaSecure - AI Governance & Access Control

Governance and security proxy ensuring regulatory compliance, RBAC, and auditing across enterprise model deployments.

## Capabilities
- Granular role-based access control and file-level permission filtering.
- Comprehensive prompt/completion audit trails and real-time query logging.
- Data residency enforcement and compliance controls for regulated industries.
- Policy-driven real-time output sanitization and filtering.
- Native integration with enterprise Identity and Access Management (IAM) systems.
""",
    "products/pricing.md": """---
id: doc_prod_pricing
type: commercial_pricing
title: NexaAI Pricing & Subscription Plans
owner: company/leadership.md#siddharth-rao
products_covered:
  - products/nexachat.md
  - products/nexainsight.md
  - products/nexasupport.md
  - products/nexasecure.md
---

# Pricing & Subscription Plans

Pricing is structured per active seat per month, supplemented by infrastructure tiers.

## Plans

| Tier | Price (User/Month) | Included Modules | Constraints & Infrastructure | Support Level |
| :--- | :--- | :--- | :--- | :--- |
| **Starter** | ₹2,499 | NexaChat (Core features) | Up to 5,000 queries/month; Shared Cloud | Standard Email |
| **Growth** | ₹5,999 | NexaChat, NexaInsight, NexaSupport | Advanced analytics; CRM/Slack/BI integrations | Priority Email & Chat |
| **Enterprise** | Custom | Full suite (includes NexaSecure) | Private Cloud or On-Premise; Custom query volumes | 24x7 SLA + Dedicated CSM |

## Billing Terms
- **Annual Commitment:** 15% overall discount applied to annual contracts.
- **Frequency:** Monthly or annual invoicing schedules.
- **Taxes:** Applicable statutory taxes calculated per local regulatory jurisdictions.
"""
}

base_dir = "nexa-ai-okf"
for path, content in files.items():
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

print(f"OKF bundle successfully generated in ./{base_dir}/")