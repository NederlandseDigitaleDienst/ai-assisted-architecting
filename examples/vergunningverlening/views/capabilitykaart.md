<!-- Gegenereerd door `archi render` — niet handmatig bewerken -->

# Capabilitykaart

```mermaid
flowchart TD
  accTitle: Capabilitykaart
  n1["Vergunningverlening"]
  n2["Aanvraag ontvangen"]
  n3["Toetsen aan regels"]
  n4["Besluit bekendmaken"]
  n5["Toezicht en handhaving"]
  n6["Snellere doorlooptijd"]
  n1 --o n2
  n1 --o n3
  n1 --o n4
  n1 --o n5
  n1 -.->|"draagt bij aan"| n6
  n3 -.->|"draagt bij aan"| n6
  classDef motivation fill:#CECBF6,stroke:#7F77DD,color:#26215C
  class n6 motivation
  classDef strategy fill:#FAC75A,stroke:#D4882A,color:#633806
  class n1,n2,n3,n4,n5 strategy
```

*Gegenereerd uit `vergunningverlening.archimate` — pijlstijlen: `--o` bevat (aggregatie/compositie), `-.->` gestippeld (beïnvloedt/realiseert), `-->` overig.*
