# Campaign Targeting Criteria

# Weekly list build configuration. Parsed by scripts/weekly_list_build.py.
# Edit this file to adjust targeting without touching code.

global_exclusions:
  emails:
    - skiernan@caseglide.com
  names:
    - "Steve Kiernan"
    - "Peter Max Zimmerman"
  bounce_statuses:
    - bounced
    - unsubscribed

# Processing order for weekly_list_build.py — higher tiers claim contacts first
tier_priority:
  - tier_1_f500_legal
  - tier_2_f500_risk
  - tier_3_insurance_leadership
  - tier_5_insurance_litigation
  # tier_4_guidewire intentionally excluded — on hold pending partnership approval

campaigns:
  campaign_1_gc_clo:
    name: "Campaign 1 - GC / CLO Cold Outreach"
    sequence_id: "699deee1299e51000d383130"
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 500
    titles:
      - "General Counsel"
      - "Chief Legal Officer"
      - "Deputy General Counsel"
      - "VP Legal"
      - "Vice President Legal"
      - "VP of Legal"
      - "Vice President of Legal"
      - "VP of Litigation"
      - "Vice President of Litigation"
      - "VP Legal Operations"
      - "Vice President Legal Operations"
      - "Director of Legal Operations"
    industries:
      - "Insurance"
      - "Financial Services"
      - "Healthcare"
      - "Manufacturing"
      - "Retail"
      - "Transportation"
      - "Real Estate"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

  tier_1_f500_legal:
    name: "Tier 1 - F500 Legal (GC / CLO)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "General Counsel"
      - "Chief Legal Officer"
      - "Deputy General Counsel"
      - "VP Legal Operations"
      - "Vice President Legal Operations"
      - "VP of Legal Operations"
    min_employees: 10000
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

  tier_2_f500_risk:
    name: "Tier 2 - F500 Risk (CRO / VP Risk)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Risk Officer"
      - "VP Risk Management"
      - "Vice President of Risk Management"
      - "VP of Risk"
      - "Vice President of Risk"
      - "VP Litigation"
      - "Vice President of Litigation"
      - "VP of Litigation"
    min_employees: 10000
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

  tier_3_insurance_leadership:
    name: "Tier 3 - Insurance Leadership (CEO / CFO / COO)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Executive Officer"
      - "CEO"
      - "Chief Financial Officer"
      - "CFO"
      - "Chief Operating Officer"
      - "COO"
      - "General Counsel"
      - "Chief Legal Officer"
      - "Chief Claims Officer"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

  tier_4_guidewire:
    name: "Tier 4 - Guidewire Ecosystem (ON HOLD)"
    sequence_id: null  # DO NOT SET — on hold pending Guidewire partnership approval
    enabled: false
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "Chief Information Officer"
      - "VP Information Technology"
      - "Vice President of IT"
      - "VP of IT"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

  tier_5_insurance_litigation:
    name: "Tier 5 - Insurance Litigation (VP Litigation)"
    sequence_id: null  # Set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 125
    titles:
      - "VP Litigation"
      - "Vice President of Litigation"
      - "VP of Litigation Management"
      - "Vice President Litigation Management"
      - "Director of Litigation"
    industries:
      - "Insurance"
    min_employees: 500
    contact_email_status:
      - "verified"
    person_locations:
      - "United States"

target_titles:
  # Used by legacy_list_audit.py for filtering legacy contacts
  - "General Counsel"
  - "Chief Legal Officer"
  - "Deputy General Counsel"
  - "VP Legal"
  - "Chief Risk Officer"
  - "VP Risk"
  - "VP Claims"
  - "Chief Claims Officer"
  - "VP of Litigation"
  - "Director of Legal Operations"
  - "VP Legal Operations"
