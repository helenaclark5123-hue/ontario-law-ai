"""Where to go next: official bodies and free legal help in Ontario.

Every name, link and phone number here was checked on the organization's own
official website on November 23, 2026. These are fixed lists, not written by
the AI, so the assistant can't invent a body or a link. Re-check them
from time to time: government web addresses change.
"""

# ---- Next steps, by Act -----------------------------------------------------
# (name, what people can do there, link)
LTB = ("Landlord and Tenant Board", "Resolves disputes between landlords and tenants.",
       "https://tribunalsontario.ca/ltb/")
ESA_CLAIM = ("Employment standards claim (Ministry of Labour)",
             "Workers can file a claim if they believe the Employment Standards Act is being broken.",
             "https://www.ontario.ca/document/your-guide-employment-standards-act-0/filing-claim")
SAFETY = ("Workplace health and safety complaint (Ministry of Labour)",
          "Workers can file a complaint about unsafe conditions, or harassment or violence at work.",
          "https://www.ontario.ca/page/filing-workplace-health-and-safety-complaint")
CONSUMER = ("Consumer Protection Ontario complaint",
            "People can file a complaint against a business, including collection agencies and payday lenders.",
            "https://www.ontario.ca/page/filing-consumer-complaint")
SMALL_CLAIMS = ("Small Claims Court", "People can sue for money or property worth $50,000 or less.",
                "https://www.ontario.ca/page/suing-someone-small-claims-court")
HRTO = ("Human Rights Tribunal of Ontario", "Resolves claims of discrimination and harassment under the Human Rights Code.",
        "https://tribunalsontario.ca/hrto/")
HRLSC = ("Human Rights Legal Support Centre", "Free legal help with Human Rights Code claims.",
         "https://www.hrlsc.on.ca/")
WSIB = ("Workplace Safety and Insurance Board (WSIB)", "Workers report a work injury or illness and claim benefits.",
        "https://www.wsib.ca/")
SBT = ("Social Benefits Tribunal", "People can appeal Ontario Works or ODSP decisions about eligibility or amounts.",
       "https://tribunalsontario.ca/sbt/")
CAT = ("Condominium Authority Tribunal", "Resolves many condo disputes online.",
       "https://www.condoauthorityontario.ca/tribunal/")
CCB = ("Consent and Capacity Board", "Holds hearings about consent to treatment, capacity and involuntary admission.",
       "https://www.ccboard.on.ca/")
IPC = ("Information and Privacy Commissioner of Ontario", "People can file a complaint about access to or privacy of health records.",
       "https://www.ipc.on.ca/en/privacy-individuals/filing-a-privacy-complaint")
CFSRB = ("Child and Family Services Review Board",
         "Hears certain complaints about children's aid societies, foster placements and school expulsions.",
         "https://tribunalsontario.ca/cfsrb/")
LTC = ("Long-Term Care Family Support and Action Line", "Concerns about a long-term care home: 1-866-434-0144 (toll free).",
       "https://www.ontario.ca/page/long-term-care-home-complaint-process")
TICKETS = ("Provincial offences tickets", "Check a ticket, see your options, or request a meeting to resolve it.",
           "https://www.ontario.ca/page/check-status-traffic-tickets-and-fines-online-or-request-meeting-resolve-your-case")
FLIC = ("Family Law Information Centres", "Free information about separation, children, child protection and court.",
        "https://www.ontario.ca/page/family-law-information-centres")

NEXT_STEPS = {
    "Residential Tenancies Act, 2006": [LTB],
    "Employment Standards Act, 2000": [ESA_CLAIM, SMALL_CLAIMS],
    "Occupational Health and Safety Act": [SAFETY],
    "Workplace Safety and Insurance Act, 1997": [WSIB],
    "Consumer Protection Act, 2002": [CONSUMER, SMALL_CLAIMS],
    "Payday Loans Act, 2008": [CONSUMER],
    "Collection and Debt Settlement Services Act": [CONSUMER],
    "Human Rights Code": [HRTO, HRLSC],
    "Ontario Works Act, 1997": [SBT],
    "Ontario Disability Support Program Act, 1997": [SBT],
    "Condominium Act, 1998": [CAT],
    "Health Care Consent Act, 1996": [CCB],
    "Mental Health Act": [CCB],
    "Personal Health Information Protection Act, 2004": [IPC],
    "Child, Youth and Family Services Act, 2017": [CFSRB, FLIC],
    "Fixing Long-Term Care Act, 2021": [LTC],
    "Highway Traffic Act": [TICKETS],
    "Provincial Offences Act": [TICKETS],
    "Courts of Justice Act": [SMALL_CLAIMS],
    "Family Law Act": [FLIC],
    "Children's Law Reform Act": [FLIC],
}

