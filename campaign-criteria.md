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

  campaign_2_cro_vp_risk:
    name: "Campaign 2 - CRO / VP Risk Outreach"
    sequence_id: null  # Must set after creating sequence in Apollo UI
    mailbox_id: "69a598bdfd80760021e01e93"
    sender: "Sarah Johnson <sarahjohnson@trycaseglide.com>"
    weekly_cap: 500
    titles:
      - "Chief Risk Officer"
      - "VP Risk"
      - "Vice President Risk"
      - "VP of Risk Management"
      - "Vice President of Risk Management"
      - "VP of Risk"
      - "Vice President of Risk"
      - "VP Claims"
      - "Vice President of Claims"
      - "Chief Claims Officer"
    industries:
      - "Insurance"
      - "Financial Services"
      - "Healthcare"
      - "Manufacturing"
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