# Acts where we always suggest talking to a professional (family and custody).
FAMILY_ACTS = {"Family Law Act", "Children's Law Reform Act", "Child, Youth and Family Services Act, 2017"}

# ---- Free and low-cost legal help ------------------------------------------
# (name, what it offers, link, phone or "")
FREE_HELP = [
    ("Legal Aid Ontario", "May pay for a lawyer if you qualify (based on income and assets). Help in 300+ languages.",
     "https://www.legalaid.on.ca/", "1-800-668-8258"),
    ("Community legal clinics", "Free legal information, advice or representation, generally for people with low income. "
     "Find the clinic near you.", "https://www.legalaid.on.ca/legal-clinics/", ""),
    ("Steps to Justice", "Free, plain-language answers to common legal problems in Ontario, from CLEO.",
     "https://stepstojustice.ca/", ""),
    ("CLEO (Community Legal Education Ontario)", "Free, plain-language legal information.", "https://www.cleo.on.ca/", ""),
    ("Pro Bono Ontario Free Legal Advice Hotline", "Free legal advice for civil problems like housing, work and consumer "
     "issues. Monday to Friday, 9 a.m. to 5 p.m.", "https://www.probonoontario.org/", "1-855-255-7256"),
    ("Law Society Referral Service", "Connects you with a lawyer or paralegal for a free consultation of up to 30 minutes.",
     "https://lso.ca/public-resources/finding-a-lawyer-or-paralegal/law-society-referral-service", ""),
    ("JusticeNet", "Lawyers, paralegals and mediators with reduced fees for people who earn too much for legal aid.",
     "https://justicenet.ca/", ""),
    ("Student legal clinics", "Free help from supervised law students at Ontario's seven law schools, including Osgoode "
     "(CLASP), U of T (Downtown Legal Services) and Queen's (Queen's Legal Aid).",
     "https://www.legalaid.on.ca/student-legal-service-organizations/", ""),
]

# ---- Talk to a professional ---------------------------------------------------
LAO_CRIMINAL = ("Legal Aid Ontario: criminal charges", "https://www.legalaid.on.ca/services/criminal-legal-issues/")
DUTY_COUNSEL = ("Duty counsel: free lawyers at the courthouse", "https://www.legalaid.on.ca/duty-counsel/")
LAO_IMMIGRATION = ("Legal Aid Ontario: refugee and immigration help",
                   "https://www.legalaid.on.ca/services/help-with-immigration-or-refugee-problems/")
LAO = ("Legal Aid Ontario", "https://www.legalaid.on.ca/")
CLINICS = ("Find a community legal clinic", "https://www.legalaid.on.ca/legal-clinics/")
LSRS = ("Law Society Referral Service (free 30-minute consultation)",
        "https://lso.ca/public-resources/finding-a-lawyer-or-paralegal/law-society-referral-service")

ESCALATION = {
    "criminal": ("Criminal charges can have serious consequences.", [LAO_CRIMINAL, DUTY_COUNSEL]),
    "court_date": ("You mentioned a court date or hearing that's already set.", [DUTY_COUNSEL, CLINICS, LSRS]),
    "immigration": ("Immigration and refugee matters are federal law, which The Bridge doesn't cover, and the stakes "
                    "are high.", [LAO_IMMIGRATION, CLINICS]),
    "family": ("Family and custody matters depend a lot on the details of your situation.",
               [(FLIC[0], FLIC[2]), LAO, LSRS]),
    "uncertain": ("The Bridge gave different answers when it asked itself this question several times, so it may be "
                  "unsure.", [CLINICS, LSRS]),
}
